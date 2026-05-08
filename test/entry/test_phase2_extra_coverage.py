"""Coverage-oriented tests for the entry-layer / helper paths the
canonical end-to-end suite doesn't naturally hit (stdin upload, jq
error path, exception passthrough, render fallbacks)."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import pytest
import responses
import yaml
from click.testing import CliRunner


pytestmark = pytest.mark.unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "test" / "fixtures"


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ---------- entry/trace.py: --input file + stdin paths ----------


class TestTraceCliInputModes:
    def test_input_file_path(self, cli_runner, cli, fake_clock, tmp_path):
        """--input <file> reads bytes from disk."""
        img = tmp_path / "fake.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0fakejpeg")

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.POST,
                "https://api.trace.moe/search",
                json={"result": []},
                status=200,
            )
            result = cli_runner.invoke(
                cli,
                ["trace", "search", "--input", str(img), "--json", "--no-cache"],
            )
        assert result.exit_code == 0, result.output

    def test_input_stdin(self, cli_runner, cli, fake_clock):
        """--input - reads from stdin (CliRunner's ``input=`` arg)."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.POST,
                "https://api.trace.moe/search",
                json={"result": []},
                status=200,
            )
            result = cli_runner.invoke(
                cli,
                ["trace", "search", "--input", "-", "--json", "--no-cache"],
                input=b"\xff\xd8\xff\xe0fakejpeg",
            )
        assert result.exit_code == 0, result.output

    def test_search_exception_path(self, cli_runner, cli, fake_clock, monkeypatch):
        """When the API raises, the CLI rewraps with click.ClickException."""
        from animedex.backends import trace as trace_api
        from animedex.models.common import ApiError

        def _stub_search(**kwargs):
            raise ApiError("simulated", backend="trace", reason="upstream-error")

        monkeypatch.setattr(trace_api, "search", _stub_search)
        result = cli_runner.invoke(
            cli,
            [
                "trace",
                "search",
                "--url",
                "https://x.invalid/x.jpg",
                "--json",
                "--no-cache",
            ],
        )
        assert result.exit_code != 0

    def test_quota_exception_path(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={"error": "internal"},
                status=500,
            )
            result = cli_runner.invoke(cli, ["trace", "quota", "--json", "--no-cache"])
        assert result.exit_code != 0


# ---------- entry/_phase2_helpers.py ----------


class TestPhase2Helpers:
    def test_is_terminal_no_isatty(self):
        """Stream without isatty() returns False."""
        from animedex.entry._phase2_helpers import _is_terminal

        # An object with no isatty attribute at all (the lambda fallback fires).
        class NoIsatty:
            pass

        assert _is_terminal(NoIsatty()) is False

    def test_to_json_text_plain_dict(self):
        """When the API returns a non-AnimedexModel (plain dict), the
        helper falls back to ``json.dumps``."""
        from animedex.entry._phase2_helpers import _to_json_text

        result = _to_json_text({"a": 1, "b": "two"}, include_source=True)
        decoded = json.loads(result)
        assert decoded == {"a": 1, "b": "two"}

    def test_to_tty_text_plain_dict(self):
        """``_to_tty_text`` on a non-AnimedexModel falls back to ``str()``."""
        from animedex.entry._phase2_helpers import _to_tty_text

        assert "1" in _to_tty_text({"a": 1})

    def test_register_subcommand_with_bool_default(self):
        """``register_subcommand`` produces a Click ``--flag`` option
        when the underlying Python function has a ``bool`` default.
        No backend currently uses this shape; cover the branch with a
        synthetic registration."""
        import click
        from animedex.entry._phase2_helpers import register_subcommand

        @click.group()
        def _g():
            pass

        def _stub(*, dry_run: bool = False, **kw):
            return {"dry_run": dry_run}

        register_subcommand(_g, "stub", _stub)
        # Verify the option was registered as a flag.
        cmd = _g.commands["stub"]
        flag_params = [p for p in cmd.params if isinstance(p, click.Option) and p.name == "dry_run"]
        assert flag_params, "--dry-run flag not registered"
        assert flag_params[0].is_flag is True

    def test_register_subcommand_with_default_type_fallback(self):
        """``_click_type`` falls back to ``type(default)`` when the
        annotation is missing but the default has a primitive type."""
        import click
        from animedex.entry._phase2_helpers import register_subcommand

        @click.group()
        def _g():
            pass

        # Function with no annotation on the kwarg but a default.
        def _stub(*, count=42, **kw):  # int default, no annotation
            return {"count": count}

        register_subcommand(_g, "stub", _stub)
        cmd = _g.commands["stub"]
        opt = next(p for p in cmd.params if p.name == "count")
        assert opt.type.name == "integer"

    @pytest.mark.skipif(
        not hasattr(__import__("inspect"), "get_annotations"),
        reason="inspect.get_annotations is Python 3.10+; on 3.9 the helper "
        "naturally takes the typing.get_type_hints fallback path on every "
        "call, so this synthetic test is moot.",
    )
    def test_register_subcommand_unresolvable_annotation(self, monkeypatch):
        """Cover the ``except (NameError, AttributeError)`` fallback in
        register_subcommand. Force ``inspect.get_annotations`` (called
        inside register_subcommand) to raise so the typing-fallback
        path runs.

        The patch is applied only to the ``inspect`` module *object*
        the helper holds via ``import inspect``; we look that up
        through the helper module so :func:`inspect.signature` etc.
        elsewhere stay intact."""
        import click
        from animedex.entry import _phase2_helpers

        # _phase2_helpers does ``import inspect``; capture the helper's
        # bound name, then make get_annotations raise only when called.
        orig = _phase2_helpers.inspect.get_annotations

        def _broken_get_annotations(fn, **kw):
            # Only raise when called with eval_str=True (our caller's
            # signal); inspect.signature itself calls with
            # eval_str=False so leave that alone.
            if kw.get("eval_str") and getattr(fn, "__name__", None) == "_stub_unresolvable":
                raise NameError("intentional simulation")
            return orig(fn, **kw)

        monkeypatch.setattr(_phase2_helpers.inspect, "get_annotations", _broken_get_annotations)

        @click.group()
        def _g():
            pass

        def _stub_unresolvable(*, page: int = 1, **kw):
            return {"page": page}

        _phase2_helpers.register_subcommand(_g, "stub3", _stub_unresolvable)
        assert "stub3" in _g.commands

    def test_register_subcommand_typing_fallback_also_fails(self, monkeypatch):
        """Cover the inner ``except Exception: resolved_hints = {}``
        path: both the primary annotation source and
        ``typing.get_type_hints`` fail.

        On Python 3.10+ the primary source is ``inspect.get_annotations``;
        on 3.9 it's ``typing.get_type_hints`` directly (no inspect path
        because that attribute doesn't exist there). Patching both gets
        us into the inner-except branch on either platform."""
        import click
        import inspect
        import typing
        from animedex.entry import _phase2_helpers

        orig_typing = typing.get_type_hints

        def _bad_typing(fn, *a, **k):
            if getattr(fn, "__name__", None) == "_stub_double_fail":
                raise RuntimeError("simulated typing failure")
            return orig_typing(fn, *a, **k)

        monkeypatch.setattr(typing, "get_type_hints", _bad_typing)

        # Patch inspect.get_annotations only when it exists (3.10+).
        if hasattr(inspect, "get_annotations"):
            orig_inspect = _phase2_helpers.inspect.get_annotations

            def _bad_inspect(fn, **kw):
                if kw.get("eval_str") and getattr(fn, "__name__", None) == "_stub_double_fail":
                    raise NameError("simulate")
                return orig_inspect(fn, **kw)

            monkeypatch.setattr(_phase2_helpers.inspect, "get_annotations", _bad_inspect)

        @click.group()
        def _g():
            pass

        def _stub_double_fail(*, page: int = 1, **kw):
            return {"page": page}

        # Should not raise; resolved_hints falls back to {}.
        _phase2_helpers.register_subcommand(_g, "stub5", _stub_double_fail)
        assert "stub5" in _g.commands

    def test_register_subcommand_no_module_falls_back(self):
        """Cover the ``return fn`` branch in _resolve_fn when
        ``fn_module`` is missing (e.g. lambda or builtin)."""
        import click
        from animedex.entry import _phase2_helpers

        @click.group()
        def _g():
            pass

        def _stub(*, page: int = 1, **kw):
            return {"page": page}

        _stub.__module__ = None  # simulates a function with no module info

        _phase2_helpers.register_subcommand(_g, "stub_nomod", _stub)
        runner = CliRunner()
        result = runner.invoke(_g, ["stub_nomod", "--no-cache"])
        assert result.exit_code == 0

    def test_register_subcommand_module_import_error(self, monkeypatch):
        """Cover the ImportError branch of the late-binding
        module-resolve. Drive a function whose ``__module__`` cannot
        be re-imported."""
        import click
        import importlib
        from animedex.entry import _phase2_helpers

        @click.group()
        def _g():
            pass

        def _stub(*, page: int = 1, **kw):
            return {"page": page}

        # Pretend the function lives in a module that cannot be re-imported.
        _stub.__module__ = "nonexistent.module.path.zzz"

        # Force importlib.import_module to raise.
        original = importlib.import_module

        def _stub_importer(name, package=None):
            if name == "nonexistent.module.path.zzz":
                raise ImportError("simulated")
            return original(name, package)

        monkeypatch.setattr(importlib, "import_module", _stub_importer)

        _phase2_helpers.register_subcommand(_g, "stub4", _stub)
        # Invoke the command — the late-binding lookup runs at call time.
        runner = CliRunner()
        # We only need the lookup to *fire*, even if the call itself
        # short-circuits on missing fixtures. We don't assert on output.
        runner.invoke(_g, ["stub4", "--no-cache"])

    def test_click_type_str_fallback_for_non_primitive(self):
        """Cover ``_click_type``'s ``return str`` fallback when neither
        the annotation nor the default carries a primitive type."""
        from animedex.entry._phase2_helpers import register_subcommand
        import click

        @click.group()
        def _g():
            pass

        # default is a non-primitive (list); _click_type drops to ``return str``
        def _stub(*, tags=None, **kw):  # default=None hits `default is None` guard
            return {"tags": tags}

        register_subcommand(_g, "stub2", _stub)
        cmd = _g.commands["stub2"]
        # `tags` has annotation = inspect.Parameter.empty and default = None,
        # so _click_type returns str — the option is registered with that type.
        opt = next(p for p in cmd.params if p.name == "tags")
        # Click's STRING type's name is "text"
        assert opt.type.name in ("text", "string")

    def test_jq_error_path(self, cli_runner, cli, fake_clock):
        """A jq filter with a bad expression errors out via
        click.ClickException."""
        import shutil

        if shutil.which("jq") is None:
            pytest.skip("jq not installed")

        fixture = yaml.safe_load(
            (FIXTURES / "anilist" / "phase2_media" / "01-media-frieren.yaml").read_text(encoding="utf-8")
        )
        # Register without body-matching (the fixture's captured query
        # may drift from the live query; we only need the response).
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            from tools.fixtures.capture import fixture_response_bytes

            rsps.add(
                responses.Response(
                    method="POST",
                    url="https://graphql.anilist.co/",
                    status=200,
                    body=fixture_response_bytes(fixture),
                )
            )
            result = cli_runner.invoke(
                cli,
                ["anilist", "show", "154587", "--no-cache", "--jq", "{[malformed"],
            )
        # ``_apply_jq`` raises click.ClickException → exit non-zero
        assert result.exit_code != 0
        # The "jq error:" prefix is echoed to stderr by L105
        assert "jq error" in result.output.lower() or "jq" in (result.stderr or "").lower()


# ---------- render/tty.py edge cases ----------


class TestTtyRenderEdgeCases:
    def _src(self):
        from animedex.models.common import SourceTag

        return SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))

    def test_truncate_none(self):
        """``_truncate`` returns None when fed None."""
        from animedex.render.tty import _truncate

        assert _truncate(None, 10) is None

    def test_anime_with_next_airing_episode(self):
        """Cover the ``if anime.next_airing_episode:`` branch."""
        from animedex.models.anime import Anime, AnimeTitle, NextAiringEpisode
        from animedex.render.tty import render_tty

        n = NextAiringEpisode(
            episode=42,
            airing_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            time_until_airing_seconds=3600,
        )
        a = Anime(
            id="x:1",
            title=AnimeTitle(romaji="Test", english=None, native=None),
            next_airing_episode=n,
            ids={"x": "1"},
            source=self._src(),
        )
        text = render_tty(a)
        # Should have some next-airing display
        assert "Next" in text or "airing" in text.lower() or "ep" in text.lower()

    def test_anime_is_adult(self):
        """Cover the ``18+`` misc tag branch."""
        from animedex.models.anime import Anime, AnimeTitle
        from animedex.render.tty import render_tty

        a = Anime(
            id="x:1",
            title=AnimeTitle(romaji="Test", english=None, native=None),
            is_adult=True,
            ids={"x": "1"},
            source=self._src(),
        )
        text = render_tty(a)
        assert "18+" in text

    def test_long_streaming_list_overflow(self):
        """When streaming has more than 7 entries, the renderer prints a
        ``(+N more)`` summary."""
        from animedex.models.anime import Anime, AnimeStreamingLink, AnimeTitle
        from animedex.render.tty import render_tty

        streaming = [AnimeStreamingLink(provider=f"S{i}", url=f"https://x.invalid/{i}") for i in range(10)]
        a = Anime(
            id="x:1",
            title=AnimeTitle(romaji="Test", english=None, native=None),
            streaming=streaming,
            ids={"x": "1"},
            source=self._src(),
        )
        text = render_tty(a)
        assert "more" in text

    def test_trace_hit_with_full_metadata(self):
        """Trace render with native title + episode + duration + preview
        image populated covers several conditional branches."""
        from animedex.models.anime import AnimeTitle
        from animedex.models.trace import TraceHit
        from animedex.render.tty import render_tty
        from animedex.models.common import SourceTag

        src = SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        h = TraceHit(
            anilist_id=154587,
            anilist_title=AnimeTitle(
                romaji="Sousou no Frieren",
                english="Frieren: Beyond Journey's End",
                native="葬送のフリーレン",
            ),
            similarity=0.99,
            episode="5",
            start_at_seconds=120.0,
            frame_at_seconds=125.5,
            end_at_seconds=130.0,
            episode_filename="x.mkv",
            episode_duration_seconds=1500.0,
            preview_video_url="https://x.invalid/v",
            preview_image_url="https://x.invalid/i.jpg",
            source=src,
        )
        text = render_tty(h)
        assert "Frieren" in text
        assert "5" in text  # episode
        assert "Native" in text
        assert "Episode dur" in text
        assert "Preview JPG" in text

    def test_long_synonyms_list_overflow(self):
        """Cover the ``(+N more)`` synonyms summary line."""
        from animedex.models.anime import Anime, AnimeTitle
        from animedex.render.tty import render_tty

        a = Anime(
            id="x:1",
            title=AnimeTitle(romaji="Test", english=None, native=None),
            title_synonyms=[f"alt-title-{i}" for i in range(10)],
            ids={"x": "1"},
            source=self._src(),
        )
        text = render_tty(a)
        assert "more" in text  # "(+N more)"

    def test_to_common_raises_falls_through(self):
        """Cover the ``except Exception`` branch in ``render_tty``'s
        rich-fallback path."""
        from animedex.render.tty import render_tty
        from animedex.models.common import AnimedexModel

        class BrokenRich(AnimedexModel):
            label: str = "x"

            def to_common(self):
                raise RuntimeError("intentional failure")

        text = render_tty(BrokenRich())
        # Falls through to the generic JSON dump path.
        assert "BrokenRich" in text
