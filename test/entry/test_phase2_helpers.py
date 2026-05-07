"""Tests for :mod:`animedex.entry._phase2_helpers`."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


class TestEmit:
    def _model(self):
        from animedex.models.anime import Anime, AnimeTitle
        from animedex.models.common import SourceTag

        return Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="Sample"),
            ids={"anilist": "1"},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )

    def test_json_flag_forces_json_output(self, capsys, monkeypatch):
        from animedex.entry._phase2_helpers import emit

        # Make stdout look like a TTY so we can confirm --json forces
        # JSON despite the auto-switch.
        import sys

        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        emit(self._model(), json_flag=True, jq_expr=None, no_source=False)
        out = capsys.readouterr().out
        import json

        decoded = json.loads(out)
        assert decoded["title"]["romaji"] == "Sample"
        # The current json_renderer surfaces source attribution under
        # _meta.sources_consulted (Phase 0 contract). Either form
        # counts as "include_source=True".
        assert "_source" in decoded or "_meta" in decoded

    def test_no_source_strips_source_attribution(self, capsys, monkeypatch):
        from animedex.entry._phase2_helpers import emit

        emit(self._model(), json_flag=True, jq_expr=None, no_source=True)
        out = capsys.readouterr().out
        import json

        decoded = json.loads(out)
        assert "_source" not in decoded
        assert "_meta" not in decoded

    def test_jq_filter_applied(self, capsys, monkeypatch):
        # Skip if jq is not on PATH
        import shutil

        if shutil.which("jq") is None:
            pytest.skip("jq not installed")

        from animedex.entry._phase2_helpers import emit

        emit(self._model(), json_flag=True, jq_expr=".title.romaji", no_source=False)
        out = capsys.readouterr().out.strip()
        assert out == '"Sample"'

    def test_jq_missing_falls_back_with_warning(self, capsys, monkeypatch):
        from animedex.entry import _phase2_helpers

        monkeypatch.setattr(_phase2_helpers, "shutil", type("M", (), {"which": staticmethod(lambda x: None)}))
        _phase2_helpers.emit(self._model(), json_flag=True, jq_expr=".x", no_source=False)
        captured = capsys.readouterr()
        assert "jq not on PATH" in captured.err

    def test_list_renders_as_json_array(self, capsys, monkeypatch):
        from animedex.entry._phase2_helpers import emit

        emit([self._model(), self._model()], json_flag=True, jq_expr=None, no_source=False)
        import json

        out = json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert len(out) == 2


class TestRegisterSubcommand:
    def test_auto_binding_creates_click_argument_for_positional(self):
        import click

        from animedex.entry._phase2_helpers import register_subcommand

        def fn(thing_id: int, *, per_page: int = 5, config=None, **kw):
            return thing_id

        grp = click.Group(name="anilist")
        register_subcommand(grp, "demo", fn)
        cmd = grp.commands["demo"]
        # The positional thing_id became a Click argument, per_page an option.
        param_names = {p.name for p in cmd.params}
        assert "thing_id" in param_names
        assert "per_page" in param_names

    def test_subcommand_docstring_has_three_blocks(self):
        """register_subcommand injects Backend / Rate limit / Agent
        Guidance so the policy lint stays green."""
        import click
        import inspect

        from animedex.entry._phase2_helpers import register_subcommand

        def fn(arg, *, config=None, **kw):
            return arg

        grp = click.Group(name="anilist")
        register_subcommand(grp, "demo", fn, help="Demo command.")
        cmd = grp.commands["demo"]
        doc = inspect.getdoc(cmd.callback)
        assert "Backend:" in doc
        assert "Rate limit:" in doc
        assert "--- LLM Agent Guidance ---" in doc
        assert "--- End ---" in doc
