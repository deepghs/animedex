"""
Tests for :mod:`animedex.policy.lint`.

Per ``plans/02 §4`` every backend command (and every MCP-registered
tool) must carry a docstring with three structural blocks:
``Backend:``, ``Rate limit:``, and the ``--- LLM Agent Guidance ---``
/ ``--- End ---`` delimiters. The lint enforces this at CI. The
tests here pin the per-function check, the iteration over a
synthetic registry, and the CLI exit code.
"""

from __future__ import annotations

import click
import pytest


pytestmark = pytest.mark.unittest


def _good_command():
    @click.command()
    def cmd() -> None:
        """One-line summary.

        Backend: Example (example.invalid). Notes about the source.

        Rate limit: 10 req/s.

        --- LLM Agent Guidance ---
        Some guidance for the agent.
        --- End ---
        """

    return cmd


def _missing_backend():
    @click.command()
    def cmd() -> None:
        """One-line summary.

        Rate limit: 10 req/s.

        --- LLM Agent Guidance ---
        guidance.
        --- End ---
        """

    return cmd


def _missing_rate_limit():
    @click.command()
    def cmd() -> None:
        """One-line summary.

        Backend: Example.

        --- LLM Agent Guidance ---
        guidance.
        --- End ---
        """

    return cmd


def _missing_agent_guidance():
    @click.command()
    def cmd() -> None:
        """One-line summary.

        Backend: Example.

        Rate limit: 10 req/s.
        """

    return cmd


def _missing_agent_guidance_end():
    @click.command()
    def cmd() -> None:
        """One-line summary.

        Backend: Example.

        Rate limit: 10 req/s.

        --- LLM Agent Guidance ---
        text without end delimiter.
        """

    return cmd


class TestCheckCommand:
    def test_well_formed_command_passes(self):
        from animedex.policy.lint import check_command_docstring

        problems = check_command_docstring(_good_command())
        assert problems == []

    def test_missing_backend(self):
        from animedex.policy.lint import check_command_docstring

        problems = check_command_docstring(_missing_backend())
        assert any("Backend:" in p for p in problems)

    def test_missing_rate_limit(self):
        from animedex.policy.lint import check_command_docstring

        problems = check_command_docstring(_missing_rate_limit())
        assert any("Rate limit:" in p for p in problems)

    def test_missing_agent_guidance(self):
        from animedex.policy.lint import check_command_docstring

        problems = check_command_docstring(_missing_agent_guidance())
        assert any("Agent Guidance" in p for p in problems)

    def test_missing_end_delimiter(self):
        from animedex.policy.lint import check_command_docstring

        problems = check_command_docstring(_missing_agent_guidance_end())
        assert any("--- End ---" in p for p in problems)


class TestLintGroup:
    def test_walks_group_recursively(self):
        from animedex.policy.lint import lint_group

        @click.group()
        def root():
            pass

        root.add_command(_good_command(), "good")
        root.add_command(_missing_backend(), "bad")

        problems = lint_group(root)
        assert any(entry["command"] == "bad" for entry in problems)
        assert all(entry["command"] != "good" for entry in problems)

    def test_no_problems_means_empty_list(self):
        from animedex.policy.lint import lint_group

        @click.group()
        def root():
            pass

        root.add_command(_good_command(), "good")
        assert lint_group(root) == []


class TestExtractAgentGuidance:
    def test_returns_block_text(self):
        from animedex.policy.lint import extract_agent_guidance

        cmd = _good_command()
        text = extract_agent_guidance(cmd)
        assert text is not None
        assert "guidance" in text.lower()

    def test_returns_none_when_absent(self):
        from animedex.policy.lint import extract_agent_guidance

        cmd = _missing_agent_guidance()
        assert extract_agent_guidance(cmd) is None


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.policy import lint

        assert lint.selftest() is True
