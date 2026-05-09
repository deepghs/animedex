"""
``animedex api nekos`` raw passthrough.

nekos.best v2 is a free, anonymous, GET-only JSON API serving a curated
SFW collection of anime imagery and GIFs. Each record carries
``url`` (the asset), plus best-effort attribution
(``anime_name`` / ``artist_name`` / ``artist_href`` / ``source_url``)
and ``dimensions`` (``width`` / ``height``).

Backend: nekos.best v2 (nekos.best/api/v2).

Rate limit: 200 req/min anonymous. The cap is visible in the
``x-rate-limit-limit`` (``"1m"`` window) and ``x-rate-limit-remaining``
response headers; the transport applies a 3 req/sec sustained
ceiling with a 10-token burst budget to stay under it.

--- LLM Agent Guidance ---
GET-only path. Common endpoints: ``/endpoints`` (lists all categories
and their per-category file format); ``/<category>?amount=N``
(retrieves ``N`` random images / GIFs from that category, ``1 <= N <=
20``); ``/search?query=...&type=1|2&category=<name>&amount=N``
(metadata search across artist / source / anime fields, ``type=1``
for images and ``type=2`` for GIFs). All v2 categories are SFW; the
high-level rich-model projection sets ``rating='g'`` unconditionally.
A 404 on ``/<category>`` means the category name is unknown — call
``/endpoints`` to discover the valid set.
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
    """Issue a nekos.best v2 request and return its envelope.

    :param path: URL path under ``/api/v2``. Examples:
                  ``/endpoints``, ``/husbando``, ``/neko``,
                  ``/search``.
    :type path: str
    :param headers: Extra request headers (overrides project default
                     ``User-Agent`` if supplied).
    :type headers: dict or None
    :param params: Query-string parameters.
                    ``amount=N`` for ``/<category>``;
                    ``query=...&type=1|2&category=...&amount=N`` for
                    ``/search``.
    :type params: dict or None
    :return: Wire envelope including body, status, headers, redirect
              chain, request snapshot, timing breakdown, and cache
              provenance.
    :rtype: animedex.api._envelope.RawResponse
    """
    return _dispatch_call(
        backend="nekos",
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
    """Smoke-test the nekos.best passthrough (firewall + signature).

    :return: ``True`` on success; raises on contract drift.
    :rtype: bool
    """
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("nekos", call, extra_params=("path",))
