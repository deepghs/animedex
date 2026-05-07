"""
Tests for :mod:`animedex.models.trace`.

:class:`TraceHit` is the typed result shape for ``animedex trace``,
which calls Trace.moe and gets back a screenshot-to-anime hit with
episode / timecode / similarity.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "trace") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestTraceHitMinimal:
    def test_construction(self):
        from animedex.models.trace import TraceHit

        hit = TraceHit(
            anilist_id=154587,
            similarity=0.95,
            start_at_seconds=12.0,
            frame_at_seconds=13.2,
            end_at_seconds=14.5,
            source=_src(),
        )
        assert hit.anilist_id == 154587
        assert hit.similarity == 0.95
        assert hit.episode is None
        assert hit.preview_video_url is None


class TestTraceHitFull:
    def test_construction(self):
        from animedex.models.trace import TraceHit

        hit = TraceHit(
            anilist_id=154587,
            similarity=0.93,
            episode="1.5",
            start_at_seconds=12.0,
            frame_at_seconds=13.2,
            end_at_seconds=14.5,
            preview_video_url="https://x.invalid/preview.mp4",
            preview_image_url="https://x.invalid/preview.jpg",
            source=_src(),
        )
        assert hit.episode == "1.5"
        assert hit.preview_video_url is not None


class TestSimilarityRange:
    def test_similarity_must_be_between_0_and_1(self):
        from animedex.models.trace import TraceHit

        with pytest.raises(Exception):
            TraceHit(
                anilist_id=1,
                similarity=1.5,
                start_at_seconds=0.0,
                frame_at_seconds=0.5,
                end_at_seconds=1.0,
                source=_src(),
            )

    def test_similarity_zero_allowed(self):
        from animedex.models.trace import TraceHit

        TraceHit(
            anilist_id=1,
            similarity=0.0,
            start_at_seconds=0.0,
            frame_at_seconds=0.0,
            end_at_seconds=1.0,
            source=_src(),
        )


class TestRoundTrip:
    def test_round_trip_json(self):
        from animedex.models.trace import TraceHit

        hit = TraceHit(
            anilist_id=154587,
            similarity=0.95,
            episode="1",
            start_at_seconds=12.0,
            frame_at_seconds=13.2,
            end_at_seconds=14.5,
            source=_src(),
        )

        assert TraceHit.model_validate_json(hit.model_dump_json()) == hit


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.models import trace

        assert trace.selftest() is True
