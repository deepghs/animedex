"""
Tests for :mod:`animedex.render.tty`.

The TTY renderer is what humans see at the terminal. Per ``plans/03
§5`` the source must always be visible to the human reader, so the
TTY path always emits ``[src: <backend>]`` annotations - there is no
``--source-attribution=off`` for TTY.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from animedex.models.anime import Anime, AnimeTitle
from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _anime() -> Anime:
    return Anime(
        id="anilist:154587",
        title=AnimeTitle(romaji="Sousou no Frieren", english="Frieren: Beyond Journey's End"),
        episodes=28,
        studios=["Madhouse"],
        ids={"mal": "52991"},
        source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
    )


class TestRenderTty:
    def test_includes_source_marker(self):
        from animedex.render.tty import render_tty

        out = render_tty(_anime())
        assert "[src: anilist]" in out

    def test_includes_title_and_episodes(self):
        from animedex.render.tty import render_tty

        out = render_tty(_anime())
        assert "Sousou no Frieren" in out
        assert "28" in out


class TestPickRenderer:
    def test_atty_picks_tty(self, monkeypatch):
        from animedex.render.tty import is_terminal, render_for_stream

        class FakeStream:
            def isatty(self):
                return True

        out = render_for_stream(_anime(), FakeStream())
        assert "[src: anilist]" in out
        assert is_terminal(FakeStream()) is True

    def test_pipe_picks_json(self, monkeypatch):
        import json

        from animedex.render.tty import render_for_stream

        class FakeStream:
            def isatty(self):
                return False

        out = render_for_stream(_anime(), FakeStream())
        # The pipe path returns parseable JSON.
        decoded = json.loads(out)
        assert decoded["id"] == "anilist:154587"


class TestRenderTtyFullFields:
    def test_includes_score_and_streaming(self):
        from animedex.models.anime import (
            Anime,
            AnimeRating,
            AnimeStreamingLink,
            AnimeTitle,
        )
        from animedex.render.tty import render_tty

        a = Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="x"),
            score=AnimeRating(score=9.0, scale=10.0),
            streaming=[AnimeStreamingLink(provider="X", url="https://x.invalid/x")],
            ids={},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(a)
        assert "9.0/10.0" in out
        assert "Streaming:" in out and "X:" in out


class TestRenderAiringScheduleRow:
    def test_renders_schedule_row(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        row = AiringScheduleRow(
            title="Shin Nippon History",
            weekday="monday",
            local_time="01:00",
            source=SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(row)
        assert "Shin Nippon History" in out
        assert "[src: jikan]" in out
        assert "Schedule: monday" in out

    def test_renders_airing_instant_and_episode(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        row = AiringScheduleRow(
            title="Exact Airing",
            airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
            episode=3,
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(row)
        assert "Airing:" in out
        assert "Episode:  3" in out


class TestRenderAggregateResult:
    def test_empty_aggregate_renders_empty_string(self):
        from animedex.models.aggregate import AggregateResult
        from animedex.render.tty import render_tty

        assert render_tty(AggregateResult()) == ""

    def test_aggregate_renders_plain_non_model_items(self):
        from animedex.models.aggregate import AggregateResult
        from animedex.render.tty import render_tty

        assert render_tty(AggregateResult(items=["plain"])) == "plain"


class TestRenderTtyNonAnime:
    def test_falls_back_with_source_marker(self):
        from animedex.models.quote import Quote
        from animedex.render.tty import render_tty

        q = Quote(
            text="x",
            source=SourceTag(backend="animechan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(q)
        assert "Quote" in out
        assert "[src: animechan]" in out


class TestRenderTtyFallbackHonorsAliases:
    """Reviewer review B2 (PR #6).

    The rich-model fallback path in ``render_tty`` (the ``hasattr
    to_common`` branch's last line) calls ``model_dump_json()``
    without ``by_alias=True``. So a rich model with aliased fields
    (e.g. ``RawTraceHit.from_`` aliased to ``from``) used to render
    ``\"from_\": ...`` instead of ``\"from\": ...``. AGENTS §13.6
    declares the renderer's output as a legitimate downstream shape;
    this drift broke the lossless contract.

    A rich model whose ``to_common()`` returns a non-renderable shape
    falls into the JSON-dump fallback path; we synthesize that case
    here.
    """

    def test_fallback_dump_uses_upstream_aliases(self):
        from animedex.models.common import BackendRichModel, SourceTag
        from animedex.render.tty import render_tty
        from pydantic import Field

        # A rich model with aliased fields whose ``to_common()`` returns
        # something the dispatcher doesn't recognise (so we land in the
        # JSON-dump fallback).
        class _RichWithAlias(BackendRichModel):
            from_: float = Field(alias="from")
            to_: float = Field(alias="to")
            source_tag: SourceTag

            def to_common(self):
                return None

        m = _RichWithAlias.model_validate(
            {
                "from": 832.7,
                "to": 836.8,
                "source_tag": SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
            }
        )
        out = render_tty(m)
        assert '"from"' in out, f"expected upstream alias 'from' in TTY fallback dump, got: {out!r}"
        assert '"to"' in out
        assert '"from_"' not in out
        assert '"to_"' not in out


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import tty

        assert tty.selftest() is True
