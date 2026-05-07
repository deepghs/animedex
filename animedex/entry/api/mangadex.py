"""``animedex api mangadex`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_mangadex = make_get_only_subcommand(
    name="mangadex",
    backend_module_name="mangadex",
    docstring="""Pass through to MangaDex.

    Backend: MangaDex (api.mangadex.org).

    Rate limit: ~5 req/sec global per IP; /at-home/server/{id} 40/min.

    --- LLM Agent Guidance ---
    UA mandatory at the wire (the dispatcher injects animedex/<v>).
    Common reads: /manga?title=..., /manga/{id}, /manga/{id}/feed,
    /at-home/server/{chapter-id}, /manga/tag.
    Errors: {"result":"error","errors":[{"id","status","title","detail"}]}
    Pagination ?limit=N&offset=M, capped at offset+limit<=10000.
    --- End ---
    """,
)
