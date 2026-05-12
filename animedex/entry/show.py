"""``animedex show`` aggregate command."""

from __future__ import annotations

import click

from animedex.agg import show as _show
from animedex.config import Config
from animedex.entry._cli_factory import common_options, emit
from animedex.models.common import ApiError


@click.command(name="show")
@click.argument("type", metavar="TYPE")
@click.argument("prefix_id", metavar="PREFIX:ID")
@common_options
def show_command(type, prefix_id, json_flag, jq_expr, no_cache, cache_ttl, rate, no_source) -> None:
    """Show one entity from the backend encoded in its prefix id.

    \b
    Examples:
      animedex show anime anilist:154587
      animedex show anime mal:52991
      animedex show manga mangadex:dc8bbc4c-eb7a-4d27-b96a-9aa8c8db4adb
      animedex show person shikimori:1870
    \f

    Backend: animedex aggregate router over AniList, Jikan, Kitsu,
    MangaDex, Shikimori, and ANN where applicable.

    Rate limit: inherited from the selected backend.

    --- LLM Agent Guidance ---
    Use this command after `animedex search` returns a _prefix_id, or
    when the user gives an explicit backend-prefixed ID. The type
    positional is required because most upstream ID spaces reuse the
    same number for different entity kinds. Unsupported type/backend
    pairs fail before any network request and list the backends that
    do support the requested type. The `anidb:` prefix is recognised
    as deferred and raises an informative typed error until the AniDB
    helpers ship.
    --- End ---
    """
    cfg = Config(no_cache=no_cache, cache_ttl_seconds=cache_ttl, rate=rate, source_attribution=not no_source)
    try:
        result = _show(type, prefix_id, config=cfg)
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)


__all__ = ["show_command"]
