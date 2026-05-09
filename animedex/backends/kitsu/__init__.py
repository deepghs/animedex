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
    KitsuCharacter,
    KitsuFranchise,
    KitsuGenre,
    KitsuManga,
    KitsuMapping,
    KitsuPerson,
    KitsuProducer,
    KitsuRelatedResource,
    KitsuStreamer,
    KitsuStreamingLink,
    KitsuUser,
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


# ---------- /anime/{id}/<sub> ----------


def anime_characters(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Cast for one anime via ``/anime/{id}/characters``."""
    payload, src = _fetch(f"/anime/{id}/characters", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_staff(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Production staff for one anime via ``/anime/{id}/staff``."""
    payload, src = _fetch(f"/anime/{id}/staff", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_episodes(id: int, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Episode list for one anime via ``/anime/{id}/episodes``."""
    payload, src = _fetch(f"/anime/{id}/episodes", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_reviews(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """User reviews for one anime via ``/anime/{id}/reviews``."""
    payload, src = _fetch(f"/anime/{id}/reviews", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_genres(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuGenre]:
    """Genres tagged on one anime via ``/anime/{id}/genres``."""
    payload, src = _fetch(f"/anime/{id}/genres", config=config, **kw)
    return [KitsuGenre.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_categories(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuCategory]:
    """Categories tagged on one anime via ``/anime/{id}/categories``."""
    payload, src = _fetch(f"/anime/{id}/categories", config=config, **kw)
    return [KitsuCategory.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_relations(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Sequel / prequel / spin-off relationships via
    ``/anime/{id}/media-relationships``."""
    payload, src = _fetch(f"/anime/{id}/media-relationships", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def anime_productions(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Producer / studio / licensor list via
    ``/anime/{id}/anime-productions``."""
    payload, src = _fetch(f"/anime/{id}/anime-productions", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /manga/{id}/<sub> ----------


def manga_characters(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Cast for one manga via ``/manga/{id}/characters``."""
    payload, src = _fetch(f"/manga/{id}/characters", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def manga_staff(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Production staff for one manga via ``/manga/{id}/staff``."""
    payload, src = _fetch(f"/manga/{id}/staff", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def manga_chapters(id: int, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Chapter list for one manga via ``/manga/{id}/chapters``."""
    payload, src = _fetch(f"/manga/{id}/chapters", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def manga_genres(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuGenre]:
    """Genres tagged on one manga via ``/manga/{id}/genres``."""
    payload, src = _fetch(f"/manga/{id}/genres", config=config, **kw)
    return [KitsuGenre.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /characters ----------


def character(id: int, *, config: Optional[Config] = None, **kw) -> KitsuCharacter:
    """One character by Kitsu ID via ``/characters/{id}``."""
    payload, src = _fetch(f"/characters/{id}", config=config, **kw)
    return KitsuCharacter.model_validate({**_data(payload), "source_tag": src})


def character_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 0, config: Optional[Config] = None, **kw
) -> List[KitsuCharacter]:
    """Free-text character search via ``/characters?filter[name]=<q>``."""
    params: Dict[str, Any] = {"page[limit]": limit, "page[offset]": page}
    if q:
        params["filter[name]"] = q
    payload, src = _fetch("/characters", params=params, config=config, **kw)
    return [KitsuCharacter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /people ----------


def person(id: int, *, config: Optional[Config] = None, **kw) -> KitsuPerson:
    """One person (VA / staff) by Kitsu ID via ``/people/{id}``."""
    payload, src = _fetch(f"/people/{id}", config=config, **kw)
    return KitsuPerson.model_validate({**_data(payload), "source_tag": src})


def person_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 0, config: Optional[Config] = None, **kw
) -> List[KitsuPerson]:
    """Free-text person search via ``/people?filter[name]=<q>``."""
    params: Dict[str, Any] = {"page[limit]": limit, "page[offset]": page}
    if q:
        params["filter[name]"] = q
    payload, src = _fetch("/people", params=params, config=config, **kw)
    return [KitsuPerson.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def person_voices(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Voice-acting credits for one person via ``/people/{id}/voices``."""
    payload, src = _fetch(f"/people/{id}/voices", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def person_castings(id: int, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """Production-staff credits for one person via
    ``/people/{id}/castings``."""
    payload, src = _fetch(f"/people/{id}/castings", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /producers, /genres, /streamers, /franchises ----------


def producer(id: int, *, config: Optional[Config] = None, **kw) -> KitsuProducer:
    """One producer by Kitsu ID via ``/producers/{id}``."""
    payload, src = _fetch(f"/producers/{id}", config=config, **kw)
    return KitsuProducer.model_validate({**_data(payload), "source_tag": src})


def producers(*, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuProducer]:
    """All producers via ``/producers``."""
    payload, src = _fetch("/producers", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuProducer.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def genre(id: int, *, config: Optional[Config] = None, **kw) -> KitsuGenre:
    """One genre by Kitsu ID via ``/genres/{id}``."""
    payload, src = _fetch(f"/genres/{id}", config=config, **kw)
    return KitsuGenre.model_validate({**_data(payload), "source_tag": src})


def genres(*, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuGenre]:
    """All genres (legacy taxonomy; the richer one is `categories`)."""
    payload, src = _fetch("/genres", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuGenre.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def category(id: int, *, config: Optional[Config] = None, **kw) -> KitsuCategory:
    """One category by Kitsu ID via ``/categories/{id}``."""
    payload, src = _fetch(f"/categories/{id}", config=config, **kw)
    return KitsuCategory.model_validate({**_data(payload), "source_tag": src})


def streamers(*, config: Optional[Config] = None, **kw) -> List[KitsuStreamer]:
    """All registered streamers via ``/streamers``."""
    payload, src = _fetch("/streamers", config=config, **kw)
    return [KitsuStreamer.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def franchise(id: int, *, config: Optional[Config] = None, **kw) -> KitsuFranchise:
    """One franchise by Kitsu ID via ``/franchises/{id}``."""
    payload, src = _fetch(f"/franchises/{id}", config=config, **kw)
    return KitsuFranchise.model_validate({**_data(payload), "source_tag": src})


def franchises(*, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuFranchise]:
    """All franchises via ``/franchises``."""
    payload, src = _fetch("/franchises", params={"page[limit]": limit}, config=config, **kw)
    return [KitsuFranchise.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /trending/manga ----------


def trending_manga(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[KitsuManga]:
    """The ``/trending/manga`` rail."""
    payload, src = _fetch("/trending/manga", params={"limit": limit}, config=config, **kw)
    return [KitsuManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /users (public read) ----------


def user(id: int, *, config: Optional[Config] = None, **kw) -> KitsuUser:
    """One user's public profile via ``/users/{id}``.

    Public fields only; the upstream silently strips private ones
    when no auth is presented.
    """
    payload, src = _fetch(f"/users/{id}", config=config, **kw)
    return KitsuUser.model_validate({**_data(payload), "source_tag": src})


def user_library(user_id: int, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """A user's public anime/manga library via
    ``/library-entries?filter[user_id]=<id>``."""
    params = {"filter[user_id]": user_id, "page[limit]": limit}
    payload, src = _fetch("/library-entries", params=params, config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def user_stats(id: int, *, config: Optional[Config] = None, **kw) -> List[KitsuRelatedResource]:
    """A user's public consumption stats via ``/users/{id}/stats``."""
    payload, src = _fetch(f"/users/{id}/stats", config=config, **kw)
    return [KitsuRelatedResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def selftest() -> bool:
    """Smoke-test the public Kitsu Python API (signatures only, no
    network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [
        show,
        search,
        streaming,
        mappings,
        trending,
        manga_show,
        manga_search,
        categories,
        anime_characters,
        anime_staff,
        anime_episodes,
        anime_reviews,
        anime_genres,
        anime_categories,
        anime_relations,
        anime_productions,
        manga_characters,
        manga_staff,
        manga_chapters,
        manga_genres,
        character,
        character_search,
        person,
        person_search,
        person_voices,
        person_castings,
        producer,
        producers,
        genre,
        genres,
        category,
        streamers,
        franchise,
        franchises,
        trending_manga,
        user,
        user_library,
        user_stats,
    ]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
