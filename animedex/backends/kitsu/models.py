"""Rich Kitsu dataclasses (one per JSON:API resource type).

Kitsu serves data in the JSON:API shape: every resource is wrapped
as ``{id, type, attributes, relationships, links}`` and listings
come back as ``{data: [...], meta, links}``. The high-level
``_fetch`` helper extracts the inner ``data`` block, and these
classes model the resources directly.

Per the project's lossless rich-model contract every class inherits
from :class:`BackendRichModel` (``extra='allow'``,
``populate_by_name=True``, ``frozen=True``). Only the fields the
high-level API touches are spelled out as typed attributes; the
JSON:API ``attributes`` block carries dozens more fields that
upstream may add or remove between releases, and they round-trip
through ``model_dump(by_alias=True)`` via ``extra='allow'``.

The :meth:`KitsuAnime.to_common` and :meth:`KitsuManga.to_common`
projections map onto :class:`~animedex.models.anime.Anime` and
:class:`~animedex.models.manga.Manga` so a downstream pipeline that
already speaks the cross-source common shape doesn't need to know
JSON:API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from animedex.models.anime import Anime, AnimeRating, AnimeStreamingLink, AnimeTitle
from animedex.models.common import BackendRichModel, SourceTag
from animedex.models.manga import Manga


# ---------- shared sub-blocks ----------


class KitsuAnimeAttributes(BackendRichModel):
    """The ``attributes`` block on an ``/anime/{id}`` resource."""

    canonicalTitle: Optional[str] = None
    titles: Optional[Dict[str, Optional[str]]] = None
    abbreviatedTitles: Optional[List[str]] = None
    synopsis: Optional[str] = None
    description: Optional[str] = None
    averageRating: Optional[str] = None
    userCount: Optional[int] = None
    favoritesCount: Optional[int] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    ageRating: Optional[str] = None
    ageRatingGuide: Optional[str] = None
    subtype: Optional[str] = None
    status: Optional[str] = None
    episodeCount: Optional[int] = None
    episodeLength: Optional[int] = None
    showType: Optional[str] = None
    youtubeVideoId: Optional[str] = None
    nsfw: Optional[bool] = None


class KitsuMangaAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/manga/{id}`` resource."""

    canonicalTitle: Optional[str] = None
    titles: Optional[Dict[str, Optional[str]]] = None
    abbreviatedTitles: Optional[List[str]] = None
    synopsis: Optional[str] = None
    description: Optional[str] = None
    averageRating: Optional[str] = None
    userCount: Optional[int] = None
    favoritesCount: Optional[int] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    status: Optional[str] = None
    chapterCount: Optional[int] = None
    volumeCount: Optional[int] = None
    mangaType: Optional[str] = None
    serialization: Optional[str] = None


class KitsuMappingAttributes(BackendRichModel):
    """The ``attributes`` block on an ``/anime/{id}/mappings`` row."""

    externalSite: Optional[str] = None
    externalId: Optional[str] = None


class KitsuStreamingLinkAttributes(BackendRichModel):
    """The ``attributes`` block on an ``/anime/{id}/streaming-links`` row."""

    url: Optional[str] = None
    subs: Optional[List[str]] = None
    dubs: Optional[List[str]] = None


class KitsuCategoryAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/categories`` row."""

    title: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    nsfw: Optional[bool] = None
    childCount: Optional[int] = None


# ---------- top-level resource shapes ----------


class KitsuAnime(BackendRichModel):
    """JSON:API anime resource from ``/anime/{id}`` or
    ``/anime?filter[text]=...``.

    :ivar id: Kitsu numeric ID (as a string per JSON:API convention).
    :vartype id: str
    :ivar type: JSON:API type tag — always ``"anime"``.
    :vartype type: str
    :ivar attributes: Typed anime attributes.
    :vartype attributes: KitsuAnimeAttributes or None
    :ivar relationships: JSON:API relationships block (link
                          descriptors for ``genres`` / ``categories`` /
                          ``streamingLinks`` / ``mappings`` / etc.).
    :vartype relationships: dict or None
    :ivar links: JSON:API links block.
    :vartype links: dict or None
    :ivar source_tag: Provenance tag.
    :vartype source_tag: SourceTag or None
    """

    id: str
    type: str = "anime"
    attributes: Optional[KitsuAnimeAttributes] = None
    relationships: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Anime:
        """Project this resource onto the cross-source
        :class:`~animedex.models.anime.Anime` shape.

        :return: Cross-source projection.
        :rtype: animedex.models.anime.Anime
        """
        attrs = self.attributes or KitsuAnimeAttributes()
        title = AnimeTitle(
            romaji=(attrs.titles or {}).get("en_jp"),
            english=(attrs.titles or {}).get("en"),
            native=(attrs.titles or {}).get("ja_jp"),
        )
        score = None
        if attrs.averageRating is not None:
            try:
                score = AnimeRating(score=float(attrs.averageRating), scale=100, votes=attrs.userCount)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                score = None
        return Anime(
            id=f"kitsu:{self.id}",
            title=title,
            ids={"kitsu": self.id},
            format=(attrs.subtype or attrs.showType),
            status=_normalise_kitsu_status(attrs.status),
            episodes=attrs.episodeCount,
            duration_minutes=attrs.episodeLength,
            season_year=_year_from_iso(attrs.startDate),
            description=attrs.synopsis or attrs.description,
            score=score,
            favourites=attrs.favoritesCount,
            popularity=attrs.userCount,
            age_rating=attrs.ageRating,
            is_adult=attrs.nsfw,
            source=self.source_tag or _default_src(),
        )


class KitsuManga(BackendRichModel):
    """JSON:API manga resource from ``/manga/{id}`` or
    ``/manga?filter[text]=...``."""

    id: str
    type: str = "manga"
    attributes: Optional[KitsuMangaAttributes] = None
    relationships: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Manga:
        """Project this resource onto the cross-source
        :class:`~animedex.models.manga.Manga` shape.

        Note that the common :class:`~animedex.models.manga.Manga`
        models ``chapters`` as a *list of* :class:`~animedex.models.manga.Chapter`
        records (not a count); Kitsu's ``/manga/{id}`` only carries
        the count, so the projection sets ``chapters=[]``. Use the
        rich shape's ``attributes.chapterCount`` for the integer.

        :return: Cross-source projection.
        :rtype: animedex.models.manga.Manga
        """
        attrs = self.attributes or KitsuMangaAttributes()
        return Manga(
            id=f"kitsu:{self.id}",
            title=(attrs.titles or {}).get("en_jp") or attrs.canonicalTitle or "",
            ids={"kitsu": self.id},
            chapters=[],
            status=_kitsu_status_to_manga_status(attrs.status),
            format=_kitsu_manga_type_to_format(attrs.mangaType),
            description=attrs.synopsis or attrs.description,
            source=self.source_tag or _default_src(),
        )


class KitsuMapping(BackendRichModel):
    """JSON:API mapping resource from ``/anime/{id}/mappings``.

    Each mapping row carries an ``externalSite`` + ``externalId``
    pair, identifying the anime on a peer upstream (e.g.
    ``externalSite='myanimelist/anime'``, ``externalId='52991'``).
    """

    id: str
    type: str = "mappings"
    attributes: Optional[KitsuMappingAttributes] = None
    relationships: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    source_tag: Optional[SourceTag] = None


class KitsuStreamingLink(BackendRichModel):
    """JSON:API streaming-link resource from
    ``/anime/{id}/streaming-links``.

    The ``url`` attribute points at the streaming destination
    (Crunchyroll / Funimation / Hulu / etc.); ``subs`` / ``dubs``
    list the available language tracks.
    """

    id: str
    type: str = "streamingLinks"
    attributes: Optional[KitsuStreamingLinkAttributes] = None
    relationships: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> AnimeStreamingLink:
        """Project this resource onto the cross-source
        :class:`~animedex.models.anime.AnimeStreamingLink` shape.

        The cross-source common shape has only ``provider`` and
        ``url``; the rich shape preserves ``subs`` / ``dubs`` for
        callers that want them.
        """
        attrs = self.attributes or KitsuStreamingLinkAttributes()
        return AnimeStreamingLink(
            provider=_provider_from_url(attrs.url),
            url=attrs.url or "",
        )


class KitsuCategory(BackendRichModel):
    """JSON:API category resource from ``/categories``."""

    id: str
    type: str = "categories"
    attributes: Optional[KitsuCategoryAttributes] = None
    relationships: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    source_tag: Optional[SourceTag] = None


# ---------- helpers ----------


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` when one isn't
    already attached. Used by ``to_common()`` for direct-from-JSON
    construction paths that bypass the high-level fetch helper."""
    from datetime import datetime, timezone

    return SourceTag(backend="kitsu", fetched_at=datetime.now(timezone.utc))


def _year_from_iso(iso: Optional[str]) -> Optional[int]:
    """Pull the year out of an ISO-8601 date string, tolerantly."""
    if not iso:
        return None
    try:
        return int(iso[:4])
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _normalise_kitsu_status(s: Optional[str]) -> Optional[str]:
    """Map Kitsu's ``status`` enum to the cross-source shape.

    Kitsu uses ``"current"`` / ``"finished"`` / ``"tba"`` /
    ``"unreleased"`` / ``"upcoming"``. The common
    :class:`~animedex.models.anime.Anime` field is a free-form
    string; we lowercase and strip but preserve any value the
    upstream sends so the lossless audit trail is preserved on the
    rich shape.
    """
    if not s:
        return None
    return s.lower().strip()


def _kitsu_status_to_manga_status(s: Optional[str]) -> Optional[str]:
    """Map Kitsu's manga ``status`` to the constrained
    :data:`~animedex.models.manga.MangaStatus` literal set.

    Kitsu uses ``"current"`` / ``"finished"`` / ``"tba"`` /
    ``"upcoming"`` / ``"unreleased"``. The common :class:`Manga`
    accepts only ``"ongoing"`` / ``"completed"`` / ``"hiatus"`` /
    ``"cancelled"`` / ``"unknown"``. Anything that doesn't map
    cleanly falls through to ``"unknown"`` so the projection always
    validates.
    """
    if not s:
        return None
    norm = s.lower().strip()
    return {
        "current": "ongoing",
        "finished": "completed",
        "tba": "unknown",
        "upcoming": "unknown",
        "unreleased": "unknown",
    }.get(norm, "unknown")


def _kitsu_manga_type_to_format(s: Optional[str]) -> Optional[str]:
    """Map Kitsu's manga ``mangaType`` to the constrained
    :data:`~animedex.models.manga.MangaFormat` literal set.

    Kitsu uses ``"manga"`` / ``"novel"`` / ``"manhua"`` /
    ``"manhwa"`` / ``"oneshot"`` / ``"oel"`` /
    ``"doujin"``. The common shape's literal set is
    ``"MANGA"`` / ``"NOVEL"`` / ``"ONE_SHOT"`` / ``"DOUJINSHI"`` /
    ``"MANHWA"`` / ``"MANHUA"``. Anything outside the mapped set
    falls back to ``"MANGA"`` (the safest default).
    """
    if not s:
        return None
    norm = s.lower().strip()
    return {
        "manga": "MANGA",
        "novel": "NOVEL",
        "oneshot": "ONE_SHOT",
        "doujin": "DOUJINSHI",
        "manhwa": "MANHWA",
        "manhua": "MANHUA",
        "oel": "MANGA",
    }.get(norm, "MANGA")


def _provider_from_url(url: Optional[str]) -> str:
    """Best-effort guess at a streaming provider from the URL
    netloc. Kitsu's ``/streaming-links`` payload doesn't carry a
    provider name as a typed field; the URL's netloc is the most
    reliable hint."""
    if not url:
        return "unknown"
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
    except Exception:  # pragma: no cover - defensive
        return "unknown"
    for marker in ("crunchyroll", "funimation", "hulu", "netflix", "amazon", "hidive", "vrv"):
        if marker in host:
            return marker
    return host or "unknown"


def selftest() -> bool:
    """Smoke-test the Kitsu rich models.

    Validates a synthetic :class:`KitsuAnime` round-trips through
    ``model_dump_json`` / ``model_validate_json`` and projects to a
    well-formed :class:`~animedex.models.anime.Anime`.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    sample = {
        "id": "46474",
        "type": "anime",
        "attributes": {
            "canonicalTitle": "Sousou no Frieren",
            "titles": {"en_jp": "Sousou no Frieren", "en": "Frieren: Beyond Journey's End"},
            "averageRating": "85.4",
            "userCount": 12345,
            "subtype": "TV",
            "status": "finished",
            "episodeCount": 28,
            "episodeLength": 24,
            "startDate": "2023-09-29",
        },
    }
    anime = KitsuAnime.model_validate({**sample, "source_tag": src})
    KitsuAnime.model_validate_json(anime.model_dump_json())
    common = anime.to_common()
    assert common.id == "kitsu:46474"
    assert common.episodes == 28
    assert common.duration_minutes == 24
    assert common.season_year == 2023

    streaming = KitsuStreamingLink.model_validate(
        {
            "id": "1",
            "type": "streamingLinks",
            "attributes": {"url": "https://www.crunchyroll.com/series/...", "subs": ["en"], "dubs": ["en"]},
            "source_tag": src,
        }
    )
    assert streaming.to_common().provider == "crunchyroll"
    return True
