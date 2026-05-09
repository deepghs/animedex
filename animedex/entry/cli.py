"""
Top-level command-line interface for animedex.

This module wires the per-backend command groups and the ``api``
raw-passthrough group onto the top-level ``animedex`` Click group,
plus the substrate utilities ``status`` and ``selftest``. Each
per-backend group lives in its own ``animedex/entry/<backend>.py``
module so contributors can edit one backend's bindings without
touching the others.
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
    catalogue with a single invocation. Defensive: exits cleanly
    even if the tree happens to carry no guidance blocks.

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
        click.echo("No Agent Guidance blocks found.")
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
from animedex.entry.anilist import anilist_group as _anilist_group  # noqa: E402
from animedex.entry.ann import ann_group as _ann_group  # noqa: E402
from animedex.entry.danbooru import danbooru_group as _danbooru_group  # noqa: E402
from animedex.entry.ghibli import ghibli_group as _ghibli_group  # noqa: E402
from animedex.entry.jikan import jikan_group as _jikan_group  # noqa: E402
from animedex.entry.kitsu import kitsu_group as _kitsu_group  # noqa: E402
from animedex.entry.mangadex import mangadex_group as _mangadex_group  # noqa: E402
from animedex.entry.nekos import nekos_group as _nekos_group  # noqa: E402
from animedex.entry.quote import quote_group as _quote_group  # noqa: E402
from animedex.entry.shikimori import shikimori_group as _shikimori_group  # noqa: E402
from animedex.entry.trace import trace_group as _trace_group  # noqa: E402
from animedex.entry.waifu import waifu_group as _waifu_group  # noqa: E402

cli.add_command(_api_group)
cli.add_command(_anilist_group)
cli.add_command(_ann_group)
cli.add_command(_danbooru_group)
cli.add_command(_ghibli_group)
cli.add_command(_jikan_group)
cli.add_command(_kitsu_group)
cli.add_command(_mangadex_group)
cli.add_command(_nekos_group)
cli.add_command(_quote_group)
cli.add_command(_shikimori_group)
cli.add_command(_trace_group)
cli.add_command(_waifu_group)


@cli.command(name="status")
def status_command() -> None:
    """Print a one-shot status banner for the CLI.

    Reports the version banner and the high-level command groups
    currently wired into the CLI. Local-only; does not contact any
    upstream. A future revision will fold in per-backend liveness
    and quota state — until those land, this command returns a
    static summary that is cheap and side-effect free.

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
    Cheap to call (no network, no I/O beyond stdout); do not
    rate-limit.
    --- End ---
    """
    click.echo(f"{__TITLE__} v{__VERSION__}")
    click.echo(
        "Wired groups: anilist, ann, danbooru, ghibli, jikan, kitsu, mangadex, nekos, quote, shikimori, trace, waifu, api (raw passthrough)."
    )
    click.echo("Run 'animedex --help' for the full command tree.")


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
