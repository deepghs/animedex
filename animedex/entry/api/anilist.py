"""``animedex api anilist`` subcommand."""

from __future__ import annotations

import click
from click.core import ParameterSource

from animedex.entry.api import (
    _call_or_paginate,
    _common_output_options,
    _common_request_options,
    _emit,
    _merge_json_objects,
    _output_mode_from_flags,
    _parse_api_fields,
    _parse_extra_headers,
    _resolve_cache,
    api_group,
)


@api_group.command("anilist")
@click.argument("query", required=True)
@click.option("--variables", "variables_json", default=None, help="GraphQL variables as a JSON object.")
@_common_request_options
@_common_output_options
@click.pass_context
def api_anilist(
    ctx,
    query,
    variables_json,
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
    """Issue a single AniList GraphQL query.

    QUERY is a complete GraphQL document; quote it. Variables go
    through `--variables` as a JSON object. The 30/min rate limit
    (currently degraded from 90/min) is enforced client-side; the
    second consecutive overshoot blocks until a token is available.
    Anonymous reads cover the entire public schema (Media,
    Character, Staff, Studio, Page, AiringSchedule, ...).

    \b
    Docs:
      https://docs.anilist.co/                              official reference
      https://anilist.gitbook.io/anilist-apiv2-docs/        GitBook mirror
      https://anilist.co/graphiql                           live schema browser

    \b
    Examples:
      animedex api anilist '{ Media(id:154587){ title{romaji english} } }'
      animedex api anilist '{ Page(perPage:5){ media(search:"Frieren"){ id title{romaji} } } }'
      animedex api anilist 'query($s:String){ Page(perPage:2){ media(search:$s){ id }}}' --variables '{"s":"Naruto"}'
      animedex api anilist '{ Media(id:154587){ id } }' --debug | jq '.timing,.cache'
    \f

    Backend: AniList (graphql.anilist.co).

    Rate limit: 30 req/min currently degraded; 90/min baseline.

    --- LLM Agent Guidance ---
    The QUERY argument is a complete GraphQL document; quote it.
    Variables go in --variables as JSON. The 30/min cap is
    client-enforced. Anonymous reads cover the public schema.
    --- End ---
    """
    import json as _json

    from animedex.api import anilist

    mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
    variables = None
    if variables_json:
        try:
            variables = _json.loads(variables_json)
        except _json.JSONDecodeError as exc:
            raise click.UsageError(f"--variables is not valid JSON: {exc}")
    variables = _merge_json_objects(
        variables, _parse_api_fields(api_fields), left_name="--variables", right_name="-f/-F"
    )
    if not variables:
        variables = None
    method_source = ctx.get_parameter_source("method")
    method_up = method.upper()
    if method_up == "GET" and method_source is not ParameterSource.COMMANDLINE:
        method_up = "POST"
    env = _call_or_paginate(
        anilist,
        backend="anilist",
        paginate=paginate,
        max_pages=max_pages,
        max_items=max_items,
        method_explicit=method_source is ParameterSource.COMMANDLINE,
        query=query,
        method=method_up,
        variables=variables,
        headers=_parse_extra_headers(extra_headers),
        cache=_resolve_cache(no_cache),
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)
