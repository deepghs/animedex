"""High-level Shikimori Python API."""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import shikimori as _raw_shikimori
from animedex.backends.shikimori.models import (
    ShikimoriAnime,
    ShikimoriCalendarEntry,
    ShikimoriCharacter,
    ShikimoriClub,
    ShikimoriManga,
    ShikimoriPerson,
    ShikimoriPublisher,
    ShikimoriResource,
    ShikimoriScreenshot,
    ShikimoriStudio,
    ShikimoriTopic,
    ShikimoriVideo,
)
from animedex.cache.sqlite import SqliteCache
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


_DEFAULT_CACHE = None


def _close_default_cache() -> None:
    """Close the lazy Shikimori cache singleton."""
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is not None:
        try:
            _DEFAULT_CACHE.close()
        finally:
            _DEFAULT_CACHE = None


def _default_cache():
    """Return the default SQLite cache for high-level Shikimori calls."""
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        import atexit

        _DEFAULT_CACHE = SqliteCache()
        atexit.register(_close_default_cache)
    return _DEFAULT_CACHE


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="shikimori",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Shikimori GET and parse the JSON body."""
    call_kw = dict(kw)
    if config is not None:
        call_kw.setdefault("no_cache", config.no_cache)
        call_kw.setdefault("cache_ttl", config.cache_ttl_seconds)
        call_kw.setdefault("rate", config.rate)
    no_cache = bool(call_kw.get("no_cache"))
    cache = call_kw.get("cache")
    if not no_cache and cache is None:
        call_kw["cache"] = _default_cache()
    elif no_cache and cache is None:
        call_kw["cache"] = None
    raw = _raw_shikimori.call(path=path, params=params, config=config, **call_kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="shikimori",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:
        raise ApiError("shikimori returned a non-text body", backend="shikimori", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"shikimori 404 on {path}", backend="shikimori", reason="not-found")
    if raw.status == 429:
        raise ApiError(f"shikimori 429 on {path}", backend="shikimori", reason="rate-limited")
    if raw.status >= 500:
        raise ApiError(f"shikimori {raw.status} on {path}", backend="shikimori", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(
            f"shikimori returned non-JSON body: {exc}",
            backend="shikimori",
            reason="upstream-decode",
        ) from exc
    return payload, _src(raw)


def _list(payload: Any) -> List[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    return [payload]


def _params(**kwargs) -> Dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def calendar(
    *,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    censored: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriCalendarEntry]:
    """Upcoming and currently airing schedule via ``/api/calendar``."""
    payload, src = _fetch(
        "/api/calendar", params=_params(page=page, limit=limit, censored=censored), config=config, **kw
    )
    return [ShikimoriCalendarEntry.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def search(
    q: Optional[str] = None,
    *,
    page: Optional[int] = None,
    limit: int = 10,
    order: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    season: Optional[str] = None,
    rating: Optional[str] = None,
    censored: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriAnime]:
    """Search anime via ``/api/animes``."""
    params = _params(
        search=q,
        page=page,
        limit=limit,
        order=order,
        kind=kind,
        status=status,
        season=season,
        rating=rating,
        censored=censored,
    )
    payload, src = _fetch("/api/animes", params=params, config=config, **kw)
    return [ShikimoriAnime.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def show(anime_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriAnime:
    """Fetch one anime by Shikimori ID."""
    payload, src = _fetch(f"/api/animes/{anime_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError("shikimori anime show did not return an object", backend="shikimori", reason="upstream-shape")
    return ShikimoriAnime.model_validate({**payload, "source_tag": src})


def manga_search(
    q: Optional[str] = None,
    *,
    page: Optional[int] = None,
    limit: int = 10,
    order: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    season: Optional[str] = None,
    censored: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriManga]:
    """Search manga via ``/api/mangas``."""
    params = _params(
        search=q,
        page=page,
        limit=limit,
        order=order,
        kind=kind,
        status=status,
        season=season,
        censored=censored,
    )
    payload, src = _fetch("/api/mangas", params=params, config=config, **kw)
    return [ShikimoriManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def manga_show(manga_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriManga:
    """Fetch one manga by Shikimori ID."""
    payload, src = _fetch(f"/api/mangas/{manga_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError("shikimori manga show did not return an object", backend="shikimori", reason="upstream-shape")
    return ShikimoriManga.model_validate({**payload, "source_tag": src})


def ranobe_search(
    q: Optional[str] = None,
    *,
    page: Optional[int] = None,
    limit: int = 10,
    order: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    season: Optional[str] = None,
    censored: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriManga]:
    """Search ranobe via ``/api/ranobe``."""
    params = _params(
        search=q,
        page=page,
        limit=limit,
        order=order,
        kind=kind,
        status=status,
        season=season,
        censored=censored,
    )
    payload, src = _fetch("/api/ranobe", params=params, config=config, **kw)
    return [ShikimoriManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def ranobe_show(ranobe_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriManga:
    """Fetch one ranobe by Shikimori ID."""
    payload, src = _fetch(f"/api/ranobe/{ranobe_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError("shikimori ranobe show did not return an object", backend="shikimori", reason="upstream-shape")
    return ShikimoriManga.model_validate({**payload, "source_tag": src})


def club_search(
    q: Optional[str] = None,
    *,
    page: Optional[int] = None,
    limit: int = 10,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriClub]:
    """Search clubs via ``/api/clubs``."""
    payload, src = _fetch("/api/clubs", params=_params(search=q, page=page, limit=limit), config=config, **kw)
    return [ShikimoriClub.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def club_show(club_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriClub:
    """Fetch one club by Shikimori ID."""
    payload, src = _fetch(f"/api/clubs/{club_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError("shikimori club show did not return an object", backend="shikimori", reason="upstream-shape")
    return ShikimoriClub.model_validate({**payload, "source_tag": src})


def character_search(
    q: Optional[str] = None,
    *,
    limit: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriCharacter]:
    """Search top-level characters via ``/api/characters/search``."""
    payload, src = _fetch("/api/characters/search", params=_params(search=q, limit=limit), config=config, **kw)
    return [ShikimoriCharacter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def character(character_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriCharacter:
    """Fetch one top-level character by Shikimori ID."""
    payload, src = _fetch(f"/api/characters/{character_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "shikimori character show did not return an object",
            backend="shikimori",
            reason="upstream-shape",
        )
    return ShikimoriCharacter.model_validate({**payload, "source_tag": src})


def publishers(*, config: Optional[Config] = None, **kw) -> List[ShikimoriPublisher]:
    """List Shikimori manga publishers."""
    payload, src = _fetch("/api/publishers", config=config, **kw)
    return [ShikimoriPublisher.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def publisher(publisher_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriPublisher:
    """Fetch one publisher from the Shikimori publisher catalogue."""
    rows = publishers(config=config, **kw)
    for row in rows:
        if row.id == publisher_id:
            return row
    raise ApiError(f"shikimori publisher {publisher_id} not found", backend="shikimori", reason="not-found")


def people_search(
    q: Optional[str] = None,
    *,
    limit: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriPerson]:
    """Search top-level people via ``/api/people/search``."""
    payload, src = _fetch("/api/people/search", params=_params(search=q, limit=limit), config=config, **kw)
    return [ShikimoriPerson.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def person(person_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriPerson:
    """Fetch one top-level person by Shikimori ID."""
    payload, src = _fetch(f"/api/people/{person_id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError("shikimori person show did not return an object", backend="shikimori", reason="upstream-shape")
    return ShikimoriPerson.model_validate({**payload, "source_tag": src})


def screenshots(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriScreenshot]:
    """List screenshots for one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/screenshots", config=config, **kw)
    return [ShikimoriScreenshot.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def videos(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriVideo]:
    """List promo and episode-preview videos for one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/videos", config=config, **kw)
    return [ShikimoriVideo.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def roles(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriResource]:
    """List role rows for one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/roles", config=config, **kw)
    return [ShikimoriResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def characters(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriCharacter]:
    """List character references for one anime."""
    rows = roles(anime_id, config=config, **kw)
    out: List[ShikimoriCharacter] = []
    for row in rows:
        raw = row.model_dump(mode="json", by_alias=True)
        character = raw.get("character")
        if isinstance(character, dict):
            out.append(ShikimoriCharacter.model_validate({**character, "source_tag": row.source_tag}))
    return out


def staff(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriPerson]:
    """List staff and voice-person references for one anime."""
    rows = roles(anime_id, config=config, **kw)
    out: List[ShikimoriPerson] = []
    for row in rows:
        raw = row.model_dump(mode="json", by_alias=True)
        person = raw.get("person")
        if isinstance(person, dict):
            out.append(ShikimoriPerson.model_validate({**person, "source_tag": row.source_tag}))
    return out


def similar(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriAnime]:
    """List anime similar to one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/similar", config=config, **kw)
    return [ShikimoriAnime.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def related(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriResource]:
    """List related anime/manga/franchise rows for one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/related", config=config, **kw)
    return [ShikimoriResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def external_links(anime_id: int, *, config: Optional[Config] = None, **kw) -> List[ShikimoriResource]:
    """List external links for one anime."""
    payload, src = _fetch(f"/api/animes/{anime_id}/external_links", config=config, **kw)
    return [ShikimoriResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def topics(
    anime_id: int,
    *,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    kind: Optional[str] = None,
    episode: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[ShikimoriTopic]:
    """List discussion topics for one anime."""
    payload, src = _fetch(
        f"/api/animes/{anime_id}/topics",
        params=_params(page=page, limit=limit, kind=kind, episode=episode),
        config=config,
        **kw,
    )
    return [ShikimoriTopic.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def studios(*, config: Optional[Config] = None, **kw) -> List[ShikimoriStudio]:
    """List Shikimori studios."""
    payload, src = _fetch("/api/studios", config=config, **kw)
    return [ShikimoriStudio.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def studio(studio_id: int, *, config: Optional[Config] = None, **kw) -> ShikimoriStudio:
    """Fetch one studio from the Shikimori studio catalogue."""
    rows = studios(config=config, **kw)
    for row in rows:
        if row.id == studio_id:
            return row
    raise ApiError(f"shikimori studio {studio_id} not found", backend="shikimori", reason="not-found")


def genres(*, config: Optional[Config] = None, **kw) -> List[ShikimoriResource]:
    """List Shikimori genres."""
    payload, src = _fetch("/api/genres", config=config, **kw)
    return [ShikimoriResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def selftest() -> bool:
    """Smoke-test the Shikimori high-level package."""
    from animedex.backends.shikimori import models

    return models.selftest()
