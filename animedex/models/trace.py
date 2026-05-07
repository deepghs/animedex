"""
Trace.moe screenshot-search hit model.

:class:`TraceHit` is the typed shape for the ``animedex trace``
command. Trace.moe takes a screenshot and returns one or more
candidate matches, each carrying the AniList id (so the result can
be chained into other animedex backends), the episode and timecode
where the frame appears, a similarity score, and optional preview
media URLs.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from animedex.models.common import AnimedexModel, SourceTag


class TraceHit(AnimedexModel):
    """A single Trace.moe match.

    :ivar anilist_id: AniList identifier of the matched series. Use
                       this to chain into the AniList backend for
                       full metadata.
    :vartype anilist_id: int
    :ivar similarity: Match confidence in the closed interval [0, 1].
                       Trace.moe documentation considers values below
                       ~0.87 unreliable.
    :vartype similarity: float
    :ivar episode: Episode identifier (string-typed because some
                    matches return non-integer values like ``"1.5"``
                    for OVAs).
    :vartype episode: str or None
    :ivar start_at_seconds: Frame timestamp from the start of the
                             episode, in seconds.
    :vartype start_at_seconds: float
    :ivar end_at_seconds: Frame end timestamp, in seconds.
    :vartype end_at_seconds: float
    :ivar preview_video_url: Short MP4 preview of the matched scene.
    :vartype preview_video_url: str or None
    :ivar preview_image_url: Single-frame JPEG preview.
    :vartype preview_image_url: str or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    anilist_id: int
    similarity: float = Field(ge=0.0, le=1.0)
    episode: Optional[str] = None
    start_at_seconds: float
    end_at_seconds: float
    preview_video_url: Optional[str] = None
    preview_image_url: Optional[str] = None
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the trace model.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    hit = TraceHit(
        anilist_id=1,
        similarity=0.9,
        episode="1",
        start_at_seconds=0.0,
        end_at_seconds=1.0,
        preview_video_url="https://x.invalid/p.mp4",
        preview_image_url="https://x.invalid/p.jpg",
        source=src,
    )
    TraceHit.model_validate_json(hit.model_dump_json())
    return True
