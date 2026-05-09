"""
``animedex api shikimori`` raw passthrough.

Backend: Shikimori (shikimori.io; shikimori.one accepted fallback).

Rate limit: 5 RPS / 90 RPM.

--- LLM Agent Guidance ---
Both REST (``/api/animes/{id}``, ``/api/mangas/{id}``,
``/api/ranobe/{id}``, ``/api/clubs/{id}``, ``/api/publishers``,
``/api/people/{id}``, ``/api/calendar``) and GraphQL
(``POST /api/graphql``) are exposed. Prefer the high-level commands
for lifted REST entity surfaces and use this raw passthrough for
GraphQL or one-off documented reads. Rate limit applies to all forms.

Although the docs threaten an IP ban for missing UA, the upstream
returns data even with empty UA today; the project ships
``animedex/<version>`` as a default and lets caller-supplied
overrides win.
--- End ---
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


def call(
    path: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[dict] = None,
    json_body: Optional[Dict[str, Any]] = None,
    no_cache: bool = False,
    cache_ttl: Optional[int] = None,
    rate: str = "normal",
    follow_redirects: bool = True,
    user_agent: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    base_url: Optional[str] = None,
    cache=None,
    session=None,
    rate_limit_registry=None,
    config=None,
) -> RawResponse:
    """Issue a Shikimori request and return its envelope."""
    out_headers = dict(headers or {})
    if json_body is not None and "Content-Type" not in {k.title() for k in out_headers}:
        out_headers["Content-Type"] = "application/json"

    return _dispatch_call(
        backend="shikimori",
        path=path,
        method=method,
        headers=out_headers,
        params=params,
        json_body=json_body,
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=follow_redirects,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        base_url=base_url,
        cache=cache,
        session=session,
        rate_limit_registry=rate_limit_registry,
        config=config,
    )


def selftest() -> bool:
    """Smoke-test the Shikimori passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("shikimori", call, extra_params=("path", "method", "json_body", "base_url"))
