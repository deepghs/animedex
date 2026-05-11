"""``animedex search`` aggregate command."""

from __future__ import annotations

import click

from animedex.agg import search as _search
from animedex.config import Config
from animedex.entry._cli_factory import common_options, emit
from animedex.models.aggregate import AggregateResult
from animedex.models.common import ApiError


def _emit_failure_lines(result: AggregateResult) -> None:
    for name, status in result.failed_sources.items():
        reason = status.reason or "failed"
        message = status.message or reason
        click.echo(f"source {name!r} failed: {message}; continuing with other sources", err=True)


@click.command(name="search")
@click.argument("type", metavar="TYPE")
@click.argument("q", metavar="Q")
@click.option("--limit", type=int, default=10, show_default=True, help="Per-source result cap.")
@click.option("--source", "source", default=None, help="Comma-separated source allowlist.")
@common_options
@click.pass_context
def search_command(ctx, type, q, limit, source, json_flag, jq_expr, no_cache, cache_ttl, rate, no_source) -> None:
    """Search one entity type across every supporting catalogue.

    \b
    Examples:
      animedex search anime Frieren
      animedex search manga Berserk --source anilist,jikan
      animedex search publisher Kodansha --json
      animedex search person Miyazaki --jq '.items[0]._prefix_id'
    \f

    Backend: animedex aggregate search over AniList, Jikan, Kitsu,
    MangaDex, Shikimori, and ANN where applicable.

    Rate limit: inherited from each selected backend.

    --- LLM Agent Guidance ---
    Use this command when the user asks for a cross-catalogue entity
    lookup and has not already chosen a backend. The type positional
    is required; do not guess it. Results are not deduplicated across
    sources, scores are not averaged, and each row carries _source
    plus _prefix_id when a follow-up `animedex show` call can route it.
    Partial source failures return the healthy rows and report failed
    sources in the envelope and stderr.
    --- End ---
    """
    cfg = Config(no_cache=no_cache, cache_ttl_seconds=cache_ttl, rate=rate, source_attribution=not no_source)
    try:
        result = _search(type, q, limit=limit, source=source, config=cfg)
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_failure_lines(result)
    emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)
    if result.all_failed:
        ctx.exit(1)
    ctx.exit(0)


__all__ = ["search_command"]
