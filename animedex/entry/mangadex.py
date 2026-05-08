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

# ---------- /chapter, /cover ----------
register_subcommand(mangadex_group, "chapter", _api.chapter, help="Chapter by UUID.")
register_subcommand(mangadex_group, "cover", _api.cover, help="Cover by UUID.")
