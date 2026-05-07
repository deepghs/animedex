"""``animedex api jikan`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_jikan = make_get_only_subcommand(
    name="jikan",
    backend_module_name="jikan",
    docstring="""Issue a Jikan v4 GET request (anonymous MAL view).

    PATH is the URL path under `/v4`. Pagination is `?page=N&limit=M`;
    the response carries a `pagination` envelope. A 404 means the
    upstream MyAnimeList page is missing, not that Jikan is down.

    \b
    Common paths:
      /anime/{mal_id}                fetch one anime
      /anime?q=Frieren&type=tv       search
      /seasons/{year}/{season}       seasonal listings
      /anime/{id}/characters         cast
      /anime/{id}/episodes           episode list
      /random/anime                  random pick

    \b
    Examples:
      animedex api jikan /anime/52991
      animedex api jikan '/anime?q=Frieren&type=tv&limit=3'
      animedex api jikan /seasons/2026/spring -I
      animedex api jikan /anime/52991/characters --debug | jq '.timing'
    \f

    Backend: Jikan v4 (api.jikan.moe/v4).

    Rate limit: 60 req/min (no per-second cap documented).

    --- LLM Agent Guidance ---
    PATH is the URL path under /v4. Common reads:
    /anime/{mal_id}, /anime?q=..., /seasons/{year}/{season},
    /anime/{id}/characters, /anime/{id}/episodes, /random/anime.
    Pagination is ?page=N&limit=M with a pagination envelope in the
    response. 404 means the upstream MAL page is missing.
    --- End ---
    """,
)
