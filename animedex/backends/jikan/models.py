"""Rich Jikan dataclasses (one per response shape).

Jikan exposes ~91 endpoints. Many share response shapes (every
``/anime/{id}/...`` returning a list of records uses the same row
type). the high-level backend layer captures distinct shapes once and reuses them across
endpoints; the mapper layer picks the right shape per call.

The :class:`JikanAnime` ``to_common()`` projects MAL data onto
:class:`~animedex.models.anime.Anime`, including a `duration` parser
("24 min per ep" → 24), an `aired` ISO-string parser, and a
`status` normaliser ("Currently Airing" → "airing").
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from animedex.models.anime import Anime, AnimeRating, AnimeStreamingLink, AnimeTitle
from animedex.models.character import Character
from animedex.models.common import BackendRichModel, SourceTag


# ---------- shared mini-types ----------


class JikanImageJpg(BackendRichModel):
    image_url: Optional[str] = None
    small_image_url: Optional[str] = None
    large_image_url: Optional[str] = None


class JikanImages(BackendRichModel):
    jpg: Optional[JikanImageJpg] = None
    webp: Optional[JikanImageJpg] = None


class JikanTrailerImages(BackendRichModel):
    image_url: Optional[str] = None
    small_image_url: Optional[str] = None
    medium_image_url: Optional[str] = None
    large_image_url: Optional[str] = None
    maximum_image_url: Optional[str] = None


class JikanTrailer(BackendRichModel):
    youtube_id: Optional[str] = None
    url: Optional[str] = None
    embed_url: Optional[str] = None
    images: Optional[JikanTrailerImages] = None


class JikanTitleEntry(BackendRichModel):
    type: str
    title: str


class JikanAiredProp(BackendRichModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


class JikanAiredFromTo(BackendRichModel):
    """``aired.prop`` / ``published.prop`` sub-block.

    ``from`` is a Python keyword, so it's stored as ``from_`` with
    ``alias="from"``. ``populate_by_name=True`` (inherited from
    :class:`BackendRichModel`) lets pydantic accept either name on
    input; ``model_dump(by_alias=True)`` re-emits ``from``.
    """

    from_: Optional[JikanAiredProp] = Field(default=None, alias="from")
    to: Optional[JikanAiredProp] = None


class JikanAired(BackendRichModel):
    """``aired`` / ``published`` block on Jikan anime / manga."""

    from_: Optional[str] = Field(default=None, alias="from")  # ISO-8601
    to: Optional[str] = None
    prop: Optional[JikanAiredFromTo] = None
    string: Optional[str] = None


class JikanBroadcast(BackendRichModel):
    day: Optional[str] = None
    time: Optional[str] = None
    timezone: Optional[str] = None
    string: Optional[str] = None


class JikanEntity(BackendRichModel):
    """Generic ``{ mal_id, type, name, url }`` entity reference used
    across Jikan responses (producers, licensors, studios, genres,
    themes, etc.).

    Some upstream rows omit ``name`` for archival entries; the field
    is left ``Optional`` so the mapper tolerates them rather than
    raising mid-replay.
    """

    mal_id: int
    type: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None


class JikanThemes(BackendRichModel):
    openings: List[str] = []
    endings: List[str] = []


class JikanExternal(BackendRichModel):
    name: str
    url: Optional[str] = None


class JikanRelation(BackendRichModel):
    relation: str
    entry: List[JikanEntity] = []


# ---------- /anime/{id}[/full] ----------


class JikanAnime(BackendRichModel):
    """Full Jikan ``/anime/{id}/full`` response payload (rich)."""

    mal_id: int
    url: Optional[str] = None
    images: Optional[JikanImages] = None
    trailer: Optional[JikanTrailer] = None
    approved: Optional[bool] = None
    titles: List[JikanTitleEntry] = []
    title: str
    title_english: Optional[str] = None
    title_japanese: Optional[str] = None
    title_synonyms: List[str] = []
    type: Optional[str] = None
    source: Optional[str] = None
    episodes: Optional[int] = None
    status: Optional[str] = None
    airing: Optional[bool] = None
    aired: Optional[JikanAired] = None
    duration: Optional[str] = None  # "24 min per ep"
    rating: Optional[str] = None
    score: Optional[float] = None
    scored_by: Optional[int] = None
    rank: Optional[int] = None
    popularity: Optional[int] = None
    members: Optional[int] = None
    favorites: Optional[int] = None
    synopsis: Optional[str] = None
    background: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    broadcast: Optional[JikanBroadcast] = None
    producers: List[JikanEntity] = []
    licensors: List[JikanEntity] = []
    studios: List[JikanEntity] = []
    genres: List[JikanEntity] = []
    explicit_genres: List[JikanEntity] = []
    themes: List[JikanEntity] = []
    demographics: List[JikanEntity] = []
    relations: List[JikanRelation] = []
    theme: Optional[JikanThemes] = None
    external: List[JikanExternal] = []
    streaming: List[JikanExternal] = []
    source_tag: SourceTag

    @staticmethod
    def _parse_duration_minutes(text: Optional[str]) -> Optional[int]:
        """Parse strings like ``"24 min per ep"`` or ``"1 hr 30 min"``."""
        if not text:
            return None
        m = re.search(r"(\d+)\s*hr\D+(\d+)\s*min", text)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        m = re.search(r"(\d+)\s*hr", text)
        if m:
            return int(m.group(1)) * 60
        m = re.search(r"(\d+)\s*min", text)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _parse_iso_date(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalise_status(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s_low = s.lower()
        if "currently airing" in s_low:
            return "airing"
        if "finished" in s_low:
            return "finished"
        if "not yet aired" in s_low:
            return "upcoming"
        if "cancelled" in s_low or "canceled" in s_low:
            return "cancelled"
        if "hiatus" in s_low:
            return "hiatus"
        return "unknown"

    @staticmethod
    def _normalise_format(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s_up = s.upper().replace(" ", "_")
        return s_up if s_up in ("TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC") else None

    def to_common(self) -> Anime:
        title = AnimeTitle(
            romaji=self.title or self.title_english or self.title_japanese or "",
            english=self.title_english,
            native=self.title_japanese,
        )
        score = None
        if self.score is not None:
            score = AnimeRating(score=self.score, scale=10.0, votes=self.scored_by)

        cover = None
        if self.images and self.images.jpg:
            cover = self.images.jpg.large_image_url or self.images.jpg.image_url

        streaming_links: List[AnimeStreamingLink] = []
        for ext in self.streaming:
            if ext.url:
                streaming_links.append(AnimeStreamingLink(provider=ext.name, url=ext.url))

        # tags = themes + demographics + explicit_genres
        tags = (
            [t.name for t in self.themes if t.name]
            + [d.name for d in self.demographics if d.name]
            + [eg.name for eg in self.explicit_genres if eg.name]
        )

        return Anime(
            id=f"jikan:{self.mal_id}",
            title=title,
            score=score,
            episodes=self.episodes,
            studios=[s.name for s in self.studios if s.name],
            streaming=streaming_links,
            description=self.synopsis,
            genres=[g.name for g in self.genres if g.name],
            tags=tags,
            status=self._normalise_status(self.status),
            format=self._normalise_format(self.type),
            season=(self.season.upper() if self.season else None),
            season_year=self.year,
            aired_from=self._parse_iso_date(self.aired.from_ if self.aired else None),
            aired_to=self._parse_iso_date(self.aired.to if self.aired else None),
            duration_minutes=self._parse_duration_minutes(self.duration),
            title_synonyms=list(self.title_synonyms),
            cover_image_url=cover,
            trailer_url=(self.trailer.url if self.trailer else None),
            source_material=(self.source.lower() if self.source else None),
            age_rating=self.rating,
            popularity=self.popularity,
            favourites=self.favorites,
            ids={"mal": str(self.mal_id)},
            source=self.source_tag,
        )


# ---------- /manga/{id}[/full] ----------


class JikanManga(BackendRichModel):
    """``/manga/{id}/full`` response. Same shape as JikanAnime minus
    a few anime-specific fields plus chapter/volume counts."""

    mal_id: int
    url: Optional[str] = None
    images: Optional[JikanImages] = None
    approved: Optional[bool] = None
    titles: List[JikanTitleEntry] = []
    title: str
    title_english: Optional[str] = None
    title_japanese: Optional[str] = None
    title_synonyms: List[str] = []
    type: Optional[str] = None
    chapters: Optional[int] = None
    volumes: Optional[int] = None
    status: Optional[str] = None
    publishing: Optional[bool] = None
    published: Optional[JikanAired] = None
    score: Optional[float] = None
    scored_by: Optional[int] = None
    rank: Optional[int] = None
    popularity: Optional[int] = None
    members: Optional[int] = None
    favorites: Optional[int] = None
    synopsis: Optional[str] = None
    background: Optional[str] = None
    authors: List[JikanEntity] = []
    serializations: List[JikanEntity] = []
    genres: List[JikanEntity] = []
    explicit_genres: List[JikanEntity] = []
    themes: List[JikanEntity] = []
    demographics: List[JikanEntity] = []
    relations: List[JikanRelation] = []
    external: List[JikanExternal] = []
    source_tag: SourceTag


# ---------- characters / people ----------


class JikanCharacterAnimeRole(BackendRichModel):
    role: Optional[str] = None
    anime: Optional[JikanEntity] = None


class JikanCharacterMangaRole(BackendRichModel):
    role: Optional[str] = None
    manga: Optional[JikanEntity] = None


class JikanCharacterVoiceActor(BackendRichModel):
    language: Optional[str] = None
    person: Optional[JikanEntity] = None


class JikanCharacter(BackendRichModel):
    """``/characters/{id}/full`` and ``/characters/{id}``."""

    mal_id: int
    url: Optional[str] = None
    images: Optional[JikanImages] = None
    name: str
    name_kanji: Optional[str] = None
    nicknames: List[str] = []
    favorites: Optional[int] = None
    about: Optional[str] = None
    anime: List[JikanCharacterAnimeRole] = []
    manga: List[JikanCharacterMangaRole] = []
    voices: List[JikanCharacterVoiceActor] = []
    source_tag: SourceTag

    def to_common(self) -> Character:
        # primary role: take first MAIN if present
        role = None
        for r in self.anime:
            if r.role:
                role = r.role
                if r.role.upper() == "MAIN":
                    break
        return Character(
            id=f"jikan:char:{self.mal_id}",
            name=self.name,
            name_native=self.name_kanji,
            name_alternatives=list(self.nicknames),
            role=role,
            image_url=(self.images.jpg.image_url if self.images and self.images.jpg else None),
            description=self.about,
            favourites=self.favorites,
            source=self.source_tag,
        )


class JikanPerson(BackendRichModel):
    """``/people/{id}/full`` and ``/people/{id}``."""

    mal_id: int
    url: Optional[str] = None
    website_url: Optional[str] = None
    images: Optional[JikanImages] = None
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    alternate_names: List[str] = []
    birthday: Optional[str] = None
    favorites: Optional[int] = None
    about: Optional[str] = None
    source_tag: SourceTag


# ---------- producers, magazines, genres, clubs ----------


class JikanProducer(BackendRichModel):
    mal_id: int
    url: Optional[str] = None
    titles: List[JikanTitleEntry] = []
    images: Optional[JikanImages] = None
    favorites: Optional[int] = None
    established: Optional[str] = None
    about: Optional[str] = None
    count: Optional[int] = None
    external: List[JikanExternal] = []
    source_tag: SourceTag


class JikanMagazine(BackendRichModel):
    mal_id: int
    name: str
    url: Optional[str] = None
    count: Optional[int] = None
    source_tag: SourceTag


class JikanGenre(BackendRichModel):
    mal_id: int
    name: str
    url: Optional[str] = None
    count: Optional[int] = None
    source_tag: SourceTag


class JikanClub(BackendRichModel):
    mal_id: int
    name: str
    url: Optional[str] = None
    images: Optional[JikanImages] = None
    members: Optional[int] = None
    category: Optional[str] = None
    created: Optional[str] = None
    access: Optional[str] = None
    source_tag: SourceTag


# ---------- users ----------


class JikanUser(BackendRichModel):
    mal_id: Optional[int] = None
    username: str
    url: Optional[str] = None
    images: Optional[JikanImages] = None
    last_online: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    location: Optional[str] = None
    joined: Optional[str] = None
    about: Optional[str] = None
    source_tag: SourceTag


# ---------- generic envelopes for long-tail endpoints ----------


class JikanGenericRow(BackendRichModel):
    """Pydantic-loose row used by long-tail endpoints (news, forum,
    pictures, statistics, moreinfo, recommendations, userupdates,
    reviews, relations, themes, external, streaming, episodes,
    videos, schedules, watch, recommendations).

    Allows arbitrary upstream fields by setting ``extra='allow'``."""

    model_config = {"populate_by_name": True, "extra": "allow", "frozen": True}


class JikanGenericResponse(BackendRichModel):
    """Wrapper for any Jikan endpoint whose payload is too large /
    unstable to map field-by-field. Carries the parsed ``data`` array
    as a list of permissive rows + the source tag.

    Use sites: ``/anime/{id}/news``, ``/anime/{id}/forum``,
    ``/anime/{id}/videos``, ``/anime/{id}/pictures``,
    ``/anime/{id}/statistics``, ``/anime/{id}/moreinfo``,
    ``/anime/{id}/recommendations``, ``/anime/{id}/userupdates``,
    ``/anime/{id}/reviews``, ``/anime/{id}/relations``,
    ``/anime/{id}/themes``, ``/anime/{id}/external``,
    ``/anime/{id}/streaming``, ``/anime/{id}/episodes``, schedules,
    watch endpoints, club sub-endpoints, user sub-endpoints,
    recommendations, reviews, top-reviews, etc.
    """

    rows: List[JikanGenericRow] = []
    pagination: Optional[JikanGenericRow] = None
    source_tag: SourceTag


def selftest() -> bool:
    """Smoke-test every Jikan dataclass."""
    from datetime import datetime, timezone

    src = SourceTag(backend="jikan", fetched_at=datetime.now(timezone.utc))
    for cls, kwargs in (
        (JikanAnime, {"mal_id": 1, "title": "x"}),
        (JikanManga, {"mal_id": 1, "title": "x"}),
        (JikanCharacter, {"mal_id": 1, "name": "x"}),
        (JikanPerson, {"mal_id": 1, "name": "x"}),
        (JikanProducer, {"mal_id": 1}),
        (JikanMagazine, {"mal_id": 1, "name": "x"}),
        (JikanGenre, {"mal_id": 1, "name": "x"}),
        (JikanClub, {"mal_id": 1, "name": "x"}),
        (JikanUser, {"username": "x"}),
        (JikanGenericResponse, {}),
    ):
        cls.model_validate_json(cls(**kwargs, source_tag=src).model_dump_json())
    return True
