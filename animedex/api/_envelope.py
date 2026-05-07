"""
Raw response envelope for ``animedex api`` and credential redaction.

The :class:`RawResponse` envelope carries everything a caller needs
to debug an HTTP exchange: the request that was actually sent (with
credentials fingerprint-redacted), the redirect chain, the final
response (status + headers + body bytes + decoded text), per-call
timing, cache provenance, and a firewall-rejection record when the
read-only middleware (:mod:`animedex.transport.read_only`) blocked
the request before it left the host.

Credential redaction follows the convention from #3 §5.0: keep the
first 4 + last 4 characters + length, redact the middle. The token
owner can recognise *which* token they are looking at (length differs,
suffixes differ) but the value is unusable to anyone with only the
redacted dump. Headers whose name matches a credential pattern are
processed; values keeping a leading scheme word (``Bearer``,
``Basic``, ``Token``) get the scheme preserved.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

from animedex.models.common import AnimedexModel


_CREDENTIAL_NAME_PATTERN = re.compile(r"(?i)(auth|cookie|api[_-]?key|token|secret)")
_SCHEME_PREFIXES = ("Bearer", "Basic", "Token", "Digest")

# Backend-specific credential header names that do not match the regex
# above. Add new entries lowercase here; the check below is
# case-insensitive.
_KNOWN_CREDENTIAL_HEADERS = frozenset(
    {
        "x-trace-key",  # Trace.moe Patreon / Sponsor key
        "x-mal-client-id",  # MAL official API
        "x-rapidapi-key",  # RapidAPI gateway key (legacy backends)
    }
)


def _is_credential_header(name: str) -> bool:
    """Return ``True`` if ``name`` should have its value redacted.

    :param name: Header name as received.
    :type name: str
    :return: Whether the header is treated as carrying a credential.
    :rtype: bool
    """
    if _CREDENTIAL_NAME_PATTERN.search(name):
        return True
    return name.lower() in _KNOWN_CREDENTIAL_HEADERS


def redact_credential_value(value: str) -> str:
    """Fingerprint-redact a single credential string.

    Behaviour:

    * Length zero or below 12 → ``"<redacted len=N>"``.
    * Otherwise → ``"<first4>...<last4> (len=N)"``.

    The length cap is set so an attacker cannot trivially brute-force
    a short token from its redacted form, but the legitimate token
    owner can still match the dump back to the credential by suffix.

    :param value: The raw credential string.
    :type value: str
    :return: A redacted form safe to print or paste.
    :rtype: str
    """
    if len(value) < 12:
        return f"<redacted len={len(value)}>"
    return f"{value[:4]}...{value[-4:]} (len={len(value)})"


def _redact_with_optional_scheme(value: str) -> str:
    """Redact a header value while preserving a leading auth scheme word.

    ``"Bearer eyJ..."`` becomes ``"Bearer eyJ0...XXXX (len=N)"``.
    A value with no recognised scheme is redacted whole.

    :param value: Original header value.
    :type value: str
    :return: Redacted header value.
    :rtype: str
    """
    parts = value.split(" ", 1)
    if len(parts) == 2 and parts[0] in _SCHEME_PREFIXES:
        scheme, secret = parts
        return f"{scheme} {redact_credential_value(secret)}"
    return redact_credential_value(value)


def _redact_cookie_value(value: str) -> str:
    """Redact each ``key=value`` pair in a Cookie / Set-Cookie style string.

    :param value: Cookie header value.
    :type value: str
    :return: Cookie value with each pair's value individually
             redacted.
    :rtype: str
    """
    out_pairs: List[str] = []
    for pair in value.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        if "=" in pair:
            key, secret = pair.split("=", 1)
            out_pairs.append(f"{key}={redact_credential_value(secret)}")
        else:
            out_pairs.append(redact_credential_value(pair))
    return "; ".join(out_pairs)


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of ``headers`` with credential values redacted.

    A header is treated as carrying a credential when its name matches
    the case-insensitive regex
    ``(auth|cookie|api[_-]?key|token|secret)``. Cookie-style values
    have each ``key=value`` pair redacted independently; auth-style
    values preserve a leading scheme word (``Bearer`` / ``Basic`` /
    ``Token`` / ``Digest``).

    :param headers: Source headers.
    :type headers: dict
    :return: New dict with the same keys and credential values
             redacted; non-credential headers unchanged.
    :rtype: dict
    """
    out: Dict[str, str] = {}
    for name, value in headers.items():
        if not _is_credential_header(name):
            out[name] = value
            continue
        if name.lower() in ("cookie", "set-cookie"):
            out[name] = _redact_cookie_value(value)
        else:
            out[name] = _redact_with_optional_scheme(value)
    return out


class RawRequest(AnimedexModel):
    """Snapshot of the request that was (or would have been) sent.

    Stored verbatim except that credential headers are pre-redacted
    when this object lands in a :class:`RawResponse`. Body is captured
    as ``body_preview`` (first 4 KiB) to keep envelope size bounded;
    callers needing the full request body should rely on the cache or
    on their own logging.

    :ivar method: HTTP method, upper-cased.
    :vartype method: str
    :ivar url: Final URL after path-join.
    :vartype url: str
    :ivar headers: Outgoing headers; credentials are redacted.
    :vartype headers: dict[str, str]
    :ivar body_preview: First 4 KiB of the request body, or ``None``.
    :vartype body_preview: str or None
    """

    method: str
    url: str
    headers: Dict[str, str]
    body_preview: Optional[str] = None


class RawRedirectHop(AnimedexModel):
    """One hop in a 3xx redirect chain.

    :ivar status: 301 / 302 / 303 / 307 / 308.
    :vartype status: int
    :ivar headers: Response headers from this hop.
    :vartype headers: dict[str, str]
    :ivar from_url: URL the request was issued against.
    :vartype from_url: str
    :ivar to_url: ``Location:`` header value.
    :vartype to_url: str
    :ivar elapsed_ms: Elapsed time for this hop, in milliseconds.
    :vartype elapsed_ms: float
    """

    status: int
    headers: Dict[str, str]
    from_url: str
    to_url: str
    elapsed_ms: float


class RawTiming(AnimedexModel):
    """Per-call timing breakdown.

    :ivar total_ms: Wall-clock time from
                     :func:`animedex.api._dispatch.call` entry to
                     return; includes everything below.
    :vartype total_ms: float
    :ivar rate_limit_wait_ms: Time spent waiting for a TokenBucket
                                slot before the request was allowed
                                to start.
    :vartype rate_limit_wait_ms: float
    :ivar request_ms: Wall-clock time of the actual on-the-wire HTTP
                       transaction including any redirect hops.
    :vartype request_ms: float
    """

    total_ms: float
    rate_limit_wait_ms: float
    request_ms: float


class RawCacheInfo(AnimedexModel):
    """Provenance of the response with respect to the local SQLite cache.

    :ivar hit: ``True`` when the response was reconstructed from the
                local cache and no live HTTP request was issued.
    :vartype hit: bool
    :ivar key: ``(backend, signature)`` digest used to look up the
                row.
    :vartype key: str or None
    :ivar ttl_remaining_s: Seconds remaining before the cached row
                            expires; only set on a cache hit.
    :vartype ttl_remaining_s: int or None
    :ivar fetched_at: Timestamp at which the cached row was originally
                       fetched from the upstream.
    :vartype fetched_at: datetime or None
    """

    hit: bool
    key: Optional[str] = None
    ttl_remaining_s: Optional[int] = None
    fetched_at: Optional[datetime] = None


class RawResponse(AnimedexModel):
    """Full envelope a CLI render mode operates on.

    :ivar backend: Backend identifier (e.g. ``"anilist"``).
    :vartype backend: str
    :ivar request: Snapshot of the request that was issued (or would
                    have been, on a firewall reject).
    :vartype request: RawRequest
    :ivar redirects: Ordered list of 3xx hops; empty when the
                      response was direct.
    :vartype redirects: list[RawRedirectHop]
    :ivar status: Final HTTP status code; ``0`` indicates the
                   firewall rejected the request before it left the
                   host.
    :vartype status: int
    :ivar response_headers: Response headers from the final hop;
                             empty on firewall reject.
    :vartype response_headers: dict[str, str]
    :ivar body_bytes: Raw response body bytes; empty on firewall
                       reject. ``--debug`` mode emits this base64-
                       encoded.
    :vartype body_bytes: bytes
    :ivar body_text: ``body_bytes.decode("utf-8")`` when valid; else
                      ``None``.
    :vartype body_text: str or None
    :ivar body_truncated_at_bytes: Set only when ``--debug`` truncated
                                     the body for display.
    :vartype body_truncated_at_bytes: int or None
    :ivar timing: Per-call timing breakdown.
    :vartype timing: RawTiming
    :ivar cache: Cache provenance.
    :vartype cache: RawCacheInfo
    :ivar firewall_rejected: ``{"reason": "...", "message": "..."}``
                               when the read-only firewall blocked the
                               request; ``None`` otherwise.
    :vartype firewall_rejected: dict[str, str] or None
    """

    backend: str
    request: RawRequest
    redirects: List[RawRedirectHop] = []
    status: int
    response_headers: Dict[str, str]
    body_bytes: bytes
    body_text: Optional[str]
    body_truncated_at_bytes: Optional[int] = None
    timing: RawTiming
    cache: RawCacheInfo
    firewall_rejected: Optional[Dict[str, str]] = None


def selftest() -> bool:
    """Smoke-test the envelope and the redaction helpers.

    :return: ``True`` on success.
    :rtype: bool
    """

    # Redaction
    assert redact_credential_value("abc") == "<redacted len=3>"
    assert (
        redact_credential_value("abcd1234567890XYZ12") == "abcd...XYZ12 (len=" + str(len("abcd1234567890XYZ12")) + ")"
    )
    out = redact_headers({"Authorization": "Bearer abcd1234567890XYZ12", "User-Agent": "x"})
    assert out["Authorization"].startswith("Bearer abcd")
    assert out["User-Agent"] == "x"

    # Envelope round-trip
    r = RawResponse(
        backend="_selftest",
        request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
        status=200,
        response_headers={},
        body_bytes=b"",
        body_text="",
        timing=RawTiming(total_ms=0, rate_limit_wait_ms=0, request_ms=0),
        cache=RawCacheInfo(hit=False),
    )
    RawResponse.model_validate_json(r.model_dump_json())
    return True
