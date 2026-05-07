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
        assert "Build info" in report
        assert "Module smoke tests" in report
        assert "CLI subcommands" in report
        assert "Summary" in report

    def test_build_info_section_handles_both_states(self):
        # The Build info section is unconditional. With the
        # generated build_info.py present, the report contains
        # "Built at:"; without it, "(not generated)" appears.
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        assert ("Built at:" in report) or ("(not generated)" in report), (
            f"Build info section in unexpected shape:\n{report}"
        )

    def test_report_lists_required_modules(self):
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        for module in (
            "animedex",
            "animedex.config.meta",
            "animedex.config.buildmeta",
            "animedex.entry.cli",
            "animedex.diag.selftest",
        ):
            assert module in report, f"selftest report did not mention {module}\n{report}"

    def test_modules_without_selftest_are_marked_import_only(self):
        # The current scaffold has no module-level selftest() callables,
        # so every module appears tagged "(import only)".
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        assert "(import only)" in report

    def test_selftest_subcommand_does_not_recurse(self):
        # The CLI-subcommand probe must not invoke selftest --help in a
        # way that recurses into selftest's own runner.
        buf = io.StringIO()
        run_selftest(stream=buf)
        report = buf.getvalue()
        assert "skipped: would recurse" in report


@pytest.mark.unittest
class TestSmokeRegistryHonoursSelftestCallable:
    """The smoke runner must call ``selftest()`` when a module exposes one,
    and degrade gracefully when it raises or returns ``False``."""

    def test_passing_selftest_is_marked_smoke_ok(self, monkeypatch):
        from animedex.diag import selftest as diag

        # Plant a selftest on an existing module rather than registering
        # a new fake target; this verifies the discovery branch and the
        # smoke success label.
        import animedex.config.meta as target

        calls = []

        def fake_selftest():
            calls.append(True)

        monkeypatch.setattr(target, "selftest", fake_selftest, raising=False)

        results = diag._check_module_smoke()
        labels = [label for label, _ok, _detail in results]
        oks = {label: ok for label, ok, _ in results}

        assert any("animedex.config.meta (smoke)" in label for label in labels)
        assert oks.get("animedex.config.meta (smoke)") is True
        assert calls == [True]

    def test_raising_selftest_is_marked_smoke_failed(self, monkeypatch):
        from animedex.diag import selftest as diag

        import animedex.config.meta as target

        def angry_selftest():
            raise RuntimeError("smoke deliberately tripped")

        monkeypatch.setattr(target, "selftest", angry_selftest, raising=False)

        results = diag._check_module_smoke()
        oks = {label: (ok, detail) for label, ok, detail in results}
        ok, detail = oks.get("animedex.config.meta (smoke)", (None, None))
        assert ok is False
        assert "smoke deliberately tripped" in detail

    def test_false_return_is_marked_smoke_failed(self, monkeypatch):
        from animedex.diag import selftest as diag

        import animedex.config.meta as target

        monkeypatch.setattr(target, "selftest", lambda: False, raising=False)

        results = diag._check_module_smoke()
        oks = {label: (ok, detail) for label, ok, detail in results}
        ok, detail = oks.get("animedex.config.meta (smoke)", (None, None))
        assert ok is False
        assert "selftest() returned False" in detail
