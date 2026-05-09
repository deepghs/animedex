"""Rich Shikimori dataclasses."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from animedex.models.anime import Anime, AnimeRating, AnimeTitle, NextAiringEpisode
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import BackendRichModel, SourceTag


class ShikimoriImage(BackendRichModel):
    """Image URL block used by Shikimori resources."""

    original: Optional[str] = None
    preview: Optional[str] = None
    x96: Optional[str] = None
    x48: Optional[str] = None


class ShikimoriEntity(BackendRichModel):
    """Generic Shikimori entity reference."""

    id: Optional[int] = None
    name: Optional[str] = None
    russian: Optional[str] = None
    image: Optional[ShikimoriImage] = None
    url: Optional[str] = None
    kind: Optional[str] = None
    entry_type: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class ShikimoriStudio(BackendRichModel):
    """Studio record."""

    id: int
    name: Optional[str] = None
    filtered_name: Optional[str] = None
    real: Optional[bool] = None
    image: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Studio:
        """Project the studio onto the common studio shape."""
        return Studio(
            id=f"shikimori:studio:{self.id}",
            name=self.filtered_name or self.name or "",
            is_animation_studio=self.real,
            source=self.source_tag or _default_src(),
        )


class ShikimoriVideo(BackendRichModel):
    """Video row from ``/api/animes/{id}/videos``."""

    id: Optional[int] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    player_url: Optional[str] = None
    name: Optional[str] = None
    kind: Optional[str] = None
    hosting: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class ShikimoriScreenshot(BackendRichModel):
    """Screenshot row from ``/api/animes/{id}/screenshots``."""

    original: Optional[str] = None
    preview: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class ShikimoriCharacter(BackendRichModel):
    """Character reference from anime roles."""

    id: int
    name: Optional[str] = None
    russian: Optional[str] = None
    image: Optional[ShikimoriImage] = None
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Character:
        """Project this character onto the common character shape."""
        return Character(
            id=f"shikimori:character:{self.id}",
            name=self.name or self.russian or "",
            name_native=self.russian,
            image_url=_absolute_url(self.image.original if self.image else None),
            source=self.source_tag or _default_src(),
        )


class ShikimoriPerson(BackendRichModel):
    """Person reference from anime roles."""

    id: int
    name: Optional[str] = None
    russian: Optional[str] = None
    image: Optional[ShikimoriImage] = None
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Staff:
        """Project this person onto the common staff shape."""
        return Staff(
            id=f"shikimori:person:{self.id}",
            name=self.name or self.russian or "",
            name_native=self.russian,
            image_url=_absolute_url(self.image.original if self.image else None),
            source=self.source_tag or _default_src(),
        )


class ShikimoriRole(BackendRichModel):
    """Role row from ``/api/animes/{id}/roles``."""

    roles: List[str] = []
    roles_russian: List[str] = []
    character: Optional[ShikimoriCharacter] = None
    person: Optional[ShikimoriPerson] = None
    source_tag: Optional[SourceTag] = None


class ShikimoriAnime(BackendRichModel):
    """Anime record from ``/api/animes`` and ``/api/animes/{id}``."""

    id: int
    name: Optional[str] = None
    russian: Optional[str] = None
    image: Optional[ShikimoriImage] = None
    url: Optional[str] = None
    kind: Optional[str] = None
    score: Optional[str] = None
    status: Optional[str] = None
    episodes: Optional[int] = None
    episodes_aired: Optional[int] = None
    aired_on: Optional[str] = None
    released_on: Optional[str] = None
    rating: Optional[str] = None
    english: List[Optional[str]] = []
    japanese: List[Optional[str]] = []
    synonyms: List[str] = []
    duration: Optional[int] = None
    description: Optional[str] = None
    description_html: Optional[str] = None
    franchise: Optional[str] = None
    favoured: Optional[bool] = None
    anons: Optional[bool] = None
    ongoing: Optional[bool] = None
    myanimelist_id: Optional[int] = None
    rates_scores_stats: List[Dict[str, Any]] = []
    rates_statuses_stats: List[Dict[str, Any]] = []
    updated_at: Optional[str] = None
    next_episode_at: Optional[str] = None
    fansubbers: List[str] = []
    fandubbers: List[str] = []
    licensors: List[str] = []
    genres: List[ShikimoriEntity] = []
    studios: List[ShikimoriStudio] = []
    videos: List[ShikimoriVideo] = []
    screenshots: List[ShikimoriScreenshot] = []
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Anime:
        """Project this Shikimori anime onto the common anime shape."""
        title = self.name or _first_string(self.english) or self.russian or ""
        score = _parse_float(self.score)
        return Anime(
            id=f"shikimori:{self.id}",
            title=AnimeTitle(romaji=title, english=_first_string(self.english), native=_first_string(self.japanese)),
            score=AnimeRating(score=score, scale=10.0, votes=_score_votes(self.rates_scores_stats))
            if score is not None
            else None,
            episodes=self.episodes,
            studios=[
                studio.filtered_name or studio.name or ""
                for studio in self.studios
                if studio.filtered_name or studio.name
            ],
            description=self.description,
            genres=[genre.name for genre in self.genres if genre.name],
            status=_normalise_status(self.status),
            format=_normalise_format(self.kind),
            aired_from=_parse_date(self.aired_on),
            aired_to=_parse_date(self.released_on),
            duration_minutes=self.duration,
            cover_image_url=_absolute_url(self.image.original if self.image else None),
            trailer_url=self.videos[0].url if self.videos else None,
            age_rating=self.rating,
            title_synonyms=[s for s in self.synonyms if s],
            ids={"shikimori": str(self.id), **({"mal": str(self.myanimelist_id)} if self.myanimelist_id else {})},
            source=self.source_tag or _default_src(),
        )


class ShikimoriCalendarEntry(BackendRichModel):
    """Calendar row from ``/api/calendar``."""

    next_episode: Optional[int] = None
    next_episode_at: Optional[str] = None
    duration: Optional[int] = None
    anime: Optional[ShikimoriAnime] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Anime:
        """Project the nested anime onto the common anime shape."""
        anime = self.anime or ShikimoriAnime(id=0)
        common = anime.to_common()
        airing_at = _parse_datetime(self.next_episode_at)
        if airing_at is None or self.next_episode is None:
            return common
        return common.model_copy(
            update={
                "next_airing_episode": NextAiringEpisode(
                    airing_at=airing_at,
                    time_until_airing_seconds=0,
                    episode=self.next_episode,
                )
            }
        )


class ShikimoriTopic(BackendRichModel):
    """Topic row from anime, manga, or global topic endpoints."""

    id: Optional[int] = None
    topic_title: Optional[str] = None
    body: Optional[str] = None
    html_body: Optional[str] = None
    type: Optional[str] = None
    linked_id: Optional[int] = None
    linked_type: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class ShikimoriResource(BackendRichModel):
    """Generic Shikimori response row for heterogeneous endpoints."""

    id: Optional[Any] = None
    source_tag: Optional[SourceTag] = None


def _default_src() -> SourceTag:
    """Construct a fallback source tag for direct model use."""
    from datetime import datetime, timezone

    return SourceTag(backend="shikimori", fetched_at=datetime.now(timezone.utc))


def _absolute_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return "https://shikimori.io" + path


def _first_string(values: List[Optional[str]]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_votes(rows: List[Dict[str, Any]]) -> Optional[int]:
    total = 0
    seen = False
    for row in rows:
        try:
            total += int(row.get("value"))
            seen = True
        except (TypeError, ValueError):
            continue
    return total if seen else None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        year, month, day = [int(part) for part in value.split("-", 2)]
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Optional[str]):
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _normalise_status(value: Optional[str]) -> Optional[str]:
    if value == "ongoing":
        return "airing"
    if value == "released":
        return "finished"
    if value == "anons":
        return "upcoming"
    if not value:
        return None
    return "unknown"


def _normalise_format(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    mapping = {
        "tv": "TV",
        "tv_13": "TV",
        "tv_24": "TV",
        "tv_48": "TV",
        "tv_special": "TV_SHORT",
        "movie": "MOVIE",
        "ova": "OVA",
        "ona": "ONA",
        "special": "SPECIAL",
        "music": "MUSIC",
    }
    return mapping.get(value)


def selftest() -> bool:
    """Smoke-test the Shikimori rich models."""
    from datetime import datetime, timezone

    src = SourceTag(backend="shikimori", fetched_at=datetime.now(timezone.utc))
    anime = ShikimoriAnime(
        id=52991,
        name="Sousou no Frieren",
        english=["Frieren: Beyond Journey's End"],
        japanese=["葬送のフリーレン"],
        score="9.27",
        status="released",
        episodes=28,
        source_tag=src,
    )
    common = anime.to_common()
    assert common.id == "shikimori:52991"
    assert common.status == "finished"
    assert common.source.backend == "shikimori"
    return True
