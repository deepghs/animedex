"""Lossless rich Trace.moe dataclasses.

Per AGENTS.md §13 (lossless rich-model contract), the backend layer
must round-trip the upstream payload field-for-field. The user-facing
common types in :mod:`animedex.models.trace` rename fields for
Pythonic ergonomics (``from`` → ``start_at_seconds`` etc.) and so
they are projections, not the raw shape. These rich classes preserve
the upstream verbatim:

* :class:`RawTraceHit` — single ``/search`` hit row, lossless.
* :class:`RawTraceQuota` — ``/me`` body, with the caller-IP ``id``
  field DROPPED (privacy carve-out per review M1).

``to_common()`` projects to :class:`~animedex.models.trace.TraceHit`
and :class:`~animedex.models.trace.TraceQuota` respectively. Loss of
information is permitted at and only at that boundary.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import Field, model_validator

from animedex.models.anime import AnimeTitle
from animedex.models.common import BackendRichModel, SourceTag
from animedex.models.trace import TraceHit, TraceQuota


class RawTraceAnilistInfo(BackendRichModel):
    """Inner ``anilist`` block when ``anilistInfo`` is set on the
    search call. Not a fixed schema — Trace.moe may inline arbitrary
    AniList fields here. ``extra='allow'`` keeps every key.
    """

    id: Optional[int] = None
    idMal: Optional[int] = None


class RawTraceHit(BackendRichModel):
    """Single ``/search`` result row, lossless to the upstream shape.

    Field names mirror the upstream: ``from`` / ``to`` are Python
    keywords so they're aliased onto ``from_`` / ``to_``; everything
    else uses upstream-native names directly.
    """

    # ``anilist`` is either a bare int (no anilistInfo) or a nested
    # object (with anilistInfo). Use Union; pre-validators handle the
    # int case by dropping it onto ``id``.
    anilist: Union[int, RawTraceAnilistInfo, None] = None
    similarity: float = Field(ge=0.0, le=1.0)
    episode: Optional[Any] = None
    from_: float = Field(alias="from")
    at: float
    to_: float = Field(alias="to")
    filename: Optional[str] = None
    duration: Optional[float] = None
    video: Optional[str] = None
    image: Optional[str] = None
    source_tag: SourceTag

    @model_validator(mode="before")
    @classmethod
    def _coerce_anilist(cls, data):
        # When the upstream returned a raw int, leave it as int. When
        # it returned a dict, pydantic will validate it as
        # RawTraceAnilistInfo. No-op here other than to document that
        # both shapes are accepted.
        return data

    def to_common(self) -> TraceHit:
        """Project to the user-facing :class:`TraceHit` (lossy:
        renames ``from``/``at``/``to`` to Pythonic, drops everything
        in ``anilist`` beyond title)."""
        anilist_id = 0
        title = None
        if isinstance(self.anilist, int):
            anilist_id = self.anilist
        elif isinstance(self.anilist, RawTraceAnilistInfo):
            anilist_id = self.anilist.id or 0
            extra = self.anilist.model_extra or {}
            t = extra.get("title")
            if isinstance(t, dict):
                title = AnimeTitle(
                    romaji=t.get("romaji") or t.get("english") or t.get("native") or "",
                    english=t.get("english"),
                    native=t.get("native"),
                )
        return TraceHit(
            anilist_id=anilist_id,
            anilist_title=title,
            similarity=self.similarity,
            episode=str(self.episode) if self.episode is not None else None,
            start_at_seconds=self.from_,
            frame_at_seconds=self.at,
            end_at_seconds=self.to_,
            episode_filename=self.filename,
            episode_duration_seconds=self.duration,
            preview_video_url=self.video,
            preview_image_url=self.image,
            source=self.source_tag,
        )


class RawTraceQuota(BackendRichModel):
    """``/me`` body, lossless except that the upstream's ``id`` field
    is **deliberately dropped** — that field carries the caller's
    egress IP and persisting it would re-leak the value review M1
    worked to suppress. The drop is documented here and tested.
    """

    priority: int
    concurrency: int
    quota: int
    quotaUsed: Union[int, str]
    source_tag: SourceTag

    @model_validator(mode="before")
    @classmethod
    def _drop_caller_ip(cls, data):
        if isinstance(data, dict) and "id" in data:
            data = {k: v for k, v in data.items() if k != "id"}
        return data

    def to_common(self) -> TraceQuota:
        used = int(self.quotaUsed) if isinstance(self.quotaUsed, str) else self.quotaUsed
        return TraceQuota(
            priority=self.priority,
            concurrency=self.concurrency,
            quota=self.quota,
            quota_used=used,
            source=self.source_tag,
        )


def selftest() -> bool:
    from datetime import datetime, timezone

    src = SourceTag(backend="trace", fetched_at=datetime.now(timezone.utc))

    # Round-trip a representative anilistInfo=True payload.
    payload_with_anilist = {
        "anilist": {"id": 154587, "idMal": 52991, "title": {"romaji": "Sousou no Frieren"}},
        "similarity": 0.95,
        "episode": 5,
        "from": 832.7,
        "at": 836.5,
        "to": 836.8,
        "filename": "x.mkv",
        "duration": 1500.0,
        "video": "https://x.invalid/v",
        "image": "https://x.invalid/i",
        "source_tag": src,
    }
    hit = RawTraceHit.model_validate(payload_with_anilist)
    dump = hit.model_dump(by_alias=True, mode="json", exclude={"source_tag"})
    assert "from" in dump and "at" in dump and "to" in dump, dump
    common = hit.to_common()
    assert common.anilist_id == 154587

    # Round-trip a /me payload; ``id`` must be dropped.
    quota = RawTraceQuota.model_validate(
        {"id": "203.0.113.42", "priority": 0, "concurrency": 1, "quota": 100, "quotaUsed": "18", "source_tag": src}
    )
    assert "id" not in quota.model_dump(mode="json")
    assert quota.to_common().quota_used == 18
    return True
