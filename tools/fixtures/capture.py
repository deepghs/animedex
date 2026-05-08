"""
Fixture capture tool for the the substrate API layer ``animedex api`` test suite.

Each captured fixture is a single YAML file at
``test/fixtures/<backend>/<path-slug>/<NN>-<label>.yaml``. YAML
chosen over JSON for readability: response bodies that are
JSON-shaped get persisted as native YAML dicts (so a PR diff shows
the structure, not a quoted JSON string), and text bodies (ANN's
XML) use literal block scalars so newlines are preserved verbatim.

Fixture shape::

    metadata:
      captured_at: "2026-05-07T..."
      label: "Frieren - finished TV show"
      backend: jikan
      path_slug: anime_by_id
    request:
      method: GET
      url: https://api.jikan.moe/v4/anime/52991
      headers: {User-Agent: animedex/0.0.1}
      params: null
      json_body: null
      raw_body_b64: null
    response:
      status: 200
      headers: {content-type: application/json, ...}
      body_json: {data: {mal_id: 52991, ...}}    # when parseable JSON
      body_text: null                              # set for non-JSON text
      body_b64: null                               # set for binary

Replay (in unit tests, see :mod:`tools.fixtures.replay`):

* ``body_json`` set -> mock with that dict (re-serialized to bytes by
  the responses library).
* ``body_text`` set -> mock with that text encoded as UTF-8.
* ``body_b64`` set -> mock with the decoded raw bytes.

The capture tool is invoked from per-backend scripts under
``tools/fixtures/run_<backend>.py`` which configure rate-limit pacing
for each upstream.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = PROJECT_ROOT / "test" / "fixtures"


# Headers that may carry the captor's identity, network position, or
# host-side fingerprints. These get a fixed placeholder before the
# fixture is committed (). Add new entries lowercase here;
# the matcher is case-insensitive. The list deliberately stays
# narrow: it matches the "do not commit *to git*" set, not every
# possible PII vector. Wider stripping happens at runtime in the
# dispatcher's redact_headers ().
_HEADERS_TO_SCRUB_AT_CAPTURE = frozenset(
    {
        # Identity / network-position headers.
        "set-cookie",
        "x-forwarded-for",
        "x-real-ip",
        "cf-connecting-ip",
        "via",
        # Cloudflare bookkeeping. These carry opaque per-request
        # tokens which often embed IPs and request fingerprints. They
        # are noisy in PR diffs and offer nothing the test layer
        # depends on; scrub wholesale.
        "content-security-policy-report-only",
        "report-to",
        "nel",
        "cf-ray",
        "cf-mitigated",
    }
)
_SCRUB_PLACEHOLDER = "<scrubbed-at-capture>"


def _redact_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of ``headers`` with credential values redacted.

    Mirrors :func:`animedex.api._envelope.redact_headers` but is
    duplicated here so the capture tool stays importable without a
    runtime dependency on the dispatcher package layout.

    Used at fixture-write time so an authenticated capture script
    that passes ``Authorization: Bearer <token>`` does not leak the
    token into the YAML committed to git. See for the
    runtime equivalent on the dispatcher side.
    """
    from animedex.api._envelope import redact_headers as _redact

    return _redact(dict(headers or {}))


_PLACEHOLDER_IPV4 = "203.0.113.42"  # RFC-5737 TEST-NET-3
_IPV4_PATTERN = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def _is_public_ipv4(text: str) -> bool:
    """Return ``True`` if ``text`` parses as an IPv4 address that is
    public (i.e. not private, loopback, link-local, or in the RFC-5737
    documentation ranges).

    :param text: Candidate dotted-quad string.
    :type text: str
    :return: Whether the string is a public IPv4.
    :rtype: bool
    """
    try:
        addr = ipaddress.IPv4Address(text)
    except (ipaddress.AddressValueError, ValueError):
        return False
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return False
    if (
        addr in ipaddress.IPv4Network("192.0.2.0/24")
        or addr in ipaddress.IPv4Network("198.51.100.0/24")
        or addr in ipaddress.IPv4Network("203.0.113.0/24")
    ):
        return False
    return True


def replace_public_ips_with_placeholder(text: str, placeholder: str = _PLACEHOLDER_IPV4) -> str:
    """Replace every public IPv4 address in ``text`` with ``placeholder``.

    Per : hard-coding a list of "known captor IPs" leaks
    those very IPs into the script that scrubs them. Instead, walk
    the text generically: anything that looks like a public IPv4 is
    replaced with the RFC-5737 documentation address. Private,
    loopback, link-local, and RFC-5737-reserved addresses are left
    intact - they are documentation/test markers and carry no
    real-world identity.

    Used both at capture time (response body scan) and by
    :mod:`tools.fixtures.scrub_existing` (bulk back-fill of older
    fixtures captured before this scrub landed).

    :param text: Source string.
    :type text: str
    :param placeholder: Replacement IP address.
    :type placeholder: str
    :return: ``text`` with every public IPv4 replaced.
    :rtype: str
    """

    def _sub(match):
        candidate = match.group(1)
        return placeholder if _is_public_ipv4(candidate) else candidate

    return _IPV4_PATTERN.sub(_sub, text)


def scrub_capture_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of ``headers`` with capture-time-sensitive values
    replaced by :data:`_SCRUB_PLACEHOLDER`.

    Per : Shikimori's DDoS-Guard ``Set-Cookie: __ddg9_=<ip>``
    embeds the captor's egress IP in the response; persisting that to
    git history leaks the contributor's home or CI IP forever. The
    same risk exists for ``X-Forwarded-For``, ``X-Real-IP``,
    ``CF-Connecting-IP``, and ``Via`` echoes from intermediate proxies.

    The original ``headers`` dict is not mutated; the call returns a
    fresh dict.

    :param headers: Response headers as captured.
    :type headers: dict[str, str]
    :return: New dict with sensitive values replaced.
    :rtype: dict[str, str]
    """
    out: Dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() in _HEADERS_TO_SCRUB_AT_CAPTURE:
            out[name] = _SCRUB_PLACEHOLDER
        else:
            out[name] = value
    return out


# Configure PyYAML so long string scalars are emitted in literal-block
# form (with leading "|") rather than folded - that preserves XML and
# multi-line text bodies verbatim and reads cleanly in PR diffs.
def _str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_representer)


def slugify(text: str) -> str:
    """Convert a free-form label to a filesystem-safe slug.

    :param text: The input label.
    :type text: str
    :return: A lowercase slug containing only alnum + ``-`` + ``_``.
    :rtype: str
    """
    safe = []
    for ch in text.lower():
        if ch.isalnum() or ch in ("-", "_"):
            safe.append(ch)
        elif ch in (" ", "/", ".", ":", "+"):
            safe.append("_")
    return "".join(safe).strip("_") or "fixture"


def _scrub_public_ips_in_obj(obj: Any) -> Any:
    """Recursively walk a YAML-shaped value and replace public IPv4
    addresses inside any string with the documentation placeholder.

    Used by :func:`_classify_body` to scrub body fields at capture
    time (). Lists and dicts are walked structurally; ints,
    floats, booleans, and ``None`` pass through unchanged.

    :param obj: Object to walk.
    :type obj: Any
    :return: A structurally identical object with strings scrubbed.
    :rtype: Any
    """
    if isinstance(obj, str):
        return replace_public_ips_with_placeholder(obj)
    if isinstance(obj, list):
        return [_scrub_public_ips_in_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub_public_ips_in_obj(v) for k, v in obj.items()}
    return obj


def _classify_body(body_bytes: bytes, content_type: str) -> Dict[str, Any]:
    """Decide which of body_json / body_text / body_b64 to populate.

    JSON-parseable responses become ``body_json`` (a native YAML dict)
    so PR diffs read like data, not strings. Text-but-not-JSON
    responses become ``body_text`` (preserving newlines via literal
    block scalar). Anything else falls through to ``body_b64``.

    Public IPv4 addresses anywhere in the body get replaced with the
    RFC-5737 documentation placeholder () so a captor's IP
    does not leak through endpoints like Trace.moe ``/me`` or any
    upstream that echoes the caller's address in the body.

    :param body_bytes: Raw response body.
    :type body_bytes: bytes
    :param content_type: Value of the ``Content-Type`` header.
    :type content_type: str
    :return: Mapping with exactly one of ``body_json`` / ``body_text``
             / ``body_b64`` set; the other two are ``None``.
    :rtype: dict
    """
    out = {"body_json": None, "body_text": None, "body_b64": None}
    if not body_bytes:
        out["body_text"] = ""
        return out

    # Try JSON first; many backends serve JSON without setting a strict
    # Content-Type, so do not gate on the header alone.
    try:
        decoded = body_bytes.decode("utf-8")
        try:
            parsed = json.loads(decoded)
            out["body_json"] = _scrub_public_ips_in_obj(parsed)
            return out
        except json.JSONDecodeError:
            pass
        # Plain text (XML for ANN, HTML for some Cloudflare challenges).
        out["body_text"] = replace_public_ips_with_placeholder(decoded)
        return out
    except UnicodeDecodeError:
        # Binary content - we cannot scrub safely without changing the
        # bytes shape. Persisting verbatim is acceptable: the inputs
        # we capture as binary are images, and our binary fixtures
        # are intentionally tiny (Trace.moe accepts 4-byte sentinels).
        out["body_b64"] = base64.b64encode(body_bytes).decode("ascii")
        return out


def capture(
    *,
    backend: str,
    path_slug: str,
    label: str,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    raw_body: Optional[bytes] = None,
    timeout: float = 30.0,
    pace_seconds: float = 1.0,
    overwrite: bool = False,
) -> Path:
    """Issue one request, persist the (request, response) pair as YAML.

    Numbering is monotonic per ``(backend, path_slug)`` directory: the
    new file is named ``NN-<label-slug>.yaml`` where ``NN`` is one
    greater than the highest existing 2-digit prefix.

    :param backend: Backend identifier (e.g. ``"jikan"``); first
                     directory level under ``test/fixtures``.
    :type backend: str
    :param path_slug: Sub-directory name describing the endpoint
                       family (e.g. ``"anime_by_id"``).
    :type path_slug: str
    :param label: Free-form short name used to disambiguate this
                   fixture from peers in the same path slug.
    :type label: str
    :param method: HTTP method.
    :type method: str
    :param url: Full URL.
    :type url: str
    :param headers: Outgoing headers; if ``User-Agent`` is missing,
                     ``animedex/0.0.1`` is injected.
    :type headers: dict or None
    :param params: Query parameters.
    :type params: dict or None
    :param json_body: JSON body for POST.
    :type json_body: Any or None
    :param raw_body: Raw byte body (mutually exclusive with
                      ``json_body``).
    :type raw_body: bytes or None
    :param timeout: Request timeout.
    :type timeout: float
    :param pace_seconds: Sleep before issuing this call (use for
                          per-backend rate-limit pacing). Defaults to
                          ``1.0`` (): a forgotten pace value
                          should *not* flood an upstream. Per-backend
                          scripts should explicitly raise this for
                          slower upstreams (ANN, MangaDex At-Home);
                          they may lower it if the upstream is known
                          to tolerate higher rates and the contributor
                          confirmed it before merging.
    :type pace_seconds: float
    :param overwrite: When ``False`` (default), an existing fixture
                       with the same path is left alone and the file
                       path is returned unchanged.
    :type overwrite: bool
    :return: Filesystem path of the persisted fixture.
    :rtype: pathlib.Path
    """
    backend_dir = FIXTURES_ROOT / backend / path_slug
    backend_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(backend_dir.glob("*.yaml"))
    label_slug = slugify(label)

    # Idempotent re-run: if a fixture with this label already exists,
    # return its path unchanged (do not re-hit upstream and do not
    # produce a duplicate-numbered sibling).
    label_matches = [p for p in existing if p.stem.split("-", 1)[1] == label_slug]
    if label_matches and not overwrite:
        return label_matches[0]

    next_idx = len(existing) + 1
    out_path = backend_dir / f"{next_idx:02d}-{label_slug}.yaml"

    if pace_seconds > 0:
        time.sleep(pace_seconds)

    out_headers = dict(headers or {})
    out_headers.setdefault("User-Agent", "animedex/0.0.1")

    response = requests.request(
        method,
        url,
        headers=out_headers,
        params=params,
        json=json_body,
        data=raw_body,
        timeout=timeout,
    )

    body_classification = _classify_body(response.content, response.headers.get("Content-Type", ""))

    fixture = {
        "metadata": {
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "label": label,
            "backend": backend,
            "path_slug": path_slug,
        },
        "request": {
            "method": method.upper(),
            "url": url,
            # Scrub credential headers (Authorization, Cookie, X-Api-
            # Key, X-Trace-Key, ...) before persisting. Without this
            # an authenticated capture script that passes ``Authorization:
            # Bearer <token>`` through ``headers={}`` would leak the
            # raw token into git. Mirrors the response-header scrub
            # added for ; see for the runtime
            # equivalent in the dispatcher.
            "headers": _redact_request_headers(out_headers),
            "params": params,
            "json_body": json_body,
            "raw_body_b64": base64.b64encode(raw_body).decode("ascii") if raw_body else None,
        },
        "response": {
            "status": response.status_code,
            # Scrub at capture time so the YAML committed to git never
            # carries the captor's IP, session cookies, or proxy
            # fingerprint. See ``scrub_capture_response_headers`` for
            # the full rationale ().
            "headers": scrub_capture_response_headers(dict(response.headers)),
            **body_classification,
        },
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.dump(
            fixture,
            fh,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        )

    return out_path


def load_fixture(path: Path) -> Dict[str, Any]:
    """Read a single fixture file from disk.

    :param path: Filesystem path returned by :func:`capture`.
    :type path: pathlib.Path
    :return: Parsed YAML.
    :rtype: dict
    """
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def list_fixtures(backend: str, path_slug: str) -> list:
    """Return the sorted list of fixture paths for a (backend, path_slug).

    :param backend: Backend identifier.
    :type backend: str
    :param path_slug: Path slug.
    :type path_slug: str
    :return: Sorted list of :class:`pathlib.Path`.
    :rtype: list
    """
    return sorted((FIXTURES_ROOT / backend / path_slug).glob("*.yaml"))


def fixture_response_bytes(fixture: Dict[str, Any]) -> bytes:
    """Reconstruct the raw response bytes from a fixture's body fields.

    :param fixture: Parsed fixture dict.
    :type fixture: dict
    :return: Bytes the upstream returned at capture time, ready to feed
             back into :mod:`responses`.
    :rtype: bytes
    """
    body = fixture["response"]
    if body.get("body_json") is not None:
        return json.dumps(body["body_json"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if body.get("body_text") is not None:
        return body["body_text"].encode("utf-8")
    if body.get("body_b64") is not None:
        return base64.b64decode(body["body_b64"])
    return b""
