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

    def test_aggregate_sources_dict_aggregates_into_meta(self):
        from animedex.models.common import AnimedexModel
        from animedex.render.json_renderer import render_json

        class MergedDict(AnimedexModel):
            sources: dict

        result = MergedDict(sources={"anilist": {"backend": "anilist", "status": "ok"}, "legacy": {"status": "ok"}})
        decoded = json.loads(render_json(result, include_source=True))
        assert decoded["_meta"]["sources_consulted"] == ["anilist", "legacy"]


class TestAggregateResultSources:
    def test_aggregate_sources_map_reports_ok_sources_only(self):
        from animedex.models.aggregate import AggregateResult, AggregateSourceStatus
        from animedex.render.json_renderer import render_json

        result = AggregateResult(
            items=[{"id": 1, "_source": "jikan", "_prefix_id": "mal:1"}],
            sources={
                "anilist": AggregateSourceStatus(backend="anilist", status="failed", reason="upstream-error"),
                "jikan": AggregateSourceStatus(backend="jikan", status="ok", items=1),
            },
        )
        decoded = json.loads(render_json(result, include_source=True))

        assert decoded["_meta"]["sources_consulted"] == ["jikan"]
        assert decoded["sources"]["anilist"]["status"] == "failed"

    def test_sources_map_keeps_legacy_scalar_entries(self):
        from animedex.models.common import AnimedexModel
        from animedex.render.json_renderer import render_json

        class LegacyAggregate(AnimedexModel):
            sources: dict

        decoded = json.loads(render_json(LegacyAggregate(sources={"legacy": True}), include_source=True))

        assert decoded["_meta"]["sources_consulted"] == ["legacy"]


class TestRichModelSourceAttribution:
    """Reviewer review B1 (PR #6).

    Rich models (``AnilistAnime``, ``JikanAnime``, ``RawTraceHit``)
    carry the :class:`SourceTag` on a ``source_tag`` field rather than
    ``source``, because their ``source`` field is taken by the
    upstream's own value (Jikan's ``source: "Manga"``, AniList's
    ``source: "MANGA"``). The JSON renderer must still surface them
    on ``_meta.sources_consulted``; before the B1 fix it only
    inspected ``payload.get("source")`` and silently emitted an empty
    list for every Phase-2 rich command.
    """

    def test_rich_model_with_source_tag_emits_backend_in_meta(self):
        """A rich-shape model whose only ``SourceTag`` lives on
        ``source_tag`` must still report its backend in
        ``_meta.sources_consulted``."""
        from animedex.backends.jikan.models import JikanAnime
        from animedex.render.json_renderer import render_json

        rich = JikanAnime.model_validate(
            {
                "mal_id": 52991,
                "title": "Sousou no Frieren",
                "source_tag": _src("jikan"),
            }
        )
        decoded = json.loads(render_json(rich))
        assert decoded["_meta"]["sources_consulted"] == ["jikan"], (
            "Rich model with SourceTag on `source_tag` must report its "
            "backend on _meta.sources_consulted (AGENTS §6 source "
            "attribution mandatory)."
        )

    def test_rich_model_source_tag_does_not_collide_with_upstream_source_string(self):
        """When the rich model's ``source`` field is a plain upstream
        string (Jikan's ``source: "Manga"``), the renderer must not
        treat it as a SourceTag. The actual backend lives on
        ``source_tag``."""
        from animedex.backends.jikan.models import JikanAnime
        from animedex.render.json_renderer import render_json

        rich = JikanAnime.model_validate(
            {
                "mal_id": 52991,
                "title": "Sousou no Frieren",
                "source": "Manga",  # upstream's own field, NOT a SourceTag
                "source_tag": _src("jikan"),
            }
        )
        decoded = json.loads(render_json(rich))
        assert decoded["_meta"]["sources_consulted"] == ["jikan"]
        # The upstream string survives in its own field.
        assert decoded["source"] == "Manga"


class TestRenderJsonHonorsAliases:
    """Reviewer review B2 (PR #6).

    The lossless contract (AGENTS §13.6) lists the JSON renderer as
    one of the four legitimate downstream shapes. Rich models with
    aliased fields (``RawTraceHit.from_`` aliased to ``from``,
    ``RawTraceHit.to_`` aliased to ``to``) must round-trip through
    the renderer with their upstream key names — not the Python
    field names. Before the B2 fix the renderer called
    ``model_dump(mode="json")`` without ``by_alias=True``, dumping
    ``"from_": ...`` instead of ``"from": ...``."""

    def test_aliased_fields_render_with_upstream_names(self):
        from animedex.backends.trace.models import RawTraceHit
        from animedex.render.json_renderer import render_json

        hit = RawTraceHit.model_validate(
            {
                "anilist": 154587,
                "similarity": 0.95,
                "from": 832.7,
                "at": 836.5,
                "to": 836.8,
                "source_tag": _src("trace"),
            }
        )
        decoded = json.loads(render_json(hit))
        assert "from" in decoded, "expected upstream-aliased 'from' key"
        assert "to" in decoded, "expected upstream-aliased 'to' key"
        assert decoded["from"] == 832.7
        assert decoded["to"] == 836.8
        # The Python field names ``from_`` / ``to_`` must NOT leak.
        assert "from_" not in decoded
        assert "to_" not in decoded


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import json_renderer

        assert json_renderer.selftest() is True
