"""``animedex api shikimori`` subcommand."""

from __future__ import annotations

import click
from click.core import ParameterSource

from animedex.entry.api import (
    _call_or_paginate,
    _common_output_options,
    _common_request_options,
    _emit,
    _merge_json_objects,
    _merge_path_and_fields,
    _output_mode_from_flags,
    _parse_api_fields,
    _parse_extra_headers,
    _resolve_cache,
    api_group,
)


@api_group.command("shikimori")
@click.argument("path", required=True)
@click.option(
    "--graphql",
    "graphql_query",
    default=None,
    help="GraphQL query string; sent as JSON body and defaults method to POST when -X is omitted.",
)
@_common_request_options
@_common_output_options
@click.pass_context
def api_shikimori(
    ctx,
    path,
    graphql_query,
    method,
    api_fields,
    paginate,
    max_pages,
    max_items,
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
    """Issue a Shikimori REST or GraphQL request.

    REST default: GET against ``/api/...``. GraphQL: pass PATH=
    ``/api/graphql`` and ``--graphql 'query'``; the wrapper sends a
    JSON body and defaults method to POST only when ``-X/--method`` is
    omitted. Both ``shikimori.io`` (canonical) and ``shikimori.one``
    (fallback) serve identical data.

    \b
    Docs:
      https://shikimori.io/api/doc                 REST v1/v2 reference
      https://shikimori.io/api/doc/graphql         GraphQL schema reference
      https://shikimori.io/api/doc/2.0             v2 reference (preferred)

    \b
    Common REST paths:
      /api/animes/{id}                       fetch one anime
      /api/animes?search=Frieren&limit=2     search anime
      /api/mangas/{id}                       fetch one manga
      /api/mangas?search=Berserk&limit=2     search manga
      /api/ranobe/{id}                       fetch one ranobe
      /api/clubs/{id}                        fetch one club
      /api/publishers                        publisher taxonomy
      /api/people/{id}                       fetch one top-level person
      /api/calendar                          airing calendar
      /api/animes/{id}/screenshots           screenshot list
      /api/animes/{id}/videos                PV/OP/ED list

    \b
    Examples:
      animedex api shikimori /api/animes/52991
      animedex api shikimori '/api/animes?search=Frieren&limit=2' -i
      animedex api shikimori '/api/mangas?search=Berserk&limit=2'
      animedex api shikimori /api/people/1870
      animedex api shikimori /api/calendar
      animedex api shikimori /api/graphql --graphql '{ animes(ids:"52991"){ id name score } }'
    \f

    Backend: Shikimori (shikimori.io; .one accepted fallback).

    Rate limit: 5 RPS / 90 RPM.

    --- LLM Agent Guidance ---
    For REST, leave PATH as e.g. /api/animes/{id}, /api/mangas/{id},
    /api/ranobe/{id}, /api/clubs/{id}, /api/publishers, or
    /api/people/{id}. Prefer the high-level shikimori commands for
    lifted REST surfaces. For GraphQL, pass PATH=/api/graphql and
    --graphql '{ animes(...){ id } }'; the wrapper sends a JSON body,
    sets Content-Type: application/json, and defaults to POST only
    when the caller did not pass -X/--method. Both shikimori.io and
    shikimori.one serve identical data; .io is canonical.
    --- End ---
    """
    from animedex.api import shikimori as shikimori_mod

    mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
    fields = _parse_api_fields(api_fields)
    json_body = {"query": graphql_query} if graphql_query is not None else None
    if json_body is not None:
        variables = fields or None
        if variables is not None:
            json_body["variables"] = variables
    method_source = ctx.get_parameter_source("method")
    method_up = method.upper()
    if method_up == "GET" and json_body is not None and method_source is not ParameterSource.COMMANDLINE:
        method_up = "POST"
    elif method_up == "POST":
        json_body = _merge_json_objects(None, fields, left_name="JSON body", right_name="-f/-F") if fields else None
    if json_body is not None:
        out_path = path
        params = None
    else:
        out_path, params = _merge_path_and_fields(path, fields)
    env = _call_or_paginate(
        shikimori_mod,
        backend="shikimori",
        paginate=paginate,
        max_pages=max_pages,
        max_items=max_items,
        method_explicit=method_source is ParameterSource.COMMANDLINE,
        path=out_path,
        method=method_up,
        params=params,
        json_body=json_body,
        headers=_parse_extra_headers(extra_headers),
        cache=_resolve_cache(no_cache),
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)
