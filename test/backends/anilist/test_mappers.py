"""Mapper tests for :mod:`animedex.backends.anilist`.

Each test parametrises over the Phase-2 fixtures captured by
``tools/fixtures/run_anilist_phase2.py``. The mapper is exercised
on a real upstream JSON payload and the resulting rich dataclass +
its ``to_common()`` projection are spot-checked.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from animedex.backends.anilist import _mapper as mp
from animedex.backends.anilist.models import (
    AnilistAnime,
    AnilistCharacter,
    AnilistStaff,
    AnilistStudio,
)
from animedex.models.anime import Anime
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import ApiError, SourceTag


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "anilist"


def _src() -> SourceTag:
    return SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


def _load(path: Path) -> dict:
    fix = yaml.safe_load(path.read_text(encoding="utf-8"))
    return fix["response"]["body_json"]


@pytest.mark.parametrize("path", sorted((FIXTURES / "media").glob("*.yaml")))
def test_media_fixture_round_trips(path):
    payload = _load(path)
    rich = mp.map_media(payload, _src())
    assert isinstance(rich, AnilistAnime)
    assert rich.id > 0
    common = rich.to_common()
    assert isinstance(common, Anime)
    assert common.id == f"anilist:{rich.id}"
    assert common.title.romaji  # at least one locale present


@pytest.mark.parametrize("path", sorted((FIXTURES / "character").glob("*.yaml")))
def test_character_fixture_round_trips(path):
    payload = _load(path)
    rich = mp.map_character(payload, _src())
    assert isinstance(rich, AnilistCharacter)
    common = rich.to_common()
    assert isinstance(common, Character)
    assert common.id.startswith("anilist:char:")


@pytest.mark.parametrize("path", sorted((FIXTURES / "staff").glob("*.yaml")))
def test_staff_fixture_round_trips(path):
    payload = _load(path)
    rich = mp.map_staff(payload, _src())
    assert isinstance(rich, AnilistStaff)
    common = rich.to_common()
    assert isinstance(common, Staff)
    assert common.id.startswith("anilist:staff:")


@pytest.mark.parametrize("path", sorted((FIXTURES / "studio").glob("*.yaml")))
def test_studio_fixture_round_trips(path):
    payload = _load(path)
    rich = mp.map_studio(payload, _src())
    assert isinstance(rich, AnilistStudio)
    common = rich.to_common()
    assert isinstance(common, Studio)
    assert common.id.startswith("anilist:studio:")


@pytest.mark.parametrize("path", sorted((FIXTURES / "search").glob("*.yaml")))
def test_search_fixture_round_trips(path):
    payload = _load(path)
    rich_list = mp.map_media_list(payload, _src())
    assert isinstance(rich_list, list)
    for r in rich_list:
        assert isinstance(r, AnilistAnime)


@pytest.mark.parametrize("path", sorted((FIXTURES / "trending").glob("*.yaml")))
def test_trending_fixture_round_trips(path):
    payload = _load(path)
    rich_list = mp.map_media_list(payload, _src())
    assert isinstance(rich_list, list)
    assert len(rich_list) > 0


def test_map_media_raises_not_found_when_payload_is_null():
    with pytest.raises(ApiError, match="not found"):
        mp.map_media({"data": {"Media": None}}, _src())


class TestToCommon:
    def test_frieren_projection(self):
        path = FIXTURES / "media" / "01-media-frieren.yaml"
        if not path.exists():
            pytest.skip("Frieren fixture not present")
        payload = _load(path)
        common = mp.map_media(payload, _src()).to_common()
        assert common.title.romaji.startswith("Sousou")
        assert "Adventure" in common.genres
        assert common.season == "FALL"
        assert common.season_year == 2023
        assert common.ids == {"anilist": "154587", "mal": "52991"}
        assert common.popularity is not None
        assert common.favourites is not None

    def test_one_piece_status_airing(self):
        path = FIXTURES / "media" / "03-media-one-piece.yaml"
        if not path.exists():
            pytest.skip("One Piece fixture not present")
        payload = _load(path)
        common = mp.map_media(payload, _src()).to_common()
        assert common.status == "airing"

    def test_movie_format_projection(self):
        path = FIXTURES / "media" / "02-media-spirited-away.yaml"
        if not path.exists():
            pytest.skip("Spirited Away fixture not present")
        payload = _load(path)
        common = mp.map_media(payload, _src()).to_common()
        assert common.format == "MOVIE"
