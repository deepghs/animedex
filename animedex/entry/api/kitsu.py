"""``animedex api kitsu`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_kitsu = make_get_only_subcommand(
    name="kitsu",
    backend_module_name="kitsu",
    docstring="""Issue a Kitsu raw request (JSON:API).

    The dispatcher injects ``Accept: application/vnd.api+json``
    automatically. Pagination uses ``page[offset]=N&page[limit]=M``;
    set includes via ``?include=streamingLinks,mappings``. Both
    ``kitsu.io/api/edge`` and ``kitsu.app/api/edge`` serve identical
    data; this command targets ``.io`` by default.

    \b
    Docs:
      https://kitsu.docs.apiary.io/                Apiary reference
      https://hummingbird-me.github.io/api-docs/   markdown mirror
      https://jsonapi.org/                          JSON:API spec

    \b
    Common paths:
      /anime?filter[text]=Frieren           search
      /anime/{id}                            fetch one
      /anime/{id}/streaming-links            legal streaming destinations
      /anime/{id}/mappings                   cross-source ID map (anilist/mal/...)
      /manga?filter[text]=Berserk            manga search

    \b
    Examples:
      animedex api kitsu /anime/46474
      animedex api kitsu '/anime?filter[text]=Frieren&include=streamingLinks&page[limit]=1'
      animedex api kitsu /anime/46474/mappings --debug | jq '.body_text | fromjson | .data[].attributes'
    \f

    Backend: Kitsu (kitsu.io/api/edge canonical; kitsu.app/api/edge
    accepted as alias).

    Rate limit: not formally published; self-imposed 10 req/sec.

    --- LLM Agent Guidance ---
    JSON:API. The dispatcher injects Accept: application/vnd.api+json.
    Pagination uses page[offset]=N&page[limit]=M. Common reads:
    /anime?filter[text]=..., /anime/{id}, /anime/{id}/streaming-links,
    /anime/{id}/mappings (cross-source IDs).
    --- End ---
    """,
)
