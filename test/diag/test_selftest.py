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


@pytest.mark.unittest
class TestSelftestDefensivePaths:
    """Drive the defensive try/except branches of run_selftest's helpers.

    These are the paths that fire when something *upstream* of the
    selftest itself goes wrong - missing modules, broken imports, etc.
    They are otherwise unreachable in normal CI.
    """

    def test_format_environment_includes_frozen_branch(self, monkeypatch):
        from animedex.diag import selftest as diag

        monkeypatch.setattr(diag, "_is_frozen", lambda: True)
        monkeypatch.setattr(diag, "_bundle_dir", lambda: "/tmp/_MEI_fake")
        lines = diag._format_environment_lines()
        assert any("Bundle dir" in line for line in lines)

    def test_format_package_handles_missing_animedex_metadata(self, monkeypatch):
        """Trigger the except branch by making the metadata import fail."""
        import builtins

        from animedex.diag import selftest as diag

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "animedex" and args and args[2] and "__VERSION__" in args[2]:
                raise RuntimeError("fake metadata-load failure")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        lines = diag._format_package_lines()
        assert any("[FAIL]" in line for line in lines)

    def test_format_build_info_handles_loader_failure(self, monkeypatch):
        from animedex.diag import selftest as diag

        # buildmeta.format_block is called inside _format_build_info_lines.
        # Replacing it with a raising function exercises the except branch.
        import animedex.config.buildmeta as bm

        def boom():
            raise RuntimeError("fake buildmeta failure")

        monkeypatch.setattr(bm, "format_block", boom)
        lines = diag._format_build_info_lines()
        assert any("[FAIL]" in line for line in lines)

    def test_check_module_smoke_handles_import_failure(self, monkeypatch):
        from animedex.diag import selftest as diag

        # Force the import_module call to fail for one of the targets.
        original_import = diag.importlib.import_module

        def fake_import(name):
            if name == "animedex.models.common":
                raise RuntimeError("fake import error")
            return original_import(name)

        monkeypatch.setattr(diag.importlib, "import_module", fake_import)
        results = diag._check_module_smoke()
        labels = {label for label, _, _ in results}
        assert any("animedex.models.common (import)" in label for label in labels)

    def test_check_cli_subcommands_handles_runner_import_failure(self, monkeypatch):
        from animedex.diag import selftest as diag

        original_import = diag.importlib.import_module if hasattr(diag, "importlib") else None
        # Patch click.testing.CliRunner so the import inside the helper
        # fails when reached. We do this by clobbering the click submodule
        # entry to a stub that raises on attribute access.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "click.testing":
                raise RuntimeError("fake CliRunner import error")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        results = diag._check_cli_subcommands()
        assert results[0][1] is False
        assert "cli runner import" in results[0][0]
        del original_import  # unused but kept for symmetry

    def test_safely_wraps_runner_exceptions(self):
        from animedex.diag.selftest import _safely

        def boom():
            raise RuntimeError("kaboom")

        result = _safely(boom, "fake-runner")
        assert len(result) == 1
        label, ok, detail = result[0]
        assert label == "fake-runner"
        assert ok is False
        assert "RuntimeError" in detail


@pytest.mark.unittest
class TestSelftestModuleMain:
    def test_main_shim_returns_zero(self):
        from animedex.diag.selftest import main

        # The shim just calls run_selftest and returns its code; on a
        # clean install that is 0.
        rc = main()
        assert rc == 0


@pytest.mark.unittest
class TestCliCheckExceptionPaths:
    def test_per_invocation_exception_recorded(self, monkeypatch):
        """Force CliRunner.invoke to raise on a single invocation."""
        from animedex.diag import selftest as diag

        from click.testing import CliRunner

        original_invoke = CliRunner.invoke
        call_counter = {"n": 0}

        def angry_invoke(self, *args, **kwargs):
            call_counter["n"] += 1
            if call_counter["n"] == 1:
                raise RuntimeError("synthetic invoke failure")
            return original_invoke(self, *args, **kwargs)

        monkeypatch.setattr(CliRunner, "invoke", angry_invoke)
        results = diag._check_cli_subcommands()
        # The first invocation (--version) should be a failure; later
        # ones should still run normally.
        labels = [(label, ok) for label, ok, _ in results]
        assert labels[0] == ("animedex --version", False)

    def test_per_subcommand_exception_recorded(self, monkeypatch):
        """Make CliRunner.invoke raise only when probing a named
        subcommand, not the version/help path."""
        from animedex.diag import selftest as diag

        from click.testing import CliRunner

        original_invoke = CliRunner.invoke

        def maybe_angry(self, root, argv, **kwargs):
            # The first two invocations (--version, --help) come with
            # a single-element argv; subcommand probes have two
            # elements like ["status", "--help"].
            if len(argv) >= 2 and argv[1] == "--help" and argv[0] != "--help":
                raise RuntimeError("synthetic per-subcommand failure")
            return original_invoke(self, root, argv, **kwargs)

        monkeypatch.setattr(CliRunner, "invoke", maybe_angry)
        results = diag._check_cli_subcommands()
        per_subcommand = [(label, ok) for label, ok, _ in results if label.startswith("animedex ")]
        # At least one named subcommand entry should report False.
        assert any(
            ok is False for label, ok in per_subcommand if label not in ("animedex --version", "animedex --help")
        )


@pytest.mark.unittest
class TestMainModuleImport:
    def test_animedex_dunder_main_imports(self):
        """Cover the bare top-level import line in animedex/__main__.py."""
        import animedex.__main__  # noqa: F401


@pytest.mark.unittest
class TestEmitCheckBlockFailedPath:
    def test_failed_results_increment_failed_count(self):
        """Drive the ``else: failed += 1`` branch directly."""
        import io as _io

        from animedex.diag.selftest import _emit_check_block

        stream = _io.StringIO()
        passed, failed = _emit_check_block(
            stream,
            "Synthetic",
            [
                ("ok-row", True, ""),
                ("bad-row", False, "trace\nlines"),
            ],
        )
        assert passed == 1
        assert failed == 1
        assert "[FAIL] bad-row" in stream.getvalue()


@pytest.mark.unittest
class TestRunSelftestFailureBranch:
    def test_failed_module_smoke_returns_one(self, monkeypatch):
        """Force a registered module's selftest to return ``False``,
        then assert the runner prints the failure summary and returns 1."""
        import animedex.config.meta as target

        monkeypatch.setattr(target, "selftest", lambda: False, raising=False)

        buf = io.StringIO()
        rc = run_selftest(stream=buf)
        report = buf.getvalue()
        assert rc == 1
        assert "[FAIL] animedex selftest detected failures." in report


@pytest.mark.unittest
class TestSqliteSelftestCleanupBranch:
    def test_pre_existing_path_is_removed(self, tmp_path, monkeypatch):
        """Pre-create the path the cache selftest will use, so the
        ``if path.exists(): os.remove(path)`` cleanup branch fires."""
        from animedex.cache import sqlite

        monkeypatch.setattr("animedex.cache.sqlite._user_cache_dir", lambda: str(tmp_path))
        leftover = tmp_path / "selftest.sqlite"
        leftover.write_bytes(b"stale")
        assert leftover.exists()

        assert sqlite.selftest() is True
