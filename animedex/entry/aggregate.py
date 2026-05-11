"""Top-level aggregate calendar commands."""

from __future__ import annotations

import sys
from typing import Optional

import click

from animedex.agg import calendar as _calendar
from animedex.config import Config
from animedex.models.aggregate import AggregateResult
from animedex.models.common import ApiError
from animedex.render.jq import apply_jq
from animedex.render.json_renderer import render_json
from animedex.render.tty import is_terminal as _is_terminal
from animedex.render.tty import render_tty


def _common_options(func):
    func = click.option("--no-source", is_flag=True, default=False, help="Drop source attribution from JSON output.")(
        func
    )
    func = click.option("--rate", type=click.Choice(["normal", "slow"]), default="normal", help="Voluntary slowdown.")(
        func
    )
    func = click.option("--cache", "cache_ttl", type=int, default=None, help="Override cache TTL in seconds.")(func)
    func = click.option("--no-cache", is_flag=True, default=False, help="Skip cache lookup and write.")(func)
    func = click.option("--jq", "jq_expr", default=None, help="Filter JSON output through jq. Forces JSON mode.")(func)
    func = click.option(
        "--json", "json_flag", is_flag=True, default=False, help="Always emit JSON (default auto-switches by TTY)."
    )(func)
    return func


def _config(no_cache: bool, cache_ttl: Optional[int], rate: str, no_source: bool) -> Config:
    return Config(no_cache=no_cache, cache_ttl_seconds=cache_ttl, rate=rate, source_attribution=not no_source)


def _apply_jq(json_text: str, jq_expr: str) -> str:
    try:
        return apply_jq(json_text, jq_expr)
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc


def _emit(result: AggregateResult, *, json_flag: bool, jq_expr: Optional[str], no_source: bool) -> None:
    use_json = json_flag or jq_expr is not None or not _is_terminal(sys.stdout)
    if use_json:
        text = render_json(result, include_source=not no_source)
        if jq_expr is not None:
            text = _apply_jq(text, jq_expr)
    else:
        text = render_tty(result)
    click.echo(text.rstrip("\n"))


def _report_failures(result: AggregateResult) -> None:
    for name, status in result.failed_sources.items():
        detail = status.reason or status.message or "failed"
        if status.http_status is not None and f"{status.http_status}" not in detail:
            detail = f"{detail} (HTTP {status.http_status})"
        click.echo(f"source {name!r} failed: {detail}; continuing with other sources", err=True)


def _finish(ctx: click.Context, result: AggregateResult, *, json_flag: bool, jq_expr: Optional[str], no_source: bool):
    _report_failures(result)
    _emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)
    if result.all_failed:
        ctx.exit(1)


@click.command(name="season")
@click.argument("year", required=False, type=int)
@click.argument(
    "season",
    required=False,
    type=click.Choice(["winter", "spring", "summer", "fall"], case_sensitive=False),
)
@click.option("--source", default="all", show_default=True, help="Comma-separated allowlist: all, anilist, jikan.")
@click.option("--limit", default=25, type=int, show_default=True, help="Per-source row limit.")
@_common_options
@click.pass_context
def season_command(
    ctx,
    year,
    season,
    source,
    limit,
    json_flag,
    jq_expr,
    no_cache,
    cache_ttl,
    rate,
    no_source,
):
    """List anime airing in a season across AniList and Jikan.

    Uses the AniList/MAL quarterly anime convention for omitted
    seasons: winter is January-March, spring is April-June, summer is
    July-September, and fall is October-December.

    \b
    Docs:
      https://docs.anilist.co/               AniList GraphQL reference
      https://docs.api.jikan.moe/            Jikan REST reference

    \b
    Examples:
      animedex season
      animedex season 2024 winter --limit 5
      animedex season 2024 spring --source jikan --jq '.items[].title'
    \f

    Backend: aggregate (AniList + Jikan season endpoints).

    Rate limit: bounded by the selected upstreams; AniList 30 req/min
    anonymous, Jikan 60 req/min and 3 req/sec.

    --- LLM Agent Guidance ---
    Use this command for a multi-source seasonal anime list. The
    aggregate path merges likely identical AniList and Jikan records
    using shared ids plus title and broadcast metadata; single-source
    records remain visible with their source attribution. Partial
    backend failure keeps successful rows on stdout, writes one
    stderr line per failed source, and exits non-zero only when every
    selected source failed.
    --- End ---
    """
    cfg = _config(no_cache, cache_ttl, rate, no_source)
    try:
        result = _calendar.season(
            year,
            season,
            source=source,
            limit=limit,
            config=cfg,
            no_cache=no_cache,
            cache_ttl=cache_ttl,
            rate=rate,
        )
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc
    _finish(ctx, result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)


@click.command(name="schedule")
@click.option(
    "--day",
    default="all",
    type=click.Choice(
        ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "today", "tomorrow", "all"],
        case_sensitive=False,
    ),
    show_default=True,
    help="Weekday, today, tomorrow, or all.",
)
@click.option("--source", default="all", show_default=True, help="Comma-separated allowlist: all, anilist, jikan.")
@click.option("--limit", default=25, type=int, show_default=True, help="Per-source row limit.")
@click.option(
    "--timezone",
    "timezone_name",
    default="local",
    show_default=True,
    help="Display/query timezone: local, UTC, IANA name, or offset like +08:00.",
)
@_common_options
@click.pass_context
def schedule_command(ctx, day, source, limit, timezone_name, json_flag, jq_expr, no_cache, cache_ttl, rate, no_source):
    """List airing schedule rows across AniList and Jikan.

    ``--day all`` covers the selected timezone's seven-day window
    starting today. Weekday names resolve to the next occurrence of
    that day in the selected timezone.

    \b
    Docs:
      https://docs.anilist.co/               AniList GraphQL reference
      https://docs.api.jikan.moe/            Jikan REST reference

    \b
    Examples:
      animedex schedule
      animedex schedule --day monday --timezone Asia/Tokyo --source jikan
      animedex schedule --day today --jq '.items[:3]'
    \f

    Backend: aggregate (AniList AiringSchedule + Jikan schedules).

    Rate limit: bounded by the selected upstreams; AniList 30 req/min
    anonymous, Jikan 60 req/min and 3 req/sec.

    --- LLM Agent Guidance ---
    Use this command for currently airing schedule rows. The JSON path
    preserves the structured aggregate envelope; the TTY path groups
    successful rows into a calendar-style view using the selected
    timezone. Empty days are successful results with ``items: []``
    when the selected sources answered. Partial failure reports failed
    sources on stderr and exits non-zero only when all selected
    sources failed.
    --- End ---
    """
    cfg = _config(no_cache, cache_ttl, rate, no_source)
    try:
        result = _calendar.schedule(
            day=day,
            source=source,
            limit=limit,
            timezone_name=timezone_name,
            config=cfg,
            no_cache=no_cache,
            cache_ttl=cache_ttl,
            rate=rate,
        )
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc
    _finish(ctx, result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)


def selftest() -> bool:
    """Smoke-test aggregate command registration objects.

    :return: ``True`` when both commands are Click commands.
    :rtype: bool
    """
    assert isinstance(season_command, click.Command)
    assert isinstance(schedule_command, click.Command)
    return True
