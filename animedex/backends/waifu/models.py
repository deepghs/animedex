"""Rich Waifu.im dataclasses (one per resource type).

Waifu.im wraps every listing in a ``{items, pageNumber, totalPages,
totalCount, pageSize, hasPreviousPage, hasNextPage}`` envelope. The
high-level API extracts ``items`` and validates each row through a
typed model; per the project's lossless contract every model
inherits from :class:`BackendRichModel` (``extra='allow'``,
``populate_by_name=True``, ``frozen=True``) so any field upstream
adds round-trips through ``model_dump``.

The :meth:`WaifuImage.to_common` projection maps image records onto
the cross-source :class:`~animedex.models.art.ArtPost` shape.
``WaifuTag`` and ``WaifuArtist`` have no cross-source common type
and surface as their rich shape only.
"""

from __future__ import annotations

from typing import List, Optional

from animedex.models.art import ArtPost
from animedex.models.common import BackendRichModel, SourceTag


# ---------- nested sub-blocks ----------


class WaifuTag(BackendRichModel):
    """A single tag record (also nested inside :class:`WaifuImage`).

    :ivar id: Numeric tag ID.
    :vartype id: int
    :ivar name: Display name (capitalised, e.g. ``"Waifu"``).
    :vartype name: str or None
    :ivar slug: URL-safe slug (lowercased, e.g. ``"waifu"``).
    :vartype slug: str or None
    :ivar description: Short description.
    :vartype description: str or None
    :ivar imageCount: Number of images carrying this tag.
    :vartype imageCount: int or None
    :ivar reviewStatus: Upstream's review state (``"Accepted"``).
    :vartype reviewStatus: str or None
    """

    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    imageCount: Optional[int] = None
    reviewStatus: Optional[str] = None
    creatorId: Optional[int] = None
    source_tag: Optional[SourceTag] = None


class WaifuArtist(BackendRichModel):
    """A single artist record (also nested inside :class:`WaifuImage`).

    :ivar id: Numeric artist ID.
    :vartype id: int
    :ivar name: Artist display name.
    :vartype name: str or None
    :ivar patreon: Artist's Patreon URL.
    :vartype patreon: str or None
    :ivar pixiv: Artist's Pixiv URL.
    :vartype pixiv: str or None
    :ivar twitter: Artist's Twitter / X URL.
    :vartype twitter: str or None
    :ivar deviantArt: Artist's DeviantArt URL.
    :vartype deviantArt: str or None
    :ivar imageCount: Number of images by this artist in the catalogue.
    :vartype imageCount: int or None
    """

    id: int
    name: Optional[str] = None
    patreon: Optional[str] = None
    pixiv: Optional[str] = None
    twitter: Optional[str] = None
    deviantArt: Optional[str] = None
    reviewStatus: Optional[str] = None
    creatorId: Optional[int] = None
    imageCount: Optional[int] = None
    source_tag: Optional[SourceTag] = None


class WaifuImageDimensions(BackendRichModel):
    """Width / height block on :class:`WaifuImage`. Note that
    Waifu.im flattens ``width`` / ``height`` directly onto the image
    record rather than nesting them, so this class is here for
    parity with other backends' typed access — Waifu.im itself has
    no nested dimensions object."""

    width: Optional[int] = None
    height: Optional[int] = None


class WaifuImage(BackendRichModel):
    """A single image record from Waifu.im.

    Returned by ``/images`` and ``/images/{id}``. Carries explicit
    ``isNsfw`` / ``isAnimated`` flags + nested ``tags`` and
    ``artists`` lists.

    :ivar id: Numeric image ID.
    :vartype id: int
    :ivar url: Direct asset URL.
    :vartype url: str
    :ivar source: Upstream source URL (artist's pixiv, twitter, etc).
    :vartype source: str or None
    :ivar isNsfw: NSFW flag — the canonical signal for the
                   ``isNsfw=`` query parameter on ``/images``.
    :vartype isNsfw: bool or None
    :ivar isAnimated: Whether the asset is an animated GIF / WebP.
    :vartype isAnimated: bool or None
    :ivar width: Image width in pixels.
    :vartype width: int or None
    :ivar height: Image height in pixels.
    :vartype height: int or None
    :ivar dominantColor: Hex colour summarising the image (used for
                         placeholder backgrounds).
    :vartype dominantColor: str or None
    :ivar tags: Nested list of typed tag records.
    :vartype tags: list of WaifuTag
    :ivar artists: Nested list of typed artist records.
    :vartype artists: list of WaifuArtist
    """

    id: int
    url: str
    source: Optional[str] = None
    isNsfw: Optional[bool] = None
    isAnimated: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
    perceptualHash: Optional[str] = None
    extension: Optional[str] = None
    dominantColor: Optional[str] = None
    uploaderId: Optional[int] = None
    uploadedAt: Optional[str] = None
    byteSize: Optional[int] = None
    favorites: Optional[int] = None
    likedAt: Optional[str] = None
    addedToAlbumAt: Optional[str] = None
    reviewStatus: Optional[str] = None
    tags: List[WaifuTag] = []
    artists: List[WaifuArtist] = []
    albums: Optional[List[dict]] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> ArtPost:
        """Project this image onto the cross-source
        :class:`~animedex.models.art.ArtPost` shape.

        ``rating`` derives from ``isNsfw``: ``True`` → ``"e"``
        (Danbooru's ``explicit``), ``False`` → ``"g"`` (general).
        ``tags`` come from the nested ``tags[].slug`` list.
        ``artist`` is the first nested artist's ``name``, when
        present.
        """
        rating = "e" if self.isNsfw else ("g" if self.isNsfw is False else None)
        artist_name = None
        if self.artists:
            artist_name = self.artists[0].name
        tag_slugs = [t.slug for t in self.tags if t.slug]
        return ArtPost(
            id=f"waifu:{self.id}",
            url=self.url,
            rating=rating,
            tags=tag_slugs,
            score=self.favorites,
            artist=artist_name,
            source_url=self.source,
            width=self.width,
            height=self.height,
            source=self.source_tag or _default_src(),
        )


# ---------- helpers ----------


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` when one isn't
    already attached. Used by ``to_common()`` for direct-from-JSON
    construction paths that bypass the high-level fetch helper."""
    from datetime import datetime, timezone

    return SourceTag(backend="waifu", fetched_at=datetime.now(timezone.utc))


def selftest() -> bool:
    """Smoke-test the Waifu.im rich models.

    Validates a synthetic :class:`WaifuImage` round-trips through
    ``model_dump_json`` / ``model_validate_json`` and projects to a
    well-formed :class:`~animedex.models.art.ArtPost`, including the
    ``isNsfw`` → rating mapping.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    img = WaifuImage.model_validate(
        {
            "id": 7115,
            "url": "https://cdn.waifu.im/7115.jpg",
            "isNsfw": False,
            "width": 2000,
            "height": 3000,
            "tags": [{"id": 12, "name": "Waifu", "slug": "waifu"}],
            "artists": [{"id": 6, "name": "An Artist"}],
            "source_tag": src.model_dump(),
        }
    )
    WaifuImage.model_validate_json(img.model_dump_json())
    common = img.to_common()
    assert common.id == "waifu:7115"
    assert common.rating == "g"
    assert common.tags == ["waifu"]
    assert common.artist == "An Artist"

    nsfw = WaifuImage.model_validate({"id": 1, "url": "x", "isNsfw": True})
    assert nsfw.to_common().rating == "e"
    return True
