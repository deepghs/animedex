"""``animedex api mangadex`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_mangadex = make_get_only_subcommand(
    name="mangadex",
    backend_module_name="mangadex",
    docstring="""Issue a MangaDex raw request.

    UA is mandatory at the wire (empty UA returns HTTP 400); the
    dispatcher injects `animedex/<version>` automatically. Pagination
    is `?limit=N&offset=M` with `offset+limit<=10000`. Errors land
    as `{"result":"error","errors":[{"id","status","title","detail"}]}`.

    \b
    Docs:
      https://api.mangadex.org/docs/             Swagger / endpoint reference
      https://api.mangadex.org/docs/2-limitations/   rate limits + headers
      https://api.mangadex.org/docs/swagger.html    interactive Swagger UI

    \b
    Common paths:
      /manga?title=Frieren                   search by title
      /manga/{uuid}                          fetch one
      /manga/{uuid}/feed?translatedLanguage[]=en   chapter feed
      /at-home/server/{chapter-uuid}         page-image base URL (40/min cap)
      /manga/tag                             tag taxonomy
      /cover?manga[]={uuid}                  cover assets

    \b
    Examples:
      animedex api mangadex '/manga?title=Berserk&limit=2'
      animedex api mangadex /manga/801513ba-a712-498c-8f57-cae55b38cc92
      animedex api mangadex '/manga/801513ba-a712-498c-8f57-cae55b38cc92/feed?translatedLanguage[]=en&limit=1'
    \f

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
