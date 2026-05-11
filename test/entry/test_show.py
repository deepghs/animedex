"""CLI tests for the top-level ``animedex show`` command."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import responses
import yaml


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[2] / "test" / "fixtures"
_STRIP_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


@pytest.fixture
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


@pytest.fixture
def force_tty(monkeypatch):
    import click.testing

    monkeypatch.setattr(click.testing._NamedTextIOWrapper, "isatty", lambda self: True, raising=False)


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze HTTP-adjacent clocks."""
    from datetime import datetime, timezone

    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 11, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


def _load_fixture(rel_path: str) -> dict:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


def _register_fixture_path_only(rsps: responses.RequestsMock, fixture: dict) -> None:
    req = fixture["request"]
    resp = fixture["response"]
    parsed = urlsplit(req["url"])
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    url_re = re.compile(re.escape(base) + r"(\?.*)?$")
    headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP_HEADERS}
    kwargs = {"status": resp["status"], "headers": headers}
    if resp.get("body_json") is not None:
        kwargs["json"] = resp["body_json"]
    elif resp.get("body_text") is not None:
        kwargs["body"] = resp["body_text"]
    elif resp.get("body_b64") is not None:
        import base64

        kwargs["body"] = base64.b64decode(resp["body_b64"])
    rsps.add(responses.Response(method=req["method"].upper(), url=url_re, **kwargs))


class TestShowCli:
    @pytest.mark.parametrize(
        "argv,fixture_rel,expected_backend",
        [
            (["show", "anime", "anilist:154587"], "anilist/media/01-media-frieren.yaml", "anilist"),
            (["show", "anime", "mal:52991"], "jikan/anime_full/01-frieren-52991.yaml", "jikan"),
            (["show", "anime", "jikan:52991"], "jikan/anime_full/01-frieren-52991.yaml", "jikan"),
            (
                ["show", "manga", "mangadex:801513ba-a712-498c-8f57-cae55b38cc92"],
                "mangadex/manga_by_id/02-berserk.yaml",
                "mangadex",
            ),
            (
                ["show", "character", "shikimori:184947"],
                "shikimori/characters_by_id/01-frieren-184947.yaml",
                "shikimori",
            ),
            (["show", "person", "shikimori:1870"], "shikimori/people_by_id/01-hayao-miyazaki-1870.yaml", "shikimori"),
            (["show", "studio", "shikimori:2"], "shikimori/studios/02-all-limit-1000.yaml", "shikimori"),
            (["show", "publisher", "shikimori:16"], "shikimori/publishers/02-all-limit-1000.yaml", "shikimori"),
        ],
    )
    def test_show_json_routes_prefixes_to_backends(
        self, cli_runner, cli, fake_clock, argv, fixture_rel, expected_backend
    ):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, _load_fixture(fixture_rel))
            result = cli_runner.invoke(cli, [*argv, "--json", "--no-cache"])

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert expected_backend in decoded["_meta"]["sources_consulted"]

    def test_show_default_tty_renders_source_marker(self, cli_runner, cli, fake_clock, force_tty):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, _load_fixture("jikan/anime_full/01-frieren-52991.yaml"))
            result = cli_runner.invoke(cli, ["show", "anime", "mal:52991", "--no-cache"])

        assert result.exit_code == 0, result.output
        assert "[src: jikan]" in result.output
        assert "Frieren" in result.output
        assert not result.output.lstrip().startswith("{")

    @pytest.mark.parametrize(
        "argv,expected",
        [
            (["show", "publisher", "anilist:1"], "type 'publisher' is not supported by backend 'anilist'"),
            (["show", "anime", "badprefix:1"], "unknown prefix"),
            (["show", "anime", "anidb:42"], "AniDB high-level helpers are not shipped yet"),
            (["show", "anime", "anilist:abc"], "ID is not numeric for backend 'anilist'"),
        ],
    )
    def test_show_rejects_invalid_references_before_http(self, cli_runner, cli, argv, expected):
        with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
            result = cli_runner.invoke(cli, [*argv, "--json", "--no-cache"])

        assert len(rsps.calls) == 0
        assert result.exit_code != 0
        assert expected in result.output

    def test_upstream_error_propagates_cleanly(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, _load_fixture("jikan/anime_full_errors/01-upstream-error.yaml"))
            result = cli_runner.invoke(cli, ["show", "anime", "mal:9999999999", "--json", "--no-cache"])

        assert result.exit_code != 0
        assert "upstream-error" in result.output or "upstream-error" in result.stderr
