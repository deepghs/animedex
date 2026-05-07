"""
Anime domain models.

The records in this module compose
:class:`~animedex.models.common.SourceTag` provenance into the typed
shape AniList, Jikan, Kitsu, and Shikimori backends populate.

The :class:`Anime` class is intentionally a *common projection*: it
holds the fields that are reasonably comparable across at least
three of the upstreams we target. Per ``plans/05-python-api.md`` and
the design discussion in `#1`'s Phase 0 closeout, each backend will
ship a *richer* per-backend dataclass under
``animedex.backends.<name>.models`` (e.g. ``AnilistAnime``) that
exposes the long tail of upstream-specific fields, plus a
``to_common() -> Anime`` mapping. Single-backend commands return
the rich type; cross-source aggregate commands return :class:`Anime`.

Per ``plans/03 §5`` every record carries ``source`` so attribution
survives every later hop (cache, render, JSON pipeline).
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Literal, Optional

from animedex.models.common import AnimedexModel, SourceTag


#: Canonical airing-status enum. Per-backend mappings normalise to
#: these values; an unrecognised upstream status maps to ``"unknown"``.
AnimeStatus = Literal["airing", "finished", "upcoming", "cancelled", "hiatus", "unknown"]

#: Canonical media-format enum. Per-backend mappings normalise to
#: these values. Unrecognised formats are dropped (left as ``None``).
AnimeFormat = Literal["TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"]

#: Broadcast season. The ISO seasons map cleanly across AniList,
#: Kitsu, MAL/Jikan, Shikimori.
AnimeSeason = Literal["WINTER", "SPRING", "SUMMER", "FALL"]


class AnimeTitle(AnimedexModel):
    """Multi-locale title block.

    :ivar romaji: Romanised Japanese title; the canonical machine
                   form for fuzzy match.
    :vartype romaji: str
    :ivar english: Localised English title when one exists.
    :vartype english: str or None
    :ivar native: Native-script title (typically Japanese).
    :vartype native: str or None
    """

    romaji: str
    english: Optional[str] = None
    native: Optional[str] = None


class AnimeRating(AnimedexModel):
    """Numeric score from one upstream.

    :ivar score: Reported rating, in the upstream's native scale.
    :vartype score: float
    :ivar scale: Maximum possible score (e.g. 10.0 or 100.0). Stored
                  explicitly so cross-source comparisons can normalise.
    :vartype scale: float
    :ivar votes: Total ratings cast when the upstream exposes the
                  count.
    :vartype votes: int or None
    """

    score: float
    scale: float
    votes: Optional[int] = None


class AnimeStreamingLink(AnimedexModel):
    """A legal streaming destination from Kitsu's ``streaming-links``.

    :ivar provider: Service name (e.g. ``"Crunchyroll"``).
    :vartype provider: str
    :ivar url: Public landing URL on the provider.
    :vartype url: str
    """

    provider: str
    url: str


class Anime(AnimedexModel):
    """An anime record as returned by any single backend.

    The field set is the cross-source projection: every field is
    expected to be populated by at least three of the upstreams we
    target (AniList, Jikan, Kitsu, Shikimori, ANN, AniDB), or is a
    backend-specific value that an aggregate consumer can ignore
    (e.g. ``streaming``, which is effectively Kitsu-only).

    Backends that expose richer data ship per-backend dataclasses
    under ``animedex.backends.<name>.models`` and provide
    ``to_common() -> Anime`` to project onto this shape.

    :ivar id: Canonical ``"<source>:<id>"`` identifier.
    :vartype id: str
    :ivar title: Multi-locale title block.
    :vartype title: AnimeTitle
    :ivar score: Score from the answering backend, when reported.
    :vartype score: AnimeRating or None
    :ivar episodes: Episode count, when known.
    :vartype episodes: int or None
    :ivar studios: Production studios, in the upstream's order.
    :vartype studios: list of str
    :ivar streaming: Legal streaming destinations.
    :vartype streaming: list of AnimeStreamingLink
    :ivar description: Synopsis / description (free text; may be
                        markdown or HTML depending on the upstream).
    :vartype description: str or None
    :ivar genres: Curated, broad genre tags (e.g. ``"Adventure"``,
                   ``"Drama"``). Smaller and stabler than ``tags``;
                   AniList separates these explicitly.
    :vartype genres: list of str
    :ivar tags: Long-tail descriptive tags (e.g. ``"Slow Burn"``,
                 ``"Magic"``). May be empty when the upstream does
                 not separate from ``genres``.
    :vartype tags: list of str
    :ivar status: Airing status, normalised to :data:`AnimeStatus`.
    :vartype status: str or None
    :ivar format: Media format, normalised to :data:`AnimeFormat`.
    :vartype format: str or None
    :ivar season: Broadcast season, normalised to :data:`AnimeSeason`.
    :vartype season: str or None
    :ivar season_year: Calendar year of the broadcast season.
    :vartype season_year: int or None
    :ivar aired_from: Date of the first aired episode.
    :vartype aired_from: datetime.date or None
    :ivar aired_to: Date of the last aired episode (or ``None``
                     when still airing).
    :vartype aired_to: datetime.date or None
    :ivar duration_minutes: Per-episode duration in minutes.
    :vartype duration_minutes: int or None
    :ivar cover_image_url: Cover image URL.
    :vartype cover_image_url: str or None
    :ivar banner_image_url: Banner image URL when one is exposed.
    :vartype banner_image_url: str or None
    :ivar trailer_url: Trailer URL when one is exposed.
    :vartype trailer_url: str or None
    :ivar source_material: Origin story type
                            (e.g. ``"manga"``, ``"light_novel"``,
                            ``"original"``); free-form because
                            backend vocabularies vary.
    :vartype source_material: str or None
    :ivar country_of_origin: ISO 3166-1 alpha-2 country code.
    :vartype country_of_origin: str or None
    :ivar is_adult: ``True`` for adult-only content. ``None`` when
                     the upstream does not expose the flag.
    :vartype is_adult: bool or None
    :ivar age_rating: Free-form rating string (e.g. ``"PG-13"``,
                       ``"TV-MA"``); upstream vocabularies vary.
    :vartype age_rating: str or None
    :ivar popularity: Popularity metric; the meaning is upstream-
                       specific (rank, favourites, member count).
    :vartype popularity: int or None
    :ivar ids: Cross-service identifier map (e.g. ``{"mal":
                "52991", "kitsu": "47390"}``).
    :vartype ids: dict[str, str]
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    title: AnimeTitle
    score: Optional[AnimeRating] = None
    episodes: Optional[int] = None
    studios: List[str] = []
    streaming: List[AnimeStreamingLink] = []
    description: Optional[str] = None
    genres: List[str] = []
    tags: List[str] = []
    status: Optional[AnimeStatus] = None
    format: Optional[AnimeFormat] = None
    season: Optional[AnimeSeason] = None
    season_year: Optional[int] = None
    aired_from: Optional[date] = None
    aired_to: Optional[date] = None
    duration_minutes: Optional[int] = None
    cover_image_url: Optional[str] = None
    banner_image_url: Optional[str] = None
    trailer_url: Optional[str] = None
    source_material: Optional[str] = None
    country_of_origin: Optional[str] = None
    is_adult: Optional[bool] = None
    age_rating: Optional[str] = None
    popularity: Optional[int] = None
    ids: Dict[str, str]
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the anime model graph.

    Instantiates and JSON-round-trips an ``Anime`` containing every
    optional field so future schema regressions surface in the
    diagnostic, not at first real backend hit.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import date as _date
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    a = Anime(
        id="_selftest:1",
        title=AnimeTitle(romaji="x", english="x", native="x"),
        score=AnimeRating(score=1.0, scale=10.0, votes=1),
        episodes=1,
        studios=["x"],
        streaming=[AnimeStreamingLink(provider="x", url="https://x.invalid/x")],
        description="d",
        genres=["g"],
        tags=["t"],
        status="finished",
        format="TV",
        season="FALL",
        season_year=2026,
        aired_from=_date(2026, 1, 1),
        aired_to=_date(2026, 6, 30),
        duration_minutes=24,
        cover_image_url="https://x.invalid/c.jpg",
        banner_image_url="https://x.invalid/b.jpg",
        trailer_url="https://x.invalid/t",
        source_material="manga",
        country_of_origin="JP",
        is_adult=False,
        age_rating="PG-13",
        popularity=1,
        ids={"_selftest": "1"},
        source=src,
    )
    Anime.model_validate_json(a.model_dump_json())
    return True
