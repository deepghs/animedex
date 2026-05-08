"""Post-build subprocess smoke-tester for the animedex binary.

This script is the *out-of-process* counterpart to
``animedex selftest``. It runs the freshly built executable as an
external process (so it sees exactly what an end user would see), checks
that ``--version``, ``--help``, ``status``, and ``selftest`` all behave
as expected, and prints a structured report.

The script is deliberately stdlib-only and PyInstaller-friendly. CI
uses it inside the build job, where Python is available; the
truly-clean second stage of the release pipeline runs the binary
directly with shell commands and does not depend on this script.

Exit codes:

* ``0`` - every probe passed.
* ``1`` - one or more probes failed (the full report still printed).
* ``2`` - the runner itself crashed before completing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import traceback
from typing import Callable, List, Tuple


CHECK_OK = "[OK]"
CHECK_FAIL = "[FAIL]"
SECTION_RULE = "=" * 60
SUBSECTION_RULE = "-" * 60


class CLIProbe:
    """Runs the animedex binary as a subprocess and accumulates results.

    :param cli_path: Filesystem path to the built ``animedex`` (or
                     ``animedex.exe``) executable.
    :type cli_path: str
    :param timeout: Per-invocation timeout in seconds, defaults to ``60``.
    :type timeout: int, optional

    :ivar cli_path: The executable path stored on the instance.
    :vartype cli_path: str
    :ivar timeout: The default subprocess timeout used by :meth:`_run`.
    :vartype timeout: int
    :ivar results: A list of ``(label, ok, detail)`` triples accumulated
                   by check methods.
    :vartype results: List[Tuple[str, bool, str]]
    """

    def __init__(self, cli_path: str, timeout: int = 60) -> None:
        self.cli_path = cli_path
        self.timeout = timeout
        self.results: List[Tuple[str, bool, str]] = []

    def _run(self, args: List[str], expect_exit: int = 0) -> Tuple[int, str, str]:
        """Run the CLI with ``args`` and return its (exit, stdout, stderr).

        :param args: Argv tail (the executable path is prepended).
        :type args: List[str]
        :param expect_exit: Sentinel used by callers; this method does
                            not enforce it and only returns the actual
                            exit code, defaults to ``0``.
        :type expect_exit: int, optional
        :return: Tuple of ``(exit_code, stdout, stderr)``.
        :rtype: Tuple[int, str, str]
        :raises subprocess.TimeoutExpired: If the subprocess exceeds
                                            :attr:`timeout`.
        """
        cmd = [self.cli_path, *args]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    def check_version(self) -> None:
        """Validate ``animedex --version`` output.

        The version banner is two lines: the package title and version,
        followed by a build-info summary (a commit short hash with
        ``built ...`` timestamp when the binary was built with
        ``make build_info``, or the literal sentinel ``build info not
        generated`` otherwise). Both forms are valid; this probe
        merely asserts that the second line is one of them so that we
        can spot a regression in the version-banner shape.
        """
        try:
            code, out, err = self._run(["--version"])
            if code != 0:
                self.results.append(("animedex --version", False, _fmt_proc(code, out, err)))
                return
            if "animedex" not in out.lower():
                self.results.append(("animedex --version", False, f"output missing project name:\n{out}"))
                return
            lines = [line for line in out.splitlines() if line.strip()]
            if len(lines) < 2:
                self.results.append(
                    ("animedex --version", False, f"expected 2 lines, got {len(lines)}:\n{out}")
                )
                return
            second = lines[1]
            if "build info not generated" in second:
                detail = f"{out.strip()}  [build_info: absent]"
            elif "built " in second:
                detail = f"{out.strip()}  [build_info: present]"
            else:
                self.results.append(
                    (
                        "animedex --version",
                        False,
                        f"second line did not match either build-info form:\n{out}",
                    )
                )
                return
            self.results.append(("animedex --version", True, detail))
        except Exception:
            self.results.append(("animedex --version", False, traceback.format_exc().rstrip()))

    def check_help(self) -> None:
        """Validate ``animedex --help`` lists at least one subcommand."""
        try:
            code, out, err = self._run(["--help"])
            if code != 0:
                self.results.append(("animedex --help", False, _fmt_proc(code, out, err)))
                return
            if "Usage" not in out and "usage" not in out:
                self.results.append(("animedex --help", False, f"missing usage banner:\n{out}"))
                return
            if "selftest" not in out:
                self.results.append(
                    ("animedex --help", False, f"selftest subcommand not advertised:\n{out}")
                )
                return
            self.results.append(("animedex --help", True, "lists selftest"))
        except Exception:
            self.results.append(("animedex --help", False, traceback.format_exc().rstrip()))

    def check_status(self) -> None:
        """Validate ``animedex status`` exits cleanly."""
        try:
            code, out, err = self._run(["status"])
            if code != 0:
                self.results.append(("animedex status", False, _fmt_proc(code, out, err)))
                return
            self.results.append(("animedex status", True, out.strip().splitlines()[0] if out.strip() else ""))
        except Exception:
            self.results.append(("animedex status", False, traceback.format_exc().rstrip()))

    def check_selftest(self) -> None:
        """Validate ``animedex selftest`` runs and exits zero.

        Asserts that the report contains both the Summary line and a
        Build info section (whether or not ``make build_info`` has run,
        the section is unconditionally present).
        """
        try:
            code, out, err = self._run(["selftest"])
            if code != 0:
                self.results.append(("animedex selftest", False, _fmt_proc(code, out, err)))
                return
            missing = [section for section in ("Build info", "Summary") if section not in out]
            if missing:
                self.results.append(
                    (
                        "animedex selftest",
                        False,
                        f"sections missing: {missing}\n{out}",
                    )
                )
                return
            if "(not generated)" in out:
                detail = "summary + build_info(absent), exit 0"
            elif "Built at:" in out:
                detail = "summary + build_info(present), exit 0"
            else:
                self.results.append(
                    (
                        "animedex selftest",
                        False,
                        f"build_info section in unexpected shape:\n{out}",
                    )
                )
                return
            self.results.append(("animedex selftest", True, detail))
        except Exception:
            self.results.append(("animedex selftest", False, traceback.format_exc().rstrip()))

    def run_all(self) -> int:
        """Execute every probe and print the full report.

        :return: ``0`` on universal success, ``1`` if any probe failed.
        :rtype: int
        """
        print(f"animedex CLI smoke-test")
        print(SECTION_RULE)
        print(f"  binary:   {self.cli_path}")
        print(f"  size:     {_fmt_size(self.cli_path)}")
        print(f"  exists:   {os.path.exists(self.cli_path)}")
        print(f"  exec:     {os.access(self.cli_path, os.X_OK)}")
        print("")

        probes: List[Tuple[str, Callable[[], None]]] = [
            ("version", self.check_version),
            ("help", self.check_help),
            ("status", self.check_status),
            # ``check_selftest`` covers the bundled jq wheel end-to-end
            # via ``animedex.render.jq.selftest()``, which calls
            # ``apply_jq('{"x":42}', '.x')`` through libjq. A separate
            # ``--jq`` probe would have to either redo that or be
            # lighter (just check ``--help`` lists ``--jq``) — and the
            # lighter version doesn't actually verify the wheel
            # bundled, since the option registration is unconditional.
            ("selftest", self.check_selftest),
        ]

        for label, fn in probes:
            try:
                fn()
            except Exception:
                self.results.append((f"probe:{label} runner", False, traceback.format_exc().rstrip()))

        print("Probes")
        print(SUBSECTION_RULE)
        passed = 0
        failed = 0
        for label, ok, detail in self.results:
            marker = CHECK_OK if ok else CHECK_FAIL
            print(f"  {marker} {label}")
            if not ok:
                for line in detail.splitlines():
                    print(f"      {line}")
            else:
                if detail:
                    print(f"      {detail}")
            if ok:
                passed += 1
            else:
                failed += 1
        print("")

        print("Summary")
        print(SUBSECTION_RULE)
        total = passed + failed
        print(f"  {passed} passed, {failed} failed (total {total}).")
        if failed == 0:
            print(f"  {CHECK_OK} {self.cli_path} is functional.")
            return 0
        else:
            print(f"  {CHECK_FAIL} {self.cli_path} has problems; see failures above.")
            return 1


def _fmt_proc(code: int, stdout: str, stderr: str) -> str:
    """Render a failed subprocess into a readable diagnostic block.

    :param code: Subprocess exit code.
    :type code: int
    :param stdout: Captured stdout bytes (decoded).
    :type stdout: str
    :param stderr: Captured stderr bytes (decoded).
    :type stderr: str
    :return: A multi-line diagnostic string.
    :rtype: str
    """
    return (
        f"exit_code={code}\n"
        f"stdout:\n{stdout.rstrip() or '<empty>'}\n"
        f"stderr:\n{stderr.rstrip() or '<empty>'}"
    )


def _fmt_size(path: str) -> str:
    """Format the size of ``path`` for the smoke-test header line.

    :param path: Filesystem path to inspect.
    :type path: str
    :return: A human-friendly size, or ``"?"`` if the file is missing.
    :rtype: str
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return "?"
    units = [("GiB", 1024 ** 3), ("MiB", 1024 ** 2), ("KiB", 1024)]
    for label, scale in units:
        if size >= scale:
            return f"{size / scale:.1f} {label} ({size} bytes)"
    return f"{size} bytes"


def main() -> int:
    """Argparse-driven entry for ``python -m tools.test_cli``.

    :return: Process exit code from :meth:`CLIProbe.run_all`.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Smoke-test the built animedex binary.")
    parser.add_argument("cli_path", help="Path to the built animedex (or animedex.exe) executable.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-probe timeout in seconds.")
    args = parser.parse_args()

    if not os.path.exists(args.cli_path):
        print(f"[FAIL] CLI executable not found: {args.cli_path}", file=sys.stderr)
        return 2

    try:
        return CLIProbe(args.cli_path, timeout=args.timeout).run_all()
    except Exception:
        try:
            print("\ntools/test_cli runner crashed:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception:
            pass
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
