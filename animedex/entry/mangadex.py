"""``animedex mangadex <subcommand>`` Click group + bindings.

Five subcommands wrapping the anonymous JSON read endpoints
(search / show / feed / chapter / cover). Bindings are programmatic
via :func:`register_subcommand`.

The page-image fetcher (``/at-home/server/{chapterId}``) is
intentionally not wired here; it has its own short-lived-base-URL
and HTTP/2 concurrency-cap concerns and lands separately.
"""

from __future__ import annotations

import click

from animedex.backends import mangadex as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="mangadex")
def mangadex_group() -> None:
    """High-level MangaDex commands (anonymous; scanlation aggregator).

    \b
    Docs:
      https://api.mangadex.org/docs/                       OpenAPI / endpoint reference
      https://mangadex.org/                                project home

    \b
    Examples:
      animedex mangadex search Berserk --limit 3
      animedex mangadex show 801513ba-a712-498c-8f57-cae55b38cc92
      animedex mangadex feed 801513ba-a712-498c-8f57-cae55b38cc92 --lang en --limit 5
      animedex mangadex chapter <chapter-uuid>
      animedex mangadex cover <cover-uuid>
    \f

    Backend: MangaDex (api.mangadex.org); scanlation aggregator.

    Rate limit: 5 req/sec anonymous (transport bucket matches).

    --- LLM Agent Guidance ---
    Read-only manga / chapter / cover lookup. The catalogue is
    scanlation-driven, so legal posture varies per series — surface
    what the upstream returns; do not pre-filter. Page-image fetching
    is deferred (At-Home reader; lands separately). Multiple
    translations of the same chapter are normal; filter by --lang at
    the call site.
    --- End ---
    """


# ---------- /manga ----------
register_subcommand(mangadex_group, "search", _api.search, help="Search manga by free-text title.")
register_subcommand(mangadex_group, "show", _api.show, help="Manga by MangaDex UUID (full payload).")
register_subcommand(
    mangadex_group,
    "feed",
    _api.feed,
    help="List chapters for one manga (filter by --lang).",
)

# ---------- /manga aux ----------
register_subcommand(mangadex_group, "aggregate", _api.aggregate, help="Volume / chapter aggregation tree for a manga.")
register_subcommand(mangadex_group, "recommendation", _api.recommendation, help="Manga recommendations for one manga.")
register_subcommand(mangadex_group, "random-manga", _api.random_manga, help="Random manga.")
register_subcommand(mangadex_group, "manga-tag", _api.manga_tag, help="Full tag taxonomy.")

# ---------- /chapter, /cover ----------
register_subcommand(mangadex_group, "chapter", _api.chapter, help="Chapter by UUID.")
register_subcommand(mangadex_group, "chapter-search", _api.chapter_search, help="Paginated chapter listing.")
register_subcommand(mangadex_group, "cover", _api.cover, help="Cover by UUID.")
register_subcommand(mangadex_group, "cover-search", _api.cover_search, help="Paginated cover listing.")

# ---------- /author ----------
register_subcommand(mangadex_group, "author", _api.author, help="Author by UUID.")
register_subcommand(mangadex_group, "author-search", _api.author_search, help="Paginated author listing.")

# ---------- /group (scanlation group) ----------
register_subcommand(mangadex_group, "group", _api.group, help="Scanlation group by UUID.")
register_subcommand(mangadex_group, "group-search", _api.group_search, help="Paginated scanlation group listing.")

# ---------- /list (custom lists) ----------
register_subcommand(mangadex_group, "list-show", _api.list_show, help="Custom list by UUID (public lists only).")
register_subcommand(mangadex_group, "list-feed", _api.list_feed, help="Chapter feed for one custom list.")

# ---------- /user (public read) ----------
register_subcommand(mangadex_group, "user", _api.user, help="User by UUID (public profile).")
register_subcommand(mangadex_group, "user-lists", _api.user_lists, help="One user's public custom lists.")

# ---------- /statistics ----------
register_subcommand(
    mangadex_group, "statistics-manga", _api.statistics_manga, help="Read / follow / rating stats for one manga."
)
register_subcommand(
    mangadex_group,
    "statistics-manga-batch",
    _api.statistics_manga_batch,
    help="Stats for many manga at once (--manga UUID, repeatable).",
)
register_subcommand(mangadex_group, "statistics-chapter", _api.statistics_chapter, help="Read stats for one chapter.")
register_subcommand(
    mangadex_group,
    "statistics-chapter-batch",
    _api.statistics_chapter_batch,
    help="Stats for many chapters at once (--chapter UUID, repeatable).",
)
register_subcommand(mangadex_group, "statistics-group", _api.statistics_group, help="Stats for one scanlation group.")

# ---------- /report ----------
register_subcommand(
    mangadex_group,
    "report-reasons",
    _api.report_reasons,
    help="Available report reasons for a category (manga / chapter / scanlation_group / user / author).",
)

# ---------- /ping ----------
register_subcommand(mangadex_group, "ping", _api.ping, help="Cheap upstream-liveness probe.")
