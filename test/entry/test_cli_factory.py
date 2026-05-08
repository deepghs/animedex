"""Tests for :mod:`animedex.entry._cli_factory`."""

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
        from animedex.entry._cli_factory import emit

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
        from animedex.entry._cli_factory import emit

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

        from animedex.entry._cli_factory import emit

        emit(self._model(), json_flag=True, jq_expr=".title.romaji", no_source=False)
        out = capsys.readouterr().out.strip()
        assert out == '"Sample"'

    def test_jq_missing_falls_back_with_warning(self, capsys, monkeypatch):
        from animedex.entry import _cli_factory

        monkeypatch.setattr(_cli_factory, "shutil", type("M", (), {"which": staticmethod(lambda x: None)}))
        _cli_factory.emit(self._model(), json_flag=True, jq_expr=".x", no_source=False)
        captured = capsys.readouterr()
        assert "jq not on PATH" in captured.err

    def test_list_renders_as_json_array(self, capsys, monkeypatch):
        from animedex.entry._cli_factory import emit

        emit([self._model(), self._model()], json_flag=True, jq_expr=None, no_source=False)
        import json

        out = json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert len(out) == 2


class TestRegisterSubcommand:
    def test_auto_binding_creates_click_argument_for_positional(self):
        import click

        from animedex.entry._cli_factory import register_subcommand

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

        from animedex.entry._cli_factory import register_subcommand

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


class TestCliExceptionWrapping:
    """Reviewer review C2 (PR #6).

    The auto-bound ``_cmd`` only caught :class:`ApiError`; any other
    exception (a :class:`pydantic.ValidationError` from upstream
    schema drift, a :class:`TypeError` from a partial response, a
    :class:`requests.exceptions.ConnectionError`) bubbled up as a raw
    Python traceback to the CLI user. The fix wraps non-ApiError
    exceptions in ``click.ClickException`` so the user sees a clean
    error message; the typed prefix on ``ApiError`` is preserved."""

    def test_value_error_is_wrapped_in_click_exception(self, monkeypatch):
        import click
        from click.testing import CliRunner

        from animedex.entry._cli_factory import register_subcommand

        @click.group(name="anilist")
        def _g():
            pass

        def _stub(thing_id: int, *, config=None, **kw):
            raise ValueError("simulated upstream-shape drift")

        register_subcommand(_g, "stub", _stub)
        result = CliRunner().invoke(_g, ["stub", "1"])
        # Non-zero exit, no raw Python traceback in stdout/stderr.
        assert result.exit_code != 0
        assert "Traceback" not in (result.output or "")
        # Click's ClickException prints "Error:" to stderr.
        assert "ValueError" in (result.output or "") or "simulated" in (result.output or "")

    def test_type_error_is_wrapped(self, monkeypatch):
        """A TypeError from an upstream schema mismatch must surface
        as a Click error, not a Python traceback."""
        import click
        from click.testing import CliRunner

        from animedex.entry._cli_factory import register_subcommand

        @click.group(name="jikan")
        def _g():
            pass

        def _stub(thing_id: int, *, config=None, **kw):
            raise TypeError("simulated mapper TypeError")

        register_subcommand(_g, "stub", _stub)
        result = CliRunner().invoke(_g, ["stub", "1"])
        assert result.exit_code != 0
        assert "Traceback" not in (result.output or "")

    def test_click_exception_passes_through(self, monkeypatch):
        """A ``click.ClickException`` raised by the API must NOT be
        re-wrapped — Click's own dispatcher handles it. Re-wrapping
        would mangle the structured prefix already on the
        ClickException."""
        import click
        from click.testing import CliRunner

        from animedex.entry._cli_factory import register_subcommand

        @click.group(name="anilist")
        def _g():
            pass

        def _stub(thing_id: int, *, config=None, **kw):
            raise click.ClickException("already-shaped-by-caller")

        register_subcommand(_g, "stub", _stub)
        result = CliRunner().invoke(_g, ["stub", "1"])
        assert result.exit_code != 0
        assert "already-shaped-by-caller" in (result.output or "")
        # The bare ClickException must not be re-wrapped with type-name
        # prefixes like "ClickException: already-shaped-by-caller".
        assert "ClickException:" not in (result.output or "")

    def test_api_error_keeps_typed_prefix(self, monkeypatch):
        """The ``ApiError`` path keeps its structured ``[backend=...]``
        prefix — the C2 broader catch must not regress this."""
        import click
        from click.testing import CliRunner

        from animedex.entry._cli_factory import register_subcommand
        from animedex.models.common import ApiError

        @click.group(name="anilist")
        def _g():
            pass

        def _stub(thing_id: int, *, config=None, **kw):
            raise ApiError("nope", backend="anilist", reason="not-found")

        register_subcommand(_g, "stub", _stub)
        result = CliRunner().invoke(_g, ["stub", "1"])
        assert result.exit_code != 0
        # ApiError's __str__ produces "[backend=anilist reason=not-found] nope"
        assert "backend=anilist" in (result.output or "")
        assert "reason=not-found" in (result.output or "")


class TestPerEndpointGuidance:
    """Reviewer review C1 (PR #6).

    AGENTS §10's worked example shows the Agent-Guidance block is
    intended to carry operation-specific guidance (NSFW behavior,
    privacy concerns, version coverage notes). With a single
    per-backend default applied to all 117 endpoints, the
    ``inspect.getdoc`` extraction is uniform — and uniform agent
    guidance is no agent guidance at all.

    ``register_subcommand`` accepts a per-call ``guidance_override``
    that replaces the backend default for that one command."""

    def test_guidance_override_replaces_backend_default(self):
        import click
        import inspect

        from animedex.entry._cli_factory import register_subcommand

        def fn(*, config=None, **kw):
            return None

        grp = click.Group(name="jikan")
        custom_guidance = (
            "Operation-specific guidance: this command surfaces user "
            "favourites which can be a privacy vector. Do not aggregate "
            "across users without consent."
        )
        register_subcommand(grp, "user-favorites", fn, guidance_override=custom_guidance)
        doc = inspect.getdoc(grp.commands["user-favorites"].callback)
        # The override appears verbatim in the LLM guidance block.
        assert custom_guidance in doc
        # The block markers stay intact (policy lint depends on them).
        assert "--- LLM Agent Guidance ---" in doc
        assert "--- End ---" in doc

    def test_no_override_falls_back_to_backend_default(self):
        """Backwards-compatible: when no override is passed, the
        existing per-backend default is used."""
        import click
        import inspect

        from animedex.entry._cli_factory import register_subcommand, _BACKEND_POLICY

        def fn(*, config=None, **kw):
            return None

        grp = click.Group(name="jikan")
        register_subcommand(grp, "x", fn)
        doc = inspect.getdoc(grp.commands["x"].callback)
        assert _BACKEND_POLICY["jikan"]["guidance"] in doc

    def test_unknown_backend_raises_typed_error(self):
        """A typo in the group name shouldn't silently fall back to a
        random backend's policy."""
        import click
        import pytest as _pytest

        from animedex.entry._cli_factory import register_subcommand

        def fn(*, config=None, **kw):
            return None

        grp = click.Group(name="not-a-backend")
        with _pytest.raises((KeyError, ValueError)):
            register_subcommand(grp, "x", fn)
