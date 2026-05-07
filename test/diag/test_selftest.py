"""In-process tests for :mod:`animedex.diag.selftest`."""

import io

import pytest

from animedex.diag.selftest import run_selftest


@pytest.mark.unittest
class TestRunSelftest:
    def test_returns_zero_on_clean_install(self):
        buf = io.StringIO()
        code = run_selftest(stream=buf)
        assert code == 0, f"run_selftest should pass on a fresh checkout. Output was:\n{buf.getvalue()}"

    def test_report_has_expected_sections(self):
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        assert "animedex selftest" in report
        assert "Environment" in report
        assert "Package" in report
        assert "Module imports" in report
        assert "CLI subcommands" in report
        assert "Summary" in report

    def test_report_lists_required_modules(self):
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        for module in (
            "animedex",
            "animedex.config.meta",
            "animedex.entry.cli",
            "animedex.diag.selftest",
        ):
            assert module in report, f"selftest report did not mention {module}\n{report}"

    def test_selftest_subcommand_does_not_recurse(self):
        # The CLI-subcommand probe must not invoke selftest --help in a
        # way that recurses into selftest's own runner.
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        assert "skipped: would recurse" in report
