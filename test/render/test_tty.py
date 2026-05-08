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


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import tty

        assert tty.selftest() is True
