"""High-level Kitsu Python API.

Wraps the eight most-used anonymous JSON:API endpoints on
``kitsu.io/api/edge`` with typed :class:`BackendRichModel`-backed
return shapes.

Kitsu serves both anime and manga catalogues plus a streaming-link
rail and a cross-source mapping table (anilist / mal / anidb / kitsu).
The mapping endpoint is the cheapest way to convert an upstream ID
to its peers, so a downstream pipeline can fan out to any other
backend without reading the same ID from each upstream in turn.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import kitsu as _raw_kitsu
from animedex.backends.kitsu.models import (
    KitsuAnime,
    KitsuCategory,
    KitsuManga,
    KitsuMapping,
    KitsuStreamingLink,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="kitsu",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Kitsu GET, parse the body, validate the JSON:API envelope.

    :return: ``(parsed_payload_dict, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` if the body is non-text.
    """
    raw = _raw_kitsu.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="kitsu",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - kitsu always returns JSON
        raise ApiError("kitsu returned a non-text body", backend="kitsu", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"kitsu 404 on {path}", backend="kitsu", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"kitsu {raw.status} on {path}", backend="kitsu", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(f"kitsu returned non-JSON body: {exc}", backend="kitsu", reason="upstream-decode") from exc
    return payload, _src(raw)


def _data(payload: dict) -> Any:
    """Pull the ``data`` block out of a JSON:API envelope."""
    if "data" not in payload:
        raise ApiError("kitsu response missing 'data' key", backend="kitsu", reason="upstream-shape")
    return payload["data"]


def _list(payload: dict) -> List[dict]:
    """Pull a list-of-resources from the envelope, tolerating
    single-resource responses by wrapping them."""
    rows = _data(payload)
    if rows is None:
        return []
    if isinstance(rows, list):
        return rows
    return [rows]


# ---------- /anime ----------


def show(id: int, *, config: Optional[Config] = None, **kw) -> KitsuAnime:
    """Fetch one anime by its Kitsu numeric ID via ``/anime/{id}``.

    :param id: Kitsu anime ID (the int that appears in
                ``kitsu.io/anime/<slug>`` URLs after the slug
                resolves; numeric only).
    :type id: int
    :return: Typed anime resource, lossless against the upstream
              JSON:API ``data`` block.
    :rtype: KitsuAnime
    """
    payload, src = _fetch(f"/anime/{id}", config=config, **kw)
    return KitsuAnime.model_validate({**_data(payload), "source_tag": src})


def search(q: str, *, limit: int = 10, page: int = 0, config: Optional[Config] = None, **kw) -> List[KitsuAnime]:
    """Free-text anime search via ``/anime?filter[text]=<q>``.

    :param q: Search phrase.
    :type q: str
    :param limit: ``page[limit]`` (defaults to ``10``).
    :type limit: int
    :param page: ``page[offset]`` (defaults to ``0``; not a 1-indexed
                  page number).
    :type page: int
    :return: List of typed anime resources.
    :rtype: list[KitsuAnime]
    """
    params = {"filter[text]": q, "page[limit]": limit, "page[offset]": page}
    payload, src = _fetch("/anime", params=params, config=config, **kw)
    return [KitsuAnime.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def streaming(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuStreamingLink]:
    """Legal streaming links for an anime via ``/anime/{id}/streaming-links``.

    :param id: Kitsu anime ID.
    :type id: int
    :return: List of typed streaming-link resources.
    :rtype: list[KitsuStreamingLink]
    """
    payload, src = _fetch(f"/anime/{id}/streaming-links", config=config, **kw)
    return [KitsuStreamingLink.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def mappings(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuMapping]:
    """Cross-source ID map for an anime via ``/anime/{id}/mappings``.

    Each row carries an ``externalSite`` (e.g. ``"myanimelist/anime"``,
    ``"anilist/anime"``, ``"anidb"``, ``"thetvdb/series"``) and an
    ``externalId`` so a downstream pipeline can fan out across
    upstream catalogues.

    :param id: Kitsu anime ID.
    :type id: int
    :return: List of typed mapping resources.
    :rtype: list[KitsuMapping]
    """
    payload, src = _fetch(f"/anime/{id}/mappings", config=config, **kw)
    return [KitsuMapping.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def trending(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuAnime]:
    """The ``/trending/anime`` rail, evaluated server-side.

    :param limit: Max rows to return (defaults to ``10``).
    :type limit: int
    :return: List of typed anime resources.
    :rtype: list[KitsuAnime]
    """
    params = {"limit": limit}
    payload, src = _fetch("/trending/anime", params=params, config=config, **kw)
    return [KitsuAnime.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /manga ----------


def manga_show(id: int, *, config: Optional[Config] = None, **kw) -> KitsuManga:
    """Fetch one manga by its Kitsu numeric ID via ``/manga/{id}``.

    :param id: Kitsu manga ID.
    :type id: int
    :return: Typed manga resource.
    :rtype: KitsuManga
    """
    payload, src = _fetch(f"/manga/{id}", config=config, **kw)
    return KitsuManga.model_validate({**_data(payload), "source_tag": src})


def manga_search(q: str, *, limit: int = 10, page: int = 0, config: Optional[Config] = None, **kw) -> List[KitsuManga]:
    """Free-text manga search via ``/manga?filter[text]=<q>``.

    :param q: Search phrase.
    :type q: str
    :param limit: ``page[limit]``.
    :type limit: int
    :param page: ``page[offset]``.
    :type page: int
    :return: List of typed manga resources.
    :rtype: list[KitsuManga]
    """
    params = {"filter[text]": q, "page[limit]": limit, "page[offset]": page}
    payload, src = _fetch("/manga", params=params, config=config, **kw)
    return [KitsuManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /categories ----------


def categories(*, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuCategory]:
    """Top-level Kitsu categories via ``/categories``.

    :param limit: ``page[limit]``.
    :type limit: int
    :return: List of typed category resources.
    :rtype: list[KitsuCategory]
    """
    params = {"page[limit]": limit}
    payload, src = _fetch("/categories", params=params, config=config, **kw)
    return [KitsuCategory.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def selftest() -> bool:
    """Smoke-test the public Kitsu Python API (signatures only, no
    network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [show, search, streaming, mappings, trending, manga_show, manga_search, categories]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
