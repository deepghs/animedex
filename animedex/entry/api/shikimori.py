"""``animedex api shikimori`` subcommand."""

from __future__ import annotations

import click

from animedex.entry.api import (
    _common_output_options,
    _common_request_options,
    _emit,
    _output_mode_from_flags,
    _parse_extra_headers,
    _resolve_cache,
    api_group,
)


@api_group.command("shikimori")
@click.argument("path", required=True)
@click.option("--method", "-X", default="GET", help="HTTP method (GET or POST).")
@click.option(
    "--graphql",
    "graphql_query",
    default=None,
    help="GraphQL query string; sent as JSON body to /api/graphql.",
)
@_common_request_options
@_common_output_options
@click.pass_context
def api_shikimori(
    ctx,
    path,
    method,
    graphql_query,
    extra_headers,
    rate,
    cache_ttl,
    no_cache,
    include_flag,
    head_flag,
    debug_flag,
    no_follow,
    debug_full_body,
):
    """Pass through to Shikimori (REST + GraphQL).

    Backend: Shikimori (shikimori.io; .one accepted fallback).

    Rate limit: 5 RPS / 90 RPM.

    --- LLM Agent Guidance ---
    For REST, leave PATH as e.g. /api/animes/{id}. For GraphQL, pass
    PATH=/api/graphql and --graphql '{ animes(...){ id } }'; the
    wrapper sets method=POST and Content-Type: application/json.
    Both shikimori.io and shikimori.one serve identical data; .io
    is canonical.
    --- End ---
    """
    from animedex.api import shikimori as shikimori_mod

    mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
    json_body = {"query": graphql_query} if graphql_query is not None else None
    method_up = "POST" if json_body is not None else method.upper()
    env = shikimori_mod.call(
        path=path,
        method=method_up,
        json_body=json_body,
        headers=_parse_extra_headers(extra_headers),
        cache=_resolve_cache(no_cache),
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)
