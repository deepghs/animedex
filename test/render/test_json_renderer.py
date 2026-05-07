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


class TestDisableSourceAttributionIsObservable:
    """When ``include_source=False`` the output is the model's clean
    JSON dump — same as ``model.model_dump_json()`` modulo separators.
    The earlier vacuous test only asserted ``"_meta" not in out``,
    which would pass even if the disable path were a no-op.
    """

    def test_disabled_output_equals_model_dump(self):
        from animedex.models.anime import Anime, AnimeTitle
        from animedex.models.common import SourceTag
        from animedex.render.json_renderer import render_json

        a = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="x"),
            ids={"mal": "52991"},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        decoded_off = json.loads(render_json(a, include_source=False))
        decoded_dump = json.loads(a.model_dump_json())
        assert decoded_off == decoded_dump
        assert "_meta" not in decoded_off


class TestMergedSources:
    def test_merged_sources_list_aggregates_into_meta(self):
        """Cross-source aggregate path: a model carrying ``sources``
        as a list (Phase 5 aggregate shape) should emit each backend
        in ``_meta.sources_consulted``."""
        from typing import List

        from animedex.models.common import AnimedexModel
        from animedex.render.json_renderer import render_json

        class Merged(AnimedexModel):
            id: str
            sources: List[SourceTag]

        merged = Merged(
            id="x:1",
            sources=[
                SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
                SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
            ],
        )
        decoded = json.loads(render_json(merged, include_source=True))
        assert decoded["_meta"]["sources_consulted"] == ["anilist", "jikan"]


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import json_renderer

        assert json_renderer.selftest() is True
