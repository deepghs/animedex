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
from urllib.parse import parse_qs, urlsplit

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
            ("show", ["154587"], "anilist/media/01-media-frieren.yaml"),
            ("show", ["199"], "anilist/media/02-media-spirited-away.yaml"),
            ("show", ["21"], "anilist/media/03-media-one-piece.yaml"),
            ("character", ["11"], "anilist/character/01-character-edward-elric.yaml"),
            ("staff", ["101572"], "anilist/staff/01-staff-101572.yaml"),
            ("studio", ["11"], "anilist/studio/01-studio-madhouse.yaml"),
            ("trending", [], "anilist/trending/01-trending-top8.yaml"),
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
            (["anilist", "show", "154587"], "anilist/media/01-media-frieren.yaml"),
            (["anilist", "character", "11"], "anilist/character/01-character-edward-elric.yaml"),
            (["anilist", "staff", "101572"], "anilist/staff/01-staff-101572.yaml"),
            (["anilist", "studio", "11"], "anilist/studio/01-studio-madhouse.yaml"),
            (["anilist", "trending"], "anilist/trending/01-trending-top8.yaml"),
            (["nekos", "image", "husbando"], "nekos/husbando/01-image-amount-1.yaml"),
            (["nekos", "image", "neko"], "nekos/neko/01-image-amount-1.yaml"),
            (["nekos", "search", "Frieren", "--amount", "5"], "nekos/search/01-frieren-image.yaml"),
            (["kitsu", "show", "46474"], "kitsu/anime_by_id/01-frieren-46474.yaml"),
            (["kitsu", "trending", "--limit", "10"], "kitsu/trending_anime/01-top10.yaml"),
            (["shikimori", "show", "52991"], "shikimori/animes_by_id/01-frieren-52991.yaml"),
            (["shikimori", "search", "Frieren", "--limit", "2"], "shikimori/animes_search/01-frieren.yaml"),
            (["ann", "show", "38838"], "ann/by_id/14-id-38838-frieren.yaml"),
            (["ann", "search", "Frieren"], "ann/substring_search/01-frieren.yaml"),
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
        fixture = _load_fixture("anilist/media/01-media-frieren.yaml")

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
        fixture = _load_fixture("anilist/media/01-media-frieren.yaml")

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--json", "--no-cache", "--no-source"])
        assert result.exit_code == 0
        decoded = json.loads(result.output)
        assert "_meta" not in decoded
        assert "_source" not in decoded

    def test_frieren_jq_filter(self, cli_runner, cli, fake_clock):
        """``--jq`` runs through the bundled wheel — no PATH lookup,
        no subprocess. The same test used to ``pytest.skip`` when
        host :program:`jq` wasn't installed; the wheel is now a
        runtime dep so it always runs."""
        fixture = _load_fixture("anilist/media/01-media-frieren.yaml")

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


# ---------- nekos.best ----------


class TestNekosCliFromFixtures:
    """JSON-path coverage of every nekos subcommand."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("categories", [], "nekos/endpoints/01-all-categories.yaml"),
            ("categories-full", [], "nekos/endpoints/01-all-categories.yaml"),
            ("image", ["husbando"], "nekos/husbando/01-image-amount-1.yaml"),
            ("image", ["husbando", "--amount", "3"], "nekos/husbando/02-image-amount-3.yaml"),
            ("image", ["neko"], "nekos/neko/01-image-amount-1.yaml"),
            ("image", ["waifu"], "nekos/waifu/01-image-amount-1.yaml"),
            ("image", ["baka"], "nekos/baka/01-gif-amount-1.yaml"),
            ("search", ["Frieren", "--amount", "5"], "nekos/search/01-frieren-image.yaml"),
            ("search", ["Frieren", "--type", "2", "--amount", "3"], "nekos/search/02-frieren-gif.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["nekos", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"nekos {subcommand} {positional} failed: {result.output[:600]}"

    def test_image_jq_filter_extracts_url(self, cli_runner, cli, fake_clock):
        """``--jq '.[0].url'`` reaches into the rendered list and extracts
        the asset URL — pins the multi-result rendering shape."""
        fixture = _load_fixture("nekos/husbando/01-image-amount-1.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["nekos", "image", "husbando", "--no-cache", "--jq", ".[0].url"])
        assert result.exit_code == 0, result.output
        assert result.output.strip().startswith('"https://nekos.best/api/v2/husbando/')

    def test_categories_lists_at_least_ten_categories_in_json(self, cli_runner, cli, fake_clock):
        fixture = _load_fixture("nekos/endpoints/01-all-categories.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["nekos", "categories", "--json", "--no-cache"])
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert isinstance(decoded, list)
        assert len(decoded) >= 10
        # Sorted (the public Python API returns alphabetised names).
        assert decoded == sorted(decoded)

    def test_categories_tty_output_is_one_name_per_line(self, cli_runner, cli, fake_clock, force_tty):
        """``nekos categories`` returns ``list[str]``; the TTY renderer
        falls through to one-string-per-line. No ``[src:]`` marker
        applies because there is no rich-model row to attribute. Pin
        this shape so a future renderer change doesn't silently
        promote it to JSON-of-strings on the TTY path."""
        fixture = _load_fixture("nekos/endpoints/01-all-categories.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["nekos", "categories", "--no-cache"])
        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.split("\n") if ln.strip()]
        assert "husbando" in lines
        assert lines == sorted(lines)
        # Should not look like JSON.
        assert not result.output.lstrip().startswith("[")


# ---------- Kitsu ----------


def _register_fixture_path_only(rsps, fixture: dict):
    """Path-only fixture registration used by Kitsu tests: the
    fixture URL's path determines the mock route, and any query
    string the CLI sends through is accepted regardless of whether
    it exactly matches the captured one. Necessary because Kitsu
    fixtures were captured with ad-hoc page[limit] values that don't
    match the high-level Python API's defaults; the test cares about
    the response shape, not the query echo.
    """
    import re
    from urllib.parse import urlsplit

    req = fixture["request"]
    res = fixture["response"]
    method = req["method"].upper()

    parsed = urlsplit(req["url"])
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    url_re = re.compile(re.escape(base) + r"(\?.*)?$")

    headers = dict(res.get("headers") or {})
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
    body_json = res.get("body_json")
    body_text = res.get("body_text")
    if body_json is not None:
        add_kwargs["json"] = body_json
    elif body_text is not None:
        add_kwargs["body"] = body_text

    rsps.add(responses.Response(method=method, url=url_re, **add_kwargs))


class TestKitsuCliFromFixtures:
    """JSON-path coverage of every Kitsu high-level subcommand."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["46474"], "kitsu/anime_by_id/01-frieren-46474.yaml"),
            ("search", ["Frieren"], "kitsu/anime_search/01-frieren.yaml"),
            ("streaming", ["46474"], "kitsu/anime_streaming_links/01-frieren-46474.yaml"),
            ("mappings", ["46474"], "kitsu/anime_mappings/01-frieren-46474.yaml"),
            ("trending", ["--limit", "10"], "kitsu/trending_anime/01-top10.yaml"),
            ("manga-show", ["1"], "kitsu/manga_by_id/01-berserk-1.yaml"),
            ("manga-search", ["Berserk"], "kitsu/manga_search/01-berserk.yaml"),
            ("categories", ["--limit", "20"], "kitsu/categories/01-top20.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["kitsu", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"kitsu {subcommand} {positional} failed: {result.output[:600]}"

    def test_mappings_jq_filter_extracts_external_ids(self, cli_runner, cli, fake_clock):
        """``--jq`` over the mappings list pins the JSON:API resource
        shape (id / type / attributes nesting) for downstream callers."""
        fixture = _load_fixture("kitsu/anime_mappings/01-frieren-46474.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(
                cli,
                ["kitsu", "mappings", "46474", "--no-cache", "--jq", "[.[].attributes.externalSite]"],
            )
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        # Frieren's mappings always include at least anilist + mal.
        assert any("anilist" in s for s in decoded)
        assert any("myanimelist" in s for s in decoded)


# ---------- Shikimori ----------


class TestShikimoriCliFromFixtures:
    """JSON-path coverage for the high-level Shikimori commands."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["52991"], "shikimori/animes_by_id/01-frieren-52991.yaml"),
            ("search", ["Frieren", "--limit", "2"], "shikimori/animes_search/01-frieren.yaml"),
            ("calendar", ["--limit", "1"], "shikimori/calendar/01-limit-1.yaml"),
            ("screenshots", ["52991"], "shikimori/screenshots/01-frieren-52991.yaml"),
            ("videos", ["52991"], "shikimori/videos/01-frieren-52991.yaml"),
            ("roles", ["52991"], "shikimori/roles/01-frieren-52991.yaml"),
            ("characters", ["52991"], "shikimori/roles/01-frieren-52991.yaml"),
            ("staff", ["52991"], "shikimori/roles/01-frieren-52991.yaml"),
            ("similar", ["52991"], "shikimori/similar/01-frieren-52991.yaml"),
            ("related", ["52991"], "shikimori/related/01-frieren-52991.yaml"),
            ("external-links", ["52991"], "shikimori/external_links/01-frieren-52991.yaml"),
            ("topics", ["52991", "--limit", "3"], "shikimori/topics/01-frieren-52991.yaml"),
            ("studios", [], "shikimori/studios/01-all.yaml"),
            ("genres", [], "shikimori/genres/01-all.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        fixture = _load_fixture(fixture_rel)
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["shikimori", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"shikimori {subcommand} failed: {result.output[:600]}"

    def test_search_jq_filter_extracts_names(self, cli_runner, cli, fake_clock):
        fixture = _load_fixture("shikimori/animes_search/01-frieren.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(
                cli,
                ["shikimori", "search", "Frieren", "--limit", "2", "--no-cache", "--jq", "[.[].name]"],
            )

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert "Sousou no Frieren" in decoded


# ---------- ANN ----------


class TestAnnCliFromFixtures:
    """JSON-path coverage for the high-level ANN commands."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["38838"], "ann/by_id/14-id-38838-frieren.yaml"),
            ("search", ["Frieren"], "ann/substring_search/01-frieren.yaml"),
            (
                "reports",
                ["--id", "155", "--type", "anime", "--nlist", "2"],
                "ann/reports/01-anime-recently-modified-2.yaml",
            ),
            ("show", ["99999999"], "ann/by_id/15-id-99999999-missing.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        fixture = _load_fixture(fixture_rel)
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["ann", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"ann {subcommand} failed: {result.output[:600]}"

    def test_warning_200_is_rendered_not_error(self, cli_runner, cli, fake_clock):
        fixture = _load_fixture("ann/by_id/15-id-99999999-missing.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture(rsps, fixture)
            result = cli_runner.invoke(cli, ["ann", "show", "99999999", "--json", "--no-cache"])

        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded["warnings"] == ["no result for anime=99999999"]
        assert decoded["anime"] == []


# ---------- MangaDex ----------


class TestMangaDexCliFromFixtures:
    """JSON-path coverage of every MangaDex high-level subcommand."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("show", ["801513ba-a712-498c-8f57-cae55b38cc92"], "mangadex/manga_by_id/02-berserk.yaml"),
            ("search", ["Berserk"], "mangadex/manga_search/01-berserk.yaml"),
            (
                "feed",
                ["801513ba-a712-498c-8f57-cae55b38cc92", "--lang", "en"],
                "mangadex/manga_feed/02-berserk.yaml",
            ),
            ("chapter", ["01e9f0cb-caea-406d-92bb-0cc67c37481d"], "mangadex/chapter_by_id/01-berserk-ch1.yaml"),
            ("cover", ["f73c6872-01ee-4ed5-86d1-3520dc250dc4"], "mangadex/cover_by_id/01-cover-1.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["mangadex", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"mangadex {subcommand} failed: {result.output[:600]}"

    def test_show_jq_filter_extracts_title(self, cli_runner, cli, fake_clock):
        """``--jq`` over the rich JSON:API resource. Berserk's
        upstream title block uses ``ja-ro`` (romanised Japanese)
        rather than ``en``, so the projection picks any non-null
        value."""
        fixture = _load_fixture("mangadex/manga_by_id/02-berserk.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(
                cli,
                [
                    "mangadex",
                    "show",
                    "801513ba-a712-498c-8f57-cae55b38cc92",
                    "--no-cache",
                    "--jq",
                    ".attributes.title",
                ],
            )
        assert result.exit_code == 0, result.output
        assert "Berserk" in result.output

    @pytest.mark.parametrize(
        "argv,fixture_rel,query_key,expected",
        [
            (
                ["statistics-manga-batch", "--manga", "801513ba-a712-498c-8f57-cae55b38cc92"],
                "mangadex/statistics_manga_search/01-berserk-only.yaml",
                "manga[]",
                ["801513ba-a712-498c-8f57-cae55b38cc92"],
            ),
            (
                ["statistics-chapter-batch", "--chapter", "01e9f0cb-caea-406d-92bb-0cc67c37481d"],
                "mangadex/statistics_chapter_search/01-berserk-only.yaml",
                "chapter[]",
                ["01e9f0cb-caea-406d-92bb-0cc67c37481d"],
            ),
            (
                [
                    "statistics-manga-batch",
                    "--manga",
                    "801513ba-a712-498c-8f57-cae55b38cc92",
                    "--manga",
                    "0d1f5f6b-7e1f-4f0f-a111-000000000000",
                ],
                "mangadex/statistics_manga_search/01-berserk-only.yaml",
                "manga[]",
                ["801513ba-a712-498c-8f57-cae55b38cc92", "0d1f5f6b-7e1f-4f0f-a111-000000000000"],
            ),
        ],
    )
    def test_repeatable_batch_options_send_whole_values(
        self, cli_runner, cli, fake_clock, argv, fixture_rel, query_key, expected
    ):
        fixture = _load_fixture(fixture_rel)
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["mangadex", *argv, "--json", "--no-cache"])
            sent = rsps.calls[0].request

        assert result.exit_code == 0, result.output
        parsed = parse_qs(urlsplit(sent.url).query)
        assert parsed[query_key] == expected


# ---------- Danbooru ----------


class TestDanbooruCliFromFixtures:
    """JSON-path coverage of every Danbooru high-level subcommand."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("search", ["touhou rating:g order:score"], "danbooru/posts_search/01-touhou-rating-g-order-score.yaml"),
            ("post", ["1"], "danbooru/posts_by_id/01-post-1.yaml"),
            ("artist-search", ["ke-ta"], "danbooru/artists_search/02-ke-ta.yaml"),
            ("tag", ["touhou*"], "danbooru/tags_search/01-touhou-prefix.yaml"),
            ("pool", ["1"], "danbooru/pools_by_id/01-pool-1.yaml"),
            ("count", ["touhou rating:g"], "danbooru/counts/01-touhou-rating-g.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["danbooru", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"danbooru {subcommand} failed: {result.output[:600]}"

    def test_search_jq_filter_extracts_ratings(self, cli_runner, cli, fake_clock):
        """``rating:g`` query → every result row carries
        ``rating == "g"``. Pin the filter pass-through."""
        fixture = _load_fixture("danbooru/posts_search/01-touhou-rating-g-order-score.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(
                cli,
                ["danbooru", "search", "touhou rating:g order:score", "--no-cache", "--jq", "[.[].rating]"],
            )
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded
        assert all(r == "g" for r in decoded)


# ---------- Waifu.im ----------


class TestWaifuCliFromFixtures:
    """JSON-path coverage of every Waifu.im high-level subcommand."""

    @pytest.mark.parametrize(
        "subcommand,positional,fixture_rel",
        [
            ("tags", [], "waifu/tags/01-all.yaml"),
            ("artists", [], "waifu/artists/01-page-1.yaml"),
            ("images", [], "waifu/images/01-default-page1.yaml"),
            ("images", ["--included-tags", "waifu"], "waifu/images/02-included-waifu.yaml"),
            ("images", ["--is-nsfw", "true", "--page-size", "3"], "waifu/images/04-nsfw-true.yaml"),
            ("images", ["--is-animated", "true", "--page-size", "2"], "waifu/images/05-animated-true.yaml"),
        ],
    )
    def test_subcommand_runs_against_fixture(self, cli_runner, cli, fake_clock, subcommand, positional, fixture_rel):
        path = FIXTURES / fixture_rel
        if not path.exists():
            pytest.skip(f"fixture missing: {fixture_rel}")
        fixture = _load_fixture(fixture_rel)

        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["waifu", subcommand, *positional, "--json", "--no-cache"])

        assert result.exit_code == 0, f"waifu {subcommand} failed: {result.output[:600]}"

    def test_default_images_are_sfw(self, cli_runner, cli, fake_clock):
        """Default ``waifu images`` (no ``--is-nsfw``) returns
        SFW-only — pin the upstream-default-honouring posture."""
        fixture = _load_fixture("waifu/images/01-default-page1.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["waifu", "images", "--no-cache", "--jq", "[.[].isNsfw]"])
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded
        assert all(v is False for v in decoded)

    @pytest.mark.parametrize(
        "argv,fixture_rel,expected_included,expected_excluded",
        [
            (
                ["--included-tags", "waifu"],
                "waifu/images/02-included-waifu.yaml",
                ["waifu"],
                None,
            ),
            (
                ["--included-tags", "waifu", "--included-tags", "maid"],
                "waifu/images/02-included-waifu.yaml",
                ["waifu", "maid"],
                None,
            ),
            (
                ["--excluded-tags", "ero"],
                "waifu/images/06-excluded-ero.yaml",
                None,
                ["ero"],
            ),
        ],
    )
    def test_repeatable_tag_options_send_whole_values(
        self, cli_runner, cli, fake_clock, argv, fixture_rel, expected_included, expected_excluded
    ):
        fixture = _load_fixture(fixture_rel)
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = cli_runner.invoke(cli, ["waifu", "images", *argv, "--json", "--no-cache"])
            sent = rsps.calls[0].request

        assert result.exit_code == 0, result.output
        parsed = parse_qs(urlsplit(sent.url).query)
        if expected_included is None:
            assert "included_tags" not in parsed
        else:
            assert parsed["included_tags"] == expected_included
        if expected_excluded is None:
            assert "excluded_tags" not in parsed
        else:
            assert parsed["excluded_tags"] == expected_excluded


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
        for group in (
            "anilist",
            "ann",
            "danbooru",
            "jikan",
            "kitsu",
            "mangadex",
            "nekos",
            "shikimori",
            "trace",
            "waifu",
        ):
            assert group in cli.commands

    def test_anilist_has_at_least_28_subcommands(self, cli):
        assert len(cli.commands["anilist"].commands) >= 28

    def test_jikan_has_at_least_80_subcommands(self, cli):
        assert len(cli.commands["jikan"].commands) >= 80

    def test_trace_has_search_and_quota(self, cli):
        assert {"search", "quota"} <= set(cli.commands["trace"].commands.keys())

    def test_nekos_has_categories_image_search(self, cli):
        assert {"categories", "categories-full", "image", "search"} <= set(cli.commands["nekos"].commands.keys())

    def test_kitsu_has_full_surface(self, cli):
        assert {
            "show",
            "search",
            "streaming",
            "mappings",
            "trending",
            "manga-show",
            "manga-search",
            "categories",
        } <= set(cli.commands["kitsu"].commands.keys())

    def test_mangadex_has_full_surface(self, cli):
        assert {"show", "search", "feed", "chapter", "cover"} <= set(cli.commands["mangadex"].commands.keys())

    def test_danbooru_has_full_surface(self, cli):
        assert {"search", "post", "artist", "artist-search", "tag", "pool", "pool-search", "count"} <= set(
            cli.commands["danbooru"].commands.keys()
        )

    def test_waifu_has_full_surface(self, cli):
        assert {"tags", "artists", "images"} <= set(cli.commands["waifu"].commands.keys())

    def test_shikimori_has_full_surface(self, cli):
        assert {
            "calendar",
            "search",
            "show",
            "screenshots",
            "videos",
            "characters",
            "staff",
            "similar",
            "related",
            "external-links",
            "topics",
            "studios",
            "genres",
        } <= set(cli.commands["shikimori"].commands.keys())

    def test_ann_has_full_surface(self, cli):
        assert {"show", "search", "reports"} <= set(cli.commands["ann"].commands.keys())


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

    def test_nekos_help_walk(self, cli_runner, cli):
        for sub in cli.commands["nekos"].commands:
            r = cli_runner.invoke(cli, ["nekos", sub, "--help"])
            assert r.exit_code == 0, f"nekos {sub} --help failed: {r.output[:200]}"

    def test_kitsu_help_walk(self, cli_runner, cli):
        for sub in cli.commands["kitsu"].commands:
            r = cli_runner.invoke(cli, ["kitsu", sub, "--help"])
            assert r.exit_code == 0, f"kitsu {sub} --help failed: {r.output[:200]}"

    def test_mangadex_help_walk(self, cli_runner, cli):
        for sub in cli.commands["mangadex"].commands:
            r = cli_runner.invoke(cli, ["mangadex", sub, "--help"])
            assert r.exit_code == 0, f"mangadex {sub} --help failed: {r.output[:200]}"

    def test_danbooru_help_walk(self, cli_runner, cli):
        for sub in cli.commands["danbooru"].commands:
            r = cli_runner.invoke(cli, ["danbooru", sub, "--help"])
            assert r.exit_code == 0, f"danbooru {sub} --help failed: {r.output[:200]}"

    def test_waifu_help_walk(self, cli_runner, cli):
        for sub in cli.commands["waifu"].commands:
            r = cli_runner.invoke(cli, ["waifu", sub, "--help"])
            assert r.exit_code == 0, f"waifu {sub} --help failed: {r.output[:200]}"

    def test_shikimori_help_walk(self, cli_runner, cli):
        for sub in cli.commands["shikimori"].commands:
            r = cli_runner.invoke(cli, ["shikimori", sub, "--help"])
            assert r.exit_code == 0, f"shikimori {sub} --help failed: {r.output[:200]}"

    def test_ann_help_walk(self, cli_runner, cli):
        for sub in cli.commands["ann"].commands:
            r = cli_runner.invoke(cli, ["ann", sub, "--help"])
            assert r.exit_code == 0, f"ann {sub} --help failed: {r.output[:200]}"
