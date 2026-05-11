"""CLI tests for the top-level ``animedex search`` command."""

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
    import inspect

    from click.testing import CliRunner

    if "mix_stderr" in inspect.signature(CliRunner).parameters:
        return CliRunner(mix_stderr=False)
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


def _register_many(rsps: responses.RequestsMock, fixture_rels: list[str]) -> None:
    for rel in fixture_rels:
        _register_fixture_path_only(rsps, _load_fixture(rel))


def _combined_output(result) -> str:
    try:
        stderr = result.stderr
    except ValueError:
        stderr = ""
    return result.output + stderr


ANIME_SEARCH_FIXTURES = [
    "anilist/search/01-search-frieren.yaml",
    "ann/substring_search/01-frieren.yaml",
    "jikan/anime_search/17-frieren-tv-limit2.yaml",
    "kitsu/anime_search/17-frieren-limit2.yaml",
    "shikimori/animes_search/17-frieren-limit2.yaml",
]


class TestSearchCli:
    def test_help_lists_types_sources_and_examples(self, cli_runner, cli):
        result = cli_runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0, result.output
        for entity_type in ("anime", "manga", "character", "person", "studio", "publisher"):
            assert entity_type in result.output
            assert f"animedex search {entity_type} " in result.output
        for expected in (
            "Searches AniList anime media, ANN anime reports",
            "Jikan anime, Kitsu anime, and Shikimori anime.",
            "Searches AniList manga media, Jikan manga",
            "Kitsu manga, MangaDex manga, and Shikimori manga.",
            "Searches AniList characters, Jikan characters",
            "Kitsu characters, and Shikimori characters.",
            "Searches AniList staff",
            "Jikan people, Kitsu people, and Shikimori people.",
            "Searches AniList",
            "studios, Jikan producers, Kitsu producers, and Shikimori studios.",
            "Kitsu and Shikimori are fetched as catalogue lists and filtered locally.",
            "Searches Shikimori publishers.",
            "catalogue is fetched and filtered locally.",
        ):
            assert expected in result.output
        assert "Use --source with the backend names listed for a type" in result.output

    def test_anime_search_json_reports_every_source(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_many(rsps, ANIME_SEARCH_FIXTURES)
            result = cli_runner.invoke(cli, ["search", "anime", "Frieren", "--limit", "5", "--json", "--no-cache"])

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert set(decoded["sources"]) == {"anilist", "ann", "jikan", "kitsu", "shikimori"}
        assert {row["_source"] for row in decoded["items"]} >= {"anilist", "ann", "jikan", "kitsu", "shikimori"}
        assert all("_prefix_id" in row for row in decoded["items"])
        assert decoded["_meta"]["sources_consulted"] == ["anilist", "ann", "jikan", "kitsu", "shikimori"]

    def test_default_tty_renders_compact_rows(self, cli_runner, cli, fake_clock, force_tty):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_many(rsps, ANIME_SEARCH_FIXTURES)
            result = cli_runner.invoke(cli, ["search", "anime", "Frieren", "--limit", "5", "--no-cache"])

        assert result.exit_code == 0, result.output
        assert "Aggregate results" in result.output
        assert "[src: anilist]" in result.output
        assert "[src: jikan]" in result.output
        assert "anilist:" in result.output
        assert not result.output.lstrip().startswith("{")

    def test_source_allowlist_limits_fanout(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_many(
                rsps,
                [
                    "anilist/search/01-search-frieren.yaml",
                    "jikan/anime_search/17-frieren-tv-limit2.yaml",
                ],
            )
            result = cli_runner.invoke(
                cli,
                ["search", "anime", "Frieren", "--limit", "2", "--source", "anilist,jikan", "--json", "--no-cache"],
            )

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert set(decoded["sources"]) == {"anilist", "jikan"}
        assert {row["_source"] for row in decoded["items"]} <= {"anilist", "jikan"}

    @pytest.mark.parametrize(
        "entity_type,query,source,fixture_rel",
        [
            ("manga", "Berserk", "mangadex", "mangadex/manga_search/01-berserk.yaml"),
            ("character", "Frieren", "shikimori", "shikimori/characters_search/02-frieren-limit2.yaml"),
            ("person", "Miyazaki", "shikimori", "shikimori/people_search/02-miyazaki-limit2.yaml"),
            ("studio", "Ghibli", "kitsu", "kitsu/producers/02-ghibli-limit2.yaml"),
            ("publisher", "Kodansha", "shikimori", "shikimori/publishers/03-kodansha-limit1000.yaml"),
        ],
    )
    def test_type_source_combinations_use_real_fixtures(
        self, cli_runner, cli, fake_clock, entity_type, query, source, fixture_rel
    ):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, _load_fixture(fixture_rel))
            result = cli_runner.invoke(
                cli,
                ["search", entity_type, query, "--limit", "2", "--source", source, "--json", "--no-cache"],
            )

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert set(decoded["sources"]) == {source}
        assert decoded["sources"][source]["status"] == "ok"
        assert all(row["_source"] == source for row in decoded["items"])

    def test_partial_failure_keeps_healthy_sources_and_reports_stderr(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_many(
                rsps,
                [
                    "ann/substring_search/17-synthetic-503.yaml",
                    "jikan/anime_search/17-frieren-tv-limit2.yaml",
                    "kitsu/anime_search/17-frieren-limit2.yaml",
                    "shikimori/animes_search/17-frieren-limit2.yaml",
                ],
            )
            result = cli_runner.invoke(
                cli,
                [
                    "search",
                    "anime",
                    "Frieren",
                    "--limit",
                    "2",
                    "--source",
                    "ann,jikan,kitsu,shikimori",
                    "--json",
                    "--no-cache",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "source 'ann' failed" in result.stderr
        decoded = json.loads(result.stdout)
        assert decoded["sources"]["ann"]["status"] == "failed"
        assert decoded["sources"]["ann"]["http_status"] == 503
        assert {row["_source"] for row in decoded["items"]} == {"jikan", "kitsu", "shikimori"}

    def test_total_failure_exits_nonzero_with_empty_envelope(self, cli_runner, cli, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, _load_fixture("ann/substring_search/17-synthetic-503.yaml"))
            result = cli_runner.invoke(
                cli,
                ["search", "anime", "Frieren", "--source", "ann", "--json", "--no-cache"],
            )

        assert result.exit_code == 1, result.output
        decoded = json.loads(result.stdout)
        assert decoded["items"] == []
        assert decoded["sources"]["ann"]["status"] == "failed"

    def test_bad_type_is_clean_click_error(self, cli_runner, cli):
        result = cli_runner.invoke(cli, ["search", "badtype", "x", "--json", "--no-cache"])

        assert result.exit_code != 0
        output = _combined_output(result)
        assert "unknown type" in output
        assert "supported types" in output

    def test_missing_type_uses_click_argument_error(self, cli_runner, cli):
        result = cli_runner.invoke(cli, ["search"])

        assert result.exit_code != 0
        assert "Missing argument 'TYPE'" in _combined_output(result)
