"""
Generate ``animedex/config/build_info.py`` from the working tree's git state.

The output module is **never** committed: it is the in-band record of how
a particular binary or development install was assembled. Re-run this
script (via ``make build_info``) whenever you want the in-process
``--version`` banner and ``animedex selftest`` report to reflect the
current commit.

Captured fields (see :mod:`animedex.config.buildmeta` for the loader):

* ``__COMMIT__`` - full 40-character HEAD SHA, or ``"unknown"``.
* ``__COMMIT_SHORT__`` - 7-character HEAD SHA, or ``"unknown"``.
* ``__TAG__`` - the tag at HEAD if and only if HEAD is *exactly* on a
  tag; otherwise ``None``. (Use ``__GIT_DESCRIBE__`` if you want the
  nearest-ancestor tag plus distance.)
* ``__GIT_DESCRIBE__`` - ``git describe --tags --always --dirty`` raw
  output, or ``"unknown"``.
* ``__DIRTY__`` - boolean; ``True`` if the working tree has any tracked
  modifications or staged changes.
* ``__BUILD_TIME__`` - UTC ISO-8601 timestamp of when this script ran
  (with seconds precision and a trailing ``Z``).
* ``__BUILD_HOST__`` - ``socket.gethostname()`` at generation time.

Usage::

    python tools/generate_build_info.py
    python tools/generate_build_info.py --output some/other/path.py

If git is unavailable (e.g. building from an extracted source tarball),
the script writes the file with all git fields set to ``"unknown"``
and ``__DIRTY__`` set to ``False``. The build still succeeds.
"""

from __future__ import annotations

import argparse
import datetime
import os
import socket
import subprocess
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path("animedex") / "config" / "build_info.py"


def _git(args, cwd: Path) -> str:
    """Run ``git args ...`` and return stripped stdout, or empty string on error.

    :param args: Argv tail to append after ``git``.
    :type args: list[str]
    :param cwd: Working directory for the git invocation.
    :type cwd: pathlib.Path
    :return: Stripped stdout, or ``""`` if the call failed for any reason.
    :rtype: str
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def collect(cwd: Path) -> dict:
    """Collect every build_info field by querying git.

    Missing or failing fields fall back to safe defaults so the output
    file is always a valid Python module.

    :param cwd: Working directory used for git invocations.
    :type cwd: pathlib.Path
    :return: Dictionary of field name to value.
    :rtype: dict
    """
    commit = _git(["rev-parse", "HEAD"], cwd) or "unknown"
    commit_short = _git(["rev-parse", "--short=7", "HEAD"], cwd) or "unknown"
    describe = _git(["describe", "--tags", "--always", "--dirty"], cwd) or "unknown"
    tag = _git(["describe", "--tags", "--exact-match"], cwd) or None
    porcelain = _git(["status", "--porcelain"], cwd)
    dirty = bool(porcelain) or describe.endswith("-dirty")
    build_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    build_host = socket.gethostname() or "unknown"
    return {
        "commit": commit,
        "commit_short": commit_short,
        "describe": describe,
        "tag": tag,
        "dirty": dirty,
        "build_time": build_time,
        "build_host": build_host,
    }


_TEMPLATE = '''"""Auto-generated build metadata. DO NOT EDIT.

Regenerate with ``make build_info`` (or ``python tools/generate_build_info.py``).
This file is not tracked in git; the package works whether or not it is
present (see :mod:`animedex.config.buildmeta`).
"""

__COMMIT__: str = {commit!r}
__COMMIT_SHORT__: str = {commit_short!r}
__GIT_DESCRIBE__: str = {describe!r}
__TAG__ = {tag!r}
__DIRTY__: bool = {dirty!r}
__BUILD_TIME__: str = {build_time!r}
__BUILD_HOST__: str = {build_host!r}
'''


def render(fields: dict) -> str:
    """Render the build_info module body from a fields dict.

    :param fields: Mapping returned by :func:`collect`.
    :type fields: dict
    :return: Module source code suitable for writing to disk.
    :rtype: str
    """
    return _TEMPLATE.format(**fields)


def main() -> int:
    """Argparse entry point.

    :return: Process exit code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "-C",
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Repository root for git invocations (default: current directory).",
    )
    args = parser.parse_args()

    fields = collect(args.cwd)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(fields), encoding="utf-8")

    print(f"Wrote {args.output}:")
    for key in ("commit_short", "describe", "tag", "dirty", "build_time", "build_host"):
        print(f"  {key:14}= {fields[key]!r}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


# Suppress unused-import lint when this module is checked in isolation.
_ = os
