"""Rich Studio Ghibli API dataclasses.

The high-level Ghibli backend reads a vendored JSON snapshot from
``animedex/data/ghibli.json``. The snapshot mirrors the public Studio
Ghibli API's five record families: films, people, locations, species,
and vehicles. Every rich type inherits from
:class:`~animedex.models.common.BackendRichModel` so a snapshot record
round-trips with every upstream key preserved.

Films project naturally onto :class:`~animedex.models.anime.Anime` and
people project onto :class:`~animedex.models.character.Character`.
Locations, vehicles, and species currently have no cross-source common
type and render through the generic source-attributed rich-model path.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from animedex.models.anime import Anime, AnimeRating, AnimeTitle
from animedex.models.character import Character
from animedex.models.common import BackendRichModel, SourceTag


class GhibliFilm(BackendRichModel):
    """One film record from the Studio Ghibli API snapshot."""

    id: str
    title: str
    original_title: Optional[str] = None
    original_title_romanised: Optional[str] = None
    image: Optional[str] = None
    movie_banner: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    producer: Optional[str] = None
    release_date: Optional[str] = None
    running_time: Optional[str] = None
    rt_score: Optional[str] = None
    people: List[str] = []
    species: List[str] = []
    locations: List[str] = []
    vehicles: List[str] = []
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Anime:
        """Project this film onto the cross-source anime shape.

        :return: Cross-source projection.
        :rtype: animedex.models.anime.Anime
        """
        score = None
        try:
            if self.rt_score is not None:
                score = AnimeRating(score=float(self.rt_score), scale=100.0)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            score = None
        year = _to_int(self.release_date)
        aired = date(year, 1, 1) if year else None
        return Anime(
            id=f"ghibli:{self.id}",
            title=AnimeTitle(
                romaji=self.original_title_romanised or self.title,
                english=self.title,
                native=self.original_title,
            ),
            ids={"ghibli": self.id},
            score=score,
            studios=["Studio Ghibli"],
            description=self.description,
            status="finished",
            format="MOVIE",
            season_year=year,
            aired_from=aired,
            duration_minutes=_to_int(self.running_time),
            cover_image_url=self.image,
            banner_image_url=self.movie_banner,
            source_material="original",
            source=self.source_tag or _default_src(),
        )


class GhibliPerson(BackendRichModel):
    """One person / character record from the snapshot."""

    id: str
    name: str
    gender: Optional[str] = None
    age: Optional[str] = None
    eye_color: Optional[str] = None
    hair_color: Optional[str] = None
    films: List[str] = []
    species: Optional[str] = None
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Character:
        """Project this person onto the cross-source character shape.

        :return: Cross-source projection.
        :rtype: animedex.models.character.Character
        """
        profile = []
        if self.eye_color:
            profile.append(f"Eye color: {self.eye_color}")
        if self.hair_color:
            profile.append(f"Hair color: {self.hair_color}")
        return Character(
            id=f"ghibli:char:{self.id}",
            name=self.name,
            gender=self.gender,
            age=self.age,
            description="; ".join(profile) if profile else None,
            source=self.source_tag or _default_src(),
        )


class GhibliLocation(BackendRichModel):
    """One location record from the snapshot."""

    id: str
    name: str
    climate: Optional[str] = None
    terrain: Optional[str] = None
    surface_water: Optional[str] = None
    residents: List[str] = []
    films: List[str] = []
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class GhibliVehicle(BackendRichModel):
    """One vehicle record from the snapshot."""

    id: str
    name: str
    description: Optional[str] = None
    vehicle_class: Optional[str] = None
    length: Optional[str] = None
    pilot: Optional[str] = None
    films: List[str] = []
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None


class GhibliSpecies(BackendRichModel):
    """One species record from the snapshot."""

    id: str
    name: str
    classification: Optional[str] = None
    eye_colors: Optional[str] = None
    hair_colors: Optional[str] = None
    people: List[str] = []
    films: List[str] = []
    url: Optional[str] = None
    source_tag: Optional[SourceTag] = None


def _to_int(value: Optional[str]) -> Optional[int]:
    """Parse an integer from a Studio Ghibli string field."""
    if value is None:
        return None
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _default_src() -> SourceTag:
    """Construct a fallback source tag for direct model usage."""
    from datetime import datetime, timezone

    return SourceTag(backend="ghibli", fetched_at=datetime.now(timezone.utc))


def selftest() -> bool:
    """Smoke-test the Ghibli rich models.

    Validates representative film, person, location, vehicle, and
    species records; confirms film and person common projections carry
    Ghibli source attribution.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="ghibli", fetched_at=datetime.now(timezone.utc))
    film = GhibliFilm.model_validate(
        {
            "id": "film-1",
            "title": "Sample Film",
            "original_title": "Sample Native",
            "original_title_romanised": "Sample Romanised",
            "release_date": "1986",
            "running_time": "124",
            "rt_score": "95",
            "source_tag": src.model_dump(),
        }
    )
    assert film.to_common().source.backend == "ghibli"
    person = GhibliPerson.model_validate(
        {"id": "person-1", "name": "Sample Person", "eye_color": "Black", "source_tag": src.model_dump()}
    )
    assert person.to_common().source.backend == "ghibli"
    GhibliLocation.model_validate({"id": "loc-1", "name": "Irontown"})
    GhibliVehicle.model_validate({"id": "veh-1", "name": "Goliath"})
    GhibliSpecies.model_validate({"id": "sp-1", "name": "Human"})
    return True
