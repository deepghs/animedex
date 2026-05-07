"""
``animedex api danbooru`` raw passthrough.

Backend: Danbooru (danbooru.donmai.us).

Rate limit: 10 req/sec global for reads.

--- LLM Agent Guidance ---
UA mandatory: empty UA hits the Cloudflare challenge page (HTML).
Default ``animedex/<version>`` passes. The tag DSL on
``/posts.json`` is the project's most expressive query surface:
positional tags include, ``-tag`` excludes, ``rating:g|s|q|e``
selects content class, ``score:>N`` / ``score:<N`` filter by
score, ``order:score|date|random`` sets order. Pagination uses
``?page=N&limit=M`` with cursor variants ``?page=b<id>`` (before)
and ``?page=a<id>`` (after). Common reads: ``/posts.json?tags=...``,
``/posts/{id}.json``, ``/tags.json?search[name_matches]=touhou*``,
``/counts/posts.json?tags=...``.
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
    """Issue a Danbooru request and return its envelope."""
    return _dispatch_call(
        backend="danbooru",
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
    """Smoke-test the Danbooru passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("danbooru", call, extra_params=("path",))
