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

# ---------- /anime/{id}/<sub> ----------
register_subcommand(kitsu_group, "anime-characters", _api.anime_characters, help="Cast for one anime.")
register_subcommand(kitsu_group, "anime-staff", _api.anime_staff, help="Production staff for one anime.")
register_subcommand(kitsu_group, "anime-episodes", _api.anime_episodes, help="Episode list for one anime.")
register_subcommand(kitsu_group, "anime-reviews", _api.anime_reviews, help="User reviews for one anime.")
register_subcommand(kitsu_group, "anime-genres", _api.anime_genres, help="Genres tagged on one anime.")
register_subcommand(kitsu_group, "anime-categories", _api.anime_categories, help="Categories tagged on one anime.")
register_subcommand(
    kitsu_group, "anime-relations", _api.anime_relations, help="Sequel / prequel / spin-off relationships."
)
register_subcommand(kitsu_group, "anime-productions", _api.anime_productions, help="Producer / studio / licensor list.")

# ---------- /manga/{id}/<sub> ----------
register_subcommand(kitsu_group, "manga-characters", _api.manga_characters, help="Cast for one manga.")
register_subcommand(kitsu_group, "manga-staff", _api.manga_staff, help="Production staff for one manga.")
register_subcommand(kitsu_group, "manga-chapters", _api.manga_chapters, help="Chapter list for one manga.")
register_subcommand(kitsu_group, "manga-genres", _api.manga_genres, help="Genres tagged on one manga.")

# ---------- /characters ----------
register_subcommand(kitsu_group, "character", _api.character, help="Character by Kitsu numeric id.")
register_subcommand(kitsu_group, "character-search", _api.character_search, help="Free-text character search.")

# ---------- /people ----------
register_subcommand(kitsu_group, "person", _api.person, help="Person (VA / staff) by Kitsu numeric id.")
register_subcommand(kitsu_group, "person-search", _api.person_search, help="Free-text person search.")
register_subcommand(kitsu_group, "person-voices", _api.person_voices, help="Voice-acting credits for one person.")
register_subcommand(
    kitsu_group, "person-castings", _api.person_castings, help="Production-staff credits for one person."
)

# ---------- /producers ----------
register_subcommand(kitsu_group, "producer", _api.producer, help="Producer by Kitsu numeric id.")
register_subcommand(kitsu_group, "producers", _api.producers, help="All producers.")

# ---------- /genres ----------
register_subcommand(kitsu_group, "genre", _api.genre, help="Genre by Kitsu numeric id.")
register_subcommand(kitsu_group, "genres", _api.genres, help="All genres (legacy taxonomy).")

# ---------- /categories ----------
register_subcommand(kitsu_group, "category", _api.category, help="Category by Kitsu numeric id.")
register_subcommand(kitsu_group, "categories", _api.categories, help="Top-level Kitsu categories.")

# ---------- /streamers ----------
register_subcommand(kitsu_group, "streamers", _api.streamers, help="All registered streamers.")

# ---------- /franchises ----------
register_subcommand(kitsu_group, "franchise", _api.franchise, help="Franchise by Kitsu numeric id.")
register_subcommand(kitsu_group, "franchises", _api.franchises, help="All franchises.")

# ---------- /trending ----------
register_subcommand(kitsu_group, "trending-manga", _api.trending_manga, help="Front-page trending manga rail.")

# ---------- /users (public read) ----------
register_subcommand(kitsu_group, "user", _api.user, help="One user's public profile.")
register_subcommand(kitsu_group, "user-library", _api.user_library, help="A user's public anime/manga library.")
register_subcommand(kitsu_group, "user-stats", _api.user_stats, help="A user's public consumption stats.")
