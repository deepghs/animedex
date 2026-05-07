"""
Top-level command-line interface for animedex.

This is a scaffolding stub. None of the per-backend commands (``anilist``,
``jikan``, ``trace``, etc.) or the ``api`` passthrough group are wired up
yet. Refer to ``plans/03-cli-architecture-gh-flavored.md`` for the planned
command tree.
"""

import sys

import click

from animedex.config.buildmeta import format_short as _format_build_short
from animedex.config.meta import __DESCRIPTION__, __TITLE__, __VERSION__
from animedex.diag.selftest import run_selftest


def _format_version_banner() -> str:
    """Compose the multi-line banner shown by ``animedex --version``.

    Includes the package title and version on the first line, then a
    second line that summarises the in-binary build metadata when
    available (commit short hash, tag, clean/dirty, build timestamp).
    On a fresh checkout where ``make build_info`` has not been run, the
    second line announces that the metadata is not generated rather
    than pretending to know.

    :return: Multi-line banner string with no trailing newline.
    :rtype: str
    """
    return f"{__TITLE__} {__VERSION__}\n{_format_build_short()}"


def _print_version(ctx: click.Context, param: click.Option, value: bool) -> None:
    """Click eager callback that prints :func:`_format_version_banner` and exits.

    :param ctx: Click command context for the active invocation.
    :type ctx: click.Context
    :param param: The ``--version`` option metadata; unused.
    :type param: click.Option
    :param value: ``True`` when the user passed ``--version``.
    :type value: bool
    :return: ``None`` (exits via :meth:`click.Context.exit` when triggered).
    :rtype: None
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(_format_version_banner())
    ctx.exit()


def _print_agent_guide(ctx: click.Context, param: click.Option, value: bool) -> None:
    """Click eager callback for ``--agent-guide``.

    Walks the registered command tree and prints every command's
    :func:`animedex.policy.lint.extract_agent_guidance` block, so an
    LLM agent shelling out without an MCP layer can read the
    catalogue with a single invocation. Exits cleanly when no
    commands have guidance (e.g. during Phase 0 before any backend
    has shipped).

    :param ctx: Click command context for the active invocation.
    :type ctx: click.Context
    :param param: The ``--agent-guide`` option metadata; unused.
    :type param: click.Option
    :param value: ``True`` when the user passed ``--agent-guide``.
    :type value: bool
    :return: ``None`` (exits via :meth:`click.Context.exit` when triggered).
    :rtype: None
    """
    if not value or ctx.resilient_parsing:
        return  # pragma: no cover
    from animedex.policy.lint import collect_agent_guidance

    blocks = collect_agent_guidance(cli)
    if not blocks:
        click.echo("No Agent Guidance blocks found (no backends are wired up yet).")
    else:
        for entry in blocks:
            click.echo(f"=== {entry['command']} ===")
            click.echo(entry["guidance"])
            click.echo("")
    ctx.exit()


@click.group(name=__TITLE__, help=__DESCRIPTION__)
@click.option(
    "--version",
    is_flag=True,
    callback=_print_version,
    expose_value=False,
    is_eager=True,
    help="Show animedex's version and build information.",
)
@click.option(
    "--agent-guide",
    is_flag=True,
    callback=_print_agent_guide,
    expose_value=False,
    is_eager=True,
    help="Print every command's --- LLM Agent Guidance --- block and exit.",
)
def cli() -> None:
    """The animedex top-level command group."""


from animedex.entry.api import api_group as _api_group  # noqa: E402

cli.add_command(_api_group)


@cli.command(name="status")
def status_command() -> None:
    """Print a one-shot status banner for the CLI.

    During Phase 0/1 this is a placeholder. Once backends ship it
    will report per-backend health, anonymous quota, and auth state
    for AniList, Jikan, Kitsu, MangaDex, Trace.moe, Danbooru,
    Shikimori, ANN, AniDB, Ghibli, NekosBest, Waifu.im, and
    AnimeChan. Local-only; does not contact any upstream.

    \b
    Examples:
      animedex status
    \f

    Backend: animedex (local; this command does not contact any
    upstream).

    Rate limit: not applicable (local-only).

    --- LLM Agent Guidance ---
    Use this command at session start to confirm the CLI is
    functional and to peek at the environment-derived banner.
    During Phase 0 it returns a placeholder; once backends ship it
    will list per-backend liveness. Cheap to call; do not rate-limit.
    --- End ---
    """
    click.echo(f"{__TITLE__} v{__VERSION__} - work in progress.")
    click.echo("No backends are wired up yet. See plans/ in the repository.")


@cli.command(name="selftest")
def selftest_command() -> None:
    """Run the in-process self-diagnostic.

    Probes every project module's import + smoke path, every
    registered Click subcommand's --help, and prints a grep-friendly
    `[OK]` / `[FAIL]` table. Designed to run cleanly inside a
    stripped PyInstaller binary on a machine that has no Python
    interpreter installed.

    \b
    Exit codes:
      0   every check passed
      1   one or more checks failed (report still printed)
      2   the runner itself crashed (should be unreachable)

    \b
    Examples:
      animedex selftest
      animedex selftest && echo OK
      animedex selftest 2>&1 | grep FAIL
    \f

    Backend: animedex (local; smoke tests do not contact any
    upstream).

    Rate limit: not applicable (local-only).

    --- LLM Agent Guidance ---
    Use this when you suspect the install or the binary is broken.
    The output is grep-friendly: each check produces a one-line
    ``[OK]`` or ``[FAIL]`` record so you do not need to parse a
    traceback. Exit 0 means healthy; exit 1 means one or more
    checks failed; exit 2 means the runner itself crashed (should
    be unreachable). Call this before assuming a real backend is
    misbehaving - a substrate-level break shows up here first.
    --- End ---
    """
    code = run_selftest()
    sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    cli()
