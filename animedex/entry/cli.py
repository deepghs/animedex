"""
Top-level command-line interface for animedex.

This is a scaffolding stub. None of the per-backend commands (``anilist``,
``jikan``, ``trace``, etc.) or the ``api`` passthrough group are wired up
yet. Refer to ``plans/03-cli-architecture-gh-flavored.md`` for the planned
command tree.
"""

import click

from animedex.config.meta import __DESCRIPTION__, __TITLE__, __VERSION__


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


if __name__ == "__main__":  # pragma: no cover
    cli()
