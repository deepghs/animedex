"""
Tests for :mod:`animedex.models.manga`.

Mirrors the anime suite: pins the public field set, optional
defaults, JSON round-trip. ``AtHomeServer`` is exercised because
it carries the short-lived base URL and per-page hashes that the
Phase 6 reader relies on - pinning the shape now keeps the public
model contract stable through that release.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "mangadex") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestMangaMinimal:
    def test_construction_with_only_required(self):
        from animedex.models.manga import Manga

        m = Manga(id="mangadex:abc-123", title="Frieren", ids={"al": "154587"}, source=_src())

        assert m.id == "mangadex:abc-123"
        assert m.title == "Frieren"

    def test_optional_defaults(self):
        from animedex.models.manga import Manga

        m = Manga(id="mangadex:abc", title="x", ids={}, source=_src())
        assert m.chapters == []
        assert m.cover_url is None
        assert m.languages == []
        assert m.description is None
        assert m.status is None
        assert m.format is None
        assert m.genres == []
        assert m.tags == []


class TestMangaFull:
    def test_construction_with_all_fields(self):
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
            description="An elf mage's journey after the demon king has fallen.",
            status="ongoing",
            format="MANGA",
            genres=["Fantasy", "Drama"],
            tags=["Elves"],
            ids={"al": "154587"},
            source=_src(),
        )

        assert m.cover_url is not None
        assert len(m.chapters) == 1
        assert m.status == "ongoing"
        assert m.format == "MANGA"

    def test_round_trip_json(self):
        from animedex.models.manga import Manga

        m = Manga(
            id="mangadex:abc",
            title="x",
            description="y",
            status="completed",
            format="ONE_SHOT",
            genres=["Comedy"],
            ids={},
            source=_src(),
        )
        assert Manga.model_validate_json(m.model_dump_json()) == m


class TestMangaStatusValidation:
    def test_known_status_accepted(self):
        from animedex.models.manga import Manga

        for value in ("ongoing", "completed", "hiatus", "cancelled", "unknown"):
            Manga(id="x:1", title="x", ids={}, source=_src(), status=value)

    def test_unknown_status_rejected(self):
        from animedex.models.manga import Manga

        with pytest.raises(Exception):
            Manga(id="x:1", title="x", ids={}, source=_src(), status="bogus")


class TestMangaFormatValidation:
    def test_known_formats_accepted(self):
        from animedex.models.manga import Manga

        for value in ("MANGA", "NOVEL", "ONE_SHOT", "DOUJINSHI", "MANHWA", "MANHUA"):
            Manga(id="x:1", title="x", ids={}, source=_src(), format=value)

    def test_unknown_format_rejected(self):
        from animedex.models.manga import Manga

        with pytest.raises(Exception):
            Manga(id="x:1", title="x", ids={}, source=_src(), format="BOGUS")


class TestMangaIdsTyping:
    def test_int_value_rejected(self):
        from animedex.models.manga import Manga

        with pytest.raises(Exception):
            Manga(id="x:1", title="x", ids={"mal": 12345}, source=_src())


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
