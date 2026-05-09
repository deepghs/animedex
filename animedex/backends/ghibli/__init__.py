"""High-level Studio Ghibli Python API.

This backend is fully offline: it reads the committed
``animedex/data/ghibli.json`` snapshot and never contacts the live API.
The raw passthrough at :mod:`animedex.api.ghibli` remains available for
callers who explicitly need live upstream data.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from importlib import resources
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar

from animedex.backends.ghibli.models import (
    GhibliFilm,
    GhibliLocation,
    GhibliPerson,
    GhibliSpecies,
    GhibliVehicle,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


T = TypeVar("T")
_SNAPSHOT = None


def _load_snapshot() -> Dict[str, List[dict]]:
    """Load the vendored Studio Ghibli snapshot once."""
    global _SNAPSHOT
    if _SNAPSHOT is None:
        try:
            data_path = resources.files("animedex.data").joinpath("ghibli.json")
            with data_path.open("r", encoding="utf-8") as fh:
                payload = _json.load(fh)
        except (FileNotFoundError, ModuleNotFoundError):
            import sys
            from pathlib import Path

            bundle_dir = getattr(sys, "_MEIPASS", None)
            if not bundle_dir:
                raise
            with (Path(bundle_dir) / "animedex" / "data" / "ghibli.json").open("r", encoding="utf-8") as fh:
                payload = _json.load(fh)
        _validate_snapshot_shape(payload)
        _SNAPSHOT = payload
    return _SNAPSHOT


def _validate_snapshot_shape(payload: Any) -> None:
    expected = {"films", "people", "locations", "vehicles", "species"}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ApiError("ghibli snapshot has an unexpected top-level shape", backend="ghibli", reason="upstream-shape")
    for key in expected:
        if not isinstance(payload.get(key), list):
            raise ApiError(f"ghibli snapshot field {key!r} is not a list", backend="ghibli", reason="upstream-shape")


def _src() -> SourceTag:
    return SourceTag(backend="ghibli", fetched_at=datetime.now(timezone.utc), cached=True, rate_limited=False)


def _contains(value: Optional[str], query: Optional[str]) -> bool:
    if query is None:
        return True
    if value is None:
        return False
    return query.casefold() in value.casefold()


def _rows(name: str) -> List[dict]:
    return list(_load_snapshot()[name])


def _by_id(name: str, id: str) -> dict:
    for row in _rows(name):
        if row.get("id") == id:
            return row
    raise ApiError(f"ghibli {name} record not found: {id}", backend="ghibli", reason="not-found")


def _model_rows(rows: Iterable[dict], model: Callable[[dict], T]) -> List[T]:
    src = _src()
    return [model({**row, "source_tag": src}) for row in rows]


def films(
    *,
    title: Optional[str] = None,
    director: Optional[str] = None,
    producer: Optional[str] = None,
    release_year: Optional[int] = None,
    min_rt_score: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[GhibliFilm]:
    """List films from the bundled snapshot with optional filters.

    :param title: Case-insensitive title substring filter.
    :type title: str or None
    :param director: Case-insensitive director substring filter.
    :type director: str or None
    :param producer: Case-insensitive producer substring filter.
    :type producer: str or None
    :param release_year: Exact release year.
    :type release_year: int or None
    :param min_rt_score: Minimum Rotten Tomatoes score.
    :type min_rt_score: int or None
    :return: Matching films in snapshot order.
    :rtype: list[GhibliFilm]
    """
    del config, kw
    out = []
    for row in _rows("films"):
        if not _contains(row.get("title"), title) and not _contains(row.get("original_title_romanised"), title):
            continue
        if not _contains(row.get("director"), director):
            continue
        if not _contains(row.get("producer"), producer):
            continue
        if release_year is not None and _to_int(row.get("release_date")) != release_year:
            continue
        if min_rt_score is not None and (_to_int(row.get("rt_score")) or 0) < min_rt_score:
            continue
        out.append(row)
    return _model_rows(out, GhibliFilm.model_validate)


def film(film_id: str, *, config: Optional[Config] = None, **kw) -> GhibliFilm:
    """Return one film by Studio Ghibli API UUID."""
    del config, kw
    return GhibliFilm.model_validate({**_by_id("films", film_id), "source_tag": _src()})


def people(
    *,
    name: Optional[str] = None,
    gender: Optional[str] = None,
    film_id: Optional[str] = None,
    species_id: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[GhibliPerson]:
    """List people from the bundled snapshot with optional filters."""
    del config, kw
    out = []
    for row in _rows("people"):
        if not _contains(row.get("name"), name):
            continue
        if gender is not None and (row.get("gender") or "").casefold() != gender.casefold():
            continue
        if film_id is not None and not _urls_contain_id(row.get("films") or [], film_id):
            continue
        if species_id is not None and not _url_endswith_id(row.get("species"), species_id):
            continue
        out.append(row)
    return _model_rows(out, GhibliPerson.model_validate)


def person(person_id: str, *, config: Optional[Config] = None, **kw) -> GhibliPerson:
    """Return one person by Studio Ghibli API UUID."""
    del config, kw
    return GhibliPerson.model_validate({**_by_id("people", person_id), "source_tag": _src()})


def locations(
    *,
    name: Optional[str] = None,
    climate: Optional[str] = None,
    terrain: Optional[str] = None,
    film_id: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[GhibliLocation]:
    """List locations from the bundled snapshot with optional filters."""
    del config, kw
    out = []
    for row in _rows("locations"):
        if not _contains(row.get("name"), name):
            continue
        if not _contains(row.get("climate"), climate):
            continue
        if not _contains(row.get("terrain"), terrain):
            continue
        if film_id is not None and not _urls_contain_id(row.get("films") or [], film_id):
            continue
        out.append(row)
    return _model_rows(out, GhibliLocation.model_validate)


def location(location_id: str, *, config: Optional[Config] = None, **kw) -> GhibliLocation:
    """Return one location by Studio Ghibli API UUID."""
    del config, kw
    return GhibliLocation.model_validate({**_by_id("locations", location_id), "source_tag": _src()})


def vehicles(
    *,
    name: Optional[str] = None,
    vehicle_class: Optional[str] = None,
    film_id: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[GhibliVehicle]:
    """List vehicles from the bundled snapshot with optional filters."""
    del config, kw
    out = []
    for row in _rows("vehicles"):
        if not _contains(row.get("name"), name):
            continue
        if not _contains(row.get("vehicle_class"), vehicle_class):
            continue
        if film_id is not None and not _urls_contain_id(row.get("films") or [], film_id):
            continue
        out.append(row)
    return _model_rows(out, GhibliVehicle.model_validate)


def vehicle(vehicle_id: str, *, config: Optional[Config] = None, **kw) -> GhibliVehicle:
    """Return one vehicle by Studio Ghibli API UUID."""
    del config, kw
    return GhibliVehicle.model_validate({**_by_id("vehicles", vehicle_id), "source_tag": _src()})


def species(
    *,
    name: Optional[str] = None,
    classification: Optional[str] = None,
    film_id: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[GhibliSpecies]:
    """List species from the bundled snapshot with optional filters."""
    del config, kw
    out = []
    for row in _rows("species"):
        if not _contains(row.get("name"), name):
            continue
        if not _contains(row.get("classification"), classification):
            continue
        if film_id is not None and not _urls_contain_id(row.get("films") or [], film_id):
            continue
        out.append(row)
    return _model_rows(out, GhibliSpecies.model_validate)


def species_by_id(species_id: str, *, config: Optional[Config] = None, **kw) -> GhibliSpecies:
    """Return one species by Studio Ghibli API UUID."""
    del config, kw
    return GhibliSpecies.model_validate({**_by_id("species", species_id), "source_tag": _src()})


def _url_endswith_id(value: Optional[str], id: str) -> bool:
    return bool(value and value.rstrip("/").rsplit("/", 1)[-1] == id)


def _urls_contain_id(values: Iterable[str], id: str) -> bool:
    return any(_url_endswith_id(value, id) for value in values)


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def selftest() -> bool:
    """Smoke-test the offline Ghibli backend.

    Loads the bundled snapshot, validates that every expected list is
    present, checks representative rich-model validation, and confirms
    single-record lookup returns the same identifier as list lookup.

    :return: ``True`` on success.
    :rtype: bool
    """
    payload = _load_snapshot()
    assert payload["films"], "ghibli snapshot has no films"
    first_film = films()[0]
    assert film(first_film.id).id == first_film.id
    assert first_film.to_common().source.backend == "ghibli"
    first_person = people()[0]
    assert person(first_person.id).to_common().source.backend == "ghibli"
    assert locations()
    assert vehicles()
    assert species()
    return True
