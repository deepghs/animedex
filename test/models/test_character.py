"""
Tests for :mod:`animedex.models.character`.

Pins the public surface of :class:`Character`, :class:`Staff`, and
:class:`Studio`. These are populated by the AniList ``character`` /
``staff`` / ``studio`` endpoints and surface as their own subcommands
in the Phase 2 CLI.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "anilist") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestCharacter:
    def test_minimal_construction(self):
        from animedex.models.character import Character

        c = Character(id="anilist:char:1", name="Frieren", source=_src())

        assert c.id == "anilist:char:1"
        assert c.name == "Frieren"
        assert c.role is None
        assert c.image_url is None

    def test_full_construction(self):
        from animedex.models.character import Character

        c = Character(
            id="anilist:char:1",
            name="Frieren",
            role="MAIN",
            image_url="https://example.invalid/c.jpg",
            description="An elf mage.",
            source=_src(),
        )
        assert c.role == "MAIN"

    def test_round_trip_json(self):
        from animedex.models.character import Character

        c = Character(id="anilist:char:1", name="Frieren", source=_src())
        assert Character.model_validate_json(c.model_dump_json()) == c


class TestStaff:
    def test_construction(self):
        from animedex.models.character import Staff

        s = Staff(id="anilist:staff:1", name="Keiichirou Saitou", source=_src())
        assert s.name == "Keiichirou Saitou"
        assert s.occupations == []
        assert s.age is None


class TestStudio:
    def test_construction(self):
        from animedex.models.character import Studio

        s = Studio(id="anilist:studio:1", name="Madhouse", source=_src())
        assert s.name == "Madhouse"
        assert s.is_animation_studio is None
