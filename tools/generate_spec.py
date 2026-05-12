"""
Generate the PyInstaller spec file used to package animedex.

Mirrors the pattern from ``pyfcstm/tools/generate_spec.py`` on the
``dev/damnx`` branch: produce a deterministic ``.spec`` file under
version-controlled rules, rather than passing increasingly elaborate
flags to ``pyinstaller`` on the command line. The spec captures:

* The Python entry point (``animedex_cli.py``).
* The data files collected by :mod:`tools.resources`.
* The hidden imports and package data that PyInstaller's static scanner
  cannot reach, most notably ``animedex.config.build_info`` (loaded via
  try/except so that animedex still works when the file has not been
  generated).
* An aggressive *exclude* list that drops the data-science, GUI, and
  test/packaging stacks Python pulls in by default but which animedex
  does not need at runtime; this keeps the binary small and the
  startup cost low.

There is **no logo / icon** asset in this build: the project ships
text only.

Usage::

    python tools/generate_spec.py -o animedex.spec
    pyinstaller animedex.spec --noconfirm --clean
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

#: Modules that the binary should never bundle. Each entry is a top-level
#: import path; PyInstaller's exclude semantics treat them as prefixes
#: only when stated as such, so a literal name like ``"numpy"`` will
#: still exclude ``numpy.linalg`` and friends.
EXCLUDED_MODULES = [
    # GUI toolkits
    "tkinter",
    # Data-science and notebook stacks animedex does not depend on.
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "IPython",
    "jupyter",
    "notebook",
    # Test, doc, and packaging tooling that should never ship.
    "pytest",
    "unittest",
    "doctest",
    "pydoc",
    "_pytest",
    "py",
    "PyInstaller",
    "_pyinstaller_hooks_contrib",
    "altgraph",
    "macholib",
    "pefile",
    "win32ctypes",
    "distutils",
    "setuptools",
    "pip",
    # Misc stdlib helpers and HTTP servers that animedex never starts.
    "xmlrpc",
    "http.server",
]

#: Modules PyInstaller's static analyser does not reach unaided.
#:
#: Most animedex submodules are picked up dynamically by
#: ``importlib.import_module`` inside :mod:`animedex.diag.selftest`
#: (the ``_SELFTEST_TARGETS`` list); PyInstaller's static scanner
#: cannot follow that, so the spec template also calls
#: ``collect_submodules("animedex")`` at build time and unions the
#: result with this list.
#:
#: ``animedex.config.build_info`` stays explicit because it is
#: ``.gitignore`` d and absent in a clean checkout: PyInstaller would
#: skip it without complaint, but ``buildmeta`` expects it whenever
#: it has been generated.
HIDDEN_IMPORTS = [
    "animedex.config.build_info",
    # Pydantic's compiled core is imported at runtime by pydantic
    # itself; PyInstaller does not always notice the C-extension
    # path, especially on stripped builds.
    "pydantic_core",
    "pydantic_core._pydantic_core",
    # The :pypi:`jq` wheel is a Cython binding to libjq; PyInstaller
    # has no auto-hook for it, so the C extension and its module
    # init must be listed explicitly. ``animedex.render.jq`` does a
    # local ``import jq`` only at first call site, which the static
    # analyser misses.
    "jq",
    # ``anyascii`` keeps transliteration tables under a resource-only
    # package that is loaded through importlib.resources at runtime.
    "anyascii._data",
    # ``unidecode`` lazy-loads per-codepoint transliteration blocks via
    # dynamic imports. Keep the package explicit so frozen builds do not
    # depend on PyInstaller's current collection heuristics.
    "unidecode",
    "unidecode.util",
]

PACKAGE_DATAS = [
    # Required by ``anyascii.anyascii`` after freezing; without these
    # resource files the binary imports successfully but selftest fails
    # when a non-ASCII title is transliterated.
    "anyascii",
    # Required by ``unidecode.unidecode`` after freezing; the package's
    # transliteration tables are loaded lazily by code-point block.
    "unidecode",
    # Required by ``zoneinfo.ZoneInfo`` on platforms that do not ship an
    # IANA timezone database, most notably Windows.
    "tzdata",
]


def collect_datas() -> list:
    """Resolve the data-file list for ``Analysis.datas``.

    Calls :func:`tools.resources.get_resource_files` and converts to the
    plain Python list PyInstaller expects. Errors are logged and
    swallowed so a missing ``tools.resources`` does not break the
    binary build.

    :return: List of ``(src_path, dst_dir)`` tuples.
    :rtype: list
    """
    datas = []
    try:
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from tools.resources import get_resource_files

        for src_file, dst_dir in get_resource_files():
            datas.append((src_file, dst_dir))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Warning: tools.resources failed: {exc}", file=sys.stderr)
    return datas


_SPEC_TEMPLATE = """# -*- mode: python ; coding: utf-8 -*-
# Auto-generated by tools/generate_spec.py. DO NOT EDIT BY HAND;
# any change here will be overwritten on the next `make build`.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Walk the animedex package and pick up every importable submodule.
# This is necessary because animedex/diag/selftest.py uses
# importlib.import_module() to smoke-test the substrate, and the
# static analyser cannot follow dynamic imports.
_animedex_hidden = collect_submodules('animedex')
_package_datas = []
for _package in {package_datas!r}:
    _package_datas += collect_data_files(_package)

a = Analysis(
    ['animedex_cli.py'],
    pathex=[],
    binaries=[],
    datas={datas!r} + _package_datas,
    hiddenimports={hidden!r} + _animedex_hidden,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes!r},
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='animedex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""


def generate_spec() -> tuple:
    """Render the spec text and return ``(content, data_count)``.

    :return: A tuple of the spec body and the number of data files that
             :func:`collect_datas` produced; the latter is printed for
             situational awareness when running the script.
    :rtype: tuple
    """
    datas = collect_datas()
    content = _SPEC_TEMPLATE.format(
        datas=datas,
        hidden=HIDDEN_IMPORTS,
        package_datas=PACKAGE_DATAS,
        excludes=EXCLUDED_MODULES,
    )
    return content, len(datas)


def main() -> int:
    """Argparse entry point for ``python -m tools.generate_spec``.

    :return: Process exit code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Generate the animedex PyInstaller spec.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("animedex.spec"),
        help="Output spec path (default: animedex.spec).",
    )
    args = parser.parse_args()

    content, data_count = generate_spec()
    args.output.write_text(content, encoding="utf-8")
    print(
        f"Generated {args.output} "
        f"(datas={data_count}, hidden={len(HIDDEN_IMPORTS)}, "
        f"excludes={len(EXCLUDED_MODULES)})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
