"""Smoke tests for the top-level Click command group."""

import pytest
from click.testing import CliRunner

from animedex.entry import animedex_cli


@pytest.mark.unittest
class TestCli:
    def test_version_flag_two_line_banner(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--version"])
        assert result.exit_code == 0
        assert "animedex" in result.output
        # The banner is two non-empty lines: title+version, then either
        # the build-info short form (commit ... built ...) or the
        # "build info not generated" sentinel.
        non_empty = [line for line in result.output.splitlines() if line.strip()]
        assert len(non_empty) >= 2, f"--version output too short:\n{result.output}"
        second = non_empty[1]
        assert ("built " in second) or ("build info not generated" in second), (
            f"second line did not match either build-info form:\n{result.output}"
        )

    def test_help_lists_status(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--help"])
        assert result.exit_code == 0
        assert "status" in result.output
        assert "selftest" in result.output

    def test_status_subcommand_runs(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["status"])
        assert result.exit_code == 0
        assert "work in progress" in result.output.lower()

    def test_selftest_subcommand_exits_zero(self):
        # The selftest command exits via sys.exit; CliRunner records
        # the resulting code on result.exit_code.
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["selftest"])
        assert result.exit_code == 0, f"selftest should exit 0 on a clean tree. Output:\n{result.output}"
        assert "Summary" in result.output
