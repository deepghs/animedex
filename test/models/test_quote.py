"""
Tests for :mod:`animedex.models.quote`.

:class:`Quote` is the shape AnimeChan returns. The free tier exposes
only the random-quote endpoint, so the typed surface is small;
character / anime fields are optional because the upstream sometimes
omits them.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "animechan") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


class TestQuote:
    def test_minimal_construction(self):
        from animedex.models.quote import Quote

        q = Quote(text="Talking is making things, things that didn't exist before.", source=_src())

        assert q.text.startswith("Talking")
        assert q.character is None
        assert q.anime is None

    def test_full_construction(self):
        from animedex.models.quote import Quote

        q = Quote(
            text="Talking is making things, things that didn't exist before.",
            character="Frieren",
            anime="Sousou no Frieren",
            source=_src(),
        )
        assert q.character == "Frieren"

    def test_round_trip_json(self):
        from animedex.models.quote import Quote

        q = Quote(text="x", character="y", anime="z", source=_src())
        assert Quote.model_validate_json(q.model_dump_json()) == q


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.models import quote

        assert quote.selftest() is True
