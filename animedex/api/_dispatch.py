"""
Universal ``animedex api`` dispatcher.

:func:`call` is the single entry point: it composes the URL, runs the
read-only firewall, waits on the per-backend rate-limit bucket, looks
up the local SQLite cache, issues the HTTP request when needed, and
assembles a :class:`~animedex.api._envelope.RawResponse` envelope
containing everything a CLI render mode needs (body, status, response
headers, redirect chain, request snapshot with credentials redacted,
timing breakdown, cache provenance).

Per-backend modules under ``animedex/api/<backend>.py`` are thin
shims that pre-fill the ``backend`` argument; this module owns the
shared envelope assembly.
"""

from __future__ import annotations

import time
from datetime import datetime  # noqa: F401  - re-exported via type hints
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from animedex.config import Config

import requests

from animedex.api._envelope import (
    RawCacheInfo,
    RawRedirectHop,
    RawRequest,
    RawResponse,
    RawTiming,
    redact_headers,
)
from animedex.cache.sqlite import SqliteCache, default_ttl_seconds
from animedex.models.common import ApiError
from animedex.transport.ratelimit import RateLimitRegistry, default_registry
from animedex.transport.read_only import enforce_read_only, known_backends
from animedex.transport.useragent import compose_user_agent


# Per-backend canonical base URL. the substrate API layer default; per-backend
# modules may pass in their own override via the ``base_url`` arg.
_BASE_URLS = {
    "anilist": "https://graphql.anilist.co",
    "jikan": "https://api.jikan.moe/v4",
    "kitsu": "https://kitsu.io/api/edge",
    "mangadex": "https://api.mangadex.org",
    "trace": "https://api.trace.moe",
    "danbooru": "https://danbooru.donmai.us",
    "shikimori": "https://shikimori.io",
    "ann": "https://cdn.animenewsnetwork.com/encyclopedia",
    "nekos": "https://nekos.best/api/v2",
    "waifu": "https://api.waifu.im",
    "ghibli": "https://ghibliapi.vercel.app",
    "quote": "https://api.animechan.io/v1",
}


_BODY_PREVIEW_BYTES = 4096

# Default HTTP timeout when neither the caller nor the per-backend
# shim supplies one. 30 s is conservative for the slowest upstream
# (ANN's encyclopedia XML can take ~10 s on a cold cache); shorter
# values are exposed via the ``timeout_seconds`` kwarg.
_DEFAULT_TIMEOUT_SECONDS = 30.0


def resolve_base_url(backend: str) -> str:
    """Return the canonical base URL for ``backend``.

    :param backend: Backend identifier.
    :type backend: str
    :return: Base URL with no trailing slash.
    :rtype: str
    :raises KeyError: When the backend is not registered.
    """
    return _BASE_URLS[backend]


def _join(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base_url.rstrip("/") + path


def _canonicalise_params(obj: Any) -> Any:
    """Recursively normalise a query-param structure for cache-key hashing.

    Multi-value query parameters (e.g. MangaDex's
    ``includes[]=cover_art&includes[]=author``) are
    semantically set-typed for every backend the project targets, so
    ``includes[]=author&includes[]=cover_art`` should produce the same
    cache key. ``json.dumps(sort_keys=True)`` stabilises dict key
    order but leaves list order alone; this helper sorts list values
    too so the signature is order-invariant.

    Per : applied **only** to ``params`` and **not** to
    ``json_body``. JSON request bodies often carry ordered semantics
    (paginated cursors, mutation order, ordered relations), and
    treating them as sets would risk cache poisoning - two distinct
    requests sharing a cache key.

    :param obj: The params structure (dict / list / scalar).
    :return: A structure with every list sorted (using string-keyed
             ordering for cross-type stability).
    :rtype: Any
    """
    import json as _json

    if isinstance(obj, dict):
        return {k: _canonicalise_params(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        # Sort by the JSON serialisation of each element so mixed-type
        # lists (e.g. ``[1, "a"]``) sort deterministically across
        # Python versions.
        return sorted(
            (_canonicalise_params(x) for x in obj),
            key=lambda x: _json.dumps(x, sort_keys=True, ensure_ascii=False),
        )
    return obj


def _signature(method: str, url: str, params: Optional[dict], json_body: Optional[Any], body: Optional[bytes]) -> str:
    """Compose a stable cache key for this request shape.

    The hash is order-invariant for query-param lists (see
    :func:`_canonicalise_params`); JSON bodies and raw bodies are
    hashed verbatim because their order may carry semantics.
    """
    import hashlib
    import json as _json

    h = hashlib.sha256()
    h.update(method.upper().encode("utf-8"))
    h.update(b"|")
    h.update(url.encode("utf-8"))
    if params:
        h.update(b"|p:")
        h.update(_json.dumps(_canonicalise_params(params), sort_keys=True).encode("utf-8"))
    if json_body is not None:
        h.update(b"|j:")
        h.update(_json.dumps(json_body, sort_keys=True).encode("utf-8"))
    if body:
        h.update(b"|b:")
        h.update(body)
    return h.hexdigest()


def _make_body_preview(json_body: Optional[Any], raw_body: Optional[bytes]) -> Optional[str]:
    if json_body is not None:
        import json as _json

        text = _json.dumps(json_body, ensure_ascii=False)
    elif raw_body is not None:
        try:
            text = raw_body.decode("utf-8", errors="replace")
        except Exception:
            return f"<{len(raw_body)} bytes binary>"
    else:
        return None
    if len(text) > _BODY_PREVIEW_BYTES:
        return text[:_BODY_PREVIEW_BYTES] + "...truncated"
    return text


def call(
    *,
    backend: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[dict] = None,
    json_body: Optional[Any] = None,
    raw_body: Optional[bytes] = None,
    follow_redirects: bool = True,
    no_cache: bool = False,
    cache_ttl: Optional[int] = None,
    rate: str = "normal",
    timeout_seconds: Optional[float] = None,
    user_agent: Optional[str] = None,
    base_url: Optional[str] = None,
    session: Optional[requests.Session] = None,
    cache: Optional[SqliteCache] = None,
    rate_limit_registry: Optional[RateLimitRegistry] = None,
    config: Optional["Config"] = None,
) -> RawResponse:
    """Issue one request and return its complete envelope.

    :param backend: Backend identifier (e.g. ``"anilist"``); determines
                     base URL, rate-limit bucket, and read-only ruleset.
    :type backend: str
    :param path: URL path (relative to base) or absolute URL.
    :type path: str
    :param method: HTTP method.
    :type method: str
    :param headers: Caller-supplied headers; override defaults.
    :type headers: dict or None
    :param params: Query parameters.
    :type params: dict or None
    :param json_body: JSON body for POST.
    :type json_body: Any or None
    :param raw_body: Raw byte body (mutually exclusive with json_body).
    :type raw_body: bytes or None
    :param follow_redirects: Whether to follow 3xx automatically.
    :type follow_redirects: bool
    :param no_cache: When ``True``, skip cache lookup and write.
    :type no_cache: bool
    :param cache_ttl: Override TTL in seconds; defaults to the metadata
                       category default.
    :type cache_ttl: int or None
    :param rate: ``"normal"`` or ``"slow"``.
    :type rate: str
    :param timeout_seconds: HTTP timeout in seconds. ``None`` falls
                              back to the project-default 30 s.
    :type timeout_seconds: float or None
    :param user_agent: Override for the project default UA.
    :type user_agent: str or None
    :param base_url: Override for the backend's canonical base URL.
    :type base_url: str or None
    :param session: Reuse a ``requests.Session``; one is created when
                     not given.
    :type session: requests.Session or None
    :param cache: SqliteCache instance; ``None`` skips cache regardless
                   of ``no_cache``.
    :type cache: SqliteCache or None
    :param rate_limit_registry: Rate-limit registry; defaults to
                                  :func:`animedex.transport.ratelimit.default_registry`.
    :type rate_limit_registry: RateLimitRegistry or None
    :param config: Optional :class:`~animedex.config.Config` whose
                    ``user_agent``, ``timeout_seconds``, and
                    ``cache_ttl_seconds`` fields supply defaults when
                    the matching kwarg is not given (or is ``None``).
                    Explicit kwargs always win. Per
                    ``plans/05 §4`` every public API function honours
                    this kwarg.
    :type config: Config or None
    :return: Full envelope.
    :rtype: RawResponse
    """
    t_start = time.monotonic()

    # 0. Resolve config-supplied defaults. Explicit kwargs win; the
    # config only fills in fields the caller left at the sentinel
    # (``None``). Per / plans/05 §4.
    if config is not None:
        if user_agent is None:
            user_agent = config.user_agent
        if timeout_seconds is None:
            timeout_seconds = config.timeout_seconds
        if cache_ttl is None:
            cache_ttl = config.cache_ttl_seconds

    # 1. Resolve URL + headers; build the redacted request snapshot.
    if base_url is None and backend in _BASE_URLS:
        base_url = _BASE_URLS[backend]
    method_up = method.upper()

    if base_url is not None:
        full_url = _join(base_url, path)
    else:
        full_url = path  # only used when path is absolute or backend already unknown

    out_headers = {"User-Agent": compose_user_agent(user_agent)}
    if headers:
        for key, value in headers.items():
            if key.lower() == "via":
                continue
            out_headers[key] = value

    request_snapshot = RawRequest(
        method=method_up,
        url=full_url,
        headers=redact_headers(out_headers),
        body_preview=_make_body_preview(json_body, raw_body),
    )

    # 2. Read-only firewall - reject before going further.
    if backend not in known_backends():
        return _firewall_envelope(
            backend=backend,
            request_snapshot=request_snapshot,
            reason="unknown-backend",
            message=f"unknown backend: {backend!r}",
            t_start=t_start,
        )

    firewall_path = path if path.startswith("/") else "/" + path
    try:
        enforce_read_only(backend, method_up, firewall_path)
    except ApiError as exc:
        return _firewall_envelope(
            backend=backend,
            request_snapshot=request_snapshot,
            reason=exc.reason or "read-only",
            message=str(exc.message),
            t_start=t_start,
        )

    # 3. Cache lookup.
    sig = _signature(method_up, full_url, params, json_body, raw_body)
    cache_lookup_skipped = no_cache or cache is None
    if not cache_lookup_skipped:
        hit = cache.get_with_meta(backend, sig)
        if hit is not None:
            payload, hdrs, fetched_at = hit
            # Defence in depth: the cache-write path already redacts
            # response headers (), but legacy rows written
            # before that fix landed may still contain raw Set-Cookie
            # / Authorization values. Redact at read time too so an
            # un-redacted row never escapes into a RawResponse.
            return _cache_hit_envelope(
                backend=backend,
                request_snapshot=request_snapshot,
                signature=sig,
                payload=payload,
                response_headers=redact_headers(hdrs or {}),
                fetched_at=fetched_at,
                cache_ttl_seconds=cache_ttl if cache_ttl is not None else default_ttl_seconds("metadata"),
                t_start=t_start,
            )

    # 4. Wait on the rate-limit bucket; capture wait time.
    registry = rate_limit_registry if rate_limit_registry is not None else default_registry()
    bucket = registry.get(backend).with_rate(rate)
    t_pre_wait = time.monotonic()
    bucket.acquire()
    wait_ms = (time.monotonic() - t_pre_wait) * 1000.0

    # 5. Issue the HTTP request.
    sess = session if session is not None else requests.Session()
    t_pre_req = time.monotonic()
    response = sess.request(
        method_up,
        full_url,
        headers=out_headers,
        params=params,
        json=json_body,
        data=raw_body,
        timeout=timeout_seconds if timeout_seconds is not None else _DEFAULT_TIMEOUT_SECONDS,
        allow_redirects=follow_redirects,
    )
    request_ms = (time.monotonic() - t_pre_req) * 1000.0

    # 6. Capture redirect hops from response.history. Redirect
    # response headers can carry the same credentials as the final
    # hop (Set-Cookie, Authorization), so redact them too.
    redirects = []
    for hop in response.history:
        redirects.append(
            RawRedirectHop(
                status=hop.status_code,
                headers=redact_headers(dict(hop.headers)),
                from_url=hop.url,
                to_url=hop.headers.get("Location", ""),
                elapsed_ms=hop.elapsed.total_seconds() * 1000.0 if hop.elapsed else 0.0,
            )
        )

    # 7. Decode body.
    body_bytes = response.content
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        body_text = None

    # 8. Redact response headers once, then reuse the redacted dict
    # for both the cache write and the live envelope. Cache rows are
    # treated as sensitive as the debug output: an attacker reading
    # the SQLite file otherwise sees raw Set-Cookie / Authorization.
    redacted_response_headers = redact_headers(dict(response.headers))

    # 9. Cache write (only on cacheable responses).
    if not cache_lookup_skipped and 200 <= response.status_code < 300:
        ttl = cache_ttl if cache_ttl is not None else default_ttl_seconds("metadata")
        cache.set_with_meta(
            backend,
            sig,
            body_bytes,
            response_headers=redacted_response_headers,
            ttl_seconds=ttl,
        )

    total_ms = (time.monotonic() - t_start) * 1000.0
    return RawResponse(
        backend=backend,
        request=request_snapshot,
        redirects=redirects,
        status=response.status_code,
        response_headers=redacted_response_headers,
        body_bytes=body_bytes,
        body_text=body_text,
        timing=RawTiming(total_ms=total_ms, rate_limit_wait_ms=wait_ms, request_ms=request_ms),
        cache=RawCacheInfo(hit=False, key=sig if not cache_lookup_skipped else None),
    )


def selftest_backend_shim(backend: str, call_fn: Any, *, extra_params: tuple = ()) -> bool:
    """Shared offline smoke check for every per-backend shim.

    Per + : a per-backend ``selftest`` that only
    exercises the firewall rejection path tells us nothing about
    whether the backend's own ``call`` was renamed, removed, or had
    its signature broken. This helper bundles two checks:

    * **Firewall path** - a ``DELETE`` to the backend is rejected by
      :func:`enforce_read_only` before leaving the host. Confirms the
      read-only contract still wires up.
    * **Signature shape** - ``call_fn`` is callable, has a Pythonic
      keyword surface, and exposes the cross-cutting kwargs every
      shim must thread (``no_cache``, ``cache_ttl``, ``rate``,
      ``timeout_seconds``, ``user_agent``, ``cache``). A rename
      that drops one of these is a regression.

    :param backend: Backend identifier passed to the firewall check.
    :type backend: str
    :param call_fn: The shim's public ``call`` function.
    :type call_fn: Callable
    :param extra_params: Backend-specific kwargs that must also be
                          present (e.g. ``("query", "variables")``
                          for anilist, ``("path",)`` for the REST
                          shims). Generic kwargs are checked
                          unconditionally.
    :type extra_params: tuple of str
    :return: ``True`` on success; raises on failure so the runner
             prints a useful traceback.
    :rtype: bool
    """
    import inspect

    raw = call(backend=backend, path="/_animedex_selftest", method="DELETE", cache=None)
    assert raw.firewall_rejected is not None, f"{backend} firewall did not reject DELETE"

    sig = inspect.signature(call_fn)
    expected = {
        "no_cache",
        "cache_ttl",
        "rate",
        "method",
        "timeout_seconds",
        "user_agent",
        "cache",
        *extra_params,
    }
    missing = expected - set(sig.parameters)
    assert not missing, f"{call_fn.__module__}.{call_fn.__name__} lost expected params: {sorted(missing)}"
    return True


def _firewall_envelope(
    *,
    backend: str,
    request_snapshot: RawRequest,
    reason: str,
    message: str,
    t_start: float,
) -> RawResponse:
    total_ms = (time.monotonic() - t_start) * 1000.0
    return RawResponse(
        backend=backend,
        request=request_snapshot,
        redirects=[],
        status=0,
        response_headers={},
        body_bytes=b"",
        body_text="",
        timing=RawTiming(total_ms=total_ms, rate_limit_wait_ms=0.0, request_ms=0.0),
        cache=RawCacheInfo(hit=False),
        firewall_rejected={"reason": reason, "message": message},
    )


def _cache_hit_envelope(
    *,
    backend: str,
    request_snapshot: RawRequest,
    signature: str,
    payload: bytes,
    response_headers: Dict[str, str],
    fetched_at: Optional[datetime],
    cache_ttl_seconds: int,
    t_start: float,
) -> RawResponse:
    total_ms = (time.monotonic() - t_start) * 1000.0
    try:
        body_text = payload.decode("utf-8")
    except UnicodeDecodeError:
        body_text = None

    ttl_remaining = None
    if fetched_at is not None:
        # Use the cache module's clock so the same fake_clock fixture
        # patches it - keeps the dispatcher in step with cache TTL math.
        from animedex.cache.sqlite import _utcnow as _cache_now

        elapsed = (_cache_now() - fetched_at).total_seconds()
        remaining = cache_ttl_seconds - int(elapsed)
        if remaining > 0:
            ttl_remaining = remaining

    return RawResponse(
        backend=backend,
        request=request_snapshot,
        redirects=[],
        status=200,
        response_headers=response_headers,
        body_bytes=payload,
        body_text=body_text,
        timing=RawTiming(total_ms=total_ms, rate_limit_wait_ms=0.0, request_ms=0.0),
        cache=RawCacheInfo(
            hit=True,
            key=signature,
            ttl_remaining_s=ttl_remaining,
            fetched_at=fetched_at,
        ),
    )


def selftest() -> bool:
    """Smoke-test the dispatcher against an in-memory mock.

    :return: ``True`` on success.
    :rtype: bool
    """
    # Import-only validation: the dispatcher's wiring is exercised
    # by unit tests; the selftest just confirms the symbols load and
    # the firewall path works without touching the network.
    from animedex.api._envelope import RawResponse as _RR

    assert resolve_base_url("anilist") == "https://graphql.anilist.co"
    raw = call(backend="anilist", path="/", method="DELETE", cache=None)
    assert isinstance(raw, _RR)
    assert raw.firewall_rejected is not None
    return True
