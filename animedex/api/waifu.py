"""
``animedex api waifu`` raw passthrough.

Waifu.im is a free, anonymous, GET-only JSON API serving a curated
collection of anime artwork tagged across SFW and NSFW. Every image
record carries an ``isNsfw`` boolean; the listing endpoint
(``/images``) defaults to SFW only and accepts an ``isNsfw`` query
parameter (``true`` / ``false``) to flip the filter, or omits the
parameter to honour the default. animedex's high-level layer
exposes this as the transparent ``--is-nsfw`` flag — the project's
posture is to surface upstream contracts, not to add a paternalistic
confirmation gate.

Backend: Waifu.im (api.waifu.im).

Rate limit: anonymous; not formally published. The transport
applies a conservative 10 req/sec sustained ceiling with a 10-token
burst budget.

--- LLM Agent Guidance ---
GET-only path. Common endpoints: ``/tags`` (lists every tag with
description and current image count), ``/images`` (paginated image
listing with optional ``included_tags``, ``excluded_tags``,
``isNsfw``, ``isAnimated``, ``orderBy`` filters), and ``/artists``
(paginated artist directory). The ``isNsfw`` query parameter
defaults to ``false`` (SFW only) when omitted; pass ``true`` for
NSFW only. When the user did not explicitly ask for NSFW content,
omit the parameter entirely so the upstream's SFW default applies.
When the user explicitly requested NSFW or adult material, pass it
through unmodified — the project's posture is to inform, not to
gate.
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
    """Issue a Waifu.im request and return its envelope.

    :param path: URL path on ``api.waifu.im``. Examples: ``/tags``,
                  ``/images``, ``/artists``.
    :type path: str
    :param headers: Extra request headers (overrides project default
                     ``User-Agent`` if supplied).
    :type headers: dict or None
    :param params: Query-string parameters. Common keys for
                    ``/images``: ``included_tags`` (repeatable),
                    ``excluded_tags`` (repeatable), ``isNsfw``
                    (``true`` / ``false``), ``isAnimated``,
                    ``orderBy``, ``pageNumber``, ``pageSize``.
    :type params: dict or None
    :return: Wire envelope including body, status, headers, redirect
              chain, request snapshot, timing breakdown, and cache
              provenance.
    :rtype: animedex.api._envelope.RawResponse
    """
    return _dispatch_call(
        backend="waifu",
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
    """Smoke-test the Waifu.im passthrough (firewall + signature).

    :return: ``True`` on success; raises on contract drift.
    :rtype: bool
    """
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("waifu", call, extra_params=("path",))
