"""Mapper tests for :mod:`animedex.backends.jikan`.

Parametrised over Phase-2 captures (``test/fixtures/jikan/anime_full``)
plus the long-tail captures from
``tools/fixtures/run_phase2_full_coverage.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from animedex.backends.jikan.models import (
    JikanAnime,
    JikanCharacter,
    JikanGenericRow,
    JikanManga,
)
from animedex.models.anime import Anime
from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "jikan"


def _src() -> SourceTag:
    return SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())["response"]["body_json"]


@pytest.mark.parametrize("path", sorted((FIXTURES / "anime_full").glob("*.yaml")))
def test_anime_full_fixture_round_trips(path):
    payload = _load(path)
    rich = JikanAnime.model_validate({**payload["data"], "source_tag": _src()})
    common = rich.to_common()
    assert isinstance(common, Anime)
    assert common.ids["mal"] == str(rich.mal_id)


def test_jikan_to_common_projection_specifics():
    path = FIXTURES / "anime_full" / "01-frieren-52991.yaml"
    if not path.exists():
        pytest.skip("Frieren full fixture not present")
    payload = _load(path)
    rich = JikanAnime.model_validate({**payload["data"], "source_tag": _src()})
    common = rich.to_common()
    # Duration parsed from "24 min per ep" string
    assert common.duration_minutes == 24
    # Status normalised
    assert common.status == "finished"
    # Season uppercased
    assert common.season == "FALL"
    # Studios projected to list of names
    assert "Madhouse" in common.studios


@pytest.mark.parametrize(
    "path",
    sorted((FIXTURES / "anime_news").glob("*.yaml"))
    + sorted((FIXTURES / "anime_pictures").glob("*.yaml"))
    + sorted((FIXTURES / "characters_full").glob("*.yaml")),
)
def test_long_tail_fixtures_validate_as_generic(path):
    """Long-tail responses parse cleanly through
    :class:`JikanGenericRow` (extra='allow')."""
    payload = _load(path)
    rows = payload.get("data") if isinstance(payload, dict) else None
    if rows is None:
        pytest.skip("non-data payload")
    if isinstance(rows, dict):
        rows = [rows]
    for r in rows:
        if isinstance(r, dict):
            JikanGenericRow.model_validate(r)


def test_random_anime_envelope():
    path = FIXTURES / "random_anime" / "01-random-01.yaml"
    if not path.exists():
        pytest.skip("Random anime fixture not present")
    payload = _load(path)
    rich = JikanAnime.model_validate({**payload["data"], "source_tag": _src()})
    assert rich.mal_id > 0


@pytest.mark.parametrize("path", sorted((FIXTURES / "manga_full").glob("*.yaml")))
def test_manga_full_validates(path):
    payload = _load(path)
    rich = JikanManga.model_validate({**payload["data"], "source_tag": _src()})
    assert rich.mal_id > 0


@pytest.mark.parametrize("path", sorted((FIXTURES / "characters_full").glob("*.yaml")))
def test_characters_full_validates(path):
    payload = _load(path)
    rich = JikanCharacter.model_validate({**payload["data"], "source_tag": _src()})
    assert rich.mal_id > 0
    common = rich.to_common()
    assert common.id.startswith("jikan:char:")
