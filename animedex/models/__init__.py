"""
Public dataclass / pydantic-model surface for :mod:`animedex`.

The submodules here define the source-attributed result types used
throughout the library and the CLI. Per ``plans/05-python-api.md``,
these are the stability boundary: backends return them, the renderers
consume them, the cache serialises them, and external Python users
import them.

The submodules are:

* :mod:`animedex.models.common` - ground-floor types
  (:class:`~animedex.models.common.SourceTag`,
  :class:`~animedex.models.common.Pagination`,
  :class:`~animedex.models.common.RateLimit`,
  :class:`~animedex.models.common.ApiError`,
  :class:`~animedex.models.common.AnimedexModel`).
* :mod:`animedex.models.anime` - anime records
  (:class:`~animedex.models.anime.Anime`, :class:`AnimeTitle`,
  :class:`AnimeRating`, :class:`AnimeStreamingLink`).
* :mod:`animedex.models.manga` - manga records
  (:class:`~animedex.models.manga.Manga`, :class:`Chapter`,
  :class:`AtHomeServer`).
* :mod:`animedex.models.character` - cast and crew records
  (:class:`~animedex.models.character.Character`,
  :class:`~animedex.models.character.Staff`,
  :class:`~animedex.models.character.Studio`).
"""

from animedex.models.anime import Anime, AnimeRating, AnimeStreamingLink, AnimeTitle
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import (
    AnimedexModel,
    ApiError,
    Pagination,
    RateLimit,
    SourceTag,
)
from animedex.models.manga import AtHomeServer, Chapter, Manga

__all__ = [
    "AnimedexModel",
    "Anime",
    "AnimeRating",
    "AnimeStreamingLink",
    "AnimeTitle",
    "ApiError",
    "AtHomeServer",
    "Chapter",
    "Character",
    "Manga",
    "Pagination",
    "RateLimit",
    "SourceTag",
    "Staff",
    "Studio",
]
