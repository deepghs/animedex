"""High-level AnimeChan Python API.

Thin wrappers over AnimeChan's anonymous read endpoints. The upstream
free tier is limited to 5 requests per hour, so these helpers rely on
the dispatcher cache by default and expose the usual ``no_cache`` /
``cache_ttl`` / ``rate`` kwargs for callers that need to override that
behaviour.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import quote as _raw_quote
from animedex.backends.quote.models import AnimeChanAnime, AnimeChanEnvelope, AnimeChanQuote
from animedex.cache.sqlite import SqliteCache
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


_DEFAULT_CACHE = None


def _close_default_cache() -> None:
    """Close the lazy Quote cache singleton."""
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is not None:
        try:
            _DEFAULT_CACHE.close()
        finally:
            _DEFAULT_CACHE = None


def _default_cache():
    """Return the default SQLite cache for high-level Quote calls."""
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        import atexit

        _DEFAULT_CACHE = SqliteCache()
        atexit.register(_close_default_cache)
    return _DEFAULT_CACHE


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="quote",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue an AnimeChan GET, parse the envelope, validate errors."""
    call_kw = dict(kw)
    if config is not None:
        call_kw.setdefault("no_cache", config.no_cache)
        call_kw.setdefault("cache_ttl", config.cache_ttl_seconds)
        call_kw.setdefault("rate", config.rate)
    no_cache = bool(call_kw.get("no_cache"))
    cache = call_kw.get("cache")
    if not call_kw.get("no_cache") and call_kw.get("cache") is None:
        call_kw["cache"] = _default_cache()
    elif no_cache and cache is None:
        call_kw["cache"] = None
    raw = _raw_quote.call(path=path, params=params, config=config, **call_kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="quote",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - AnimeChan returns JSON
        raise ApiError("AnimeChan returned a non-text body", backend="quote", reason="upstream-decode")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(f"AnimeChan returned non-JSON body: {exc}", backend="quote", reason="upstream-decode") from exc
    if raw.status == 404:
        raise ApiError(f"AnimeChan 404 on {path}", backend="quote", reason="not-found")
    if raw.status == 429:
        msg = payload.get("message") if isinstance(payload, dict) else None
        raise ApiError(msg or "AnimeChan anonymous rate limit exceeded", backend="quote", reason="rate-limited")
    if raw.status >= 500:
        raise ApiError(f"AnimeChan {raw.status} on {path}", backend="quote", reason="upstream-error")
    if raw.status >= 400:
        msg = payload.get("message") if isinstance(payload, dict) else None
        raise ApiError(msg or f"AnimeChan {raw.status} on {path}", backend="quote", reason="upstream-error")
    if not isinstance(payload, dict):
        raise ApiError("AnimeChan response is not a JSON object", backend="quote", reason="upstream-shape")
    if payload.get("status") not in (None, "success"):
        msg = payload.get("message") or "AnimeChan returned an unsuccessful envelope"
        raise ApiError(msg, backend="quote", reason="upstream-error")
    return payload, _src(raw)


def _quote(row: dict, src: SourceTag) -> AnimeChanQuote:
    if not isinstance(row, dict):
        raise ApiError("AnimeChan quote row is not an object", backend="quote", reason="upstream-shape")
    return AnimeChanQuote.model_validate({**row, "source_tag": src})


def _single(payload: dict, src: SourceTag) -> AnimeChanQuote:
    envelope = AnimeChanEnvelope.model_validate({**payload, "source_tag": src})
    if not isinstance(envelope.data, AnimeChanQuote):
        raise ApiError("AnimeChan response did not contain one quote", backend="quote", reason="upstream-shape")
    return envelope.data.model_copy(update={"source_tag": src})


def _list(payload: dict, src: SourceTag) -> List[AnimeChanQuote]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ApiError("AnimeChan response did not contain a quote list", backend="quote", reason="upstream-shape")
    return [_quote(row, src) for row in data]


def random(*, config: Optional[Config] = None, **kw) -> AnimeChanQuote:
    """Return one random AnimeChan quote.

    :return: Typed quote.
    :rtype: AnimeChanQuote
    """
    payload, src = _fetch("/quotes/random", config=config, **kw)
    return _single(payload, src)


def random_by_anime(title: str, *, config: Optional[Config] = None, **kw) -> AnimeChanQuote:
    """Return one random quote filtered to an anime title."""
    _validate_text(title, "anime title")
    payload, src = _fetch("/quotes/random", params={"anime": title}, config=config, **kw)
    return _single(payload, src)


def random_by_character(name: str, *, config: Optional[Config] = None, **kw) -> AnimeChanQuote:
    """Return one random quote filtered to a character name."""
    _validate_text(name, "character name")
    payload, src = _fetch("/quotes/random", params={"character": name}, config=config, **kw)
    return _single(payload, src)


def quotes_by_anime(title: str, *, page: int = 1, config: Optional[Config] = None, **kw) -> List[AnimeChanQuote]:
    """Return one page of quotes filtered to an anime title.

    AnimeChan currently returns five ordered quotes per page.
    """
    _validate_text(title, "anime title")
    _validate_page(page)
    payload, src = _fetch("/quotes", params={"anime": title, "page": page}, config=config, **kw)
    return _list(payload, src)


def quotes_by_character(name: str, *, page: int = 1, config: Optional[Config] = None, **kw) -> List[AnimeChanQuote]:
    """Return one page of quotes filtered to a character name.

    AnimeChan currently returns five ordered quotes per page.
    """
    _validate_text(name, "character name")
    _validate_page(page)
    payload, src = _fetch("/quotes", params={"character": name, "page": page}, config=config, **kw)
    return _list(payload, src)


def anime(identifier: str, *, config: Optional[Config] = None, **kw) -> AnimeChanAnime:
    """Return AnimeChan's anime information by ID or name.

    The upstream recommends ID lookup for accuracy; name lookup is
    accepted but may return a fuzzy match.
    """
    _validate_text(identifier, "anime identifier")
    payload, src = _fetch(f"/anime/{identifier}", config=config, **kw)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ApiError("AnimeChan anime response did not contain an object", backend="quote", reason="upstream-shape")
    return AnimeChanAnime.model_validate({**data, "source_tag": src})


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ApiError(f"AnimeChan {label} must be non-empty", backend="quote", reason="bad-args")


def _validate_page(page: int) -> None:
    if not isinstance(page, int) or page < 1:
        raise ApiError(f"AnimeChan page must be an integer >= 1; got {page!r}", backend="quote", reason="bad-args")


def selftest() -> bool:
    """Smoke-test the public AnimeChan Python API (signatures only).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [random, random_by_anime, random_by_character, quotes_by_anime, quotes_by_character, anime]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    assert callable(_default_cache)
    return True
