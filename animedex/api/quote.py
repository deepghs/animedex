"""
``animedex api quote`` raw passthrough.

AnimeChan is a free, anonymous, GET-only quote API. The free tier
serves random quotes and paginated quote lists filtered by anime or
character name. Every successful response is a JSON envelope with a
``status`` string and a ``data`` field containing either one quote or
an array of quotes.

Backend: AnimeChan (api.animechan.io/v1).

Rate limit: 5 req/hour anonymous. Supporter tokens can receive higher
limits, but this backend only configures the anonymous free-tier
bucket.

--- LLM Agent Guidance ---
GET-only path. Common endpoints: ``/quotes/random``,
``/quotes/random?anime=<title>``, ``/quotes/random?character=<name>``,
``/quotes?anime=<title>&page=N``, and
``/quotes?character=<name>&page=N``. The free tier is very tight
(5 req/hour), so prefer cached high-level calls and avoid exploratory
live probing unless the user needs fresh quotes.
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
    """Issue an AnimeChan request and return its envelope.

    :param path: URL path under ``/v1``. Examples:
                  ``/quotes/random`` and ``/quotes``.
    :type path: str
    :param headers: Extra request headers.
    :type headers: dict or None
    :param params: Query-string parameters such as ``anime``,
                    ``character``, and ``page``.
    :type params: dict or None
    :return: Wire envelope including body, status, headers, redirect
              chain, request snapshot, timing breakdown, and cache
              provenance.
    :rtype: animedex.api._envelope.RawResponse
    """
    return _dispatch_call(
        backend="quote",
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
    """Smoke-test the AnimeChan passthrough.

    Exercises the shared shim checks: firewall rejection happens
    before the wire, and the public ``call`` signature retains the
    cross-cutting transport kwargs.

    :return: ``True`` on success; raises on contract drift.
    :rtype: bool
    """
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("quote", call, extra_params=("path",))
