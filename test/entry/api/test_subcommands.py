"""CliRunner-driven tests for ``animedex api <backend>`` subcommands.

Each backend's ``entry/api/<backend>.py`` body is exercised by
patching the per-backend ``call`` function so the subcommand never
hits the network. The tests verify that flags translate into the
right ``call`` kwargs and that the output is rendered through the
expected path.
"""

from __future__ import annotations

import json

import pytest


pytestmark = pytest.mark.unittest


def _envelope(status=200, body_text='{"ok":true}'):
    from animedex.api._envelope import RawCacheInfo, RawRequest, RawResponse, RawTiming

    bt = body_text or ""
    return RawResponse(
        backend="x",
        request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
        status=status,
        response_headers={"Content-Type": "application/json"},
        body_bytes=bt.encode("utf-8"),
        body_text=bt,
        timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0.0, request_ms=0.1),
        cache=RawCacheInfo(hit=False),
    )


def _captured_call(captured: list, return_envelope=None):
    """Build a stub ``call`` that records its kwargs and returns the
    pre-baked envelope."""
    env = return_envelope if return_envelope is not None else _envelope()

    def _stub(**kwargs):
        captured.append(kwargs)
        return env

    return _stub


@pytest.fixture
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


class TestApiAnilist:
    def test_minimal_query(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "anilist", "{ Media(id:1){ id } }"])
        assert result.exit_code == 0, result.output
        assert captured[0]["query"] == "{ Media(id:1){ id } }"
        assert captured[0]["variables"] is None

    def test_variables_parsed_as_json(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(
            cli,
            ["api", "anilist", "query($s:String){ Media(search:$s){id} }", "--variables", '{"s":"Frieren"}'],
        )
        assert result.exit_code == 0
        assert captured[0]["variables"] == {"s": "Frieren"}

    def test_invalid_variables_raises_usage_error(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "anilist", "{ x }", "--variables", "not-json"])
        assert result.exit_code != 0
        assert "not valid JSON" in result.output
        # Stub call must not have been reached.
        assert captured == []

    def test_debug_mode_emits_envelope_json(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "anilist", "{ x }", "--debug"])
        assert result.exit_code == 0
        decoded = json.loads(result.output)
        assert decoded["status"] == 200

    def test_extra_headers_passed_to_call(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "anilist", "{ x }", "-H", "X-Foo: bar"])
        assert result.exit_code == 0
        assert captured[0]["headers"] == {"X-Foo": "bar"}

    def test_no_cache_passes_through(self, cli_runner, cli, monkeypatch):
        from animedex.api import anilist as anilist_mod

        captured: list = []
        monkeypatch.setattr(anilist_mod, "call", _captured_call(captured))

        cli_runner.invoke(cli, ["api", "anilist", "{ x }", "--no-cache"])
        assert captured[0]["no_cache"] is True
        assert captured[0]["cache"] is None


class TestApiTrace:
    def test_get_path(self, cli_runner, cli, monkeypatch):
        from animedex.api import trace as trace_mod

        captured: list = []
        monkeypatch.setattr(trace_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "trace", "/me"])
        assert result.exit_code == 0, result.output
        assert captured[0]["path"] == "/me"
        assert captured[0]["method"] == "GET"
        assert captured[0]["raw_body"] is None

    def test_input_file_becomes_post_body(self, cli_runner, cli, monkeypatch, tmp_path):
        from animedex.api import trace as trace_mod

        captured: list = []
        monkeypatch.setattr(trace_mod, "call", _captured_call(captured))

        img = tmp_path / "shot.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        result = cli_runner.invoke(cli, ["api", "trace", "/search", "--input", str(img)])
        assert result.exit_code == 0, result.output
        assert captured[0]["method"] == "POST"
        assert captured[0]["raw_body"] == b"\xff\xd8\xff\xe0"

    def test_input_dash_reads_stdin(self, cli_runner, cli, monkeypatch):
        """``--input -`` reads the request body from stdin (binary).

        ``click.testing.CliRunner`` substitutes its own stdin around
        the invocation, so monkeypatching ``sys.stdin`` directly does
        not survive. Instead patch the ``sys`` reference inside the
        ``trace`` entry module after invocation begins, by stubbing
        ``trace_mod.call`` to read from a known buffer."""
        # Use the runner's own ``input`` channel (text), then patch
        # the reader inside the entry module so the bytes match.
        from animedex.entry.api import trace as trace_entry
        from animedex.api import trace as trace_mod

        captured: list = []
        monkeypatch.setattr(trace_mod, "call", _captured_call(captured))

        # Patch the ``sys.stdin.buffer.read`` lookup in trace_entry's
        # module namespace by swapping its bound ``sys`` symbol.
        import io
        import types

        fake_sys = types.SimpleNamespace(stdin=types.SimpleNamespace(buffer=io.BytesIO(b"\xff\xd8\xff\xe0")))
        monkeypatch.setattr(trace_entry, "sys", fake_sys)

        result = cli_runner.invoke(cli, ["api", "trace", "/search", "--input", "-"])
        assert result.exit_code == 0, result.output
        assert captured[0]["method"] == "POST"
        assert captured[0]["raw_body"] == b"\xff\xd8\xff\xe0"


class TestApiShikimori:
    def test_rest_default_method_is_get(self, cli_runner, cli, monkeypatch):
        from animedex.api import shikimori as shikimori_mod

        captured: list = []
        monkeypatch.setattr(shikimori_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "shikimori", "/api/animes/52991"])
        assert result.exit_code == 0, result.output
        assert captured[0]["method"] == "GET"
        assert captured[0]["json_body"] is None

    def test_graphql_query_sets_post_method(self, cli_runner, cli, monkeypatch):
        from animedex.api import shikimori as shikimori_mod

        captured: list = []
        monkeypatch.setattr(shikimori_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "shikimori", "/api/graphql", "--graphql", '{ animes(ids:"1"){ id } }'])
        assert result.exit_code == 0, result.output
        assert captured[0]["method"] == "POST"
        assert captured[0]["json_body"] == {"query": '{ animes(ids:"1"){ id } }'}

    def test_explicit_post_method_passed_through(self, cli_runner, cli, monkeypatch):
        from animedex.api import shikimori as shikimori_mod

        captured: list = []
        monkeypatch.setattr(shikimori_mod, "call", _captured_call(captured))

        cli_runner.invoke(cli, ["api", "shikimori", "/api/x", "-X", "POST"])
        assert captured[0]["method"] == "POST"


class TestGetOnlySubcommands:
    """The four GET-only backends share the same template body
    (``_get_only_template.make_get_only_subcommand``). Exercising one
    backend covers the template; the others are covered indirectly.
    Keep two so a regression in either side is visible."""

    def test_jikan_path_is_threaded(self, cli_runner, cli, monkeypatch):
        from animedex.api import jikan as jikan_mod

        captured: list = []
        monkeypatch.setattr(jikan_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "jikan", "/anime/52991"])
        assert result.exit_code == 0, result.output
        assert captured[0]["path"] == "/anime/52991"

    def test_kitsu_extra_headers_threaded(self, cli_runner, cli, monkeypatch):
        from animedex.api import kitsu as kitsu_mod

        captured: list = []
        monkeypatch.setattr(kitsu_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "kitsu", "/anime/1", "-H", "X-Trace: yes"])
        assert result.exit_code == 0, result.output
        assert captured[0]["headers"] == {"X-Trace": "yes"}

    def test_danbooru_no_follow_threaded(self, cli_runner, cli, monkeypatch):
        from animedex.api import danbooru as danbooru_mod

        captured: list = []
        monkeypatch.setattr(danbooru_mod, "call", _captured_call(captured))

        result = cli_runner.invoke(cli, ["api", "danbooru", "/posts/1.json", "--no-follow"])
        assert result.exit_code == 0, result.output
        assert captured[0]["follow_redirects"] is False

    def test_4xx_status_yields_exit_4(self, cli_runner, cli, monkeypatch):
        from animedex.api import jikan as jikan_mod

        captured: list = []
        monkeypatch.setattr(jikan_mod, "call", _captured_call(captured, return_envelope=_envelope(status=404)))

        result = cli_runner.invoke(cli, ["api", "jikan", "/anime/99999999"])
        assert result.exit_code == 4

    def test_5xx_status_yields_exit_5(self, cli_runner, cli, monkeypatch):
        from animedex.api import jikan as jikan_mod

        captured: list = []
        monkeypatch.setattr(jikan_mod, "call", _captured_call(captured, return_envelope=_envelope(status=502)))

        result = cli_runner.invoke(cli, ["api", "jikan", "/anime/x"])
        assert result.exit_code == 5
