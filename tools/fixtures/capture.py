"""
Fixture capture tool for the Phase 1 ``animedex api`` test suite.

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
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = PROJECT_ROOT / "test" / "fixtures"


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


def _classify_body(body_bytes: bytes, content_type: str) -> Dict[str, Any]:
    """Decide which of body_json / body_text / body_b64 to populate.

    JSON-parseable responses become ``body_json`` (a native YAML dict)
    so PR diffs read like data, not strings. Text-but-not-JSON
    responses become ``body_text`` (preserving newlines via literal
    block scalar). Anything else falls through to ``body_b64``.

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
            out["body_json"] = parsed
            return out
        except json.JSONDecodeError:
            pass
        # Plain text (XML for ANN, HTML for some Cloudflare challenges).
        out["body_text"] = decoded
        return out
    except UnicodeDecodeError:
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
    pace_seconds: float = 0.0,
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
                          per-backend rate-limit pacing).
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
            "headers": out_headers,
            "params": params,
            "json_body": json_body,
            "raw_body_b64": base64.b64encode(raw_body).decode("ascii") if raw_body else None,
        },
        "response": {
            "status": response.status_code,
            "headers": dict(response.headers),
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
