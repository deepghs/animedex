"""``animedex kitsu <subcommand>`` Click group + bindings.

Eight subcommands wrapping the most-used anonymous JSON:API
endpoints on ``kitsu.io/api/edge``. Bindings are programmatic via
:func:`register_subcommand`, so the group's ``--help`` covers the
full surface without one hand-written wrapper per endpoint.
"""

from __future__ import annotations

import click

from animedex.backends import kitsu as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="kitsu")
def kitsu_group() -> None:
    """High-level Kitsu commands (anonymous; JSON:API).

    \b
    Docs:
      https://kitsu.docs.apiary.io/                     Apiary reference
      https://hummingbird-me.github.io/api-docs/        markdown mirror
      https://jsonapi.org/                              JSON:API spec

    \b
    Examples:
      animedex kitsu show 46474
      animedex kitsu search Frieren --limit 5
      animedex kitsu streaming 46474
      animedex kitsu mappings 46474
      animedex kitsu trending --limit 5
      animedex kitsu manga-show 1
      animedex kitsu manga-search Berserk --limit 3
      animedex kitsu categories --limit 10
    \f

    Backend: Kitsu (kitsu.io/api/edge canonical; kitsu.app/api/edge
    accepted alias).

    Rate limit: not formally published; project applies a 10 req/sec
    sustained ceiling.

    --- LLM Agent Guidance ---
    JSON:API. Anime + manga catalogue plus a streaming-link rail and
    a cross-source mapping table (anilist / mal / anidb / kitsu /
    thetvdb). The mappings endpoint is the cheapest way to convert
    a Kitsu ID to its peers; prefer it over reading the same ID from
    each upstream in turn. Pagination uses page[limit]=N and
    page[offset]=N (offset, not 1-indexed page).
    --- End ---
    """


# ---------- /anime ----------
register_subcommand(kitsu_group, "show", _api.show, help="Anime by Kitsu numeric id (full payload).")
register_subcommand(kitsu_group, "search", _api.search, help="Free-text anime search.")
register_subcommand(kitsu_group, "streaming", _api.streaming, help="Legal streaming destinations for an anime.")
register_subcommand(
    kitsu_group,
    "mappings",
    _api.mappings,
    help="Cross-source ID map (anilist / mal / anidb / kitsu / thetvdb).",
)
register_subcommand(kitsu_group, "trending", _api.trending, help="Front-page trending anime rail.")

# ---------- /manga ----------
register_subcommand(kitsu_group, "manga-show", _api.manga_show, help="Manga by Kitsu numeric id.")
register_subcommand(kitsu_group, "manga-search", _api.manga_search, help="Free-text manga search.")

# ---------- /categories ----------
register_subcommand(kitsu_group, "categories", _api.categories, help="Top-level Kitsu categories.")
