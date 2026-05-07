"""
Tests for :mod:`animedex.models.art`.

:class:`ArtPost` is the common shape across image-tagging upstreams
(Danbooru, Waifu.im, NekosBest). The tests pin the field set,
the per-source ``rating`` enum (Danbooru's ``g/s/q/e``), and the
JSON round-trip.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "danbooru") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestArtPostMinimal:
    def test_construction_with_only_required(self):
        from animedex.models.art import ArtPost

        p = ArtPost(id="danbooru:1", url="https://example.invalid/x.jpg", source=_src())

        assert p.id == "danbooru:1"
        assert p.url.endswith(".jpg")
        assert p.preview_url is None
        assert p.rating is None
        assert p.tags == []
        assert p.score is None
        assert p.artist is None
        assert p.source_url is None
        assert p.width is None
        assert p.height is None


class TestArtPostFull:
    def test_construction_with_all_fields(self):
        from animedex.models.art import ArtPost

        p = ArtPost(
            id="danbooru:1",
            url="https://example.invalid/x.jpg",
            preview_url="https://example.invalid/x_thumb.jpg",
            rating="g",
            tags=["touhou", "marisa", "score:>100"],
            score=200,
            artist="someone",
            source_url="https://artist-page.invalid",
            width=1920,
            height=1080,
            source=_src(),
        )

        assert p.rating == "g"
        assert p.score == 200
        assert p.width == 1920


class TestArtPostRatingValidation:
    def test_known_ratings_accepted(self):
        from animedex.models.art import ArtPost

        for value in ("g", "s", "q", "e"):
            ArtPost(
                id="x:1",
                url="https://x.invalid/x.jpg",
                source=_src(),
                rating=value,
            )

    def test_unknown_rating_rejected(self):
        from animedex.models.art import ArtPost

        with pytest.raises(Exception):
            ArtPost(
                id="x:1",
                url="https://x.invalid/x.jpg",
                source=_src(),
                rating="x",
            )


class TestRoundTrip:
    def test_round_trip_json(self):
        from animedex.models.art import ArtPost

        p = ArtPost(
            id="danbooru:1",
            url="https://x.invalid/x.jpg",
            rating="g",
            tags=["touhou"],
            score=42,
            source=_src(),
        )

        assert ArtPost.model_validate_json(p.model_dump_json()) == p

    def test_is_frozen(self):
        from animedex.models.art import ArtPost

        p = ArtPost(id="x:1", url="https://x.invalid/x.jpg", source=_src())
        with pytest.raises(Exception):
            p.id = "x:2"


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.models import art

        assert art.selftest() is True
