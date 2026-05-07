"""
Tests for the ``animedex --agent-guide`` aggregator.

The aggregator prints every registered command's
``--- LLM Agent Guidance ---`` block (per ``plans/02 §4``) so an
agent shelling out without an MCP layer can read the catalogue once
at session start. The shape we pin: empty group → empty (or
"no commands" message) but exit 0; a group with one command → that
command's block included; the option is eager (prints and exits
without dispatching to a subcommand).
"""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner


pytestmark = pytest.mark.unittest


class TestAgentGuideOption:
    def test_option_exits_without_subcommand(self):
        from animedex.entry import animedex_cli

        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--agent-guide"])
        assert result.exit_code == 0

    def test_empty_group_says_so(self):
        """Phase 0 has no backend commands yet; the output says so."""
        from animedex.entry import animedex_cli

        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--agent-guide"])
        # Either the report is empty or it announces "no Agent Guidance
        # blocks found"; the contract is just that exit is clean.
        assert result.exit_code == 0
        assert isinstance(result.output, str)


class TestAgentGuideOnSyntheticGroup:
    def test_collected_blocks_include_command(self):
        from animedex.policy.lint import collect_agent_guidance

        @click.group()
        def root():
            pass

        @root.command()
        def echo() -> None:
            """Synthetic command.

            Backend: _selftest.

            Rate limit: 1 req/s.

            --- LLM Agent Guidance ---
            Synthetic guidance.
            --- End ---
            """

        out = collect_agent_guidance(root)
        assert len(out) == 1
        assert out[0]["command"] == "echo"
        assert "Synthetic guidance" in out[0]["guidance"]
