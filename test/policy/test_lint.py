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


class TestNestedGroups:
    def test_lint_recurses_into_subgroups(self):
        from animedex.policy.lint import lint_group

        @click.group()
        def root():
            pass

        @click.group()
        def sub():
            pass

        @sub.command()
        def bad() -> None:
            """One-liner only - no policy blocks."""

        root.add_command(sub, "sub")

        problems = lint_group(root)
        # The flat command name should reflect nesting: "sub bad".
        assert any("sub bad" in entry["command"] for entry in problems)

    def test_collect_agent_guidance_recurses(self):
        from animedex.policy.lint import collect_agent_guidance

        @click.group()
        def root():
            pass

        @click.group()
        def sub():
            pass

        @sub.command()
        def echo() -> None:
            """Nested.

            Backend: _selftest.

            Rate limit: 1 req/s.

            --- LLM Agent Guidance ---
            nested guidance.
            --- End ---
            """

        root.add_command(sub, "sub")

        out = collect_agent_guidance(root)
        assert any(entry["command"] == "sub echo" for entry in out)


class TestResolveCallableNoCallback:
    def test_no_callback_falls_back_to_command(self):
        """Exercise the ``callback is None`` branch of ``_resolve_callable``.

        The branch matters when a Click :class:`click.Command` has had
        its callback cleared (e.g. some Click groups). The fallback
        should return the command object itself without raising.
        """
        from animedex.policy.lint import _resolve_callable

        @click.command()
        def cmd() -> None:
            """doc"""

        cmd.callback = None
        resolved = _resolve_callable(cmd)
        assert resolved is cmd


class TestMain:
    def test_main_returns_zero_on_clean(self, capsys):
        """`animedex_cli` itself is policy-clean as of Phase 0."""
        from animedex.policy.lint import main

        rc = main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "OK" in captured.out

    def test_main_returns_one_on_violation(self, capsys, monkeypatch):
        from animedex.policy import lint

        @click.group()
        def fake_root():
            pass

        @fake_root.command()
        def bad() -> None:
            """Lacks the required blocks."""

        # Replace the resolved animedex_cli with our policy-violating
        # synthetic group; main() imports through animedex.entry so we
        # patch that surface.
        import animedex.entry as entry_pkg

        monkeypatch.setattr(entry_pkg, "animedex_cli", fake_root, raising=False)
        rc = lint.main()
        captured = capsys.readouterr()
        assert rc == 1
        assert "FAIL" in captured.err
        assert "bad" in captured.err


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.policy import lint

        assert lint.selftest() is True
