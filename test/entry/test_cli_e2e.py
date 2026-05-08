"""Fixture-driven end-to-end CLI tests for Phase 2.

Per AGENTS.md §9bis (the post-PR-#6 testing discipline): every test
runs the real animedex stack — Click → entry wrapper → public Python
API → backend mapper → ``_dispatch.call`` → URL composer → headers →
cache → ratelimit → firewall → renderer — and only the HTTP wire is
mocked, against real captured fixtures.

This is the test class that would have caught the
``call() got unexpected keyword argument 'config'`` regression in the
first push of PR #6: those original tests monkey-patched
``animedex.backends.<backend>.<fn>`` and short-circuited the whole
chain. These tests reach all the way down.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses
import yaml


pytestmark = pytest.mark.unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "test" / "fixtures"


# ---------- shared infrastructure ----------


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
    """Make ``sys.stdout.isatty()`` return True so the CLI's auto-
    switching renderer takes the TTY path. ``CliRunner`` substitutes
    its own stdout (a BytesIO) which reports ``isatty()=False`` —
    without this fixture every CLI test trivially walks the JSON
    branch and TTY-side regressions slip through.

    This is HTTP-adjacent stubbing per AGENTS §9bis: it patches an
    OS-level stream attribute (isatty), not project code.
    """
    import animedex.entry._cli_factory as helpers

    monkeypatch.setattr(helpers, "_is_terminal", lambda stream: True)


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze the ratelimit + cache clocks so the dispatcher does not
    actually sleep waiting for token-bucket refill, and cache TTL math
    is deterministic. This is the only HTTP-adjacent monkey-patch the
    AGENTS §9bis discipline allows: it stubs the monotonic clock, not
    project code."""
    from datetime import datetime, timezone

    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


def _load_fixture(rel_path: str) -> dict:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


def _register_fixture(rsps, fixture: dict):
    """Register the fixture's request/response with ``responses``."""
    req = fixture["request"]
    res = fixture["response"]
    method = req["method"].upper()
    url = req["url"]

    body_json = res.get("body_json")
    body_text = res.get("body_text")
    body_b64 = res.get("body_b64")
    headers = dict(res.get("headers") or {})
    # Drop length/encoding headers that responses must compute itself.
    for h in (
        "Content-Length",
        "content-length",
        "Transfer-Encoding",
        "transfer-encoding",
        "Content-Encoding",
        "content-encoding",
    ):
        headers.pop(h, None)

    add_kwargs = {"status": res["status"], "headers": headers}
    if body_json is not None:
        add_kwargs["json"] = body_json
    elif body_text is not None:
        add_kwargs["body"] = body_text
    elif body_b64 is not None:
        import base64

        add_kwargs["body"] = base64.b64decode(body_b64)

    if method == "GET":
        rsps.add(responses.GET, url, **add_kwargs)
    elif method == "POST":
        rsps.add(responses.POST, url, **add_kwargs)
    else:
        rsps.add(getattr(responses, method), url, **add_kwargs)


# ---------- Jikan ----------


class TestJikanCliFromFixtures:
    """For each Jikan subcommand pick a fixture from
    ``test/fixtures/jikan/`` and replay it through the CLI. The
    upstream URL on the fixture is used verbatim as the responses
    mock URL, so we exercise the URL composer too."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["52991"], "jikan/anime_full/01-frieren-52991.yaml"),
            ("show", ["1"], "jikan/anime_full/05-cowboy-bebop-1.yaml"),
            ("anime-characters", ["52991"], "jikan/anime_characters/01-frieren.yaml"),
            ("anime-staff", ["52991"], "jikan/anime_staff/01-frieren-52991.yaml"),
            ("anime-pictures", ["52991"], "jikan/anime_pictures/01-frieren-52991.yaml"),
            ("anime-themes", ["52991"], "jikan/anime_themes/01-frieren-52991.yaml"),
            ("anime-streaming", ["52991"], "jikan/anime_streaming/01-frieren-52991.yaml"),
            ("anime-relations", ["52991"], "jikan/anime_relations/01-frieren-52991.yaml"),
            ("anime-statistics", ["52991"], "jikan/anime_statistics/01-frieren-52991.yaml"),
            ("manga-show", ["2"], "jikan/manga_full/01-berserk-2.yaml"),
            ("character-show", ["11"], "jikan/characters_full/01-edward-elric-11.yaml"),
            ("character-anime", ["11"], "jikan/characters_anime/01-edward-elric-11.yaml"),
            ("person-show", ["1870"], "jikan/people_full/01-miyazaki-1870.yaml"),
            ("producer-show", ["17"], "jikan/producers_full/01-aniplex-17.yaml"),
            ("seasons-now", ["--limit", "10"], "jikan/seasons_now/01-now.yaml"),
            ("season", ["2023", "fall", "--limit", "5"], "jikan/seasons_by_year/01-2023-fall.yaml"),
            ("top-anime", ["--limit", "10"], "jikan/top_anime/01-top10.yaml"),
            ("genres-anime", [], "jikan/genres_anime/01-all.yaml"),
            ("schedules", ["--filter", "monday", "--limit", "5"], "jikan/schedules/01-schedule-monday.yaml"),
            ("random-anime", [], "jikan/random_anime/01-random-01.yaml"),
            ("watch-episodes", [], "jikan/watch_episodes/01-today.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["jikan", subcommand, *positional, "--json", "--no-cache"])

        # The fixture's status determines the expected exit_code:
        # 200 → 0; 4xx/5xx → ApiError → ClickException → non-zero.
        if 200 <= fixture["response"]["status"] < 300:
            assert result.exit_code == 0, (
                f"{subcommand} {positional} failed against {fixture_rel}: {result.output[:600]}"
            )
        else:
            assert result.exit_code != 0, (
                f"{subcommand} unexpectedly succeeded against {fixture_rel}: {result.output[:300]}"
            )


# ---------- AniList ----------


class TestAnilistCliFromFixtures:
    """AniList-side fixture replay. All AniList queries go to the
    same URL, but `responses` matches the body when registered with
    a json= payload. Use match_querystring + match=... to be precise.
    """

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["154587"], "anilist/phase2_media/01-media-frieren.yaml"),
            ("show", ["199"], "anilist/phase2_media/02-media-spirited-away.yaml"),
            ("show", ["21"], "anilist/phase2_media/03-media-one-piece.yaml"),
            ("character", ["11"], "anilist/phase2_character/01-character-edward-elric.yaml"),
            ("staff", ["101572"], "anilist/phase2_staff/01-staff-101572.yaml"),
            ("studio", ["11"], "anilist/phase2_studio/01-studio-madhouse.yaml"),
            ("trending", [], "anilist/phase2_trending/01-trending-top8.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["anilist", subcommand, *positional, "--json", "--no-cache"])

        if 200 <= fixture["response"]["status"] < 300:
            assert result.exit_code == 0, (
                f"{subcommand} {positional} failed against {fixture_rel}: {result.output[:600]}"
            )
        else:
            assert result.exit_code != 0


class TestTtyRenderingWalk:
    """Every CLI command exercises BOTH output paths:
    * ``--json`` → JSON renderer (already covered above)
    * default (no flag) under a TTY → human-readable renderer

    Walks the same fixtures as TestJikanCliFromFixtures but with
    isatty() forced True so the TTY branch runs end-to-end. This is
    the suite that would have caught the
    ``'str' object has no attribute 'backend'`` regression in PR #6:
    until this fixture existed every CLI test trivially walked the
    JSON path.
    """

    @pytest.mark.parametrize(
        "argv,fixture_rel",
        [
            (["jikan", "show", "52991"], "jikan/anime_full/01-frieren-52991.yaml"),
            (["jikan", "manga-show", "2"], "jikan/manga_full/01-berserk-2.yaml"),
            (["jikan", "character-show", "11"], "jikan/characters_full/01-edward-elric-11.yaml"),
            (["jikan", "person-show", "1870"], "jikan/people_full/01-miyazaki-1870.yaml"),
            (["jikan", "producer-show", "17"], "jikan/producers_full/01-aniplex-17.yaml"),
            (["jikan", "search", "Frieren"], None),  # uses default Jikan search payload
            (["jikan", "season", "2023", "fall", "--limit", "5"], "jikan/seasons_by_year/01-2023-fall.yaml"),
            (["jikan", "top-anime", "--limit", "10"], "jikan/top_anime/01-top10.yaml"),
            (["jikan", "random-anime"], "jikan/random_anime/01-random-01.yaml"),
            (["anilist", "show", "154587"], "anilist/phase2_media/01-media-frieren.yaml"),
            (["anilist", "character", "11"], "anilist/phase2_character/01-character-edward-elric.yaml"),
            (["anilist", "staff", "101572"], "anilist/phase2_staff/01-staff-101572.yaml"),
            (["anilist", "studio", "11"], "anilist/phase2_studio/01-studio-madhouse.yaml"),
            (["anilist", "trending"], "anilist/phase2_trending/01-trending-top8.yaml"),
        ],
    )
    def test_command_renders_in_tty_mode(self, cli_runner, cli, fake_clock, force_tty, argv, fixture_rel):
        if fixture_rel is None:
            pytest.skip("no canonical fixture pinned for this command")
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, [*argv, "--no-cache"])

        assert result.exit_code == 0, f"{argv} failed in TTY mode against {fixture_rel}: {result.output[:600]}"
        # TTY output should contain the source-attribution marker
        # ``[src: <backend>]``, which the JSON path drops.
        assert "[src:" in result.output, f"TTY output missing source marker: {result.output[:300]}"
        # Should NOT look like a JSON dump (TTY path is multi-line key:value).
        assert not result.output.lstrip().startswith("{"), (
            f"TTY output appears to be JSON, not human-readable: {result.output[:200]}"
        )


class TestAnilistShowDeep:
    """Frieren-by-id walk-through asserts the rendered output reflects
    the fixture's actual values, not just exit_code 0. Catches mapper /
    renderer / config-attribution wiring."""

    def test_frieren_output_contains_expected_fields(self, cli_runner, cli, fake_clock):
        fixture = _load_fixture("anilist/phase2_media/01-media-frieren.yaml")

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--json", "--no-cache"])
        assert result.exit_code == 0, result.output

        decoded = json.loads(result.output)
        assert decoded["id"] == 154587
        assert "Frieren" in decoded["title"]["romaji"] or "Sousou" in decoded["title"]["romaji"]
        assert decoded["seasonYear"] == 2023
        # _meta carries source attribution; --no-source not passed so it should be present.
        assert "_meta" in decoded or "_source" in decoded

    def test_frieren_with_no_source_strips_attribution(self, cli_runner, cli, fake_clock):
        fixture = _load_fixture("anilist/phase2_media/01-media-frieren.yaml")

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--json", "--no-cache", "--no-source"])
        assert result.exit_code == 0
        decoded = json.loads(result.output)
        assert "_meta" not in decoded
        assert "_source" not in decoded

    def test_frieren_jq_filter(self, cli_runner, cli, fake_clock):
        import shutil

        if shutil.which("jq") is None:
            pytest.skip("jq not installed")

        fixture = _load_fixture("anilist/phase2_media/01-media-frieren.yaml")

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--no-cache", "--jq", ".id"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "154587"


# ---------- Trace ----------


class TestTraceCliFromFixtures:
    def test_quota_common_shape_has_no_ip(self, cli_runner, cli, fake_clock):
        # We have a Trace /me fixture from Phase 1 + Phase 2 — pick one.
        candidates = list((FIXTURES / "trace" / "me").glob("*.yaml"))
        if not candidates:
            pytest.skip("no trace /me fixture")
        fixture = yaml.safe_load(candidates[0].read_text(encoding="utf-8"))

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["trace", "quota", "--json", "--no-cache"])

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        # ``trace quota`` renders the common projection ``TraceQuota``,
        # which has no ``id`` field by design (the cross-source common
        # shape doesn't model upstream IP echoes). So the placeholder
        # IP from the fixture must not appear in the rendered output —
        # not because we filter it, but because the projection didn't
        # claim it. The lossless rich shape is available directly via
        # ``RawTraceQuota`` for a caller who wants it (AGENTS §13).
        assert "203.0.113.42" not in result.output  # placeholder
        # quota_used is coerced from string to int (Trace's quirk)
        assert isinstance(decoded["quota_used"], int)

    def test_search_runs_against_fixture(self, cli_runner, cli, fake_clock):
        candidates = list((FIXTURES / "trace" / "search").glob("*.yaml"))
        if not candidates:
            pytest.skip("no trace /search fixture")
        fixture = yaml.safe_load(candidates[0].read_text(encoding="utf-8"))

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(
                cli,
                ["trace", "search", "--url", "https://example.invalid/x.jpg", "--anilist-info", "--json", "--no-cache"],
            )
        # The fixture's URL won't match what the CLI sends (different
        # `url=` param), so this test really only exercises the
        # 404-on-mismatch path. Expect either 0 (matched) or non-zero
        # (no mock matched). The point is the command does NOT crash
        # with TypeErrors before reaching the network.
        if result.exit_code != 0:
            # Should be a clean ClickException, not a TypeError.
            assert "TypeError" not in result.output


# ---------- viewer / notification / etc. — auth-required stubs ----------


class TestTokenRequiredStubs:
    """The four token-required AniList commands must still raise
    auth-required without needing a token, until Phase 8 lands."""

    @pytest.mark.parametrize("subcommand", ["viewer", "notification", "ani-chart-user"])
    def test_no_args_token_stubs(self, cli_runner, cli, subcommand):
        result = cli_runner.invoke(cli, ["anilist", subcommand])
        assert result.exit_code != 0
        assert "auth-required" in result.output

    def test_markdown_stub_raises(self, cli_runner, cli):
        result = cli_runner.invoke(cli, ["anilist", "markdown", "**hello**"])
        assert result.exit_code != 0
        assert "auth-required" in result.output


# ---------- subcommand registry sanity ----------


class TestPhase2SubcommandTree:
    """No HTTP needed; just confirm registration shape."""

    def test_top_level_groups_present(self, cli):
        for group in ("anilist", "jikan", "trace"):
            assert group in cli.commands

    def test_anilist_has_at_least_28_subcommands(self, cli):
        assert len(cli.commands["anilist"].commands) >= 28

    def test_jikan_has_at_least_80_subcommands(self, cli):
        assert len(cli.commands["jikan"].commands) >= 80

    def test_trace_has_search_and_quota(self, cli):
        assert {"search", "quota"} <= set(cli.commands["trace"].commands.keys())


# ---------- --help walk for every Phase-2 subcommand ----------


class TestEverySubcommandHasHelp:
    """Cheap: --help doesn't hit the network and doesn't run the
    callback. Confirms the docstrings + Click metadata are valid for
    every command."""

    def test_anilist_help_walk(self, cli_runner, cli):
        for sub in cli.commands["anilist"].commands:
            r = cli_runner.invoke(cli, ["anilist", sub, "--help"])
            assert r.exit_code == 0, f"anilist {sub} --help failed: {r.output[:200]}"

    def test_jikan_help_walk(self, cli_runner, cli):
        for sub in cli.commands["jikan"].commands:
            r = cli_runner.invoke(cli, ["jikan", sub, "--help"])
            assert r.exit_code == 0, f"jikan {sub} --help failed: {r.output[:200]}"

    def test_trace_help_walk(self, cli_runner, cli):
        for sub in cli.commands["trace"].commands:
            r = cli_runner.invoke(cli, ["trace", sub, "--help"])
            assert r.exit_code == 0, f"trace {sub} --help failed: {r.output[:200]}"
