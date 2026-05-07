"""
Helper to play captured YAML fixtures back through the
:mod:`responses` library so unit tests stay offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlsplit

import responses
import yaml

from tools.fixtures.capture import FIXTURES_ROOT, fixture_response_bytes


def load_fixture(path: Path) -> Dict[str, Any]:
    """Load a single fixture YAML file."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def list_fixtures(backend: str, path_slug: str):
    """Sorted list of fixture paths for a (backend, path_slug) combo."""
    return sorted((FIXTURES_ROOT / backend / path_slug).glob("*.yaml"))


def register_fixture_with_responses(rsps: responses.RequestsMock, fixture: Dict[str, Any]) -> None:
    """Register the fixture's response with an active ``responses`` mock.

    Looks up the captured request URL + method, registers the
    captured response (status, headers, body) so the SUT can play it
    back deterministically.

    :param rsps: The active :class:`responses.RequestsMock`.
    :param fixture: Parsed fixture dict.
    """
    req = fixture["request"]
    resp = fixture["response"]
    body = fixture_response_bytes(fixture)

    method_attr = req["method"].upper()
    method = getattr(responses, method_attr, method_attr)

    # The `responses` library matches body content for POST when we
    # use json= for the registration; otherwise it matches by URL +
    # method only. Most of our fixtures match by URL + method.
    match = []
    if req.get("json_body") is not None:
        match.append(responses.matchers.json_params_matcher(req["json_body"]))
    if req.get("params"):
        match.append(responses.matchers.query_param_matcher(req["params"]))

    # Strip headers whose value is computed from the body bytes; if we
    # play a re-serialised body with a stale length/encoding header,
    # requests' content-decoder raises IncompleteRead.
    _STRIP = {"content-encoding", "content-length", "transfer-encoding"}
    sanitised_headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP}

    rsps.add(
        responses.Response(
            method=method,
            url=req["url"],
            status=resp["status"],
            headers=sanitised_headers,
            body=body,
            match=match,
        )
    )


def url_match_pattern(url: str) -> re.Pattern:
    """Return a regex matching ``url`` exactly (responses lib accepts patterns)."""
    return re.compile(re.escape(url) + r"$")


def split_url(url: str):
    """Return ``(scheme://host/path, query_string)`` for diagnostics."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}", parts.query


def fixture_request_body_json(fixture: Dict[str, Any]):
    return fixture["request"].get("json_body")


def fixture_response_status(fixture: Dict[str, Any]) -> int:
    return fixture["response"]["status"]


def fixture_response_body_payload(fixture: Dict[str, Any]):
    """Return the parsed body payload for assertion convenience."""
    resp = fixture["response"]
    if resp.get("body_json") is not None:
        return resp["body_json"]
    if resp.get("body_text") is not None:
        try:
            return json.loads(resp["body_text"])
        except (ValueError, TypeError):
            return resp["body_text"]
    return None
