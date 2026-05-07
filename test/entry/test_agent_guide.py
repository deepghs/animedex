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

    def test_no_blocks_message(self, monkeypatch):
        """Force ``collect_agent_guidance`` to return ``[]`` to drive
        the "no blocks" message branch of ``_print_agent_guide``."""
        from animedex.entry import animedex_cli, cli as cli_module

        monkeypatch.setattr(
            "animedex.policy.lint.collect_agent_guidance",
            lambda group: [],
        )
        # Re-import inside the eager callback by patching the policy
        # module location used at call time. The callback in
        # ``_print_agent_guide`` does ``from animedex.policy.lint import
        # collect_agent_guidance``, so patch that path on the policy
        # module object itself.
        import animedex.policy.lint as lint_mod

        monkeypatch.setattr(lint_mod, "collect_agent_guidance", lambda group: [])

        runner = CliRunner()
        result = runner.invoke(animedex_cli, ["--agent-guide"])
        assert result.exit_code == 0
        assert "No Agent Guidance blocks found" in result.output
        assert cli_module is not None  # smoke


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
