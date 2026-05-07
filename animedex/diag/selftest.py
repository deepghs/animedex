"""
In-process self-diagnostic for the animedex CLI.

The :func:`run_selftest` routine prints a structured environment and
package report, exercises every public module's importability, and
invokes each registered Click subcommand's ``--help`` page. It is
designed to terminate cleanly under all conditions, even when a check
itself throws an unexpected exception, so that:

* a stripped binary built with PyInstaller can be smoke-tested in a
  clean environment without a Python interpreter installed (see
  ``plans/04-roadmap-and-mvp.md`` and ``.github/workflows/release_test.yml``);
* an LLM agent invoking ``animedex selftest`` always gets a parseable
  status block back, regardless of why something failed.

Output format
=============

The selftest prints a banner, four sections, and a summary line. Each
check produces a one-line ``[OK]`` / ``[FAIL]`` record so the report
can be grepped from CI logs without parsing tracebacks; failure detail
follows the failing record on subsequent indented lines.

Exit codes
==========

* ``0`` - every check passed.
* ``1`` - one or more checks failed; the report still printed cleanly.
* ``2`` - the runner itself crashed before completing (should be
  unreachable in practice; defensive).
"""

from __future__ import annotations

import importlib
import io
import platform
import sys
import traceback
from typing import Callable, List, Tuple


CHECK_OK = "[OK]"
CHECK_FAIL = "[FAIL]"
SECTION_RULE = "=" * 60
SUBSECTION_RULE = "-" * 60


# Modules whose import we expect to succeed in any environment that
# successfully launched ``animedex selftest`` at all. New top-level
# modules / packages should be added here as they appear.
_REQUIRED_MODULES: Tuple[str, ...] = (
    "animedex",
    "animedex.config",
    "animedex.config.meta",
    "animedex.entry",
    "animedex.entry.cli",
    "animedex.diag",
    "animedex.diag.selftest",
)


def _is_frozen() -> bool:
    """Return ``True`` if running inside a PyInstaller (or similar) bundle.

    :return: Whether the interpreter is running from a frozen executable.
    :rtype: bool
    """
    return bool(getattr(sys, "frozen", False))


def _bundle_dir() -> str:
    """Return the runtime bundle directory when frozen, or empty string.

    :return: The PyInstaller temporary extract directory, or ``""``.
    :rtype: str
    """
    return getattr(sys, "_MEIPASS", "") or ""


def _format_environment_lines() -> List[str]:
    """Compose the environment section as a list of pre-formatted lines.

    :return: Lines describing Python, OS, freeze state, and arguments.
    :rtype: List[str]
    """
    lines = [
        f"  Python:        {platform.python_version()} ({platform.python_implementation()})",
        f"  Executable:    {sys.executable}",
        f"  Platform:      {platform.platform()}",
        f"  Architecture:  {platform.machine() or 'unknown'}",
        f"  Frozen:        {_is_frozen()}",
    ]
    if _is_frozen():
        lines.append(f"  Bundle dir:    {_bundle_dir()}")
    lines.append(f"  argv:          {sys.argv!r}")
    return lines


def _format_package_lines() -> List[str]:
    """Compose the package metadata section, tolerating import errors.

    :return: Lines describing the loaded ``animedex`` distribution, or a
             single ``[FAIL]`` line if metadata cannot be loaded.
    :rtype: List[str]
    """
    try:
        from animedex import (
            __AUTHOR__,
            __AUTHOR_EMAIL__,
            __DESCRIPTION__,
            __TITLE__,
            __VERSION__,
        )

        try:
            import animedex as _pkg

            origin = getattr(_pkg, "__file__", "?") or "?"
        except Exception:
            origin = "?"
        return [
            f"  Title:         {__TITLE__}",
            f"  Version:       {__VERSION__}",
            f"  Author:        {__AUTHOR__} <{__AUTHOR_EMAIL__}>",
            f"  Description:   {__DESCRIPTION__}",
            f"  Loaded from:   {origin}",
        ]
    except Exception as exc:
        tb = traceback.format_exc().rstrip()
        return [f"  {CHECK_FAIL} cannot read animedex metadata: {exc}", *(f"    {line}" for line in tb.splitlines())]


def _check_module_imports() -> List[Tuple[str, bool, str]]:
    """Attempt to import every module in :data:`_REQUIRED_MODULES`.

    :return: A list of ``(module_name, ok, detail)`` triples where
             ``detail`` is the failure traceback when ``ok`` is ``False``.
    :rtype: List[Tuple[str, bool, str]]
    """
    results: List[Tuple[str, bool, str]] = []
    for name in _REQUIRED_MODULES:
        try:
            importlib.import_module(name)
            results.append((name, True, ""))
        except Exception:
            results.append((name, False, traceback.format_exc().rstrip()))
    return results


def _check_cli_subcommands() -> List[Tuple[str, bool, str]]:
    """Probe the registered Click subcommands with the in-process runner.

    Each subcommand is invoked with ``--help``; any non-zero exit code
    or runner exception is reported as a failure.

    :return: A list of ``(command_label, ok, detail)`` triples.
    :rtype: List[Tuple[str, bool, str]]
    """
    results: List[Tuple[str, bool, str]] = []
    try:
        from click.testing import CliRunner

        from animedex.entry import animedex_cli
    except Exception:
        return [("cli runner import", False, traceback.format_exc().rstrip())]

    runner = CliRunner()

    invocations: Tuple[Tuple[str, List[str]], ...] = (
        ("animedex --version", ["--version"]),
        ("animedex --help", ["--help"]),
    )
    for label, argv in invocations:
        try:
            result = runner.invoke(animedex_cli, argv)
            ok = result.exit_code == 0
            detail = "" if ok else f"exit_code={result.exit_code}\noutput:\n{result.output}"
            results.append((label, ok, detail))
        except Exception:
            results.append((label, False, traceback.format_exc().rstrip()))

    # Discover registered subcommands after the version/help probes so
    # that even if discovery fails we still have those datapoints.
    try:
        commands = sorted(animedex_cli.commands.keys())
    except Exception:
        results.append(("cli subcommand discovery", False, traceback.format_exc().rstrip()))
        return results

    for name in commands:
        if name == "selftest":
            # Calling selftest from inside selftest would recurse forever.
            results.append((f"animedex {name} --help", True, "(skipped: would recurse)"))
            continue
        try:
            result = runner.invoke(animedex_cli, [name, "--help"])
            ok = result.exit_code == 0
            detail = "" if ok else f"exit_code={result.exit_code}\noutput:\n{result.output}"
            results.append((f"animedex {name} --help", ok, detail))
        except Exception:
            results.append((f"animedex {name} --help", False, traceback.format_exc().rstrip()))

    return results


def _emit_section(stream: io.TextIOBase, title: str, lines: List[str]) -> None:
    """Write a titled section to ``stream``.

    :param stream: Destination text stream.
    :type stream: io.TextIOBase
    :param title: Section title.
    :type title: str
    :param lines: Body lines, already indented by the caller.
    :type lines: List[str]
    """
    print(title, file=stream)
    print(SUBSECTION_RULE, file=stream)
    for line in lines:
        print(line, file=stream)
    print("", file=stream)


def _emit_check_block(
    stream: io.TextIOBase,
    title: str,
    results: List[Tuple[str, bool, str]],
) -> Tuple[int, int]:
    """Write a check-block section and return (passed, failed) counts.

    :param stream: Destination text stream.
    :type stream: io.TextIOBase
    :param title: Section title.
    :type title: str
    :param results: A list of ``(label, ok, detail)`` triples produced
                    by an underlying check function.
    :type results: List[Tuple[str, bool, str]]
    :return: ``(passed, failed)`` tally for the section.
    :rtype: Tuple[int, int]
    """
    print(title, file=stream)
    print(SUBSECTION_RULE, file=stream)
    passed = 0
    failed = 0
    for label, ok, detail in results:
        marker = CHECK_OK if ok else CHECK_FAIL
        print(f"  {marker} {label}", file=stream)
        if detail:
            for detail_line in detail.splitlines():
                print(f"      {detail_line}", file=stream)
        if ok:
            passed += 1
        else:
            failed += 1
    print("", file=stream)
    return passed, failed


def _safely(fn: Callable[[], List[Tuple[str, bool, str]]], label: str) -> List[Tuple[str, bool, str]]:
    """Run ``fn`` and convert any escaping exception into a single FAIL row.

    :param fn: The check producer to invoke.
    :type fn: Callable[[], List[Tuple[str, bool, str]]]
    :param label: A label to attach to the synthesised failure row.
    :type label: str
    :return: Either ``fn``'s return value or a single ``(label, False,
             traceback)`` triple if ``fn`` itself raised.
    :rtype: List[Tuple[str, bool, str]]
    """
    try:
        return fn()
    except Exception:
        return [(label, False, traceback.format_exc().rstrip())]


def run_selftest(stream: io.TextIOBase = None) -> int:
    """Execute the full self-diagnostic and return an exit code.

    :param stream: Optional destination text stream; defaults to
                   :data:`sys.stdout`. The stream is *not* closed by
                   this function.
    :type stream: io.TextIOBase, optional
    :return: ``0`` if every check passed, ``1`` if any failed, ``2`` if
             the runner itself crashed before completing.
    :rtype: int
    """
    if stream is None:
        stream = sys.stdout

    try:
        print("animedex selftest", file=stream)
        print(SECTION_RULE, file=stream)
        print("", file=stream)

        _emit_section(stream, "Environment", _format_environment_lines())
        _emit_section(stream, "Package", _format_package_lines())

        passed_total = 0
        failed_total = 0

        for title, fn, label in (
            ("Module imports", _check_module_imports, "module-import runner"),
            ("CLI subcommands", _check_cli_subcommands, "cli-subcommand runner"),
        ):
            results = _safely(fn, label)
            passed, failed = _emit_check_block(stream, title, results)
            passed_total += passed
            failed_total += failed

        # Backend probes will be added as backends ship; this is a
        # forward-looking placeholder so the report shape stays stable.
        _emit_section(
            stream,
            "Backend health",
            ["  (skipped) - no backends are implemented yet."],
        )

        total = passed_total + failed_total
        print("Summary", file=stream)
        print(SUBSECTION_RULE, file=stream)
        print(f"  {passed_total} passed, {failed_total} failed (total {total}).", file=stream)
        if failed_total == 0:
            print(f"  {CHECK_OK} animedex is functional.", file=stream)
            return 0
        else:
            print(f"  {CHECK_FAIL} animedex selftest detected failures.", file=stream)
            return 1
    except Exception:
        # The runner is supposed to be unkillable. If anything escapes
        # the per-check guards above, log it and exit 2 so callers know
        # the report itself is suspect.
        try:
            print("\nanimedex selftest runner crashed:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception:
            # Truly defensive: never re-raise out of the diagnostic.
            pass
        return 2


def main() -> int:  # pragma: no cover - thin shim
    """Console-script style entry point for ``python -m animedex.diag.selftest``.

    :return: Process exit code (see :func:`run_selftest`).
    :rtype: int
    """
    return run_selftest()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
