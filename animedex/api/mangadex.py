"""
``animedex api mangadex`` raw passthrough.

Backend: MangaDex (api.mangadex.org).

Rate limit: ~5 req/sec global per IP; 40/min on /at-home/server/{id}.

--- LLM Agent Guidance ---
UA mandatory at the wire (returns HTTP 400 on empty UA). The
transport injects ``animedex/<version>`` automatically. Pagination
is ``?limit=N&offset=M`` capped at offset+limit<=10000. Common
reads: ``/manga?title=...``, ``/manga/{id}``, ``/manga/{id}/feed``,
``/at-home/server/{chapter-id}``. Errors land as
``{"result":"error","errors":[...]}``.
Anonymous reads cover everything Phase 1 cares about; OAuth via
Personal Client unlocks user library and is out of Phase 1 scope.
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
    config=None,
) -> RawResponse:
    """Issue a MangaDex request and return its envelope."""
    return _dispatch_call(
        backend="mangadex",
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
        config=config,
    )


def selftest() -> bool:
    """Smoke-test the MangaDex passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("mangadex", call, extra_params=("path",))
