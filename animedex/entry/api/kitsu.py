"""``animedex api kitsu`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_kitsu = make_get_only_subcommand(
    name="kitsu",
    backend_module_name="kitsu",
    docstring="""Pass through to Kitsu (JSON:API).

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
