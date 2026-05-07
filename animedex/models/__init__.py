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

Domain models (anime, manga, character) layer on top and arrive as
their respective submodules ship.
"""

from animedex.models.common import (
    AnimedexModel,
    ApiError,
    Pagination,
    RateLimit,
    SourceTag,
)

__all__ = [
    "AnimedexModel",
    "ApiError",
    "Pagination",
    "RateLimit",
    "SourceTag",
]
