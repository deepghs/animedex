"""
Tests for :mod:`animedex.models.anime`.

The anime models compose :class:`~animedex.models.common.SourceTag`
provenance into a typed surface the AniList, Jikan, Kitsu, and
Shikimori backends will all populate. The tests pin the public field
names, the optional-vs-required defaults, and the JSON round-trip
shape that the cache layer will serialise through.
"""

from __future__ import annotations

from datetime import datetime, timezone

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


class TestAnime:
    def test_minimal_construction(self):
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
        assert a.score is None
        assert a.episodes is None
        assert a.studios == []
        assert a.streaming == []

    def test_full_construction(self):
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
            ids={"mal": "52991", "kitsu": "47390"},
            source=_src(),
        )

        assert a.score.score == 9.34
        assert a.episodes == 28
        assert a.studios == ["Madhouse"]
        assert a.streaming[0].provider == "Crunchyroll"

    def test_round_trip_json(self):
        """The cache layer round-trips backend records via JSON."""
        from animedex.models.anime import Anime, AnimeTitle

        original = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="Sousou no Frieren"),
            episodes=28,
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
