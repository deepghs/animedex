"""Tests for :mod:`animedex.backends.ghibli`.

The Ghibli backend is intentionally offline, so these tests exercise
real reads of the bundled snapshot rather than an HTTP mock.
"""

from __future__ import annotations

import pytest

from animedex.backends import ghibli
from animedex.backends.ghibli.models import GhibliFilm, GhibliPerson


pytestmark = pytest.mark.unittest


class TestFilms:
    def test_films_returns_snapshot_rows(self):
        out = ghibli.films()
        assert len(out) >= 20
        assert isinstance(out[0], GhibliFilm)
        assert out[0].source_tag.backend == "ghibli"

    def test_film_by_id_matches_list(self):
        first = ghibli.films()[0]
        one = ghibli.film(first.id)
        assert one.id == first.id
        assert one.title == first.title

    def test_filters_by_director_and_score(self):
        out = ghibli.films(director="Miyazaki", min_rt_score=90)
        assert out
        assert all("Miyazaki" in (film.director or "") for film in out)
        assert all(int(film.rt_score or 0) >= 90 for film in out)

    def test_film_to_common_projects_to_anime(self):
        from animedex.models.anime import Anime

        common = ghibli.films()[0].to_common()
        assert isinstance(common, Anime)
        assert common.id.startswith("ghibli:")
        assert common.source.backend == "ghibli"


class TestPeople:
    def test_people_returns_snapshot_rows(self):
        out = ghibli.people()
        assert len(out) >= 50
        assert isinstance(out[0], GhibliPerson)

    def test_people_name_filter(self):
        out = ghibli.people(name="Haku")
        assert out
        assert any(row.name == "Haku" for row in out)

    def test_person_to_common_projects_to_character(self):
        from animedex.models.character import Character

        common = ghibli.people(name="Haku")[0].to_common()
        assert isinstance(common, Character)
        assert common.source.backend == "ghibli"


class TestOtherFamilies:
    def test_locations_vehicles_species_are_available(self):
        assert ghibli.locations()
        assert ghibli.vehicles()
        assert ghibli.species()

    def test_singleton_lookups(self):
        loc = ghibli.locations()[0]
        veh = ghibli.vehicles()[0]
        sp = ghibli.species()[0]
        assert ghibli.location(loc.id).id == loc.id
        assert ghibli.vehicle(veh.id).id == veh.id
        assert ghibli.species_by_id(sp.id).id == sp.id


class TestErrors:
    def test_missing_id_raises_not_found(self):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            ghibli.film("not-a-real-id")
        assert ei.value.reason == "not-found"


class TestSelftest:
    def test_selftest_runs(self):
        assert ghibli.selftest() is True
