"""Rich MangaDex dataclasses (one per resource type).

MangaDex serves data in a JSON:API-flavoured shape: every resource
is wrapped as ``{id, type, attributes, relationships}`` and listings
come back as
``{result, response, data: [...], limit, offset, total}``.

Per the project's lossless rich-model contract (§13), every class
below inherits from :class:`BackendRichModel` (``extra='allow'``,
``populate_by_name=True``, ``frozen=True``). The ``attributes``
sub-classes only spell out the fields the high-level API touches;
upstream may add more, and they round-trip through ``model_dump``
via ``extra='allow'``.

The :meth:`MangaDexManga.to_common` and
:meth:`MangaDexChapter.to_common` projections map onto
:class:`~animedex.models.manga.Manga` and
:class:`~animedex.models.manga.Chapter` so a downstream pipeline can
diff MangaDex output against any other manga upstream without
needing to know JSON:API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from animedex.models.common import BackendRichModel, SourceTag
from animedex.models.manga import Chapter, Manga


# ---------- attribute sub-blocks ----------


class MangaDexMangaAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/manga/{id}`` resource."""

    # MangaDex usually returns description / title / links as
    # ``{lang: text}`` maps but occasionally returns an empty list
    # ``[]`` for description on bare-bones records. ``Any`` keeps the
    # lossless round-trip valid across both shapes.
    title: Optional[Any] = None
    altTitles: Optional[List[Any]] = None
    description: Optional[Any] = None
    isLocked: Optional[bool] = None
    links: Optional[Any] = None
    originalLanguage: Optional[str] = None
    lastVolume: Optional[str] = None
    lastChapter: Optional[str] = None
    publicationDemographic: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    contentRating: Optional[str] = None
    tags: Optional[List[Dict[str, Any]]] = None
    state: Optional[str] = None
    chapterNumbersResetOnNewVolume: Optional[bool] = None


class MangaDexChapterAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/chapter/{id}`` resource."""

    volume: Optional[str] = None
    chapter: Optional[str] = None
    title: Optional[str] = None
    translatedLanguage: Optional[str] = None
    externalUrl: Optional[str] = None
    isUnavailable: Optional[bool] = None
    publishAt: Optional[str] = None
    readableAt: Optional[str] = None
    pages: Optional[int] = None
    uploader: Optional[str] = None


class MangaDexCoverAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/cover/{id}`` resource."""

    description: Optional[str] = None
    volume: Optional[str] = None
    fileName: Optional[str] = None
    locale: Optional[str] = None


# ---------- top-level resource shapes ----------


class MangaDexManga(BackendRichModel):
    """JSON:API manga resource from ``/manga/{id}`` or
    ``/manga?title=...``.

    :ivar id: MangaDex UUID.
    :vartype id: str
    :ivar type: JSON:API type tag — always ``"manga"``.
    :vartype type: str
    :ivar attributes: Typed manga attributes.
    :vartype attributes: MangaDexMangaAttributes or None
    :ivar relationships: List of ``{id, type, ...}`` relationship
                          descriptors (authors, artists, cover_art,
                          tags, etc.).
    :vartype relationships: list[dict] or None
    :ivar source_tag: Provenance tag.
    :vartype source_tag: SourceTag or None
    """

    id: str
    type: str = "manga"
    attributes: Optional[MangaDexMangaAttributes] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Manga:
        """Project this resource onto the cross-source
        :class:`~animedex.models.manga.Manga` shape.

        Notes:

        * MangaDex's ``title`` and ``description`` are language-keyed
          maps; we pick ``en`` first, ``ja-ro`` next, then any value.
        * The cross-source ``Manga.chapters`` field models a *list*
          of :class:`~animedex.models.manga.Chapter`, not a count;
          MangaDex does not return the chapter list on
          ``/manga/{id}`` (the ``/manga/{id}/feed`` endpoint does),
          so the projection sets ``chapters=[]``.
        * ``status`` and ``contentRating`` map into the constrained
          common literal sets via ``_normalise_status`` and
          ``_normalise_format``.
        """
        attrs = self.attributes or MangaDexMangaAttributes()
        return Manga(
            id=f"mangadex:{self.id}",
            title=_pick_localised(attrs.title) or "",
            ids={"mangadex": self.id},
            chapters=[],
            status=_normalise_mangadex_status(attrs.status),
            format=_format_from_demographic(attrs.publicationDemographic),
            description=_pick_localised(attrs.description),
            source=self.source_tag or _default_src(),
        )


class MangaDexChapter(BackendRichModel):
    """JSON:API chapter resource from ``/chapter/{id}`` or
    ``/manga/{id}/feed``."""

    id: str
    type: str = "chapter"
    attributes: Optional[MangaDexChapterAttributes] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Chapter:
        """Project this resource onto the cross-source
        :class:`~animedex.models.manga.Chapter` shape.

        The cross-source :class:`Chapter` carries ``number`` and
        ``language`` as strings (MangaDex's ``"1"`` / ``"1.5"`` /
        ``"1.5a"`` shapes round-trip directly). MangaDex's
        ``publishAt`` / ``readableAt`` timestamps and ``volume`` /
        ``externalUrl`` are preserved on the rich shape but the
        common :class:`Chapter` does not carry them — reach for the
        rich model when those fields matter.
        """
        attrs = self.attributes or MangaDexChapterAttributes()
        return Chapter(
            id=f"mangadex:{self.id}",
            number=attrs.chapter or "",
            title=attrs.title,
            language=attrs.translatedLanguage or "",
            pages=attrs.pages,
            source=self.source_tag or _default_src(),
        )


class MangaDexCover(BackendRichModel):
    """JSON:API cover resource from ``/cover/{id}``.

    The ``fileName`` attribute is the path component for the
    upstream cover URL (resolved against
    ``https://uploads.mangadex.org/covers/<manga-id>/<fileName>``).
    """

    id: str
    type: str = "cover_art"
    attributes: Optional[MangaDexCoverAttributes] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    source_tag: Optional[SourceTag] = None


class MangaDexUserAttributes(BackendRichModel):
    """The ``attributes`` block on a ``/user/me`` (or
    ``/user/{id}``-when-authenticated) resource."""

    username: Optional[str] = None
    roles: Optional[List[str]] = None
    avatarFileName: Optional[str] = None
    bannerFileName: Optional[str] = None
    version: Optional[int] = None


class MangaDexUser(BackendRichModel):
    """JSON:API user resource from ``/user/me`` and
    ``/user/{id}``."""

    id: str
    type: str = "user"
    attributes: Optional[MangaDexUserAttributes] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    source_tag: Optional[SourceTag] = None


class MangaDexResource(BackendRichModel):
    """Catch-all JSON:API resource for endpoints we wrap but have not
    typed individually.

    Used for ``/author/{id}`` / ``/group/{id}`` / ``/list/{id}`` /
    ``/user/{id}`` / ``/manga/tag`` / ``/manga/{id}/recommendation``
    / ``/statistics/manga/{id}`` / ``/statistics/chapter/{id}`` /
    ``/statistics/group/{id}`` / ``/report/reasons/{category}`` /
    ``/manga/{id}/aggregate``.
    The shape is the same JSON:API resource envelope; ``attributes``
    is left as a ``dict`` because the typed-attribute story for these
    endpoints would multiply the model count without much downstream
    benefit. ``extra='allow'`` round-trips every upstream key.
    """

    id: Optional[str] = None
    type: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    source_tag: Optional[SourceTag] = None


# ---------- helpers ----------


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` when one isn't
    already attached. Used by ``to_common()`` for direct-from-JSON
    construction paths that bypass the high-level fetch helper."""
    from datetime import datetime, timezone

    return SourceTag(backend="mangadex", fetched_at=datetime.now(timezone.utc))


def _pick_localised(d: Any) -> Optional[str]:
    """Pick the most-readable string from a MangaDex
    language-keyed attribute. Order: ``en``, ``ja-ro``, ``ja``,
    then any non-empty value.

    Tolerates non-dict inputs (the upstream occasionally returns an
    empty list ``[]`` for missing description / links blocks).
    """
    if not d or not isinstance(d, dict):
        return None
    for key in ("en", "ja-ro", "ja"):
        v = d.get(key)
        if v:
            return v
    for v in d.values():
        if v:
            return v
    return None


def _normalise_mangadex_status(s: Optional[str]) -> Optional[str]:
    """Map MangaDex's ``status`` to the constrained
    :data:`~animedex.models.manga.MangaStatus` literal set.

    MangaDex uses ``"ongoing"`` / ``"completed"`` / ``"hiatus"`` /
    ``"cancelled"`` — already exactly the common set — so the
    mapping is identity, with anything unrecognised falling through
    to ``"unknown"``.
    """
    if not s:
        return None
    norm = s.lower().strip()
    if norm in {"ongoing", "completed", "hiatus", "cancelled"}:
        return norm
    return "unknown"


def _format_from_demographic(s: Optional[str]) -> Optional[str]:
    """MangaDex doesn't expose a top-level ``format`` field; the
    closest signal on ``/manga/{id}`` is ``publicationDemographic``
    (``"shounen"`` / ``"shoujo"`` / ``"josei"`` / ``"seinen"``),
    which doesn't map cleanly onto the common
    :data:`~animedex.models.manga.MangaFormat` set. Default to
    ``"MANGA"`` when the upstream gave us anything; ``None`` when
    truly empty.
    """
    if not s:
        return None
    return "MANGA"


def selftest() -> bool:
    """Smoke-test the MangaDex rich models.

    Validates a synthetic :class:`MangaDexManga` round-trips through
    ``model_dump_json`` / ``model_validate_json`` and projects to a
    well-formed :class:`~animedex.models.manga.Manga`.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    manga = MangaDexManga.model_validate(
        {
            "id": "801513ba-a712-498c-8f57-cae55b38cc92",
            "type": "manga",
            "attributes": {
                "title": {"en": "Berserk"},
                "description": {"en": "..."},
                "status": "ongoing",
                "publicationDemographic": "seinen",
                "year": 1989,
            },
            "relationships": [{"id": "x", "type": "author"}],
            "source_tag": src.model_dump(),
        }
    )
    MangaDexManga.model_validate_json(manga.model_dump_json())
    common = manga.to_common()
    assert common.id == "mangadex:801513ba-a712-498c-8f57-cae55b38cc92"
    assert common.title == "Berserk"
    assert common.status == "ongoing"

    chapter = MangaDexChapter.model_validate(
        {"id": "abc", "type": "chapter", "attributes": {"chapter": "1.5", "translatedLanguage": "en"}}
    )
    cc = chapter.to_common()
    assert cc.number == "1.5"
    assert cc.language == "en"
    return True
