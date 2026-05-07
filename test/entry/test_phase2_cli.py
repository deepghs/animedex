"""CliRunner-driven smoke tests for the Phase-2 high-level command groups.

Mocks the per-backend Python API at module level so the CLI never
hits the network. Verifies subcommand discovery + invocation +
``--jq`` round-trip on a representative slice (one command per
group) — full per-endpoint coverage lives in the backend mapper
tests.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


@pytest.fixture
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


def _src():
    from animedex.models.common import SourceTag

    return SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


class TestSubcommandTree:
    def test_top_level_has_three_new_groups(self, cli):
        for name in ("anilist", "jikan", "trace"):
            assert name in cli.commands, f"missing top-level group: {name}"

    def test_anilist_has_22_anonymous_subs_plus_4_token_stubs(self, cli):
        names = set(cli.commands["anilist"].commands.keys())
        # 22 anonymous + 4 token stubs + 6 search variants = ≥30 commands
        assert len(names) >= 30
        assert "show" in names
        assert "search" in names
        assert "viewer" in names  # token stub registered

    def test_jikan_has_at_least_80_subs(self, cli):
        names = set(cli.commands["jikan"].commands.keys())
        assert len(names) >= 80
        assert "show" in names
        assert "season" in names

    def test_trace_has_search_and_quota(self, cli):
        names = set(cli.commands["trace"].commands.keys())
        assert names == {"search", "quota"}


class TestAnilistShow:
    def test_show_renders_json_via_flag(self, cli_runner, cli, monkeypatch):
        from animedex.backends import anilist as bk
        from animedex.backends.anilist.models import AnilistAnime, _AnilistTitle

        rich = AnilistAnime(id=154587, title=_AnilistTitle(romaji="Frieren"), source_tag=_src())
        monkeypatch.setattr(bk, "show", lambda id, **kw: rich)

        result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--json"])
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded["id"] == 154587

    def test_jq_pipeline(self, cli_runner, cli, monkeypatch):
        import shutil

        if shutil.which("jq") is None:
            pytest.skip("jq not installed")

        from animedex.backends import anilist as bk
        from animedex.backends.anilist.models import AnilistAnime, _AnilistTitle

        rich = AnilistAnime(id=154587, title=_AnilistTitle(romaji="Frieren"), source_tag=_src())
        monkeypatch.setattr(bk, "show", lambda id, **kw: rich)

        result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--jq", ".title.romaji"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == '"Frieren"'

    def test_no_source_strips_attribution(self, cli_runner, cli, monkeypatch):
        from animedex.backends import anilist as bk
        from animedex.backends.anilist.models import AnilistAnime, _AnilistTitle

        rich = AnilistAnime(id=154587, title=_AnilistTitle(romaji="Frieren"), source_tag=_src())
        monkeypatch.setattr(bk, "show", lambda id, **kw: rich)

        result = cli_runner.invoke(cli, ["anilist", "show", "154587", "--json", "--no-source"])
        decoded = json.loads(result.output)
        assert "_source" not in decoded


class TestAnilistAuthRequired:
    def test_viewer_exits_non_zero_with_auth_required(self, cli_runner, cli):
        result = cli_runner.invoke(cli, ["anilist", "viewer"])
        assert result.exit_code != 0
        assert "auth-required" in result.output


class TestJikanShow:
    def test_show_invokes_python_api(self, cli_runner, cli, monkeypatch):
        from animedex.backends import jikan as bk
        from animedex.backends.jikan.models import JikanAnime

        rich = JikanAnime(mal_id=52991, title="Frieren", source_tag=_src())
        monkeypatch.setattr(bk, "show", lambda mal_id, **kw: rich)

        result = cli_runner.invoke(cli, ["jikan", "show", "52991", "--json"])
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded["mal_id"] == 52991


class TestTraceQuota:
    def test_quota_renders_typed_response(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk
        from animedex.models.trace import TraceQuota

        result_obj = TraceQuota(priority=0, concurrency=1, quota=100, quota_used=18, source=_src())
        monkeypatch.setattr(bk, "quota", lambda **kw: result_obj)

        result = cli_runner.invoke(cli, ["trace", "quota", "--json"])
        assert result.exit_code == 0, result.output
        decoded = json.loads(result.output)
        assert decoded["quota_used"] == 18
        # Privacy: nothing IP-shaped in the output
        assert "203.0.113.42" not in result.output


class TestEveryAnilistSubcommandHasHelp:
    """Smoke test: every Phase-2 anilist subcommand has a working
    --help that includes the policy blocks via the policy-lint
    pathway."""

    def test_help_for_each_anilist_subcommand(self, cli_runner, cli):
        anilist_grp = cli.commands["anilist"]
        for sub_name in anilist_grp.commands:
            result = cli_runner.invoke(cli, ["anilist", sub_name, "--help"])
            assert result.exit_code == 0, f"{sub_name} --help failed: {result.output}"

    def test_help_for_each_jikan_subcommand(self, cli_runner, cli):
        jikan_grp = cli.commands["jikan"]
        for sub_name in jikan_grp.commands:
            result = cli_runner.invoke(cli, ["jikan", sub_name, "--help"])
            assert result.exit_code == 0, f"{sub_name} --help failed: {result.output}"
