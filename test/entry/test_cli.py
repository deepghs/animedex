"""Smoke tests for the top-level Click command group."""

import pytest
from click.testing import CliRunner

from animedex.entry import animedex_cli


@pytest.mark.unittest
class TestCli:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--version"])
        assert result.exit_code == 0
        assert "animedex" in result.output

    def test_help_lists_status(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--help"])
        assert result.exit_code == 0
        assert "status" in result.output

    def test_status_subcommand_runs(self):
        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["status"])
        assert result.exit_code == 0
        assert "work in progress" in result.output.lower()
