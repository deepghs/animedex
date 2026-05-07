"""
``animedex api`` Click group and per-backend subcommands.

Each backend gets one subcommand. Output flag handling is shared:
``-i`` / ``-I`` / ``--debug`` / ``--no-follow`` / ``--debug-full-body``,
mutually exclusive among the first three. The shared logic is in
:func:`_render_output`; per-backend subcommands just collect the
caller's path / params / body and call into the corresponding
``animedex.api.<backend>.call``.
"""

from __future__ import annotations

import sys
from typing import Optional

import click

from animedex.api._envelope import RawResponse
from animedex.render.raw import render_body, render_debug, render_head, render_include


def _output_mode_from_flags(include_flag: bool, head_flag: bool, debug_flag: bool) -> str:
    selected = [name for name, on in (("-i", include_flag), ("-I", head_flag), ("--debug", debug_flag)) if on]
    if len(selected) > 1:
        raise click.UsageError(f"output flags are mutually exclusive: {' '.join(selected)}")
    if include_flag:
        return "include"
    if head_flag:
        return "head"
    if debug_flag:
        return "debug"
    return "body"


def _render_output(envelope: RawResponse, mode: str, full_body: bool) -> str:
    if mode == "include":
        return render_include(envelope)
    if mode == "head":
        return render_head(envelope)
    if mode == "debug":
        return render_debug(envelope, full_body=full_body)
    return render_body(envelope)


def _exit_code_for(envelope: RawResponse) -> int:
    """Map an envelope to a CLI exit code.

    * ``firewall_rejected`` → 2 (caller error, project policy).
    * 2xx → 0.
    * 4xx → 4.
    * 5xx → 5.
    * 3xx (only with --no-follow) → 3.
    * other → 1.
    """
    if envelope.firewall_rejected is not None:
        return 2
    s = envelope.status
    if 200 <= s < 300:
        return 0
    if 300 <= s < 400:
        return 3
    if 400 <= s < 500:
        return 4
    if 500 <= s < 600:
        return 5
    return 1


def _common_output_options(func):
    """Decorator factory adding the shared output flags."""
    func = click.option(
        "--debug-full-body",
        "debug_full_body",
        is_flag=True,
        default=False,
        help="With --debug, do not truncate the body at 64 KiB.",
    )(func)
    func = click.option(
        "--no-follow", "no_follow", is_flag=True, default=False, help="Do not auto-follow 3xx redirects."
    )(func)
    func = click.option(
        "--debug",
        "debug_flag",
        is_flag=True,
        default=False,
        help="Emit the full RawResponse envelope as JSON (data + debug).",
    )(func)
    func = click.option(
        "-I", "--head", "head_flag", is_flag=True, default=False, help="Print status line + response headers; no body."
    )(func)
    func = click.option(
        "-i",
        "--include",
        "include_flag",
        is_flag=True,
        default=False,
        help="Print status line + response headers + body (curl-style).",
    )(func)
    return func


def _common_request_options(func):
    func = click.option("--no-cache", is_flag=True, default=False, help="Skip cache lookup and write.")(func)
    func = click.option("--cache", "cache_ttl", type=int, default=None, help="Override cache TTL in seconds.")(func)
    func = click.option(
        "--rate",
        type=click.Choice(["normal", "slow"]),
        default="normal",
        help="Voluntary slowdown: 'slow' halves the rate-limit refill rate.",
    )(func)
    func = click.option(
        "--header", "-H", "extra_headers", multiple=True, help="Extra header (repeatable): 'Name: Value'."
    )(func)
    return func


def _parse_extra_headers(extra_headers):
    out = {}
    for h in extra_headers or []:
        if ":" not in h:
            raise click.UsageError(f"--header must be 'Name: Value', got {h!r}")
        name, value = h.split(":", 1)
        out[name.strip()] = value.strip()
    return out


def _emit(ctx: click.Context, envelope: RawResponse, mode: str, full_body: bool) -> None:
    click.echo(_render_output(envelope, mode, full_body))
    ctx.exit(_exit_code_for(envelope))


# Build the api group; each backend registers its own subcommand below.


@click.group(name="api")
def api_group() -> None:
    """Raw HTTP/GraphQL passthrough to upstream APIs.

    Backend: animedex (local; routes to one of 8 upstream backends).

    Rate limit: not applicable at this level (each backend's bucket
    applies inside the call).

    --- LLM Agent Guidance ---
    The api group is the project's escape hatch for endpoints not
    covered by the higher-level commands. Each subcommand wraps one
    backend's raw HTTP/GraphQL surface; the dispatcher injects the
    project User-Agent, runs the read-only firewall, applies rate
    limiting, and consults the local cache. The output flags are
    shared:

    * default (no flag): print the response body.
    * ``-i`` / ``--include``: print status line + response headers +
      blank line + body (curl-style).
    * ``-I`` / ``--head``: print status line + response headers only.
    * ``--debug``: print the full RawResponse envelope as indented
      JSON; includes the request snapshot (with credentials
      fingerprint-redacted), redirect chain, timing breakdown, and
      cache provenance. Use this when you need to debug a flaky
      upstream call.

    The output flags are mutually exclusive. Use ``--no-follow`` to
    disable 3xx auto-following. Use ``--debug-full-body`` to opt out
    of the 64 KiB body truncation in ``--debug`` mode.

    Caller-supplied User-Agent in ``--header User-Agent: ...``
    overrides the project default per AGENTS.md §0.
    --- End ---
    """


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
    """Pass through to AniList GraphQL.

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

    env = anilist.call(
        query=query,
        variables=variables,
        headers=_parse_extra_headers(extra_headers),
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)


def _make_get_subcommand(name: str, backend_module_name: str):
    """Generate a GET-only subcommand for jikan / kitsu / mangadex /
    danbooru / shikimori / ann."""

    @api_group.command(name)
    @click.argument("path", required=True)
    @_common_request_options
    @_common_output_options
    @click.pass_context
    def _cmd(
        ctx,
        path,
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
        """Pass through to the backend's REST surface.

        Backend: routed by the subcommand name to the matching upstream.

        Rate limit: per-backend (see plan 01 / #3).

        --- LLM Agent Guidance ---
        The PATH argument is the request path (or absolute URL); the
        dispatcher joins it with the backend's canonical base URL.
        Use the shared output flags (-i / -I / --debug) for varied
        output forms.
        --- End ---
        """
        from importlib import import_module

        backend_module = import_module(f"animedex.api.{backend_module_name}")
        mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
        env = backend_module.call(
            path=path,
            headers=_parse_extra_headers(extra_headers),
            no_cache=no_cache,
            cache_ttl=cache_ttl,
            rate=rate,
            follow_redirects=not no_follow,
        )
        _emit(ctx, env, mode, debug_full_body)

    _cmd.__name__ = f"api_{backend_module_name}"
    return _cmd


api_jikan = _make_get_subcommand("jikan", "jikan")
api_kitsu = _make_get_subcommand("kitsu", "kitsu")
api_mangadex = _make_get_subcommand("mangadex", "mangadex")
api_danbooru = _make_get_subcommand("danbooru", "danbooru")
api_ann = _make_get_subcommand("ann", "ann")


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
    """Pass through to Trace.moe.

    Backend: Trace.moe (api.trace.moe).

    Rate limit: anonymous tier concurrency 1, quota 100/month.

    --- LLM Agent Guidance ---
    Two paths matter for Phase 1: ``GET /me`` (free) and
    ``GET /search?url=<encoded>`` (1 quota each). To search by image
    upload, pass ``--input path/to/image.jpg`` and a path of
    ``/search``; the body bytes are sent as the POST payload.
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
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)


@api_group.command("shikimori")
@click.argument("path", required=True)
@click.option("--method", "-X", default="GET", help="HTTP method (GET or POST).")
@click.option(
    "--graphql", "graphql_query", default=None, help="GraphQL query string; sent as JSON body to /api/graphql."
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

    Backend: Shikimori (shikimori.io).

    Rate limit: 5 RPS / 90 RPM.

    --- LLM Agent Guidance ---
    For REST, leave PATH as ``/api/animes/{id}`` etc. For GraphQL,
    pass PATH=``/api/graphql`` and ``--graphql '{ animes(...){ id } }'``;
    the wrapper sets method=POST and ``Content-Type: application/json``.
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
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=not no_follow,
    )
    _emit(ctx, env, mode, debug_full_body)
