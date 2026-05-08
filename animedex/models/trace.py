"""
Trace.moe screenshot-search models.

:class:`TraceHit` is the typed shape returned by ``animedex trace
search``: each hit carries the AniList id (so the result can be
chained into the AniList backend for richer metadata), the episode
and timecode where the frame appears, a similarity score, and
optional preview media URLs.

:class:`TraceQuota` is the typed shape of ``animedex trace quota``
(``GET /me``). The upstream returns the caller's IP in the ``id``
field; the mapper unconditionally drops it before constructing the
record (of #4 covered the same vector for fixtures).
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from animedex.models.anime import AnimeTitle
from animedex.models.common import AnimedexModel, SourceTag


class TraceHit(AnimedexModel):
    """A single Trace.moe match.

    :ivar anilist_id: AniList identifier of the matched series. Use
                       this to chain into the AniList backend for
                       full metadata.
    :vartype anilist_id: int
    :ivar anilist_title: AniList title block, populated when the
                          ``/search`` call was made with
                          ``anilistInfo=true``. Saves a follow-up
                          AniList round-trip.
    :vartype anilist_title: AnimeTitle or None
    :ivar similarity: Match confidence in the closed interval [0, 1].
                       Trace.moe documentation considers values below
                       ~0.87 unreliable.
    :vartype similarity: float
    :ivar episode: Episode identifier (string-typed because some
                    matches return non-integer values like ``"1.5"``
                    for OVAs).
    :vartype episode: str or None
    :ivar start_at_seconds: Scene start timestamp inside the episode,
                             in seconds.
    :vartype start_at_seconds: float
    :ivar frame_at_seconds: Exact matched-frame timestamp, in seconds.
                             Lies between ``start_at_seconds`` and
                             ``end_at_seconds``.
    :vartype frame_at_seconds: float
    :ivar end_at_seconds: Scene end timestamp, in seconds.
    :vartype end_at_seconds: float
    :ivar episode_filename: Source video filename. Useful for human
                              verification of the match (e.g.
                              ``"[Group][Show][05][1080p].mkv"``).
    :vartype episode_filename: str or None
    :ivar episode_duration_seconds: Total length of the matched
                                      episode, in seconds.
    :vartype episode_duration_seconds: float or None
    :ivar preview_video_url: Short MP4 preview of the matched scene.
    :vartype preview_video_url: str or None
    :ivar preview_image_url: Single-frame JPEG preview.
    :vartype preview_image_url: str or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    anilist_id: int
    anilist_title: Optional[AnimeTitle] = None
    similarity: float = Field(ge=0.0, le=1.0)
    episode: Optional[str] = None
    start_at_seconds: float
    frame_at_seconds: float
    end_at_seconds: float
    episode_filename: Optional[str] = None
    episode_duration_seconds: Optional[float] = None
    preview_video_url: Optional[str] = None
    preview_image_url: Optional[str] = None
    source: SourceTag


class TraceQuota(AnimedexModel):
    """Trace.moe quota state for the calling client.

    Returned by ``GET /me``. The upstream payload also carries an
    ``id`` field that holds the caller's egress IP — the mapper
    drops it unconditionally so the value never appears in cache
    rows or rendered output.

    :ivar priority: API priority class (0 for anonymous, higher for
                     sponsor / patron tiers).
    :vartype priority: int
    :ivar concurrency: Max simultaneous searches the tier allows.
                        Anonymous tier: 1.
    :vartype concurrency: int
    :ivar quota: Monthly search budget.
    :vartype quota: int
    :ivar quota_used: Searches consumed this month. Upstream returns
                       this as a JSON string; the mapper coerces to
                       ``int``.
    :vartype quota_used: int
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    priority: int
    concurrency: int
    quota: int
    quota_used: int
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the trace models.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    hit = TraceHit(
        anilist_id=1,
        anilist_title=AnimeTitle(romaji="x"),
        similarity=0.9,
        episode="1",
        start_at_seconds=0.0,
        frame_at_seconds=0.5,
        end_at_seconds=1.0,
        episode_filename="x.mkv",
        episode_duration_seconds=1500.0,
        preview_video_url="https://x.invalid/p.mp4",
        preview_image_url="https://x.invalid/p.jpg",
        source=src,
    )
    TraceHit.model_validate_json(hit.model_dump_json())

    quota = TraceQuota(priority=0, concurrency=1, quota=100, quota_used=18, source=src)
    TraceQuota.model_validate_json(quota.model_dump_json())
    return True
