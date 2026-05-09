"""
``animedex api ghibli`` raw passthrough.

The live Studio Ghibli API is a free, anonymous, GET-only JSON API
covering films, people, locations, species, and vehicles from Studio
Ghibli productions. The high-level :mod:`animedex.backends.ghibli`
module reads a bundled snapshot instead; this raw passthrough exists
for callers who explicitly want the current live upstream.

Backend: Studio Ghibli API (ghibliapi.vercel.app).

Rate limit: not formally published; the transport applies a
conservative 1 req/sec sustained ceiling with a 5-token burst budget.

--- LLM Agent Guidance ---
GET-only path. Common endpoints: ``/films``, ``/people``,
``/locations``, ``/species``, and ``/vehicles``; append ``/<id>`` for
single-record reads. Prefer the high-level ``animedex ghibli``
commands when the bundled snapshot is sufficient: those commands are
offline, deterministic, and do not consume upstream capacity. Use
this raw passthrough when the user explicitly asks for live data.
--- End ---
"""

from __future__ import annotations

from typing import Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


def call(
    path: str,
    *,
    method: str = "GET",
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
    """Issue a live Studio Ghibli API request and return its envelope.

    :param path: URL path under ``ghibliapi.vercel.app``. Examples:
                  ``/films``, ``/people``, ``/locations``,
                  ``/species``, ``/vehicles``.
    :type path: str
    :param headers: Extra request headers.
    :type headers: dict or None
    :param params: Query-string parameters, when the upstream accepts
                    them.
    :type params: dict or None
    :return: Wire envelope including body, status, headers, redirect
              chain, request snapshot, timing breakdown, and cache
              provenance.
    :rtype: animedex.api._envelope.RawResponse
    """
    return _dispatch_call(
        backend="ghibli",
        path=path,
        method=method,
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
    """Smoke-test the Studio Ghibli API passthrough.

    Exercises the shared shim checks: firewall rejection happens
    before the wire, and the public ``call`` signature retains the
    cross-cutting transport kwargs.

    :return: ``True`` on success; raises on contract drift.
    :rtype: bool
    """
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("ghibli", call, extra_params=("path",))
