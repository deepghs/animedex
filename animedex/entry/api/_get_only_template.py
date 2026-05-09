"""
Template for simple raw path backend subcommands.

Used by jikan / kitsu / mangadex / danbooru / ann to share the
identical body. Each backend's own ``.py`` file imports
:func:`make_get_only_subcommand` and decorates it onto the api group.

Keeping the body shared is intentional: the only per-backend variation
in this layer is the backend identifier and the docstring text.
"""

from __future__ import annotations

import click

from animedex.entry.api import (
    _call_or_paginate,
    _common_output_options,
    _common_request_options,
    _emit,
    _merge_path_and_fields,
    _output_mode_from_flags,
    _parse_api_fields,
    _parse_extra_headers,
    _resolve_cache,
    api_group,
)


def make_get_only_subcommand(*, name: str, backend_module_name: str, docstring: str):
    """Register a simple raw-path ``api <name>`` subcommand on the api group.

    Each backend gets its own click.Command with its own docstring;
    the docstring carries the ``Backend:`` / ``Rate limit:`` /
    ``--- LLM Agent Guidance --- ... --- End ---`` blocks the
    project policy lint asserts.

    :param name: CLI subcommand name (also the backend identifier).
    :type name: str
    :param backend_module_name: Module under :mod:`animedex.api` that
                                  exposes ``call(path=..., ...)``.
    :type backend_module_name: str
    :param docstring: The full docstring including the three policy
                       blocks.
    :type docstring: str
    """

    def _cmd(
        ctx,
        path,
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
        from importlib import import_module

        backend_module = import_module(f"animedex.api.{backend_module_name}")
        mode = _output_mode_from_flags(include_flag, head_flag, debug_flag)
        out_path, params = _merge_path_and_fields(path, _parse_api_fields(api_fields))
        env = _call_or_paginate(
            backend_module,
            backend=name,
            paginate=paginate,
            max_pages=max_pages,
            max_items=max_items,
            method_explicit=True,
            path=out_path,
            method=method.upper(),
            params=params,
            headers=_parse_extra_headers(extra_headers),
            cache=_resolve_cache(no_cache),
            no_cache=no_cache,
            cache_ttl=cache_ttl,
            rate=rate,
            follow_redirects=not no_follow,
        )
        _emit(ctx, env, mode, debug_full_body)

    # Set docstring + name BEFORE applying decorators so click captures
    # them when it builds the Command object.
    _cmd.__doc__ = docstring
    _cmd.__name__ = f"api_{backend_module_name}"

    decorated = click.pass_context(_cmd)
    decorated = _common_output_options(decorated)
    decorated = _common_request_options(decorated)
    decorated = click.argument("path", required=True)(decorated)
    decorated = api_group.command(name)(decorated)
    return decorated
