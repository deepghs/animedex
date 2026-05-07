"""
Manga domain models.

Mirrors the anime side. :class:`Manga` is the cross-source common
projection (MangaDex provides the lion's share of fields; AniList
also exposes manga but with thinner coverage). :class:`AtHomeServer`
is included from day one because the Phase 6 reader path consumes
it; defining the shape now keeps the public model surface stable
through that release.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from animedex.models.common import AnimedexModel, SourceTag


#: Manga publication status.
MangaStatus = Literal["ongoing", "completed", "hiatus", "cancelled", "unknown"]

#: Manga format / kind. Includes the broader Asian-comics taxonomy
#: because AniList classifies them at this granularity.
MangaFormat = Literal["MANGA", "NOVEL", "ONE_SHOT", "DOUJINSHI", "MANHWA", "MANHUA"]


class Chapter(AnimedexModel):
    """A manga chapter as returned by any single backend.

    :ivar id: Backend-native chapter identifier.
    :vartype id: str
    :ivar number: Human-friendly number (kept as a string because
                   numbering is non-monotonic and frequently fractional).
    :vartype number: str
    :ivar title: Chapter title when set upstream.
    :vartype title: str or None
    :ivar language: ISO 639 language code or upstream's locale string.
    :vartype language: str
    :ivar pages: Page count when known.
    :vartype pages: int or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    number: str
    title: Optional[str] = None
    language: str
    pages: Optional[int] = None
    source: SourceTag


class Manga(AnimedexModel):
    """A manga record.

    :ivar id: Canonical ``"<source>:<id>"`` identifier.
    :vartype id: str
    :ivar title: Display title (single string; manga upstreams are
                  less locale-rich than anime).
    :vartype title: str
    :ivar cover_url: Public cover image URL.
    :vartype cover_url: str or None
    :ivar chapters: Known chapters, in upstream order.
    :vartype chapters: list of Chapter
    :ivar languages: Languages with at least one translated chapter.
    :vartype languages: list of str
    :ivar description: Synopsis / description.
    :vartype description: str or None
    :ivar status: Publication status, normalised to
                   :data:`MangaStatus`.
    :vartype status: str or None
    :ivar format: Media format, normalised to :data:`MangaFormat`.
    :vartype format: str or None
    :ivar genres: Broad genre tags.
    :vartype genres: list of str
    :ivar tags: Long-tail descriptive tags.
    :vartype tags: list of str
    :ivar ids: Cross-service identifier map.
    :vartype ids: dict[str, str]
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    title: str
    cover_url: Optional[str] = None
    chapters: List[Chapter] = []
    languages: List[str] = []
    description: Optional[str] = None
    status: Optional[MangaStatus] = None
    format: Optional[MangaFormat] = None
    genres: List[str] = []
    tags: List[str] = []
    ids: Dict[str, str]
    source: SourceTag


class AtHomeServer(AnimedexModel):
    """Result of MangaDex's ``GET /at-home/server/{chapter}`` call.

    The base URL is short-lived (~5 min). Per ``plans/03`` we never
    cache it across chapters; the model carries it so a single Phase
    6 invocation has a typed object to thread through the page-fetch
    loop.

    :ivar base_url: Per-call base URL for the page bytes endpoint.
    :vartype base_url: str
    :ivar chapter_hash: Hash that goes between the base URL and the
                         per-page filenames.
    :vartype chapter_hash: str
    :ivar data: Filenames for full-resolution pages, in order.
    :vartype data: list of str
    :ivar data_saver: Filenames for compressed-quality pages, in
                       order. Empty when the upstream did not provide
                       a saver-quality variant.
    :vartype data_saver: list of str
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    base_url: str
    chapter_hash: str
    data: List[str]
    data_saver: List[str] = []
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the manga model graph.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    chap = Chapter(id="_ch", number="1", title="x", language="en", pages=1, source=src)
    m = Manga(
        id="_selftest:1",
        title="x",
        cover_url="https://x.invalid/c.jpg",
        chapters=[chap],
        languages=["en"],
        description="d",
        status="ongoing",
        format="MANGA",
        genres=["g"],
        tags=["t"],
        ids={"_selftest": "1"},
        source=src,
    )
    Manga.model_validate_json(m.model_dump_json())
    s = AtHomeServer(
        base_url="https://x.invalid",
        chapter_hash="abc",
        data=["1.jpg"],
        data_saver=["1-s.jpg"],
        source=src,
    )
    AtHomeServer.model_validate_json(s.model_dump_json())
    return True
