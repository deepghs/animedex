"""
Raw response envelope for ``animedex api`` and credential redaction.

The :class:`RawResponse` envelope carries everything a caller needs
to debug an HTTP exchange: the request that was actually sent (with
credentials fingerprint-redacted), the redirect chain, the final
response (status + headers + body bytes + decoded text), per-call
timing, cache provenance, and a legacy local-rejection record for
requests that never left the host.

Credential redaction follows the convention from #3 §5.0: keep the
first 4 + last 4 characters + length, redact the middle. The token
owner can recognise *which* token they are looking at (length differs,
suffixes differ) but the value is unusable to anyone with only the
redacted dump. Headers whose name matches a credential pattern are
processed; values keeping a leading scheme word (``Bearer``,
``Basic``, ``Token``) get the scheme preserved.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import field_serializer, field_validator, model_validator

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


_FINGERPRINT_MIN_LENGTH = 24


def redact_credential_value(value: str) -> str:
    """Fingerprint-redact a single credential string.

    Behaviour:

    * Length below :data:`_FINGERPRINT_MIN_LENGTH` (24) →
      ``"<redacted len=N>"``.
    * Otherwise → ``"<first4>...<last4> (len=N)"``.

    The threshold is set so a fingerprinted token has at least 16
    unrevealed characters in the middle (16⁴ ≈ 65k for hex / 64⁴ ≈
    16M for base64url is brute-forceable; 16¹⁶ ≈ 10¹⁹ / 64¹⁶ ≈ 10²⁹
    is not). The legitimate token owner can still match the dump
    back to the credential by length and suffix.

    :param value: The raw credential string.
    :type value: str
    :return: A redacted form safe to print or paste.
    :rtype: str
    """
    if len(value) < _FINGERPRINT_MIN_LENGTH:
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
                    have been, on a local reject).
    :vartype request: RawRequest
    :ivar redirects: Ordered list of 3xx hops; empty when the
                      response was direct.
    :vartype redirects: list[RawRedirectHop]
    :ivar status: Final HTTP status code; ``0`` indicates a local
                   rejection before the request left the host.
    :vartype status: int
    :ivar response_headers: Response headers from the final hop;
                             empty on local reject.
    :vartype response_headers: dict[str, str]
    :ivar body_bytes: Raw response body bytes; empty on local
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
                               for local pre-request rejection metadata,
                               currently unknown-backend envelopes;
                               ``None`` otherwise.
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

    @field_serializer("body_bytes", when_used="json")
    def _serialize_body_bytes(self, value: bytes) -> str:
        """Serialise bytes as base64 in JSON output.

        Pydantic v2's default bytes serialiser attempts ``.decode('utf-8')``
        first, which raises :class:`UnicodeDecodeError` on any binary
        body (image bytes, gzip slipping through, CDN binary error
        pages). The renderer in :mod:`animedex.render.raw` promises
        base64 for non-UTF-8 bodies; that promise is honoured here, at
        the model level, so every JSON dump path (CLI ``--debug``,
        cache write, JSON-renderer pipeline) gets the same safe output.

        :param value: Raw response bytes.
        :type value: bytes
        :return: Base64-encoded ASCII string.
        :rtype: str
        """
        return base64.b64encode(value).decode("ascii")

    @field_validator("body_bytes", mode="before")
    @classmethod
    def _deserialize_body_bytes(cls, value):
        """Symmetric deserialiser: decode base64 strings back to bytes.

        Pairs with :meth:`_serialize_body_bytes` so that
        ``model_validate_json(model_dump_json())`` round-trips the
        bytes verbatim. When the input is already ``bytes`` (e.g.
        constructed in Python), it passes through unchanged.

        :param value: Raw bytes (Python construction) or a base64-
                       encoded ASCII string (JSON decode).
        :type value: bytes or str
        :return: Bytes ready for storage.
        :rtype: bytes
        """
        if isinstance(value, str):
            return base64.b64decode(value)
        return value

    @model_validator(mode="after")
    def _check_body_text_matches_bytes(self) -> "RawResponse":
        """Pin the ``body_text`` / ``body_bytes`` invariant ().

        The two fields must agree: either ``body_text`` is the UTF-8
        decode of ``body_bytes``, or ``body_text`` is ``None`` (because
        the bytes are not valid UTF-8). Anything else means the live-
        call path and the cache-hit reconstruction path have drifted
        from a single source of truth. Locking the invariant in the
        model itself catches the drift at construction, before the
        envelope reaches a renderer or the cache.

        :raises ValueError: When ``body_text`` and ``body_bytes`` are
                             inconsistent.
        :return: ``self`` unchanged on success.
        :rtype: RawResponse
        """
        try:
            decoded: Optional[str] = self.body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded = None
        if self.body_text != decoded:
            raise ValueError(
                "body_text must equal body_bytes.decode('utf-8') when the bytes are valid "
                "UTF-8, and must be None otherwise; "
                f"got body_text={self.body_text!r}, "
                f"expected={decoded!r}"
            )
        return self


def selftest() -> bool:
    """Smoke-test the envelope and the redaction helpers.

    :return: ``True`` on success.
    :rtype: bool
    """

    # Redaction
    assert redact_credential_value("abc") == "<redacted len=3>"
    # Use a 30-char token so the fingerprint form fires (threshold is 24).
    sample = "abcd1234567890XYZabcd1234XYZ99"
    assert redact_credential_value(sample) == f"{sample[:4]}...{sample[-4:]} (len={len(sample)})"
    out = redact_headers({"Authorization": f"Bearer {sample}", "User-Agent": "x"})
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
