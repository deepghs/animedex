"""
Tests for :mod:`animedex.models.manga`.

Mirrors the anime suite: pin field names, optional defaults, and JSON
round-trip. The ``AtHomeServer`` model is exercised because it carries
the short-lived base URL and per-page hashes that the Phase 6 reader
will rely on - it is part of the public model contract from day one,
even though the reader itself ships later.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "mangadex") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestManga:
    def test_minimal_construction(self):
        from animedex.models.manga import Manga

        m = Manga(id="mangadex:abc-123", title="Frieren", ids={"al": "154587"}, source=_src())

        assert m.id == "mangadex:abc-123"
        assert m.title == "Frieren"
        assert m.chapters == []
        assert m.cover_url is None
        assert m.languages == []

    def test_full_construction(self):
        from animedex.models.manga import Chapter, Manga

        m = Manga(
            id="mangadex:abc-123",
            title="Frieren",
            cover_url="https://example.invalid/cover.jpg",
            chapters=[
                Chapter(
                    id="ch-1",
                    number="1",
                    title="A bond forgotten",
                    language="en",
                    pages=20,
                    source=_src(),
                ),
            ],
            languages=["en", "ja"],
            ids={"al": "154587"},
            source=_src(),
        )

        assert m.cover_url is not None
        assert len(m.chapters) == 1
        assert m.chapters[0].number == "1"

    def test_round_trip_json(self):
        from animedex.models.manga import Manga

        m = Manga(id="mangadex:abc", title="x", ids={}, source=_src())
        assert Manga.model_validate_json(m.model_dump_json()) == m


class TestChapter:
    def test_minimal_construction(self):
        from animedex.models.manga import Chapter

        ch = Chapter(id="ch-1", number="1", language="en", source=_src())

        assert ch.id == "ch-1"
        assert ch.title is None
        assert ch.pages is None

    def test_round_trip_json(self):
        from animedex.models.manga import Chapter

        ch = Chapter(id="ch-1", number="1", language="en", pages=20, source=_src())
        assert Chapter.model_validate_json(ch.model_dump_json()) == ch


class TestAtHomeServer:
    def test_construction(self):
        """Reflects the ``GET /at-home/server/{chapter}`` envelope."""
        from animedex.models.manga import AtHomeServer

        s = AtHomeServer(
            base_url="https://uploads.example.invalid",
            chapter_hash="HHHH",
            data=["page1.jpg", "page2.jpg"],
            data_saver=["page1.jpg", "page2.jpg"],
            source=_src(),
        )

        assert s.base_url.endswith("invalid")
        assert len(s.data) == 2

    def test_data_saver_optional(self):
        from animedex.models.manga import AtHomeServer

        s = AtHomeServer(
            base_url="https://x.invalid",
            chapter_hash="HHHH",
            data=["a.jpg"],
            source=_src(),
        )
        assert s.data_saver == []
