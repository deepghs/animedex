"""``animedex api ghibli`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_ghibli = make_get_only_subcommand(
    name="ghibli",
    backend_module_name="ghibli",
    docstring="""Issue a live Studio Ghibli API raw request.

    PATH is the URL path under `https://ghibliapi.vercel.app`. The
    high-level `animedex ghibli` commands use a bundled offline
    snapshot; this raw passthrough is for callers who explicitly need
    live upstream data.

    \b
    Docs:
      https://ghibliapi.vercel.app/                  live API reference
      https://github.com/janismdhanbad/studio-ghibli-api   source repository

    \b
    Common paths:
      /films
      /people
      /locations
      /species
      /vehicles
      /films/<id>

    \b
    Examples:
      animedex api ghibli /films
      animedex api ghibli /people -i
      animedex api ghibli /vehicles --debug | jq '.timing'
    \f

    Backend: Studio Ghibli API (ghibliapi.vercel.app).

    Rate limit: not formally published; the transport applies a
    conservative 1 req/sec sustained ceiling with a 5-token burst
    budget.

    --- LLM Agent Guidance ---
    PATH is the URL path under ghibliapi.vercel.app. Common reads:
    /films, /people, /locations, /species, /vehicles, and /<family>/<id>.
    Prefer the high-level offline ghibli commands unless the user asks
    for live data.
    --- End ---
    """,
)
