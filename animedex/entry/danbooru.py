"""``animedex danbooru <subcommand>`` Click group + bindings.

Eight subcommands wrapping the most-used anonymous read endpoints
on ``danbooru.donmai.us``: search / post / artist / artist-search /
tag / pool / pool-search / count.
"""

from __future__ import annotations

import click

from animedex.backends import danbooru as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="danbooru")
def danbooru_group() -> None:
    """High-level Danbooru commands (anonymous; tag-DSL search).

    \b
    Docs:
      https://danbooru.donmai.us/wiki_pages/help:api      API help
      https://danbooru.donmai.us/wiki_pages/howto%3Asearch  search DSL guide

    \b
    Examples:
      animedex danbooru search 'touhou marisa rating:g order:score' --limit 5
      animedex danbooru post 1
      animedex danbooru artist 1
      animedex danbooru artist-search "Hayao Miyazaki" --limit 3
      animedex danbooru tag "touhou*" --limit 5
      animedex danbooru pool 1
      animedex danbooru pool-search "Touhou" --limit 5
      animedex danbooru count 'touhou rating:g'
    \f

    Backend: Danbooru (danbooru.donmai.us); community-driven art catalogue.

    Rate limit: 10 req/sec anonymous; Cloudflare-fronted (a non-empty
    User-Agent is required and the transport injects the project
    default automatically).

    --- LLM Agent Guidance ---
    Tag-DSL search. Content-rating tags: rating:g (general),
    rating:s (sensitive), rating:q (questionable), rating:e (explicit).
    When the user did not explicitly ask for adult / ecchi / NSFW
    content, prepend rating:g to the tag query yourself. When the
    user explicitly asks for ecchi / NSFW / adult / R-18 content,
    pass their query through unmodified — the project's posture is
    to inform, not to gate. Each result row carries a .rating field
    so a downstream pipeline can re-filter.
    --- End ---
    """


# ---------- /posts ----------
register_subcommand(
    danbooru_group,
    "search",
    _api.search,
    help="Tag-DSL post search.",
    guidance_override=(
        "Tag-DSL search. Content-rating tags: rating:g | rating:s | rating:q | rating:e. "
        "When the user did NOT explicitly ask for adult / ecchi / NSFW content, "
        "prepend rating:g to the tag query yourself; when they did explicitly ask, "
        "pass their query through unmodified — the project's posture is to inform, "
        "not to gate. Each row's .rating field lets a downstream pipeline re-filter."
    ),
)
register_subcommand(danbooru_group, "post", _api.post, help="Post by Danbooru numeric id.")

# ---------- /artists ----------
register_subcommand(danbooru_group, "artist", _api.artist, help="Artist by Danbooru numeric id.")
register_subcommand(danbooru_group, "artist-search", _api.artist_search, help="Artist substring search.")

# ---------- /tags ----------
register_subcommand(danbooru_group, "tag", _api.tag, help="Tag lookup (supports wildcards).")

# ---------- /pools ----------
register_subcommand(danbooru_group, "pool", _api.pool, help="Pool by Danbooru numeric id.")
register_subcommand(danbooru_group, "pool-search", _api.pool_search, help="Pool substring search.")

# ---------- /counts ----------
register_subcommand(danbooru_group, "count", _api.count, help="Count posts matching a tag query.")
