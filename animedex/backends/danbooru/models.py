"""Rich Danbooru dataclasses (one per resource type).

Danbooru's REST surface is conventional: every record returns as a
flat JSON object whose keys map directly onto the rich type. The
high-level helpers project image-post records onto the cross-source
:class:`~animedex.models.art.ArtPost` shape; artists / tags / pools
have no cross-source common type today and surface as their rich
shape only.

Per the project's lossless rich-model contract every class inherits
from :class:`BackendRichModel` (``extra='allow'``,
``populate_by_name=True``, ``frozen=True``). Only the fields the
high-level API touches are spelled out as typed attributes; upstream
may add more (Danbooru is actively maintained), and they round-trip
through ``model_dump`` losslessly via ``extra='allow'``.
"""

from __future__ import annotations

from typing import List, Optional

from animedex.models.art import ArtPost
from animedex.models.common import BackendRichModel, SourceTag


# ---------- top-level resource shapes ----------


class DanbooruPost(BackendRichModel):
    """A single post (image + metadata) on Danbooru.

    :ivar id: Numeric post ID.
    :vartype id: int
    :ivar rating: Content rating, one of ``g`` / ``s`` / ``q`` /
                   ``e`` (general / sensitive / questionable /
                   explicit).
    :vartype rating: str or None
    :ivar score: Net upvote score.
    :vartype score: int or None
    :ivar md5: MD5 hash of the image file.
    :vartype md5: str or None
    :ivar file_url: Full-resolution image URL.
    :vartype file_url: str or None
    :ivar large_file_url: Reduced-resolution preview URL (1280-wide).
    :vartype large_file_url: str or None
    :ivar preview_file_url: Thumbnail URL.
    :vartype preview_file_url: str or None
    :ivar tag_string: Space-separated tag list (the canonical form).
    :vartype tag_string: str or None
    :ivar tag_string_artist: Space-separated artist tags.
    :vartype tag_string_artist: str or None
    :ivar source: External provenance URL.
    :vartype source: str or None
    :ivar image_width: Image width in pixels.
    :vartype image_width: int or None
    :ivar image_height: Image height in pixels.
    :vartype image_height: int or None
    :ivar fav_count: Favourite count.
    :vartype fav_count: int or None
    :ivar source_tag: Provenance tag stamped by the high-level
                       fetch helper.
    :vartype source_tag: SourceTag or None
    """

    id: int
    rating: Optional[str] = None
    score: Optional[int] = None
    md5: Optional[str] = None
    file_url: Optional[str] = None
    large_file_url: Optional[str] = None
    preview_file_url: Optional[str] = None
    tag_string: Optional[str] = None
    tag_string_artist: Optional[str] = None
    source: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    fav_count: Optional[int] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> ArtPost:
        """Project this post onto the cross-source
        :class:`~animedex.models.art.ArtPost` shape.

        ``rating`` round-trips directly (Danbooru's vocabulary is
        the project's normalised one). ``tags`` come from
        ``tag_string`` (whitespace-split). ``artist`` is the first
        non-empty entry in ``tag_string_artist``. The lossless rich
        shape carries the rest.
        """
        rating = self.rating if self.rating in ("g", "s", "q", "e") else None
        tags = (self.tag_string or "").split()
        artist = None
        if self.tag_string_artist:
            artist_tags = self.tag_string_artist.split()
            artist = artist_tags[0] if artist_tags else None
        return ArtPost(
            id=f"danbooru:{self.id}",
            url=self.file_url or self.large_file_url or "",
            preview_url=self.preview_file_url,
            rating=rating,
            tags=tags,
            score=self.score,
            artist=artist,
            source_url=self.source,
            width=self.image_width,
            height=self.image_height,
            source=self.source_tag or _default_src(),
        )


class DanbooruArtist(BackendRichModel):
    """A single artist record."""

    id: int
    name: Optional[str] = None
    group_name: Optional[str] = None
    other_names: Optional[List[str]] = None
    is_deleted: Optional[bool] = None
    is_banned: Optional[bool] = None
    source_tag: Optional[SourceTag] = None


class DanbooruTag(BackendRichModel):
    """A single tag record (with usage statistics)."""

    id: int
    name: Optional[str] = None
    post_count: Optional[int] = None
    category: Optional[int] = None
    is_deprecated: Optional[bool] = None
    words: Optional[List[str]] = None
    source_tag: Optional[SourceTag] = None


class DanbooruPool(BackendRichModel):
    """A single pool record (an ordered collection of posts)."""

    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    post_ids: Optional[List[int]] = None
    post_count: Optional[int] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
    source_tag: Optional[SourceTag] = None


class DanbooruCount(BackendRichModel):
    """The ``/counts/posts.json?tags=...`` envelope: ``{counts: {posts: N}}``.

    Wraps the upstream's already-wrapped count so callers get a
    typed ``counts.posts`` access.
    """

    counts: Optional[dict] = None
    source_tag: Optional[SourceTag] = None

    def total(self) -> Optional[int]:
        """Return the post count, when present.

        :return: Number of posts matching the tag query, or ``None``
                  if the upstream omitted the count.
        :rtype: int or None
        """
        if not self.counts:
            return None
        v = self.counts.get("posts")
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None


# ---------- helpers ----------


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` when one isn't
    already attached. Used by ``to_common()`` for direct-from-JSON
    construction paths that bypass the high-level fetch helper."""
    from datetime import datetime, timezone

    return SourceTag(backend="danbooru", fetched_at=datetime.now(timezone.utc))


def selftest() -> bool:
    """Smoke-test the Danbooru rich models.

    Validates a synthetic :class:`DanbooruPost` round-trips through
    ``model_dump_json`` / ``model_validate_json`` and projects to a
    well-formed :class:`~animedex.models.art.ArtPost`.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    post = DanbooruPost(
        id=1,
        rating="g",
        score=42,
        file_url="https://danbooru.donmai.us/data/abc.jpg",
        preview_file_url="https://danbooru.donmai.us/data/preview/abc.jpg",
        tag_string="touhou marisa rating:g",
        tag_string_artist="zun",
        source="https://example.invalid/",
        image_width=1024,
        image_height=768,
        source_tag=src,
    )
    DanbooruPost.model_validate_json(post.model_dump_json())
    common = post.to_common()
    assert common.id == "danbooru:1"
    assert common.rating == "g"
    assert "touhou" in common.tags
    assert common.artist == "zun"

    count = DanbooruCount.model_validate({"counts": {"posts": "12345"}})
    assert count.total() == 12345
    return True
