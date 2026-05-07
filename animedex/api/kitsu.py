"""
``animedex api kitsu`` raw passthrough.

Backend: Kitsu (kitsu.io/api/edge; kitsu.app/api/edge accepted).

Rate limit: not formally published; self-imposed 10/sec polite cap.

--- LLM Agent Guidance ---
JSON:API. Inject ``Accept: application/vnd.api+json`` automatically.
Pagination uses ``page[offset]=N&page[limit]=M``. Common reads:
``/anime?filter[text]=Frieren&page[limit]=5&include=streamingLinks``,
``/anime/{id}``, ``/anime/{id}/streaming-links``,
``/anime/{id}/mappings`` (cross-source IDs).
Both kitsu.io and kitsu.app serve identical data; the canonical
default is .io. Anonymous reads cover the surface; a token unlocks
user library / private data.
--- End ---
"""

from __future__ import annotations

from typing import Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


_DEFAULT_HEADERS = {"Accept": "application/vnd.api+json"}


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
    base_url: Optional[str] = None,
    cache=None,
    session=None,
    rate_limit_registry=None,
) -> RawResponse:
    """Issue a Kitsu request and return its envelope."""
    out_headers = dict(_DEFAULT_HEADERS)
    if headers:
        out_headers.update(headers)
    return _dispatch_call(
        backend="kitsu",
        path=path,
        method="GET",
        headers=out_headers,
        params=params,
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=follow_redirects,
        user_agent=user_agent,
        base_url=base_url,
        cache=cache,
        session=session,
        rate_limit_registry=rate_limit_registry,
    )


def selftest() -> bool:
    raw = _dispatch_call(backend="kitsu", path="/anime/1", method="DELETE", cache=None)
    assert raw.firewall_rejected is not None
    return True
