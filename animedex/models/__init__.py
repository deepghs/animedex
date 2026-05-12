"""
Public dataclass / pydantic-model surface for :mod:`animedex`.

The submodules here define the source-attributed result types used
throughout the library and the CLI. Per ``plans/05-python-api.md``,
these are the stability boundary: backends return them, the
renderers consume them, the cache serialises them, and external
Python users import them.

The types here are the **cross-source common projection**: each
captures the fields that at least three of the upstreams we target
populate (or that are uniquely valuable from one source, like
:class:`~animedex.models.anime.AnimeStreamingLink` from Kitsu).

Each backend additionally ships a richer per-backend dataclass under
``animedex.backends.<name>.models`` (e.g. ``AnilistAnime``) that
exposes the long tail of upstream-specific fields, plus a
``to_common()`` mapping into the projection types here. Single-
backend commands (``animedex anilist show``) return the rich type;
cross-source aggregate commands (``animedex show``) return the
projection.

The submodules are:

* :mod:`animedex.models.common` - ground-floor types
  (:class:`~animedex.models.common.SourceTag`, :class:`Pagination`,
  :class:`RateLimit`, :class:`ApiError`, :class:`AnimedexModel`).
* :mod:`animedex.models.anime` - anime records.
* :mod:`animedex.models.manga` - manga records.
* :mod:`animedex.models.character` - cast and crew records.
* :mod:`animedex.models.art` - tagged image-post records (Danbooru,
  Waifu.im, NekosBest).
* :mod:`animedex.models.trace` - Trace.moe screenshot-search hits.
* :mod:`animedex.models.quote` - AnimeChan quotes.
* :mod:`animedex.models.aggregate` - multi-source aggregate envelopes.
"""

from animedex.models.anime import (
    AiringScheduleRow,
    Anime,
    AnimeFormat,
    AnimeRating,
    AnimeSeason,
    AnimeStatus,
    AnimeStreamingLink,
    AnimeTitle,
)
from animedex.models.aggregate import AggregateResult, AggregateSourceStatus, MergedAnime, ScheduleCalendarResult
from animedex.models.art import ArtPost, ArtRating
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import (
    AnimedexModel,
    ApiError,
    Pagination,
    RateLimit,
    SourceTag,
)
from animedex.models.manga import (
    AtHomeServer,
    Chapter,
    Manga,
    MangaFormat,
    MangaStatus,
)
from animedex.models.quote import Quote
from animedex.models.trace import TraceHit

__all__ = [
    "AnimedexModel",
    "Anime",
    "AnimeFormat",
    "AnimeRating",
    "AnimeSeason",
    "AnimeStatus",
    "AnimeStreamingLink",
    "AnimeTitle",
    "AiringScheduleRow",
    "AggregateResult",
    "AggregateSourceStatus",
    "ApiError",
    "ArtPost",
    "ArtRating",
    "AtHomeServer",
    "Chapter",
    "Character",
    "Manga",
    "MangaFormat",
    "MangaStatus",
    "MergedAnime",
    "Pagination",
    "Quote",
    "RateLimit",
    "ScheduleCalendarResult",
    "SourceTag",
    "Staff",
    "Studio",
    "TraceHit",
]
