"""
Anime domain models.

The records in this module compose
:class:`~animedex.models.common.SourceTag` provenance into the typed
shape AniList, Jikan, Kitsu, and Shikimori backends will all populate.
``plans/05-python-api.md`` §3 fixes the field set; per ``plans/03``,
every record carries ``source`` so attribution survives every later
hop (cache, render, JSON pipeline).
"""

from __future__ import annotations

from typing import List, Optional

from animedex.models.common import AnimedexModel, SourceTag


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
    :ivar ids: Cross-service identifier map (e.g. ``{"mal": "52991",
                "kitsu": "47390"}``).
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
    ids: dict
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the anime model graph.

    Instantiates and JSON-round-trips an ``Anime`` containing every
    optional field so future schema regressions surface in the
    diagnostic, not at first real backend hit.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    a = Anime(
        id="_selftest:1",
        title=AnimeTitle(romaji="x", english="x", native="x"),
        score=AnimeRating(score=1.0, scale=10.0, votes=1),
        episodes=1,
        studios=["x"],
        streaming=[AnimeStreamingLink(provider="x", url="https://x.invalid/x")],
        ids={"_selftest": "1"},
        source=src,
    )
    Anime.model_validate_json(a.model_dump_json())
    return True
