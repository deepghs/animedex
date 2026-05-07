"""
Tests for :mod:`animedex.models.anime`.

The anime models compose :class:`~animedex.models.common.SourceTag`
provenance into the typed shape AniList, Jikan, Kitsu, and
Shikimori backends populate. The tests pin the public field set,
optional defaults, JSON round-trip, and the canonical Literal
enums for ``status`` / ``format`` / ``season`` so per-backend
mapping functions have a stable target.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "anilist") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestAnimeTitle:
    def test_minimal_construction(self):
        from animedex.models.anime import AnimeTitle

        t = AnimeTitle(romaji="Sousou no Frieren")

        assert t.romaji == "Sousou no Frieren"
        assert t.english is None
        assert t.native is None

    def test_all_variants(self):
        from animedex.models.anime import AnimeTitle

        t = AnimeTitle(
            romaji="Sousou no Frieren",
            english="Frieren: Beyond Journey's End",
            native="葬送のフリーレン",
        )

        assert t.english == "Frieren: Beyond Journey's End"
        assert t.native is not None


class TestAnimeRating:
    def test_construction(self):
        from animedex.models.anime import AnimeRating

        r = AnimeRating(score=9.34, scale=10.0, votes=120000)

        assert r.score == 9.34
        assert r.scale == 10.0
        assert r.votes == 120000

    def test_votes_optional(self):
        from animedex.models.anime import AnimeRating

        r = AnimeRating(score=9.0, scale=10.0)
        assert r.votes is None


class TestAnimeStreamingLink:
    def test_construction(self):
        from animedex.models.anime import AnimeStreamingLink

        link = AnimeStreamingLink(provider="Crunchyroll", url="https://example.invalid/x")

        assert link.provider == "Crunchyroll"
        assert link.url == "https://example.invalid/x"


class TestAnimeMinimal:
    def test_construction_with_only_required(self):
        from animedex.models.anime import Anime, AnimeTitle

        a = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="Sousou no Frieren"),
            ids={"mal": "52991"},
            source=_src(),
        )

        assert a.id == "anilist:154587"
        assert a.title.romaji == "Sousou no Frieren"
        assert a.ids == {"mal": "52991"}
        assert a.source.backend == "anilist"

    def test_optional_defaults(self):
        from animedex.models.anime import Anime, AnimeTitle

        a = Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="x"),
            ids={},
            source=_src(),
        )
        assert a.score is None
        assert a.episodes is None
        assert a.studios == []
        assert a.streaming == []
        assert a.description is None
        assert a.genres == []
        assert a.tags == []
        assert a.status is None
        assert a.format is None
        assert a.season is None
        assert a.season_year is None
        assert a.aired_from is None
        assert a.aired_to is None
        assert a.duration_minutes is None
        assert a.cover_image_url is None
        assert a.banner_image_url is None
        assert a.trailer_url is None
        assert a.source_material is None
        assert a.country_of_origin is None
        assert a.is_adult is None
        assert a.age_rating is None
        assert a.popularity is None


class TestAnimeFull:
    def test_construction_with_all_fields(self):
        from animedex.models.anime import (
            Anime,
            AnimeRating,
            AnimeStreamingLink,
            AnimeTitle,
        )

        a = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="Sousou no Frieren", english="Frieren: Beyond Journey's End"),
            score=AnimeRating(score=9.34, scale=10.0),
            episodes=28,
            studios=["Madhouse"],
            streaming=[AnimeStreamingLink(provider="Crunchyroll", url="https://example.invalid/x")],
            description="An elf mage's journey after the demon king has fallen.",
            genres=["Adventure", "Drama", "Fantasy"],
            tags=["Elves", "Magic", "Slow Burn"],
            status="finished",
            format="TV",
            season="FALL",
            season_year=2023,
            aired_from=date(2023, 9, 29),
            aired_to=date(2024, 3, 22),
            duration_minutes=24,
            cover_image_url="https://example.invalid/cover.jpg",
            banner_image_url="https://example.invalid/banner.jpg",
            trailer_url="https://example.invalid/trailer",
            source_material="manga",
            country_of_origin="JP",
            is_adult=False,
            age_rating="PG-13",
            popularity=15000,
            ids={"mal": "52991", "kitsu": "47390"},
            source=_src(),
        )
        assert a.description.startswith("An elf")
        assert "Adventure" in a.genres
        assert a.status == "finished"
        assert a.format == "TV"
        assert a.season == "FALL"
        assert a.aired_from == date(2023, 9, 29)
        assert a.duration_minutes == 24


class TestAnimeStatusValidation:
    def test_known_status_accepted(self):
        from animedex.models.anime import Anime, AnimeTitle

        for value in ("airing", "finished", "upcoming", "cancelled", "hiatus", "unknown"):
            Anime(
                id="x:1",
                title=AnimeTitle(romaji="x"),
                ids={},
                source=_src(),
                status=value,
            )

    def test_unknown_status_rejected(self):
        from animedex.models.anime import Anime, AnimeTitle

        with pytest.raises(Exception):
            Anime(
                id="x:1",
                title=AnimeTitle(romaji="x"),
                ids={},
                source=_src(),
                status="bogus",
            )


class TestAnimeFormatValidation:
    def test_known_formats_accepted(self):
        from animedex.models.anime import Anime, AnimeTitle

        for value in ("TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"):
            Anime(
                id="x:1",
                title=AnimeTitle(romaji="x"),
                ids={},
                source=_src(),
                format=value,
            )

    def test_unknown_format_rejected(self):
        from animedex.models.anime import Anime, AnimeTitle

        with pytest.raises(Exception):
            Anime(
                id="x:1",
                title=AnimeTitle(romaji="x"),
                ids={},
                source=_src(),
                format="BOGUS",
            )


class TestIdsTyping:
    """Per ``plans/05 §3`` ids is ``dict[str, str]``. Backends emit
    int ids occasionally (MAL via Jikan); we want pydantic to refuse
    them at the boundary so a downstream ``a.ids["mal"].startswith(...)``
    fails at parse time, not at render time."""

    def test_int_value_rejected(self):
        from animedex.models.anime import Anime, AnimeTitle

        with pytest.raises(Exception):
            Anime(
                id="x:1",
                title=AnimeTitle(romaji="x"),
                ids={"mal": 12345},
                source=_src(),
            )


class TestRoundTrip:
    def test_round_trip_json(self):
        from animedex.models.anime import Anime, AnimeRating, AnimeTitle

        original = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="Sousou no Frieren"),
            score=AnimeRating(score=9.34, scale=10.0),
            episodes=28,
            description="An elf's journey.",
            genres=["Fantasy"],
            status="finished",
            format="TV",
            season="FALL",
            season_year=2023,
            aired_from=date(2023, 9, 29),
            aired_to=date(2024, 3, 22),
            duration_minutes=24,
            cover_image_url="https://example.invalid/c.jpg",
            popularity=15000,
            ids={"mal": "52991"},
            source=_src(),
        )

        rt = Anime.model_validate_json(original.model_dump_json())

        assert rt == original

    def test_is_frozen(self):
        from animedex.models.anime import Anime, AnimeTitle

        a = Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="x"),
            ids={},
            source=_src(),
        )
        with pytest.raises(Exception):
            a.id = "anilist:2"

    def test_extra_fields_ignored(self):
        from animedex.models.anime import Anime

        Anime.model_validate(
            {
                "id": "anilist:1",
                "title": {"romaji": "x", "future_subfield": "ignored"},
                "ids": {},
                "source": {
                    "backend": "anilist",
                    "fetched_at": "2026-05-07T10:00:00+00:00",
                },
                "future_top_level": "ignored",
            }
        )
