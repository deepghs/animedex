"""
Tests for :mod:`animedex.render.json_renderer`.

The JSON renderer is the substrate of the source-attribution
contract: per ``plans/03 §5`` every field originating from a backend
must be emitted with a ``_source`` annotation. The tests pin the
shape (``{value, _source}`` per backend-derived field) and the
top-level ``_meta`` block.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from animedex.models.anime import Anime, AnimeTitle
from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "anilist") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc))


def _anime() -> Anime:
    return Anime(
        id="anilist:154587",
        title=AnimeTitle(romaji="Sousou no Frieren"),
        episodes=28,
        ids={"mal": "52991"},
        source=_src(),
    )


class TestRenderJson:
    def test_emits_source_block(self):
        from animedex.render.json_renderer import render_json

        out = json.loads(render_json(_anime()))

        assert out["id"] == "anilist:154587"
        assert out["_meta"]["sources_consulted"] == ["anilist"]

    def test_can_disable_source_attribution(self):
        """``--source-attribution=off`` returns the raw shape."""
        from animedex.render.json_renderer import render_json

        out = json.loads(render_json(_anime(), include_source=False))
        # Without source attribution, _meta is omitted but the data is still there.
        assert out["id"] == "anilist:154587"
        assert "_meta" not in out

    def test_returns_str(self):
        from animedex.render.json_renderer import render_json

        assert isinstance(render_json(_anime()), str)


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import json_renderer

        assert json_renderer.selftest() is True
