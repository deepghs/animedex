"""``animedex api nekos`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_nekos = make_get_only_subcommand(
    name="nekos",
    backend_module_name="nekos",
    docstring="""Issue a nekos.best v2 GET request (anonymous, SFW image / GIF API).

    PATH is the URL path under `/api/v2`. The collection is read-only
    JSON; every category is SFW, so consumers do not have to re-filter
    on rating.

    \b
    Docs:
      https://docs.nekos.best/                       project docs index
      https://docs.nekos.best/getting-started/api-endpoints.html   v2 endpoint reference
      https://nekos.best/                             project home

    \b
    Common paths:
      /endpoints                            list categories + per-category file format
      /husbando                             one random husbando image
      /husbando?amount=5                    five random husbando images
      /neko                                 one random neko image
      /search?query=Frieren&type=1          metadata search across all categories (images)
      /search?query=loop&type=2&amount=3    metadata search across GIF categories

    \b
    Examples:
      animedex api nekos /endpoints
      animedex api nekos '/husbando?amount=3'
      animedex api nekos '/search?query=Frieren&type=1&amount=5' -i
      animedex api nekos /neko --debug | jq '.timing'
    \f

    Backend: nekos.best v2 (nekos.best/api/v2).

    Rate limit: anonymous; no formal cap published (treat ~10 req/sec
    as a soft ceiling).

    --- LLM Agent Guidance ---
    PATH is the URL path under /api/v2. Common reads:
    /endpoints (categories + file formats), /<category>?amount=N (1-20
    random images / GIFs), /search?query=...&type=1|2&category=...
    &amount=N (metadata search). Every category is SFW. A 404 on
    /<category> means the category name is unknown — fetch /endpoints
    to discover the valid set.
    --- End ---
    """,
)
