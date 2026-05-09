"""Tests for :mod:`animedex.backends.ghibli`.

The Ghibli backend is intentionally offline, so these tests exercise
real reads of the bundled snapshot rather than an HTTP mock.
"""

from __future__ import annotations

import pytest

from animedex.backends import ghibli
from animedex.backends.ghibli import models as ghibli_models
from animedex.backends.ghibli.models import GhibliFilm, GhibliPerson
from animedex.models.common import ApiError


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

    def test_filters_reject_non_matching_film_fields(self):
        assert ghibli.films(title="not a real ghibli film title") == []
        assert ghibli.films(producer="not a real ghibli producer") == []
        assert ghibli.films(release_year=1900) == []

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

    def test_people_filters_reject_non_matching_fields(self):
        assert ghibli.people(gender="not-a-real-gender") == []
        assert ghibli.people(film_id="not-a-real-film-id") == []
        assert ghibli.people(species_id="not-a-real-species-id") == []

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

    def test_location_filters_reject_non_matching_fields(self):
        assert ghibli.locations(name="not a real location") == []
        assert ghibli.locations(climate="not a real climate") == []
        assert ghibli.locations(terrain="not a real terrain") == []
        assert ghibli.locations(film_id="not-a-real-film-id") == []

    def test_vehicle_filters_reject_non_matching_fields(self):
        assert ghibli.vehicles(name="not a real vehicle") == []
        assert ghibli.vehicles(vehicle_class="not a real vehicle class") == []
        assert ghibli.vehicles(film_id="not-a-real-film-id") == []

    def test_species_filters_reject_non_matching_fields(self):
        assert ghibli.species(name="not a real species") == []
        assert ghibli.species(classification="not a real classification") == []
        assert ghibli.species(film_id="not-a-real-film-id") == []


class TestErrors:
    def test_missing_id_raises_not_found(self):
        with pytest.raises(ApiError) as ei:
            ghibli.film("not-a-real-id")
        assert ei.value.reason == "not-found"

    def test_snapshot_shape_rejects_bad_top_level(self):
        with pytest.raises(ApiError) as ei:
            ghibli._validate_snapshot_shape({"films": []})
        assert ei.value.reason == "upstream-shape"

    def test_snapshot_shape_rejects_non_list_family(self):
        payload = {"films": [], "people": [], "locations": [], "vehicles": [], "species": {}}
        with pytest.raises(ApiError) as ei:
            ghibli._validate_snapshot_shape(payload)
        assert ei.value.reason == "upstream-shape"

    def test_snapshot_loader_reads_pyinstaller_fallback(self, tmp_path, monkeypatch):
        snapshot = ghibli._load_snapshot()
        data_dir = tmp_path / "animedex" / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "ghibli.json").write_text(
            """{"films":[],"people":[],"locations":[],"vehicles":[],"species":[]}""",
            encoding="utf-8",
        )
        monkeypatch.setattr(ghibli.resources, "files", lambda *_args, **_kw: (_ for _ in ()).throw(FileNotFoundError()))
        monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
        monkeypatch.setattr(ghibli, "_SNAPSHOT", None)
        try:
            assert ghibli._load_snapshot() == {
                "films": [],
                "people": [],
                "locations": [],
                "vehicles": [],
                "species": [],
            }
        finally:
            monkeypatch.setattr(ghibli, "_SNAPSHOT", snapshot)

    def test_snapshot_loader_reraises_without_pyinstaller_bundle(self, monkeypatch):
        snapshot = ghibli._load_snapshot()
        monkeypatch.setattr(ghibli.resources, "files", lambda *_args, **_kw: (_ for _ in ()).throw(FileNotFoundError()))
        monkeypatch.delattr("sys._MEIPASS", raising=False)
        monkeypatch.setattr(ghibli, "_SNAPSHOT", None)
        try:
            with pytest.raises(FileNotFoundError):
                ghibli._load_snapshot()
        finally:
            monkeypatch.setattr(ghibli, "_SNAPSHOT", snapshot)


class TestModelEdges:
    def test_backend_helpers_handle_empty_and_invalid_values(self):
        assert ghibli._contains(None, "sample") is False
        assert ghibli._to_int("not-an-int") is None

    def test_direct_film_model_to_common_handles_invalid_numbers(self):
        common = GhibliFilm(
            id="film-1", title="Sample", release_date="unknown", running_time="n/a", rt_score="n/a"
        ).to_common()
        assert common.source.backend == "ghibli"
        assert common.score is None
        assert common.season_year is None
        assert common.duration_minutes is None

    def test_direct_person_model_to_common_uses_default_source(self):
        common = GhibliPerson(id="person-1", name="Sample").to_common()
        assert common.source.backend == "ghibli"
        assert common.description is None

    def test_model_int_parser_handles_none(self):
        assert ghibli_models._to_int(None) is None

    def test_model_selftest_runs(self):
        assert ghibli_models.selftest() is True


class TestSelftest:
    def test_selftest_runs(self):
        assert ghibli.selftest() is True
