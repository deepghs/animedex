"""``animedex shikimori <subcommand>`` Click group + bindings."""

from __future__ import annotations

import click

from animedex.backends import shikimori as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="shikimori")
def shikimori_group() -> None:
    """High-level Shikimori commands (anonymous; REST catalogue).

    \b
    Docs:
      https://shikimori.io/api/doc/2.0       v2 reference
      https://shikimori.io/api/doc/1.0       v1 reference
      https://shikimori.io/api/doc/graphql   GraphQL reference

    \b
    Examples:
      animedex shikimori show 52991
      animedex shikimori search Frieren --limit 2
      animedex shikimori calendar --limit 3
      animedex shikimori screenshots 52991
      animedex shikimori videos 52991
    \f

    Backend: Shikimori (shikimori.io; shikimori.one accepted alias).

    Rate limit: 5 RPS / 90 RPM.

    --- LLM Agent Guidance ---
    Read-only Shikimori catalogue wrapper. The project transport
    injects a default User-Agent, while explicit caller overrides win.
    High-level commands cover the anonymous REST entity surfaces for
    anime, manga, ranobe, clubs, publishers, people, taxonomies, and
    anime rails; use ``animedex api shikimori /api/graphql --graphql
    ...`` for GraphQL queries.
    --- End ---
    """


register_subcommand(shikimori_group, "calendar", _api.calendar, help="Upcoming and currently-airing schedule.")
register_subcommand(shikimori_group, "search", _api.search, help="Search Shikimori anime by title.")
register_subcommand(shikimori_group, "show", _api.show, help="Anime by Shikimori numeric id.")
register_subcommand(shikimori_group, "manga-search", _api.manga_search, help="Search Shikimori manga by title.")
register_subcommand(shikimori_group, "manga-show", _api.manga_show, help="Manga by Shikimori numeric id.")
register_subcommand(shikimori_group, "ranobe-search", _api.ranobe_search, help="Search Shikimori ranobe by title.")
register_subcommand(shikimori_group, "ranobe-show", _api.ranobe_show, help="Ranobe by Shikimori numeric id.")
register_subcommand(shikimori_group, "club-search", _api.club_search, help="Search Shikimori clubs.")
register_subcommand(shikimori_group, "club-show", _api.club_show, help="Club by Shikimori numeric id.")
register_subcommand(shikimori_group, "publishers", _api.publishers, help="Manga publisher taxonomy.")
register_subcommand(shikimori_group, "people-search", _api.people_search, help="Search top-level Shikimori people.")
register_subcommand(shikimori_group, "person", _api.person, help="Top-level person by Shikimori numeric id.")
register_subcommand(shikimori_group, "screenshots", _api.screenshots, help="Screenshot list for one anime.")
register_subcommand(shikimori_group, "videos", _api.videos, help="Promo and episode-preview videos for one anime.")
register_subcommand(shikimori_group, "roles", _api.roles, help="Raw character/person role rows for one anime.")
register_subcommand(shikimori_group, "characters", _api.characters, help="Character references for one anime.")
register_subcommand(shikimori_group, "staff", _api.staff, help="Staff and voice-person references for one anime.")
register_subcommand(shikimori_group, "similar", _api.similar, help="Anime similar to one anime.")
register_subcommand(shikimori_group, "related", _api.related, help="Related anime, manga, and franchise rows.")
register_subcommand(shikimori_group, "external-links", _api.external_links, help="External links for one anime.")
register_subcommand(shikimori_group, "topics", _api.topics, help="Discussion topics for one anime.")
register_subcommand(shikimori_group, "studios", _api.studios, help="Studio taxonomy.")
register_subcommand(shikimori_group, "genres", _api.genres, help="Genre taxonomy.")
