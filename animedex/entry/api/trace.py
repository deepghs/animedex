"""``animedex api trace`` subcommand."""

from __future__ import annotations

import sys
from typing import Optional

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


@api_group.command("trace")
@click.argument("path", required=True)
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, allow_dash=True),
    default=None,
    help="Read POST body bytes from a file (or '-' for stdin).",
)
@_common_request_options
@_common_output_options
@click.pass_context
def api_trace(
    ctx,
    path,
    input_path,
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
    """Issue a Trace.moe request (screenshot reverse search).

    Anonymous tier: concurrency 1, quota 100 searches/month.
    `GET /me` reports the current quota state and is free; every
    `/search` call consumes one from the monthly budget. To search
    by image upload pass `--input <file>` (or `-` for stdin) with
    PATH=`/search`; the bytes are sent as the POST body.

    \b
    Common paths:
      /me                                    quota state (free)
      /search?url=<encoded-image-url>        search by URL
      /search?anilistInfo&url=<encoded>      search + AniList metadata
      /search                                POST upload (use --input)

    \b
    Examples:
      animedex api trace /me
      animedex api trace '/search?anilistInfo&url=https%3A%2F%2Fi.imgur.com%2FzLxHIeo.jpg'
      animedex api trace /search --input ./screenshot.jpg
      cat screenshot.jpg | animedex api trace /search --input -
    \f

    Backend: Trace.moe (api.trace.moe).

    Rate limit: anonymous tier concurrency 1, quota 100/month.

    --- LLM Agent Guidance ---
    Two paths matter for Phase 1: GET /me (free) and
    GET /search?url=<encoded> (1 quota each). To search by image
    upload, pass --input path/to/image.jpg with PATH=/search; the
    bytes are sent as the POST body.
    --- End ---
    """
    from animedex.api import trace as trace_mod

    raw_body: Optional[bytes] = None
    method = "GET"
    if input_path:
        if input_path == "-":
            raw_body = sys.stdin.buffer.read()
        else:
            with open(input_path, "rb") as fh:
                raw_body = fh.read()
        method = "POST"

    mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
    env = trace_mod.call(
        path=path,
        method=method,
        raw_body=raw_body,
        headers=_parse_extra_headers(extra_headers),
        cache=_resolve_cache(no_cache),
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)
