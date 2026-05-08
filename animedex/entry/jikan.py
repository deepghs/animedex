"""``animedex jikan <subcommand>`` Click group + bindings.

87 subcommands wrapping every anonymous Jikan v4 endpoint. Bindings
are programmatic via :func:`register_subcommand`, so the group's
``--help`` covers the full API surface without 87 hand-written
wrappers.
"""

from __future__ import annotations

import click

from animedex.backends import jikan as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="jikan")
def jikan_group() -> None:
    """High-level Jikan (MyAnimeList) commands (anonymous).

    \b
    Docs:
      https://docs.api.jikan.moe/                       OpenAPI reference
      https://jikan.moe/                                 project home

    \b
    Examples:
      animedex jikan show 52991
      animedex jikan search Frieren --limit 5
      animedex jikan character-show 11
      animedex jikan top-anime --filter bypopularity
      animedex jikan season 2024 spring --limit 10
      animedex jikan random-anime
      animedex jikan watch-episodes
    \f

    Backend: Jikan v4 (api.jikan.moe).

    Rate limit: 60 req/min (3 req/sec).

    --- LLM Agent Guidance ---
    Every endpoint is anonymous; no token concept exists. Core
    entities (anime, manga, character, person, producer, magazine,
    genre, club, user) return typed dataclasses; long-tail sub-
    endpoints (news / forum / videos / pictures / statistics /
    moreinfo / recommendations / userupdates / reviews / relations /
    themes / external / streaming / episodes / watch / schedules)
    return :class:`JikanGenericResponse` (a permissive
    ``extra='allow'`` envelope). Use ``--jq`` to filter the JSON
    output structurally when only specific fields are needed.
    --- End ---
    """


# ---------- /anime ----------
register_subcommand(jikan_group, "show", _api.show, help="Anime by MAL id (full payload).")
register_subcommand(
    jikan_group,
    "search",
    _api.search,
    help="Search anime.",
    guidance_override=(
        "Search returns anime regardless of content rating by default. Pass --sfw "
        "true if the user did not explicitly ask for adult/ecchi material. When the "
        "user did explicitly request such content, pass it through unmodified — "
        "the project's posture is to inform, not to gate. The 'rating' field on "
        "each row tags general/PG-13/R+/Rx so a downstream pipeline can re-filter."
    ),
)
register_subcommand(jikan_group, "anime-characters", _api.anime_characters, help="Characters in an anime.")
register_subcommand(jikan_group, "anime-staff", _api.anime_staff, help="Anime production staff.")
register_subcommand(jikan_group, "anime-episodes", _api.anime_episodes, help="Anime episode list.")
register_subcommand(jikan_group, "anime-episode", _api.anime_episode, help="Single anime episode.")
register_subcommand(jikan_group, "anime-news", _api.anime_news, help="News articles for an anime.")
register_subcommand(jikan_group, "anime-forum", _api.anime_forum, help="Forum topics for an anime.")
register_subcommand(jikan_group, "anime-videos", _api.anime_videos, help="Anime PVs / OPs / EDs / music videos.")
register_subcommand(jikan_group, "anime-videos-episodes", _api.anime_videos_episodes, help="Episode videos.")
register_subcommand(jikan_group, "anime-pictures", _api.anime_pictures, help="Anime image gallery.")
register_subcommand(jikan_group, "anime-statistics", _api.anime_statistics, help="Anime score distribution.")
register_subcommand(jikan_group, "anime-moreinfo", _api.anime_moreinfo, help="Extra anime synopsis/notes.")
register_subcommand(jikan_group, "anime-recommendations", _api.anime_recommendations, help="User-recommended anime.")
register_subcommand(jikan_group, "anime-userupdates", _api.anime_userupdates, help="Recent user list updates.")
register_subcommand(jikan_group, "anime-reviews", _api.anime_reviews, help="Anime reviews.")
register_subcommand(jikan_group, "anime-relations", _api.anime_relations, help="Sequels / prequels / adaptations.")
register_subcommand(jikan_group, "anime-themes", _api.anime_themes, help="Anime opening / ending themes.")
register_subcommand(jikan_group, "anime-external", _api.anime_external, help="Anime external site links.")
register_subcommand(jikan_group, "anime-streaming", _api.anime_streaming, help="Anime streaming providers.")

# ---------- /manga ----------
register_subcommand(jikan_group, "manga-show", _api.manga_show, help="Manga by MAL id (full).")
register_subcommand(jikan_group, "manga-search", _api.manga_search, help="Search manga.")
register_subcommand(jikan_group, "manga-characters", _api.manga_characters, help="Characters in a manga.")
register_subcommand(jikan_group, "manga-news", _api.manga_news, help="Manga news articles.")
register_subcommand(jikan_group, "manga-forum", _api.manga_forum, help="Forum topics for a manga.")
register_subcommand(jikan_group, "manga-pictures", _api.manga_pictures, help="Manga image gallery.")
register_subcommand(jikan_group, "manga-statistics", _api.manga_statistics, help="Manga score / status distribution.")
register_subcommand(jikan_group, "manga-moreinfo", _api.manga_moreinfo, help="Extra manga notes.")
register_subcommand(jikan_group, "manga-recommendations", _api.manga_recommendations, help="Recommended manga.")
register_subcommand(jikan_group, "manga-userupdates", _api.manga_userupdates, help="Recent manga user updates.")
register_subcommand(jikan_group, "manga-reviews", _api.manga_reviews, help="Manga reviews.")
register_subcommand(jikan_group, "manga-relations", _api.manga_relations, help="Related manga.")
register_subcommand(jikan_group, "manga-external", _api.manga_external, help="Manga external links.")

# ---------- /characters ----------
register_subcommand(jikan_group, "character-show", _api.character_show, help="Character by MAL id (full).")
register_subcommand(jikan_group, "character-search", _api.character_search, help="Search characters.")
register_subcommand(jikan_group, "character-anime", _api.character_anime, help="Anime appearances.")
register_subcommand(jikan_group, "character-manga", _api.character_manga, help="Manga appearances.")
register_subcommand(jikan_group, "character-voices", _api.character_voices, help="Voice actors per language.")
register_subcommand(jikan_group, "character-pictures", _api.character_pictures, help="Character images.")

# ---------- /people ----------
register_subcommand(jikan_group, "person-show", _api.person_show, help="Person by MAL id (full).")
register_subcommand(jikan_group, "person-search", _api.person_search, help="Search staff/creators/VAs.")
register_subcommand(jikan_group, "person-anime", _api.person_anime, help="Person anime credits.")
register_subcommand(jikan_group, "person-voices", _api.person_voices, help="Person VA roles.")
register_subcommand(jikan_group, "person-manga", _api.person_manga, help="Person manga authorship.")
register_subcommand(jikan_group, "person-pictures", _api.person_pictures, help="Person photographs.")

# ---------- producers / magazines / genres / clubs ----------
register_subcommand(jikan_group, "producer-show", _api.producer_show, help="Producer by id.")
register_subcommand(jikan_group, "producer-search", _api.producer_search, help="Search producers.")
register_subcommand(jikan_group, "producer-external", _api.producer_external, help="Producer external links.")
register_subcommand(jikan_group, "magazines", _api.magazines, help="Search manga magazines.")
register_subcommand(jikan_group, "genres-anime", _api.genres_anime, help="Anime genre taxonomy.")
register_subcommand(jikan_group, "genres-manga", _api.genres_manga, help="Manga genre taxonomy.")
register_subcommand(jikan_group, "clubs", _api.clubs, help="Search clubs.")
register_subcommand(jikan_group, "club-show", _api.club_show, help="Club by id.")
register_subcommand(jikan_group, "club-members", _api.club_members, help="Club members.")
register_subcommand(jikan_group, "club-staff", _api.club_staff, help="Club staff.")
register_subcommand(jikan_group, "club-relations", _api.club_relations, help="Club related clubs.")

# ---------- /users ----------
register_subcommand(jikan_group, "user-show", _api.user_show, help="MAL user (full).")
register_subcommand(jikan_group, "user-basic", _api.user_basic, help="MAL user (basic).")
register_subcommand(jikan_group, "user-statistics", _api.user_statistics, help="User watching/reading stats.")
register_subcommand(
    jikan_group,
    "user-favorites",
    _api.user_favorites,
    help="User favorite anime/manga/characters/people.",
    guidance_override=(
        "Surfaces a named MAL user's public-favourites list. The list is "
        "user-public on MAL, so reading it does not exfiltrate private state. "
        "Aggregating across many users (e.g. building a per-user fingerprint "
        "from favourites + history + clubs) is a privacy concern even when "
        "every individual call is to a public profile — do not stitch this "
        "endpoint with /users/{name}/history or /users/{name}/friends without "
        "the operator's express authorisation. Single-user lookups are fine."
    ),
)
register_subcommand(jikan_group, "user-userupdates", _api.user_userupdates, help="User list update history.")
register_subcommand(jikan_group, "user-about", _api.user_about, help="User about-me block.")
register_subcommand(jikan_group, "user-history", _api.user_history, help="User recent activity.")
register_subcommand(jikan_group, "user-friends", _api.user_friends, help="User friend list.")
register_subcommand(jikan_group, "user-reviews", _api.user_reviews, help="User authored reviews.")
register_subcommand(
    jikan_group, "user-recommendations", _api.user_recommendations, help="User authored recommendations."
)
register_subcommand(jikan_group, "user-clubs", _api.user_clubs, help="User club memberships.")
register_subcommand(jikan_group, "user-search", _api.user_search, help="Search users.")
register_subcommand(jikan_group, "user-by-mal-id", _api.user_by_mal_id, help="Resolve numeric MAL user id.")

# ---------- /seasons /top /random /recommendations /reviews /watch ----------
register_subcommand(jikan_group, "seasons-list", _api.seasons_list, help="List of all available seasons.")
register_subcommand(jikan_group, "seasons-now", _api.seasons_now, help="Current season anime.")
register_subcommand(jikan_group, "seasons-upcoming", _api.seasons_upcoming, help="Upcoming season anime.")
register_subcommand(jikan_group, "season", _api.season, help="Anime aired in given season.")
register_subcommand(jikan_group, "top-anime", _api.top_anime, help="Top anime.")
register_subcommand(jikan_group, "top-manga", _api.top_manga, help="Top manga.")
register_subcommand(jikan_group, "top-characters", _api.top_characters, help="Top characters.")
register_subcommand(jikan_group, "top-people", _api.top_people, help="Top people.")
register_subcommand(jikan_group, "top-reviews", _api.top_reviews, help="Most helpful reviews.")
register_subcommand(jikan_group, "schedules", _api.schedules, help="Weekly airing schedule.")
register_subcommand(jikan_group, "random-anime", _api.random_anime, help="Random anime entry.")
register_subcommand(jikan_group, "random-manga", _api.random_manga, help="Random manga entry.")
register_subcommand(jikan_group, "random-character", _api.random_character, help="Random character.")
register_subcommand(jikan_group, "random-person", _api.random_person, help="Random person.")
register_subcommand(jikan_group, "random-user", _api.random_user, help="Random user.")
register_subcommand(
    jikan_group, "recommendations-anime", _api.recommendations_anime, help="Recent anime recommendations."
)
register_subcommand(
    jikan_group, "recommendations-manga", _api.recommendations_manga, help="Recent manga recommendations."
)
register_subcommand(jikan_group, "reviews-anime", _api.reviews_anime, help="Recent anime reviews.")
register_subcommand(jikan_group, "reviews-manga", _api.reviews_manga, help="Recent manga reviews.")
register_subcommand(jikan_group, "watch-episodes", _api.watch_episodes, help="Recent episode releases.")
register_subcommand(jikan_group, "watch-episodes-popular", _api.watch_episodes_popular, help="Popular episodes.")
register_subcommand(jikan_group, "watch-promos", _api.watch_promos, help="Recent promotional videos.")
register_subcommand(jikan_group, "watch-promos-popular", _api.watch_promos_popular, help="Popular promotional videos.")
