"""
Resource collector used by ``tools/generate_spec.py``.

Yields ``(src_abspath, dst_dir)`` tuples to feed PyInstaller's
``Analysis.datas`` argument. Only **non-Python** assets are returned;
Python source modules are handled by PyInstaller's normal auto-discovery
plus the ``hiddenimports`` list in the generated spec.

The animedex package currently has no non-.py resources inside it, so
this collector yields nothing in the default build. The generator is in
place so that future bundled assets - JSON snapshots, schema files, etc.
that the roadmap (``plans/04-roadmap-and-mvp.md``) plans to ship under
``animedex/data/`` - are picked up automatically without further build
plumbing.

Run as a script for diagnostic purposes::

    python tools/resources.py

This prints one ``--add-data SRC<sep>DST`` line per resource, in the
form PyInstaller's CLI would consume.
"""

from __future__ import annotations

import os
import sys
from typing import Iterator, Tuple


def list_package_resources(package_root: str) -> Iterator[str]:
    """Walk ``package_root`` and yield absolute paths of non-.py files.

    ``__pycache__`` directories are skipped. Hidden files (whose name
    begins with ``.``) are also skipped to keep editor turds and
    OS-level metadata out of the bundle.

    :param package_root: Filesystem path to the package's source root
                         (the directory that contains ``__init__.py``).
    :type package_root: str
    :return: Iterator of absolute paths to candidate resource files.
    :rtype: Iterator[str]
    """
    for root, dirs, files in os.walk(package_root):
        if "__pycache__" in root:
            continue
        # Skip hidden directories in-place so we do not descend into them.
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.startswith("."):
                continue
            _, ext = os.path.splitext(file)
            if ext == ".py":
                continue
            yield os.path.abspath(os.path.join(root, file))


def get_resource_files() -> Iterator[Tuple[str, str]]:
    """Yield ``(src_abspath, dst_dir)`` tuples for the animedex package.

    The destination directory is computed relative to the project root
    so PyInstaller lays the bundled tree out the same way the source
    repository does.

    :return: Iterator of ``(src_file, dst_dir)`` tuples for ``Analysis.datas``.
    :rtype: Iterator[Tuple[str, str]]
    """
    import animedex

    package_root = os.path.dirname(os.path.abspath(animedex.__file__))
    project_root = os.path.dirname(package_root)
    for rfile in list_package_resources(package_root):
        dst_dir = os.path.dirname(os.path.relpath(rfile, project_root))
        yield rfile, dst_dir


def print_resource_mappings() -> None:
    """Print the resource list as PyInstaller ``--add-data`` lines.

    Intended for ad-hoc debugging only; the canonical consumer is
    :func:`tools.generate_spec.collect_datas`.
    """
    sep = os.pathsep
    for rfile, dst_dir in get_resource_files():
        print(f"--add-data {rfile}{sep}{dst_dir}")


if __name__ == "__main__":  # pragma: no cover
    print_resource_mappings()
    sys.exit(0)
