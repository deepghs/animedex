"""Tests for Shikimori rich model helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src() -> SourceTag:
    return SourceTag(backend="shikimori", fetched_at=datetime(2026, 5, 9, tzinfo=timezone.utc))


class TestCommonProjection:
    def test_anime_to_common_projects_rich_fields(self):
        from animedex.backends.shikimori.models import (
            ShikimoriAnime,
            ShikimoriEntity,
            ShikimoriImage,
            ShikimoriStudio,
            ShikimoriVideo,
        )

        anime = ShikimoriAnime(
            id=52991,
            name="Sousou no Frieren",
            english=["Frieren: Beyond Journey's End"],
            japanese=["Sousou no Frieren Native"],
            image=ShikimoriImage(original="/system/animes/original/52991.jpg"),
            kind="tv",
            score="9.27",
            status="released",
            episodes=28,
            aired_on="2023-09-29",
            released_on="2024-03-22",
            rating="pg_13",
            synonyms=["Frieren at the Funeral", ""],
            duration=24,
            description="A Shikimori fixture-sized synopsis.",
            myanimelist_id=52991,
            rates_scores_stats=[{"name": 10, "value": 100}, {"name": 9, "value": "25"}, {"name": 8, "value": None}],
            genres=[ShikimoriEntity(id=1, name="Adventure"), ShikimoriEntity(id=2)],
            studios=[ShikimoriStudio(id=3, filtered_name="Madhouse"), ShikimoriStudio(id=4)],
            videos=[ShikimoriVideo(url="https://video.example/trailer")],
            source_tag=_src(),
        )

        common = anime.to_common()

        assert common.id == "shikimori:52991"
        assert common.title.romaji == "Sousou no Frieren"
        assert common.title.english == "Frieren: Beyond Journey's End"
        assert common.title.native == "Sousou no Frieren Native"
        assert common.score is not None
        assert common.score.score == 9.27
        assert common.score.votes == 125
        assert common.episodes == 28
        assert common.studios == ["Madhouse"]
        assert common.description == "A Shikimori fixture-sized synopsis."
        assert common.genres == ["Adventure"]
        assert common.status == "finished"
        assert common.format == "TV"
        assert common.aired_from == date(2023, 9, 29)
        assert common.aired_to == date(2024, 3, 22)
        assert common.duration_minutes == 24
        assert common.cover_image_url == "https://shikimori.io/system/animes/original/52991.jpg"
        assert common.trailer_url == "https://video.example/trailer"
        assert common.age_rating == "pg_13"
        assert common.title_synonyms == ["Frieren at the Funeral"]
        assert common.ids == {"shikimori": "52991", "mal": "52991"}

    def test_related_models_project_to_common_shapes(self):
        from animedex.backends.shikimori.models import (
            ShikimoriCharacter,
            ShikimoriImage,
            ShikimoriPerson,
            ShikimoriStudio,
        )

        image = ShikimoriImage(original="system/characters/original/1.jpg")
        character = ShikimoriCharacter(id=1, name=None, russian="Native Character", image=image)
        person = ShikimoriPerson(id=2, name=None, russian="Native Person", image=image)
        studio = ShikimoriStudio(id=3, name="Raw Studio", filtered_name=None, real=True)

        common_character = character.to_common()
        common_person = person.to_common()
        common_studio = studio.to_common()

        assert common_character.id == "shikimori:character:1"
        assert common_character.name == "Native Character"
        assert common_character.image_url == "https://shikimori.io/system/characters/original/1.jpg"
        assert common_character.source.backend == "shikimori"
        assert common_person.id == "shikimori:person:2"
        assert common_person.name == "Native Person"
        assert common_person.image_url == "https://shikimori.io/system/characters/original/1.jpg"
        assert common_person.source.backend == "shikimori"
        assert common_studio.id == "shikimori:studio:3"
        assert common_studio.name == "Raw Studio"
        assert common_studio.is_animation_studio is True
        assert common_studio.source.backend == "shikimori"

    def test_calendar_to_common_adds_next_airing_when_complete(self):
        from animedex.backends.shikimori.models import ShikimoriAnime, ShikimoriCalendarEntry

        entry = ShikimoriCalendarEntry(
            next_episode=5,
            next_episode_at="2026-05-09T12:30:00.000+03:00",
            anime=ShikimoriAnime(id=10, name="Airing", status="ongoing"),
            source_tag=_src(),
        )

        common = entry.to_common()

        assert common.id == "shikimori:10"
        assert common.status == "airing"
        assert common.next_airing_episode is not None
        assert common.next_airing_episode.episode == 5

    def test_calendar_to_common_returns_base_anime_when_schedule_incomplete(self):
        from animedex.backends.shikimori.models import ShikimoriAnime, ShikimoriCalendarEntry

        entry = ShikimoriCalendarEntry(anime=ShikimoriAnime(id=10, name="Airing"))
        fallback = ShikimoriCalendarEntry(next_episode=1, next_episode_at="not-a-date")

        assert entry.to_common().id == "shikimori:10"
        assert entry.to_common().next_airing_episode is None
        assert fallback.to_common().id == "shikimori:0"


class TestHelperEdges:
    def test_scalar_helpers_cover_empty_invalid_and_unknown_values(self):
        from animedex.backends.shikimori import models

        assert models._absolute_url(None) is None
        assert models._absolute_url("https://cdn.example/image.jpg") == "https://cdn.example/image.jpg"
        assert models._absolute_url("path/image.jpg") == "https://shikimori.io/path/image.jpg"
        assert models._first_string([None, "", "Title"]) == "Title"
        assert models._first_string([]) is None
        assert models._parse_float(None) is None
        assert models._parse_float("bad") is None
        assert models._parse_float("1.5") == 1.5
        assert models._score_votes([]) is None
        assert models._score_votes([{"value": "bad"}, {"value": 2}]) == 2
        assert models._parse_date(None) is None
        assert models._parse_date("bad") is None
        assert models._parse_date("2026-05-09") == date(2026, 5, 9)
        assert models._parse_datetime(None) is None
        assert models._parse_datetime("bad") is None
        assert models._parse_datetime("2026-05-09T00:00:00Z") is not None
        assert models._normalise_status("anons") == "upcoming"
        assert models._normalise_status(None) is None
        assert models._normalise_status("paused") == "unknown"
        assert models._normalise_format(None) is None
        assert models._normalise_format("tv_special") == "TV_SHORT"
        assert models._normalise_format("unknown") is None


class TestSelftest:
    def test_package_and_model_selftests_run(self):
        from animedex.backends import shikimori
        from animedex.backends.shikimori import models

        assert models.selftest() is True
        assert shikimori.selftest() is True
