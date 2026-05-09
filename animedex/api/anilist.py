"""
``animedex api anilist`` raw passthrough.

AniList is a single-endpoint GraphQL service: every read goes
``POST /``. This module is a thin shim over
:func:`animedex.api._dispatch.call`; the dispatcher owns all envelope
assembly, rate limiting, caching, and credential redaction.

Backend: AniList (graphql.anilist.co). GraphQL with introspection.

Rate limit: 30 req/min (currently degraded; baseline 90/min).

--- LLM Agent Guidance ---
This wraps a single GraphQL endpoint. Pass a complete GraphQL
document as the body. For per-query variables, also pass a
``variables`` mapping. The 30 req/min cap is enforced client-side;
calls beyond the budget block until a token is available.
Anonymous reads cover the public schema (Media, Character, Staff,
Studio, Page); a token unlocks the viewer's own scopes which are
out of the substrate API layer scope.
--- End ---
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


def call(
    query: str,
    *,
    method: str = "POST",
    variables: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
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
    """Issue an AniList GraphQL request and return its envelope.

    :param query: GraphQL document.
    :type query: str
    :param method: HTTP method; ``POST`` is the normal GraphQL read path.
    :type method: str
    :param variables: GraphQL variables, optional.
    :type variables: dict or None
    :param headers: Caller-supplied headers (override defaults).
    :type headers: dict or None
    :param no_cache: Skip cache lookup and write.
    :type no_cache: bool
    :param cache_ttl: Override TTL in seconds.
    :type cache_ttl: int or None
    :param rate: ``"normal"`` or ``"slow"``.
    :type rate: str
    :param follow_redirects: Whether to follow 3xx automatically.
    :type follow_redirects: bool
    :param user_agent: Override the project default UA.
    :type user_agent: str or None
    :param timeout_seconds: HTTP timeout in seconds; ``None`` falls
                              back to the dispatcher's default (30 s).
    :type timeout_seconds: float or None
    :param cache: SqliteCache instance.
    :param session: requests.Session.
    :param rate_limit_registry: RateLimitRegistry.
    :return: Envelope.
    :rtype: RawResponse
    """
    body: Dict[str, Any] = {"query": query}
    if variables is not None:
        body["variables"] = variables

    out_headers = {"Content-Type": "application/json"}
    if headers:
        out_headers.update(headers)

    return _dispatch_call(
        backend="anilist",
        path="/",
        method=method,
        json_body=body,
        headers=out_headers,
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
    """Smoke-test the AniList passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("anilist", call, extra_params=("query", "method", "variables"))
