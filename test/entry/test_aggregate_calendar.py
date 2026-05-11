"""Fixture-driven tests for top-level calendar aggregate commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml
from click.testing import CliRunner

from test.api._fixture_replay import register_fixture_with_responses


pytestmark = pytest.mark.unittest

FIXTURES = Path("test/fixtures")


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr("animedex.transport.ratelimit._sleep", lambda s: state.update({"rl_now": state["rl_now"] + s}))
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


@pytest.fixture
def force_tty(monkeypatch):
    import animedex.entry.aggregate as aggregate_entry

    monkeypatch.setattr(aggregate_entry, "_is_terminal", lambda stream: True)


def _load(rel_path: str) -> dict:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


def _fixture_with_request(rel_path: str, *, variables: dict | None = None, url: str | None = None) -> dict:
    fixture = _load(rel_path)
    if variables is not None:
        fixture["request"]["json_body"]["variables"] = variables
    if url is not None:
        fixture["request"]["url"] = url
    return fixture


def _stdout(result) -> str:
    return result.stdout if hasattr(result, "stdout") else result.output


def _stderr(result) -> str:
    try:
        stderr = result.stderr
    except (AttributeError, ValueError):
        return result.output
    return stderr or result.output


def _json_payload(result) -> dict:
    """Parse the JSON envelope even when older Click mixes stderr into output."""
    for line in reversed(_stdout(result).splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError(f"no JSON object found in output: {_stdout(result)!r}")


def _register(rsps, *fixtures):
    for fixture in fixtures:
        register_fixture_with_responses(rsps, fixture)


def _anilist_season(limit: int = 3) -> dict:
    return _fixture_with_request(
        "anilist/schedule/01-schedule-2024-spring.yaml",
        variables={"year": 2024, "season": "SPRING", "perPage": limit},
    )


def _jikan_season(limit: int = 3) -> dict:
    return _fixture_with_request(
        "jikan/seasons/03-2024-spring.yaml",
        url=f"https://api.jikan.moe/v4/seasons/2024/spring?limit={limit}",
    )


def _anilist_schedule(limit: int = 5) -> dict:
    fixture = _load("anilist/longtail/03-airing-schedule-not-yet-aired.yaml")
    fixture["request"]["json_body"] = {
        "query": (
            "query ($mediaId: Int, $notYetAired: Boolean, $airingAtGreater: Int, $airingAtLesser: Int, $perPage: Int) {\n"
            "  Page(page: 1, perPage: $perPage) {\n"
            "    pageInfo { total hasNextPage }\n"
            "    airingSchedules(\n"
            "      mediaId: $mediaId,\n"
            "      notYetAired: $notYetAired,\n"
            "      airingAt_greater: $airingAtGreater,\n"
            "      airingAt_lesser: $airingAtLesser,\n"
            "      sort: TIME\n"
            "    ) {\n"
            "      id airingAt episode timeUntilAiring\n"
            "      media { id title { romaji english } }\n"
            "    }\n"
            "  }\n"
            "}"
        ),
        "variables": {
            "mediaId": None,
            "notYetAired": None,
            "airingAtGreater": 1778457600,
            "airingAtLesser": 1778544000,
            "perPage": limit,
        },
    }
    for row in fixture["response"]["body_json"]["data"]["Page"]["airingSchedules"]:
        row.setdefault("timeUntilAiring", 0)
    return fixture


def _jikan_schedule(limit: int = 5) -> dict:
    return _fixture_with_request(
        "jikan/schedules/01-schedule-monday.yaml",
        url=f"https://api.jikan.moe/v4/schedules?filter=monday&limit={limit}",
    )


def _synthetic_failure(fixture: dict, *, status: int, body: dict, label: str) -> dict:
    out = json.loads(json.dumps(fixture))
    out["metadata"]["label"] = label
    out["response"]["status"] = status
    out["response"]["captured_from"] = f"synthetic-{status}"
    out["response"]["headers"] = {"Content-Type": "application/json"}
    out["response"]["body_json"] = body
    out["response"]["body_text"] = None
    out["response"]["body_b64"] = None
    return out


def test_season_json_aggregates_two_sources(runner, cli, fake_clock):
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, _anilist_season(), _jikan_season())
        result = runner.invoke(cli, ["season", "2024", "spring", "--limit", "3", "--json", "--no-cache"])

    assert result.exit_code == 0, result.output
    payload = _json_payload(result)
    assert set(payload["sources"]) == {"anilist", "jikan"}
    assert payload["sources"]["anilist"]["status"] == "ok"
    assert payload["sources"]["jikan"]["items"] == 3
    assert len(payload["items"]) == 11
    assert payload["_meta"]["sources_consulted"] == ["anilist", "jikan"]


def test_season_source_allowlist_only_calls_jikan(runner, cli, fake_clock):
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, _jikan_season())
        result = runner.invoke(
            cli, ["season", "2024", "spring", "--source", "jikan", "--limit", "3", "--json", "--no-cache"]
        )

    assert result.exit_code == 0, result.output
    payload = _json_payload(result)
    assert set(payload["sources"]) == {"jikan"}
    assert payload["sources"]["jikan"]["items"] == 3


def test_schedule_json_aggregates_and_projects_rows(runner, cli, fake_clock, monkeypatch):
    import animedex.agg.calendar as calendar

    monkeypatch.setattr(calendar, "_now_local", lambda: datetime(2026, 5, 11, tzinfo=timezone.utc))
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, _anilist_schedule(), _jikan_schedule())
        result = runner.invoke(cli, ["schedule", "--day", "monday", "--limit", "5", "--json", "--no-cache"])

    assert result.exit_code == 0, result.output
    payload = _json_payload(result)
    assert set(payload["sources"]) == {"anilist", "jikan"}
    assert payload["sources"]["anilist"]["items"] == 5
    assert payload["sources"]["jikan"]["items"] == 5
    assert any(
        item.get("source", {}).get("backend") == "jikan" and item.get("title") == "Shin Nippon History"
        for item in payload["items"]
    )


def test_schedule_tty_renders_source_markers(runner, cli, fake_clock, force_tty, monkeypatch):
    import animedex.agg.calendar as calendar

    monkeypatch.setattr(calendar, "_now_local", lambda: datetime(2026, 5, 11, tzinfo=timezone.utc))
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, _jikan_schedule())
        result = runner.invoke(cli, ["schedule", "--day", "monday", "--source", "jikan", "--limit", "5", "--no-cache"])

    assert result.exit_code == 0, result.output
    assert "Shin Nippon History" in result.output
    assert "[src: jikan]" in result.output
    assert not result.output.lstrip().startswith("{")


def test_partial_failure_returns_success_with_stderr(runner, cli, fake_clock):
    anilist_fail = _synthetic_failure(
        _anilist_season(),
        status=429,
        body={"errors": [{"message": "rate limited"}], "data": None},
        label="aggregate-season-anilist-synthetic-429",
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, anilist_fail, _jikan_season())
        result = runner.invoke(cli, ["season", "2024", "spring", "--limit", "3", "--json", "--no-cache"])

    assert result.exit_code == 0, result.output
    payload = _json_payload(result)
    assert payload["sources"]["anilist"]["status"] == "failed"
    assert payload["sources"]["anilist"]["reason"] == "rate-limited"
    assert payload["sources"]["jikan"]["status"] == "ok"
    assert "source 'anilist' failed: rate-limited (HTTP 429)" in _stderr(result)


def test_total_failure_exits_nonzero_with_empty_envelope(runner, cli, fake_clock):
    anilist_fail = _synthetic_failure(
        _anilist_season(),
        status=500,
        body={"error": "boom"},
        label="aggregate-season-anilist-synthetic-500",
    )
    jikan_fail = _synthetic_failure(
        _jikan_season(),
        status=503,
        body={"status": 503, "type": "ServiceUnavailable", "message": "boom", "error": "boom"},
        label="aggregate-season-jikan-synthetic-503",
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, anilist_fail, jikan_fail)
        result = runner.invoke(cli, ["season", "2024", "spring", "--limit", "3", "--json", "--no-cache"])

    assert result.exit_code == 1
    payload = _json_payload(result)
    assert payload["items"] == []
    assert payload["sources"]["anilist"]["status"] == "failed"
    assert payload["sources"]["jikan"]["status"] == "failed"
    assert "source 'anilist' failed" in _stderr(result)
    assert "source 'jikan' failed" in _stderr(result)


def test_top_level_help_lists_aggregate_commands_without_policy_blocks(runner, cli):
    result = runner.invoke(cli, ["season", "--help"])

    assert result.exit_code == 0, result.output
    assert "List anime airing in a season across AniList and Jikan." in result.output
    assert "Examples:" in result.output
    assert "LLM Agent Guidance" not in result.output

    result = runner.invoke(cli, ["schedule", "--help"])

    assert result.exit_code == 0, result.output
    assert "List airing schedule rows across AniList and Jikan." in result.output
    assert "Examples:" in result.output
    assert "LLM Agent Guidance" not in result.output


def test_invalid_aggregate_options_surface_click_errors(runner, cli):
    result = runner.invoke(cli, ["season", "2024", "spring", "--source", "all,jikan"])
    assert result.exit_code != 0
    assert "--source all cannot be combined" in result.output

    result = runner.invoke(cli, ["schedule", "--day", "noday"])
    assert result.exit_code != 0
    assert "Invalid value for '--day'" in result.output

    result = runner.invoke(cli, ["season", "2024", "spring", "--limit", "0"])
    assert result.exit_code != 0
    assert "--limit must be >= 1" in result.output


def test_jq_errors_are_wrapped(runner, cli, fake_clock):
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        _register(rsps, _jikan_season())
        result = runner.invoke(
            cli,
            [
                "season",
                "2024",
                "spring",
                "--source",
                "jikan",
                "--limit",
                "3",
                "--json",
                "--no-cache",
                "--jq",
                "{[broken",
            ],
        )

    assert result.exit_code != 0
    assert "jq" in result.output.lower()


def test_schedule_bad_args_surface_click_error(runner, cli):
    result = runner.invoke(cli, ["schedule", "--limit", "0"])
    assert result.exit_code != 0
    assert "--limit must be >= 1" in result.output


def test_entry_selftest_runs():
    import animedex.entry.aggregate as aggregate_entry

    assert aggregate_entry.selftest() is True
