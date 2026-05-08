"""``animedex trace <subcommand>`` Click group + bindings.

Two subcommands: ``search`` (by URL or stdin upload) and ``quota``
(``/me``).
"""

from __future__ import annotations

import sys

import click

from animedex.backends import trace as _api
from animedex.entry._cli_factory import common_options, emit
from animedex.config import Config


@click.group(name="trace")
def trace_group() -> None:
    """High-level Trace.moe screenshot search.

    \b
    Docs:
      https://soruly.github.io/trace.moe-api/    endpoint reference
      https://github.com/soruly/trace.moe-api    project repo
      https://trace.moe/                          web UI

    \b
    Examples:
      animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info
      animedex trace search --input ./screenshot.jpg --anilist-info
      cat shot.jpg | animedex trace search --input - --anilist-info
      animedex trace quota
    \f

    Backend: Trace.moe (api.trace.moe).

    Rate limit: anonymous tier concurrency 1, quota 100 searches/month.

    --- LLM Agent Guidance ---
    To identify an anime scene from a screenshot, prefer
    ``--input <file>`` for local images and ``--url <public-url>``
    for already-online ones. Setting ``--anilist-info`` populates each
    hit with an inline AnimeTitle, saving a follow-up AniList round-
    trip; downstream code can read ``hit.anilist_id`` to chain into
    other backends. ``quota`` is free and does not consume from the
    monthly budget.
    --- End ---
    """


@trace_group.command("search")
@click.option("--url", "image_url", default=None, help="Public URL of the image to identify.")
@click.option(
    "--input", "input_path", type=click.Path(allow_dash=True), default=None, help="Local file path or '-' for stdin."
)
@click.option("--anilist-info", is_flag=True, default=False, help="Inline AniList title with each hit.")
@click.option("--cut-borders", is_flag=True, default=False, help="Strip letterboxing before matching.")
@click.option("--anilist-id", type=int, default=None, help="Restrict matches to a specific AniList show.")
@common_options
def search_cmd(
    image_url,
    input_path,
    anilist_info,
    cut_borders,
    anilist_id,
    json_flag,
    jq_expr,
    no_cache,
    cache_ttl,
    rate,
    no_source,
):
    """Identify an anime scene from a screenshot.

    \f

    Backend: Trace.moe (api.trace.moe).

    Rate limit: anonymous concurrency 1, quota 100/month.

    --- LLM Agent Guidance ---
    Search a screenshot URL with --url or upload bytes with --input.
    --anilist-info inlines AnimeTitle so callers can chain into
    anilist commands without an extra round-trip.
    --- End ---
    """
    cfg = Config(
        no_cache=no_cache,
        cache_ttl_seconds=cache_ttl,
        rate=rate,
        source_attribution=not no_source,
    )
    raw_bytes = None
    if input_path:
        if input_path == "-":
            raw_bytes = sys.stdin.buffer.read()
        else:
            with open(input_path, "rb") as fh:
                raw_bytes = fh.read()
    try:
        hits = _api.search(
            image_url=image_url,
            raw_bytes=raw_bytes,
            anilist_info=anilist_info,
            cut_borders=cut_borders,
            anilist_id=anilist_id,
            config=cfg,
        )
    except Exception as exc:
        raise click.ClickException(str(exc))
    emit(hits, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)


@trace_group.command("quota")
@common_options
def quota_cmd(json_flag, jq_expr, no_cache, cache_ttl, rate, no_source):
    """Show the caller's Trace.moe quota state (free; no quota cost).

    \f

    Backend: Trace.moe (api.trace.moe).

    Rate limit: anonymous concurrency 1, quota 100/month (this call is free).

    --- LLM Agent Guidance ---
    Returns priority / concurrency / quota / quota_used. The
    upstream's caller-IP echo is dropped by the mapper.
    --- End ---
    """
    cfg = Config(
        no_cache=no_cache,
        cache_ttl_seconds=cache_ttl,
        rate=rate,
        source_attribution=not no_source,
    )
    try:
        result = _api.quota(config=cfg)
    except Exception as exc:
        raise click.ClickException(str(exc))
    emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)
