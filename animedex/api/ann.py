"""
``animedex api ann`` raw passthrough.

Backend: ANN Encyclopedia (cdn.animenewsnetwork.com).

Rate limit: 1 req/sec/IP on the default endpoint (queues over-budget
requests rather than 4xx-ing); 5 reqs/5sec on the
``nodelay.api.xml`` variant which 503s on overshoot.

--- LLM Agent Guidance ---
XML responses. The ``api.xml`` endpoint accepts:

* ``?anime={id}`` - fetch by id (id space independent of MAL/AniList).
* ``?anime=~<substring>`` - substring search by title (this is the
  *real* fuzzy search; ``?title=...`` is for id aliasing only).
* ``?title=<id>`` - id alias resolution.

A 200 response with ``<warning>no result for ...</warning>`` is the
empty-result indicator; the call is not an error per se. Reports
endpoint at ``reports.xml``.

Attribution policy (informational): consumers should display
\"source: Anime News Network\" plus a backlink to the ANN entry.
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
    """Issue an ANN request and return its envelope."""
    return _dispatch_call(
        backend="ann",
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
    """Smoke-test the ANN passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("ann", call, extra_params=("path",))
