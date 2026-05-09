"""High-level Jikan Python API.

Covers every anonymous Jikan v4 endpoint. Core entities (anime, manga,
character, person, producer, magazine, genre, club, user) get
typed dataclass returns; long-tail sub-endpoints (news, forum,
videos, pictures, statistics, ...) return
:class:`~animedex.backends.jikan.models.JikanGenericResponse` (a
permissive ``extra='allow'`` envelope).

The Jikan v4 API is fully anonymous; no token branch exists.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import jikan as _raw_jikan
from animedex.backends.jikan.models import (
    JikanAnime,
    JikanCharacter,
    JikanClub,
    JikanGenericResponse,
    JikanGenericRow,
    JikanGenre,
    JikanMagazine,
    JikanManga,
    JikanPerson,
    JikanProducer,
    JikanUser,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="jikan",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Jikan GET, parse the body, validate the envelope.

    :return: ``(parsed_payload_dict, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` if body is non-text.
    """
    raw = _raw_jikan.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="jikan",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:
        raise ApiError("Jikan returned a non-text body", backend="jikan", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"Jikan 404 on {path}", backend="jikan", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"Jikan {raw.status} on {path}", backend="jikan", reason="upstream-error")
    payload = _json.loads(raw.body_text)
    return payload, _src(raw)


def _data(payload: dict) -> Any:
    """Pull the ``data`` block out of a Jikan envelope."""
    if "data" not in payload:
        raise ApiError("Jikan response missing 'data' key", backend="jikan", reason="upstream-shape")
    return payload["data"]


def _generic(payload: dict, src: SourceTag) -> JikanGenericResponse:
    rows = _data(payload)
    if not isinstance(rows, list):
        rows = [rows]
    return JikanGenericResponse(
        rows=[
            JikanGenericRow.model_validate(r) if isinstance(r, dict) else JikanGenericRow.model_validate({"value": r})
            for r in rows
        ],
        pagination=JikanGenericRow.model_validate(payload.get("pagination") or {}),
        source_tag=src,
    )


# ---------- /anime ----------


def show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanAnime:
    """Fetch ``/anime/{mal_id}/full``."""
    payload, src = _fetch(f"/anime/{mal_id}/full", config=config, **kw)
    return JikanAnime.model_validate({**_data(payload), "source_tag": src})


def search(
    q: Optional[str] = None,
    *,
    type: Optional[str] = None,
    status: Optional[str] = None,
    rating: Optional[str] = None,
    sfw: Optional[bool] = None,
    genres: Optional[str] = None,
    order_by: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 10,
    page: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[JikanAnime]:
    """Search ``/anime``."""
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    if type is not None:
        params["type"] = type
    if status is not None:
        params["status"] = status
    if rating is not None:
        params["rating"] = rating
    if sfw is not None:
        params["sfw"] = "true" if sfw else "false"
    if genres is not None:
        params["genres"] = genres
    if order_by is not None:
        params["order_by"] = order_by
    if sort is not None:
        params["sort"] = sort
    payload, src = _fetch("/anime", params=params, config=config, **kw)
    return [JikanAnime.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def anime_characters(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/characters", config=config, **kw)
    return _generic(payload, src)


def anime_staff(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/staff", config=config, **kw)
    return _generic(payload, src)


def anime_episodes(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/episodes", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def anime_episode(mal_id: int, episode: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/episodes/{episode}", config=config, **kw)
    return _generic(payload, src)


def anime_news(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/news", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def anime_forum(
    mal_id: int, *, filter: Optional[str] = None, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    params = {"filter": filter} if filter else None
    payload, src = _fetch(f"/anime/{mal_id}/forum", params=params, config=config, **kw)
    return _generic(payload, src)


def anime_videos(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/videos", config=config, **kw)
    return _generic(payload, src)


def anime_videos_episodes(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/videos/episodes", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def anime_pictures(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/pictures", config=config, **kw)
    return _generic(payload, src)


def anime_statistics(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/statistics", config=config, **kw)
    return _generic(payload, src)


def anime_moreinfo(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/moreinfo", config=config, **kw)
    return _generic(payload, src)


def anime_recommendations(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/recommendations", config=config, **kw)
    return _generic(payload, src)


def anime_userupdates(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/userupdates", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def anime_reviews(
    mal_id: int,
    *,
    page: int = 1,
    preliminary: Optional[bool] = None,
    spoilers: Optional[bool] = None,
    config: Optional[Config] = None,
    **kw,
) -> JikanGenericResponse:
    params: Dict[str, Any] = {"page": page}
    if preliminary is not None:
        params["preliminary"] = "true" if preliminary else "false"
    if spoilers is not None:
        params["spoilers"] = "true" if spoilers else "false"
    payload, src = _fetch(f"/anime/{mal_id}/reviews", params=params, config=config, **kw)
    return _generic(payload, src)


def anime_relations(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/relations", config=config, **kw)
    return _generic(payload, src)


def anime_themes(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/themes", config=config, **kw)
    return _generic(payload, src)


def anime_external(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/external", config=config, **kw)
    return _generic(payload, src)


def anime_streaming(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/anime/{mal_id}/streaming", config=config, **kw)
    return _generic(payload, src)


# ---------- /manga ----------


def manga_show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanManga:
    """Fetch ``/manga/{mal_id}/full``."""
    payload, src = _fetch(f"/manga/{mal_id}/full", config=config, **kw)
    return JikanManga.model_validate({**_data(payload), "source_tag": src})


def manga_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanManga]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/manga", params=params, config=config, **kw)
    return [JikanManga.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def manga_characters(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/characters", config=config, **kw)
    return _generic(payload, src)


def manga_news(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/news", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def manga_forum(
    mal_id: int, *, filter: Optional[str] = None, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    params = {"filter": filter} if filter else None
    payload, src = _fetch(f"/manga/{mal_id}/forum", params=params, config=config, **kw)
    return _generic(payload, src)


def manga_pictures(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/pictures", config=config, **kw)
    return _generic(payload, src)


def manga_statistics(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/statistics", config=config, **kw)
    return _generic(payload, src)


def manga_moreinfo(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/moreinfo", config=config, **kw)
    return _generic(payload, src)


def manga_recommendations(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/recommendations", config=config, **kw)
    return _generic(payload, src)


def manga_userupdates(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/userupdates", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def manga_reviews(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/reviews", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def manga_relations(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/relations", config=config, **kw)
    return _generic(payload, src)


def manga_external(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/manga/{mal_id}/external", config=config, **kw)
    return _generic(payload, src)


# ---------- /characters ----------


def character_show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanCharacter:
    """Fetch ``/characters/{mal_id}/full``."""
    payload, src = _fetch(f"/characters/{mal_id}/full", config=config, **kw)
    return JikanCharacter.model_validate({**_data(payload), "source_tag": src})


def character_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanCharacter]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/characters", params=params, config=config, **kw)
    return [JikanCharacter.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def character_anime(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/characters/{mal_id}/anime", config=config, **kw)
    return _generic(payload, src)


def character_manga(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/characters/{mal_id}/manga", config=config, **kw)
    return _generic(payload, src)


def character_voices(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/characters/{mal_id}/voices", config=config, **kw)
    return _generic(payload, src)


def character_pictures(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/characters/{mal_id}/pictures", config=config, **kw)
    return _generic(payload, src)


# ---------- /people ----------


def person_show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanPerson:
    """Fetch ``/people/{mal_id}/full``."""
    payload, src = _fetch(f"/people/{mal_id}/full", config=config, **kw)
    return JikanPerson.model_validate({**_data(payload), "source_tag": src})


def person_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanPerson]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/people", params=params, config=config, **kw)
    return [JikanPerson.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def person_anime(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/people/{mal_id}/anime", config=config, **kw)
    return _generic(payload, src)


def person_voices(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/people/{mal_id}/voices", config=config, **kw)
    return _generic(payload, src)


def person_manga(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/people/{mal_id}/manga", config=config, **kw)
    return _generic(payload, src)


def person_pictures(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/people/{mal_id}/pictures", config=config, **kw)
    return _generic(payload, src)


# ---------- producers / magazines / genres / clubs ----------


def producer_show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanProducer:
    payload, src = _fetch(f"/producers/{mal_id}/full", config=config, **kw)
    return JikanProducer.model_validate({**_data(payload), "source_tag": src})


def producer_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanProducer]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/producers", params=params, config=config, **kw)
    return [JikanProducer.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def producer_external(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/producers/{mal_id}/external", config=config, **kw)
    return _generic(payload, src)


def magazines(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanMagazine]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/magazines", params=params, config=config, **kw)
    return [JikanMagazine.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def genres_anime(*, filter: Optional[str] = None, config: Optional[Config] = None, **kw) -> List[JikanGenre]:
    params = {"filter": filter} if filter else None
    payload, src = _fetch("/genres/anime", params=params, config=config, **kw)
    return [JikanGenre.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def genres_manga(*, filter: Optional[str] = None, config: Optional[Config] = None, **kw) -> List[JikanGenre]:
    params = {"filter": filter} if filter else None
    payload, src = _fetch("/genres/manga", params=params, config=config, **kw)
    return [JikanGenre.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def clubs(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> List[JikanClub]:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/clubs", params=params, config=config, **kw)
    return [JikanClub.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def club_show(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanClub:
    payload, src = _fetch(f"/clubs/{mal_id}", config=config, **kw)
    return JikanClub.model_validate({**_data(payload), "source_tag": src})


def club_members(mal_id: int, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/clubs/{mal_id}/members", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def club_staff(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/clubs/{mal_id}/staff", config=config, **kw)
    return _generic(payload, src)


def club_relations(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/clubs/{mal_id}/relations", config=config, **kw)
    return _generic(payload, src)


# ---------- /users ----------


def user_show(username: str, *, config: Optional[Config] = None, **kw) -> JikanUser:
    payload, src = _fetch(f"/users/{username}/full", config=config, **kw)
    return JikanUser.model_validate({**_data(payload), "source_tag": src})


def user_basic(username: str, *, config: Optional[Config] = None, **kw) -> JikanUser:
    payload, src = _fetch(f"/users/{username}", config=config, **kw)
    return JikanUser.model_validate({**_data(payload), "source_tag": src})


def user_statistics(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/statistics", config=config, **kw)
    return _generic(payload, src)


def user_favorites(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/favorites", config=config, **kw)
    return _generic(payload, src)


def user_userupdates(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/userupdates", config=config, **kw)
    return _generic(payload, src)


def user_about(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/about", config=config, **kw)
    return _generic(payload, src)


def user_history(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/history", config=config, **kw)
    return _generic(payload, src)


def user_friends(username: str, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/friends", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def user_reviews(username: str, *, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/reviews", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def user_recommendations(
    username: str, *, page: int = 1, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/recommendations", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def user_clubs(username: str, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/{username}/clubs", config=config, **kw)
    return _generic(payload, src)


def user_search(
    q: Optional[str] = None, *, limit: int = 10, page: int = 1, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if q is not None:
        params["q"] = q
    payload, src = _fetch("/users", params=params, config=config, **kw)
    return _generic(payload, src)


def user_by_mal_id(mal_id: int, *, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch(f"/users/userbyid/{mal_id}", config=config, **kw)
    return _generic(payload, src)


# ---------- /seasons ----------


def seasons_list(*, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/seasons", config=config, **kw)
    return _generic(payload, src)


def seasons_now(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanAnime]:
    payload, src = _fetch("/seasons/now", params={"limit": limit}, config=config, **kw)
    return [JikanAnime.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def seasons_upcoming(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanAnime]:
    payload, src = _fetch("/seasons/upcoming", params={"limit": limit}, config=config, **kw)
    return [JikanAnime.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def season(year: int, season: str, *, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanAnime]:
    payload, src = _fetch(f"/seasons/{year}/{season.lower()}", params={"limit": limit}, config=config, **kw)
    return [JikanAnime.model_validate({**r, "source_tag": src}) for r in _data(payload)]


# ---------- /top ----------


def top_anime(
    *, type: Optional[str] = None, filter: Optional[str] = None, limit: int = 10, config: Optional[Config] = None, **kw
) -> List[JikanAnime]:
    params: Dict[str, Any] = {"limit": limit}
    if type is not None:
        params["type"] = type
    if filter is not None:
        params["filter"] = filter
    payload, src = _fetch("/top/anime", params=params, config=config, **kw)
    return [JikanAnime.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def top_manga(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanManga]:
    payload, src = _fetch("/top/manga", params={"limit": limit}, config=config, **kw)
    return [JikanManga.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def top_characters(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanCharacter]:
    payload, src = _fetch("/top/characters", params={"limit": limit}, config=config, **kw)
    return [JikanCharacter.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def top_people(*, limit: int = 10, config: Optional[Config] = None, **kw) -> List[JikanPerson]:
    payload, src = _fetch("/top/people", params={"limit": limit}, config=config, **kw)
    return [JikanPerson.model_validate({**r, "source_tag": src}) for r in _data(payload)]


def top_reviews(
    *, type: Optional[str] = None, limit: int = 10, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    params: Dict[str, Any] = {"limit": limit}
    if type is not None:
        params["type"] = type
    payload, src = _fetch("/top/reviews", params=params, config=config, **kw)
    return _generic(payload, src)


# ---------- /schedules /random /recommendations /reviews /watch ----------


def schedules(
    *, filter: Optional[str] = None, limit: int = 10, config: Optional[Config] = None, **kw
) -> JikanGenericResponse:
    params: Dict[str, Any] = {"limit": limit}
    if filter is not None:
        params["filter"] = filter
    payload, src = _fetch("/schedules", params=params, config=config, **kw)
    return _generic(payload, src)


def random_anime(*, config: Optional[Config] = None, **kw) -> JikanAnime:
    payload, src = _fetch("/random/anime", config=config, **kw)
    return JikanAnime.model_validate({**_data(payload), "source_tag": src})


def random_manga(*, config: Optional[Config] = None, **kw) -> JikanManga:
    payload, src = _fetch("/random/manga", config=config, **kw)
    return JikanManga.model_validate({**_data(payload), "source_tag": src})


def random_character(*, config: Optional[Config] = None, **kw) -> JikanCharacter:
    payload, src = _fetch("/random/characters", config=config, **kw)
    return JikanCharacter.model_validate({**_data(payload), "source_tag": src})


def random_person(*, config: Optional[Config] = None, **kw) -> JikanPerson:
    payload, src = _fetch("/random/people", config=config, **kw)
    return JikanPerson.model_validate({**_data(payload), "source_tag": src})


def random_user(*, config: Optional[Config] = None, **kw) -> JikanUser:
    payload, src = _fetch("/random/users", config=config, **kw)
    return JikanUser.model_validate({**_data(payload), "source_tag": src})


def recommendations_anime(*, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/recommendations/anime", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def recommendations_manga(*, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/recommendations/manga", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def reviews_anime(*, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/reviews/anime", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def reviews_manga(*, page: int = 1, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/reviews/manga", params={"page": page}, config=config, **kw)
    return _generic(payload, src)


def watch_episodes(*, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/watch/episodes", config=config, **kw)
    return _generic(payload, src)


def watch_episodes_popular(*, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/watch/episodes/popular", config=config, **kw)
    return _generic(payload, src)


def watch_promos(*, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/watch/promos", config=config, **kw)
    return _generic(payload, src)


def watch_promos_popular(*, config: Optional[Config] = None, **kw) -> JikanGenericResponse:
    payload, src = _fetch("/watch/promos/popular", config=config, **kw)
    return _generic(payload, src)


def selftest() -> bool:
    """Smoke-test the Jikan public API (signatures only, no network)."""
    import inspect

    public_callables = [
        show,
        search,
        anime_characters,
        anime_staff,
        anime_episodes,
        anime_episode,
        anime_news,
        anime_forum,
        anime_videos,
        anime_videos_episodes,
        anime_pictures,
        anime_statistics,
        anime_moreinfo,
        anime_recommendations,
        anime_userupdates,
        anime_reviews,
        anime_relations,
        anime_themes,
        anime_external,
        anime_streaming,
        manga_show,
        manga_search,
        manga_characters,
        manga_news,
        manga_forum,
        manga_pictures,
        manga_statistics,
        manga_moreinfo,
        manga_recommendations,
        manga_userupdates,
        manga_reviews,
        manga_relations,
        manga_external,
        character_show,
        character_search,
        character_anime,
        character_manga,
        character_voices,
        character_pictures,
        person_show,
        person_search,
        person_anime,
        person_voices,
        person_manga,
        person_pictures,
        producer_show,
        producer_search,
        producer_external,
        magazines,
        genres_anime,
        genres_manga,
        clubs,
        club_show,
        club_members,
        club_staff,
        club_relations,
        user_show,
        user_basic,
        user_statistics,
        user_favorites,
        user_userupdates,
        user_about,
        user_history,
        user_friends,
        user_reviews,
        user_recommendations,
        user_clubs,
        user_search,
        user_by_mal_id,
        seasons_list,
        seasons_now,
        seasons_upcoming,
        season,
        top_anime,
        top_manga,
        top_characters,
        top_people,
        top_reviews,
        schedules,
        random_anime,
        random_manga,
        random_character,
        random_person,
        random_user,
        recommendations_anime,
        recommendations_manga,
        reviews_anime,
        reviews_manga,
        watch_episodes,
        watch_episodes_popular,
        watch_promos,
        watch_promos_popular,
    ]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    assert len(public_callables) >= 80, f"Jikan API surface too small: {len(public_callables)}"
    return True
