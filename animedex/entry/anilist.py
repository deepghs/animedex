"""``animedex anilist <subcommand>`` Click group + bindings.

Each public function in :mod:`animedex.backends.anilist` is bound as
a Click subcommand via :func:`register_subcommand`. The auto-binder
infers positional arguments from the Python signature and exposes
common flags (``--json``, ``--jq``, ``--no-cache``, ``--cache``,
``--rate``, ``--no-source``) on every subcommand.
"""

from __future__ import annotations

import click

from animedex.backends import anilist as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="anilist")
def anilist_group() -> None:
    """High-level AniList commands (anonymous read-only).

    \b
    Docs:
      https://docs.anilist.co/                              official reference
      https://anilist.co/graphiql                            live schema browser

    \b
    Examples:
      animedex anilist show 154587
      animedex anilist search Frieren --per-page 5
      animedex anilist character 11 --json
      animedex anilist trending --jq '.[].title.romaji'
      animedex anilist user AniList
    \f

    Backend: AniList (graphql.anilist.co).

    Rate limit: 30 req/min (anonymous; degraded from baseline 90/min).

    --- LLM Agent Guidance ---
    The subcommand surface covers every anonymous Query root on the
    AniList GraphQL schema. Use ``show <id>`` for single Media,
    ``search <q>`` for fuzzy title match, ``schedule <year> <season>``
    for calendar slices, ``trending`` for what's hot. Long-tail
    subcommands (``review``, ``recommendation``, ``thread``,
    ``activity``, ``following`` / ``follower``) cover the social
    surface.

    Token-required commands (``viewer``, ``notification``,
    ``markdown``, ``ani-chart-user``) are registered but raise
    auth-required at runtime; the OAuth flow has not landed yet.
    --- End ---
    """


# ---------- core ----------
register_subcommand(anilist_group, "show", _api.show, help="Show one Media (anime/manga) by AniList id.")
register_subcommand(anilist_group, "search", _api.search, help="Search Media by title.")
register_subcommand(anilist_group, "character", _api.character, help="Show one Character by id.")
register_subcommand(anilist_group, "character-search", _api.character_search, help="Search characters.")
register_subcommand(anilist_group, "staff", _api.staff, help="Show one Staff by id.")
register_subcommand(anilist_group, "staff-search", _api.staff_search, help="Search staff.")
register_subcommand(anilist_group, "studio", _api.studio, help="Show one Studio by id.")
register_subcommand(anilist_group, "studio-search", _api.studio_search, help="Search studios.")
register_subcommand(anilist_group, "schedule", _api.schedule, help="Anime by season/year.")
register_subcommand(anilist_group, "trending", _api.trending, help="Currently-trending anime.")
register_subcommand(anilist_group, "user", _api.user, help="Public user profile by name.")
register_subcommand(anilist_group, "user-search", _api.user_search, help="Search users.")

# ---------- collections ----------
register_subcommand(anilist_group, "genre-collection", _api.genre_collection, help="Full genre vocabulary.")
register_subcommand(anilist_group, "media-tag-collection", _api.media_tag_collection, help="Full tag taxonomy.")
register_subcommand(anilist_group, "site-statistics", _api.site_statistics, help="AniList-wide entity counts.")
register_subcommand(
    anilist_group,
    "external-link-source-collection",
    _api.external_link_source_collection,
    help="Registered external sites.",
)

# ---------- long-tail ----------
register_subcommand(anilist_group, "airing-schedule", _api.airing_schedule, help="Upcoming-episode schedule.")
register_subcommand(anilist_group, "media-trend", _api.media_trend, help="Daily score / popularity trend rows.")
register_subcommand(anilist_group, "review", _api.review, help="User reviews for a Media.")
register_subcommand(anilist_group, "recommendation", _api.recommendation, help="Recommendations rooted at a Media.")
register_subcommand(anilist_group, "thread", _api.thread, help="Forum thread search.")
register_subcommand(anilist_group, "thread-comment", _api.thread_comment, help="Comments on a forum thread.")
register_subcommand(anilist_group, "activity", _api.activity, help="Recent global activity.")
register_subcommand(anilist_group, "activity-reply", _api.activity_reply, help="Replies to a public activity item.")
register_subcommand(anilist_group, "following", _api.following, help="Users a given user follows.")
register_subcommand(anilist_group, "follower", _api.follower, help="Users following a given user.")
register_subcommand(
    anilist_group,
    "media-list-public",
    _api.media_list_public,
    help="Public user's media list rows.",
    guidance_override=(
        "Returns rows from a named AniList user's *public* media list. "
        "Same privacy considerations as Jikan user-favorites: the list is "
        "user-public so single-user lookups are fine, but aggregating across "
        "many users to build per-user fingerprints (favourites x history x "
        "follows) is a privacy concern that requires express operator "
        "authorisation."
    ),
)
register_subcommand(
    anilist_group,
    "media-list-collection-public",
    _api.media_list_collection_public,
    help="Public user's full list grouped by status.",
)

# ---------- token-required (raise auth-required until OAuth lands) ----------
register_subcommand(anilist_group, "viewer", _api.viewer, help="Current user. Token required.")
register_subcommand(anilist_group, "notification", _api.notification, help="Notifications. Token required.")
register_subcommand(anilist_group, "markdown", _api.markdown, help="Markdown render. Token required.")
register_subcommand(anilist_group, "ani-chart-user", _api.ani_chart_user, help="AniChart user. Token required.")
