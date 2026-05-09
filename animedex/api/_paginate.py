"""
Pagination strategies for the raw API passthrough.

The dispatcher owns HTTP execution, cache lookup, rate limiting, and
envelope assembly. This module owns only backend-specific pagination
state: how to mutate the next request's parameters, how to extract
items from one decoded page, and when to stop.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from animedex.api._envelope import RawCacheInfo, RawRequest, RawResponse, RawTiming
from animedex.api._params import first_int, merge_params, split_path_query
from animedex.models.common import ApiError

if TYPE_CHECKING:
    import requests

    from animedex.cache.sqlite import SqliteCache
    from animedex.config import Config
    from animedex.transport.ratelimit import RateLimitRegistry


@dataclass(frozen=True)
class PageRequest:
    """Request shape for one paginated page.

    :ivar path: Path with no query string.
    :vartype path: str
    :ivar params: Query parameters for the page.
    :vartype params: dict
    """

    path: str
    params: Dict[str, Any]


@dataclass(frozen=True)
class PageResult:
    """Decoded information from one paginated response.

    :ivar items: Items extracted from the page.
    :vartype items: list
    :ivar has_next: Whether the upstream indicates that another page
                    may exist.
    :vartype has_next: bool
    :ivar reason: Termination reason when ``has_next`` is ``False``.
    :vartype reason: str or None
    """

    items: List[Any]
    has_next: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class PaginationStrategy:
    """Backend-specific pagination operations.

    :ivar name: Strategy/backend name.
    :vartype name: str
    :ivar initial: Build the first request from user input.
    :vartype initial: callable
    :ivar next_request: Build the next request after a response.
    :vartype next_request: callable
    :ivar decode: Extract page items and upstream termination state.
    :vartype decode: callable
    """

    name: str
    initial: Callable[[str, Dict[str, Any]], PageRequest]
    next_request: Callable[[PageRequest, int, PageResult], PageRequest]
    decode: Callable[[Any, PageRequest], PageResult]


def _decode_json_page(envelope: RawResponse) -> Any:
    """Decode a page body as JSON or raise a typed API error."""
    if envelope.body_text is None:
        raise ApiError("paginated raw response is not UTF-8 text", backend=envelope.backend, reason="upstream-decode")
    try:
        return json.loads(envelope.body_text)
    except ValueError as exc:
        raise ApiError(
            f"paginated raw response is not JSON: {exc}",
            backend=envelope.backend,
            reason="upstream-decode",
        ) from exc


def _coerce_items(value: Any, *, backend: str) -> List[Any]:
    """Return ``value`` as a list or raise an upstream-shape error."""
    if isinstance(value, list):
        return value
    raise ApiError(
        f"{backend} paginated response did not contain a list of items", backend=backend, reason="upstream-shape"
    )


def _page_initial(path: str, params: Dict[str, Any]) -> PageRequest:
    page = first_int(params, ("page",), 1)
    limit = first_int(params, ("limit",), 25)
    out = merge_params(params, {"page": page, "limit": limit})
    return PageRequest(path=path, params=out)


def _offset_initial(path: str, params: Dict[str, Any]) -> PageRequest:
    offset = first_int(params, ("offset",), 0)
    limit = first_int(params, ("limit",), 25)
    out = merge_params(params, {"offset": offset, "limit": limit})
    return PageRequest(path=path, params=out)


def _quote_initial(path: str, params: Dict[str, Any]) -> PageRequest:
    page = first_int(params, ("page",), 1)
    out = merge_params(params, {"page": page})
    return PageRequest(path=path, params=out)


def _increment_page(current: PageRequest, _page_number: int, _result: PageResult) -> PageRequest:
    page = first_int(current.params, ("page",), 1)
    return PageRequest(path=current.path, params=merge_params(current.params, {"page": page + 1}))


def _increment_offset(current: PageRequest, _page_number: int, _result: PageResult) -> PageRequest:
    offset = first_int(current.params, ("offset",), 0)
    limit = first_int(current.params, ("limit",), 25)
    return PageRequest(path=current.path, params=merge_params(current.params, {"offset": offset + limit}))


def _decode_jikan(payload: Any, _request: PageRequest) -> PageResult:
    if not isinstance(payload, dict):
        raise ApiError("jikan paginated response was not an object", backend="jikan", reason="upstream-shape")
    items = _coerce_items(payload.get("data"), backend="jikan")
    pagination = payload.get("pagination") or {}
    if not isinstance(pagination, dict):
        raise ApiError("jikan pagination field was not an object", backend="jikan", reason="upstream-shape")
    has_next = bool(pagination.get("has_next_page"))
    reason = None if has_next else "upstream-last-page"
    return PageResult(items=items, has_next=has_next, reason=reason)


def _decode_mangadex(payload: Any, request: PageRequest) -> PageResult:
    if not isinstance(payload, dict):
        raise ApiError("mangadex paginated response was not an object", backend="mangadex", reason="upstream-shape")
    items = _coerce_items(payload.get("data"), backend="mangadex")
    offset = int(payload.get("offset", first_int(request.params, ("offset",), 0)))
    limit = int(payload.get("limit", first_int(request.params, ("limit",), len(items) or 1)))
    total = payload.get("total")
    has_next = bool(total is not None and offset + limit < int(total))
    reason = None if has_next else "upstream-last-page"
    return PageResult(items=items, has_next=has_next, reason=reason)


def _decode_short_page_list(backend: str, payload: Any, request: PageRequest) -> PageResult:
    items = _coerce_items(payload, backend=backend)
    limit = first_int(request.params, ("limit",), len(items) or 1)
    has_next = len(items) >= limit
    reason = None if has_next else "short-page"
    return PageResult(items=items, has_next=has_next, reason=reason)


def _decode_danbooru(payload: Any, request: PageRequest) -> PageResult:
    return _decode_short_page_list("danbooru", payload, request)


def _decode_shikimori(payload: Any, request: PageRequest) -> PageResult:
    return _decode_short_page_list("shikimori", payload, request)


def _decode_quote(payload: Any, _request: PageRequest) -> PageResult:
    if not isinstance(payload, dict):
        raise ApiError("quote paginated response was not an object", backend="quote", reason="upstream-shape")
    items = _coerce_items(payload.get("data"), backend="quote")
    has_next = len(items) >= 5
    reason = None if has_next else "short-page"
    return PageResult(items=items, has_next=has_next, reason=reason)


_STRATEGIES = {
    "jikan": PaginationStrategy("jikan", _page_initial, _increment_page, _decode_jikan),
    "mangadex": PaginationStrategy("mangadex", _offset_initial, _increment_offset, _decode_mangadex),
    "danbooru": PaginationStrategy("danbooru", _page_initial, _increment_page, _decode_danbooru),
    "shikimori": PaginationStrategy("shikimori", _page_initial, _increment_page, _decode_shikimori),
    "quote": PaginationStrategy("quote", _quote_initial, _increment_page, _decode_quote),
}


def get_strategy(backend: str) -> PaginationStrategy:
    """Return the pagination strategy for ``backend``.

    :param backend: Backend identifier.
    :type backend: str
    :return: Pagination strategy.
    :rtype: PaginationStrategy
    :raises ApiError: When the backend is not paginate-aware.
    """
    try:
        return _STRATEGIES[backend]
    except KeyError as exc:
        raise ApiError(f"{backend} does not support raw --paginate", backend=backend, reason="bad-args") from exc


def call_paginated(
    *,
    backend: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[dict] = None,
    follow_redirects: bool = True,
    no_cache: bool = False,
    cache_ttl: Optional[int] = None,
    rate: str = "normal",
    timeout_seconds: Optional[float] = None,
    user_agent: Optional[str] = None,
    base_url: Optional[str] = None,
    session: Optional["requests.Session"] = None,
    cache: Optional["SqliteCache"] = None,
    rate_limit_registry: Optional["RateLimitRegistry"] = None,
    config: Optional["Config"] = None,
    max_pages: int = 10,
    max_items: Optional[int] = None,
) -> RawResponse:
    """Issue a raw paginated GET sequence and return an aggregate envelope.

    :param backend: Backend identifier.
    :type backend: str
    :param path: URL path, optionally carrying a query string.
    :type path: str
    :param method: HTTP method. Only ``GET`` is currently valid for
                   paginate-aware raw endpoints.
    :type method: str
    :param headers: Caller-supplied headers.
    :type headers: dict or None
    :param params: Query parameters merged over any query embedded in
                   ``path``.
    :type params: dict or None
    :param follow_redirects: Whether to follow redirects.
    :type follow_redirects: bool
    :param no_cache: Skip cache lookup and writes.
    :type no_cache: bool
    :param cache_ttl: Override cache TTL in seconds.
    :type cache_ttl: int or None
    :param rate: ``"normal"`` or ``"slow"``.
    :type rate: str
    :param timeout_seconds: HTTP timeout in seconds.
    :type timeout_seconds: float or None
    :param user_agent: Override default User-Agent.
    :type user_agent: str or None
    :param base_url: Backend base URL override.
    :type base_url: str or None
    :param session: Optional requests session.
    :type session: requests.Session or None
    :param cache: Optional cache.
    :type cache: SqliteCache or None
    :param rate_limit_registry: Optional rate-limit registry.
    :type rate_limit_registry: RateLimitRegistry or None
    :param config: Optional config defaults.
    :type config: Config or None
    :param max_pages: Maximum pages to fetch.
    :type max_pages: int
    :param max_items: Maximum items to emit.
    :type max_items: int or None
    :return: Aggregate raw envelope whose body is JSON.
    :rtype: RawResponse
    """
    if max_pages < 1:
        raise ApiError("--max-pages must be >= 1", backend=backend, reason="bad-args")
    if max_items is not None and max_items < 1:
        raise ApiError("--max-items must be >= 1", backend=backend, reason="bad-args")
    method_up = method.upper()
    if method_up != "GET":
        raise ApiError("--paginate currently supports GET raw endpoints only", backend=backend, reason="bad-args")

    from animedex.api._dispatch import call

    strategy = get_strategy(backend)
    clean_path, merged_params = split_path_query(path, params)
    request = strategy.initial(clean_path, merged_params)
    t_start = time.monotonic()
    items: List[Any] = []
    page_meta: List[Dict[str, Any]] = []
    pages_fetched = 0
    termination_reason = "max-pages"
    last_env: Optional[RawResponse] = None
    first_request: Optional[RawRequest] = None
    redirects = []
    response_headers: Dict[str, str] = {}
    status = 0

    while pages_fetched < max_pages:
        env = call(
            backend=backend,
            path=request.path,
            method=method_up,
            headers=headers,
            params=request.params,
            follow_redirects=follow_redirects,
            no_cache=no_cache,
            cache_ttl=cache_ttl,
            rate=rate,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            base_url=base_url,
            session=session,
            cache=cache,
            rate_limit_registry=rate_limit_registry,
            config=config,
        )
        last_env = env
        if first_request is None:
            first_request = env.request
        redirects.extend(env.redirects)
        response_headers = env.response_headers
        status = env.status
        pages_fetched += 1

        if env.firewall_rejected is not None or not (200 <= env.status < 300):
            termination_reason = "non-2xx-response"
            break

        page_result = strategy.decode(_decode_json_page(env), request)
        remaining = None if max_items is None else max_items - len(items)
        if (
            remaining is not None and remaining <= 0
        ):  # pragma: no cover - guarded by max_items validation and prior break
            termination_reason = "max-items"
            break
        page_items = page_result.items if remaining is None else page_result.items[:remaining]
        items.extend(page_items)
        page_meta.append(
            {
                "page": pages_fetched,
                "url": env.request.url,
                "status": env.status,
                "cache_hit": env.cache.hit,
                "item_count": len(page_items),
            }
        )

        if max_items is not None and len(items) >= max_items:
            termination_reason = "max-items"
            break
        if not page_result.has_next:
            termination_reason = page_result.reason or "upstream-last-page"
            break
        if pages_fetched >= max_pages:
            termination_reason = "max-pages"
            break
        request = strategy.next_request(request, pages_fetched + 1, page_result)

    total_ms = (time.monotonic() - t_start) * 1000.0
    body = {
        "items": items,
        "pagination": {
            "backend": backend,
            "pages_fetched": pages_fetched,
            "items_fetched": len(items),
            "terminated_by": termination_reason,
            "max_pages": max_pages,
            "max_items": max_items,
            "pages": page_meta,
        },
    }
    body_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    if first_request is None:  # pragma: no cover - max_pages validation guarantees at least one request attempt
        first_request = RawRequest(method=method_up, url="", headers={})
    cache_hit = bool(page_meta) and all(page["cache_hit"] for page in page_meta)
    return RawResponse(
        backend=backend,
        request=first_request,
        redirects=redirects,
        status=status,
        response_headers=response_headers,
        body_bytes=body_bytes,
        body_text=body_bytes.decode("utf-8"),
        timing=RawTiming(
            total_ms=total_ms,
            rate_limit_wait_ms=last_env.timing.rate_limit_wait_ms if last_env is not None else 0.0,
            request_ms=last_env.timing.request_ms if last_env is not None else 0.0,
        ),
        cache=RawCacheInfo(hit=cache_hit),
        firewall_rejected=last_env.firewall_rejected if last_env is not None else None,
    )


def selftest() -> bool:
    """Smoke-test strategy registration and representative decoders."""
    assert get_strategy("jikan").name == "jikan"
    assert get_strategy("mangadex").name == "mangadex"
    assert _decode_jikan({"data": [1], "pagination": {"has_next_page": False}}, PageRequest("/", {})).items == [1]
    assert _decode_mangadex({"data": [1], "offset": 0, "limit": 1, "total": 1}, PageRequest("/", {})).has_next is False
    assert _decode_danbooru([1], PageRequest("/", {"limit": 2})).reason == "short-page"
    try:
        get_strategy("anilist")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover - defensive selftest assertion
        raise AssertionError("anilist should not be paginate-aware")
    return True
