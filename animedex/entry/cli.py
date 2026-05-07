"""
Top-level command-line interface for animedex.

This is a scaffolding stub. None of the per-backend commands (``anilist``,
``jikan``, ``trace``, etc.) or the ``api`` passthrough group are wired up
yet. Refer to ``plans/03-cli-architecture-gh-flavored.md`` for the planned
command tree.
"""

import sys

import click

from animedex.config.meta import __DESCRIPTION__, __TITLE__, __VERSION__
from animedex.diag.selftest import run_selftest


@click.group(name=__TITLE__, help=__DESCRIPTION__)
@click.version_option(__VERSION__, prog_name=__TITLE__)
def cli() -> None:
    """The animedex top-level command group."""


@cli.command(name="status")
def status_command() -> None:
    """Print a placeholder status banner.

    The real implementation will report the health, anonymous quota, and
    auth state of each backend (AniList, Jikan, Kitsu, MangaDex, Trace.moe,
    Danbooru, Shikimori, ANN, AniDB, Ghibli, NekosBest, Waifu.im, AnimeChan).
    """
    click.echo(f"{__TITLE__} v{__VERSION__} - work in progress.")
    click.echo("No backends are wired up yet. See plans/ in the repository.")


@cli.command(name="selftest")
def selftest_command() -> None:
    """Run the in-process self-diagnostic and exit with its status code.

    Invokes :func:`animedex.diag.run_selftest`. The diagnostic is
    designed to run in a stripped, no-Python environment (such as a
    PyInstaller bundle smoke-tested by CI) and to return a
    machine-grepable ``[OK]`` / ``[FAIL]`` block under all conditions,
    including when individual checks crash.

    Exit codes:

    * ``0`` - every check passed.
    * ``1`` - one or more checks failed (the report still printed).
    * ``2`` - the runner itself crashed (should be unreachable).
    """
    code = run_selftest()
    sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    cli()
