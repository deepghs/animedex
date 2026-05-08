"""
Image / art-post models for the tagging upstreams.

:class:`ArtPost` is the cross-source projection for Danbooru,
Waifu.im, and NekosBest. The shapes are remarkably similar: every
upstream returns an image URL plus a tag list, and most expose
some content-rating axis (Danbooru's four-letter ``g/s/q/e`` is the
most expressive; Waifu.im collapses to a boolean ``is_nsfw``;
NekosBest is SFW-only).

Per ``plans/02`` and ```` we **do not** filter results
by rating; the model simply preserves whichever rating the upstream
reports so a downstream filter step is possible without a second
HTTP call.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from animedex.models.common import AnimedexModel, SourceTag


#: Danbooru's four-letter content rating. Backends that use a less
#: granular vocabulary normalise to this set.
ArtRating = Literal["g", "s", "q", "e"]


class ArtPost(AnimedexModel):
    """A single image record from an art-tagging upstream.

    :ivar id: Canonical ``"<source>:<id>"`` identifier.
    :vartype id: str
    :ivar url: Full-resolution image URL.
    :vartype url: str
    :ivar preview_url: Thumbnail URL when one is exposed.
    :vartype preview_url: str or None
    :ivar rating: Content rating, when reported. Normalised to
                   :data:`ArtRating`.
    :vartype rating: str or None
    :ivar tags: Tag list (free-form; vocabulary varies per upstream).
    :vartype tags: list of str
    :ivar score: Upstream's popularity / vote count.
    :vartype score: int or None
    :ivar artist: Attributed artist when reported.
    :vartype artist: str or None
    :ivar source_url: External URL where the image was originally
                       sourced (e.g. the artist's gallery page).
    :vartype source_url: str or None
    :ivar width: Image width in pixels.
    :vartype width: int or None
    :ivar height: Image height in pixels.
    :vartype height: int or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    url: str
    preview_url: Optional[str] = None
    rating: Optional[ArtRating] = None
    tags: List[str] = []
    score: Optional[int] = None
    artist: Optional[str] = None
    source_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the art model.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    p = ArtPost(
        id="_selftest:1",
        url="https://x.invalid/x.jpg",
        preview_url="https://x.invalid/x_thumb.jpg",
        rating="g",
        tags=["x"],
        score=1,
        artist="x",
        source_url="https://x.invalid",
        width=1,
        height=1,
        source=src,
    )
    ArtPost.model_validate_json(p.model_dump_json())
    return True
