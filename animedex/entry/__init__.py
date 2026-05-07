"""
Entry points for the :mod:`animedex.entry` package.

Re-exports the top-level CLI group so it can be referenced from
``setup.py``'s ``console_scripts`` entry point and from the
``__main__`` module.
"""

from .cli import cli as animedex_cli

__all__ = ["animedex_cli"]
