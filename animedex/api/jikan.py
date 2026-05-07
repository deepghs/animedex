"""
``animedex api jikan`` raw passthrough.

Jikan v4 is a REST proxy over MyAnimeList. Anonymous, no headers
required.

Backend: Jikan v4 (api.jikan.moe).

Rate limit: 60 req/min (no per-second cap documented).

--- LLM Agent Guidance ---
GET-only path. Common endpoints: ``/anime/{mal_id}``, ``/anime?q=...``,
``/seasons/{year}/{season}``, ``/anime/{id}/characters``,
``/anime/{id}/episodes``, ``/random/anime``. Pagination is
``?page=N&limit=M`` with the response carrying a ``pagination``
envelope. Errors land as JSON with ``status`` / ``type`` /
``message`` / ``error``; HTTP status mirrors the upstream
(404 for missing entity, 500 when MAL itself is unreachable).
--- End ---
"""

from __future__ import annotations

from typing import Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


def call(
    path: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[dict] = None,
    no_cache: bool = False,
    cache_ttl: Optional[int] = None,
    rate: str = "normal",
    follow_redirects: bool = True,
    user_agent: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    cache=None,
    session=None,
    rate_limit_registry=None,
) -> RawResponse:
    """Issue a Jikan request and return its envelope."""
    return _dispatch_call(
        backend="jikan",
        path=path,
        method="GET",
        headers=headers,
        params=params,
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=follow_redirects,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        cache=cache,
        session=session,
        rate_limit_registry=rate_limit_registry,
    )


def selftest() -> bool:
    """Smoke-test the Jikan passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("jikan", call, extra_params=("path",))
