"""
``animedex api`` Click group + shared helpers.

The group itself lives here. Each backend subcommand is registered
from its own sibling module (``animedex/entry/api/<backend>.py``)
which imports and decorates onto :data:`api_group`. Keeping each
subcommand in its own file keeps any one file readable and lets
contributors edit one backend's CLI without touching the others.

Shared utilities used by every subcommand:

* :func:`_default_cache` - lazy singleton
  :class:`~animedex.cache.sqlite.SqliteCache` at the platform-default
  path.
* :func:`_output_mode_from_flags` - mutual-exclusion check on
  ``-i / -I / --debug``.
* :func:`_render_output` - dispatch to the four renderers.
* :func:`_exit_code_for` - status-class-aware exit code.
* :func:`_emit` - print + ctx.exit one-shot.
* :func:`_parse_extra_headers` - turn ``-H "Name: Value"`` into a dict.
* :func:`_common_request_options`, :func:`_common_output_options` -
  decorator factories.
"""

from __future__ import annotations

import click

from animedex.api._envelope import RawResponse
from animedex.render.raw import render_body, render_debug, render_head, render_include


_DEFAULT_CACHE = None


def _default_cache():
    """Lazy singleton :class:`SqliteCache` at the default platform path.

    Created on first use so paths that pass ``--no-cache`` everywhere
    or that run in unit tests never instantiate it.

    :return: A reusable ``SqliteCache`` instance.
    :rtype: SqliteCache
    """
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        from animedex.cache.sqlite import SqliteCache

        _DEFAULT_CACHE = SqliteCache()
    return _DEFAULT_CACHE


def _output_mode_from_flags(include_flag: bool, head_flag: bool, debug_flag: bool) -> str:
    """Pick the output mode from the three mutually-exclusive flags.

    :raises click.UsageError: When more than one of the three flags
                                 is set.
    """
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
    """Dispatch to the four renderers in :mod:`animedex.render.raw`."""
    if mode == "include":
        return render_include(envelope)
    if mode == "head":
        return render_head(envelope)
    if mode == "debug":
        return render_debug(envelope, full_body=full_body)
    return render_body(envelope)


def _exit_code_for(envelope: RawResponse) -> int:
    """Map an envelope to a CLI exit code.

    * ``firewall_rejected`` -> 2
    * 2xx -> 0
    * 3xx (only with ``--no-follow``) -> 3
    * 4xx -> 4
    * 5xx -> 5
    * other -> 1
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
    """Decorator factory: add ``-i / -I / --debug / --no-follow / --debug-full-body``."""
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
    """Decorator factory: add ``--header / -H``, ``--rate``, ``--cache``, ``--no-cache``."""
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
    """Turn ``("Name: Value", ...)`` into a dict; raise on malformed."""
    out = {}
    for h in extra_headers or []:
        if ":" not in h:
            raise click.UsageError(f"--header must be 'Name: Value', got {h!r}")
        name, value = h.split(":", 1)
        out[name.strip()] = value.strip()
    return out


def _emit(ctx: click.Context, envelope: RawResponse, mode: str, full_body: bool) -> None:
    """Print the rendered output and exit with the status-class code."""
    click.echo(_render_output(envelope, mode, full_body))
    ctx.exit(_exit_code_for(envelope))


def _resolve_cache(no_cache: bool):
    """Pick the cache to pass into :func:`animedex.api._dispatch.call`.

    :param no_cache: When ``True``, the call should bypass the cache.
    :type no_cache: bool
    :return: ``None`` when ``no_cache`` is set; otherwise the lazy
             singleton from :func:`_default_cache`.
    """
    if no_cache:
        return None
    return _default_cache()


@click.group(name="api")
def api_group() -> None:
    """Raw HTTP / GraphQL passthrough to one of the 8 upstream backends.

    Each subcommand wraps one backend's raw API surface. The
    dispatcher injects the project `User-Agent`, runs the read-only
    firewall, applies a per-backend rate-limit token bucket, and
    consults the local SQLite cache before issuing the request.

    \b
    Output modes (mutually exclusive):
      (default)         response body only (gh-api equivalent)
      -i, --include     status line + response headers + body
      -I, --head        status line + response headers (no body)
      --debug           full RawResponse envelope as indented JSON;
                        includes the request snapshot (credentials
                        fingerprint-redacted), redirect chain, per-
                        call timing breakdown, and cache provenance

    \b
    Other behaviour:
      --no-follow             disable 3xx auto-following
      --debug-full-body       opt out of the 64 KiB body cap in --debug
      --no-cache              skip cache lookup and write
      --cache TTL_SECONDS     override default cache TTL
      --rate {normal,slow}    voluntary slowdown (slow halves refill)
      -H, --header K:V        add request header (repeatable)

    Per AGENTS.md §0, a caller-supplied `User-Agent` via `--header`
    overrides the project default verbatim.

    \b
    Examples:
      animedex api jikan /anime/52991
      animedex api anilist '{ Media(id:154587){ title{romaji} } }'
      animedex api kitsu '/anime?filter[text]=Frieren&page[limit]=2' -i
      animedex api shikimori /api/graphql --graphql '{ animes(ids:"52991"){ id name }}'
      animedex api jikan /anime/52991 --debug | jq '{cache, timing}'
    \f

    Backend: animedex (local; routes to one of 8 upstream backends).

    Rate limit: not applicable at this level (each backend's bucket
    applies inside the call).

    --- LLM Agent Guidance ---
    The api group is the project's escape hatch for endpoints not
    covered by the higher-level commands. Each subcommand wraps one
    backend's raw HTTP/GraphQL surface; the dispatcher injects the
    project User-Agent, runs the read-only firewall, applies rate
    limiting, and consults the local cache. The output flags
    (-i / -I / --debug) are shared and mutually exclusive. Use
    --debug when you need to inspect the full envelope (redirect
    chain, timing, cache provenance, fingerprint-redacted request
    headers) - this is the "data + debug" mode.

    Caller-supplied User-Agent via --header overrides the project
    default per AGENTS.md §0.
    --- End ---
    """


# Importing the subcommand modules registers them onto the api_group
# at import time. Order does not matter functionally; alphabetical for
# diff-friendliness.
from animedex.entry.api import anilist  # noqa: E402, F401
from animedex.entry.api import ann  # noqa: E402, F401
from animedex.entry.api import danbooru  # noqa: E402, F401
from animedex.entry.api import jikan  # noqa: E402, F401
from animedex.entry.api import kitsu  # noqa: E402, F401
from animedex.entry.api import mangadex  # noqa: E402, F401
from animedex.entry.api import shikimori  # noqa: E402, F401
from animedex.entry.api import trace  # noqa: E402, F401


__all__ = ["api_group"]
