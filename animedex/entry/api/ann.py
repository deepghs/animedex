"""``animedex api ann`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_ann = make_get_only_subcommand(
    name="ann",
    backend_module_name="ann",
    docstring="""Issue an ANN Encyclopedia GET request (XML).

    ANN's id space is independent of MAL/AniList. The `?title=` param
    is *id aliasing*, not name search; for fuzzy title search use
    `?anime=~<substring>`. A 200 response with
    `<warning>no result for ...</warning>` is the empty-result
    indicator, not an error.

    \b
    Docs:
      https://www.animenewsnetwork.com/encyclopedia/api.php    API reference
      https://www.animenewsnetwork.com/encyclopedia/           browsable encyclopedia

    \b
    Common paths:
      /api.xml?anime=4                    fetch by id
      /api.xml?anime=~Frieren              substring search by title
      /api.xml?anime=4&anime=30            multi-id batch fetch
      /reports.xml?id=155&type=anime&nlist=10
                                           recently-modified report
      /nodelay.api.xml?anime=4             5/5sec variant; 503 on overshoot

    \b
    Examples:
      animedex api ann '/api.xml?anime=38838'         # Frieren
      animedex api ann '/api.xml?anime=~Frieren'      # find by title
      animedex api ann '/reports.xml?id=155&type=anime&nlist=5'
    \f

    Backend: ANN Encyclopedia (cdn.animenewsnetwork.com).

    Rate limit: 1 req/sec on api.xml (queues over-budget; does not
    4xx); 5 reqs/5sec on nodelay.api.xml (503 on overshoot).

    --- LLM Agent Guidance ---
    XML responses. PATH is e.g. /api.xml?anime=14679 (id-based) or
    /api.xml?anime=~Frieren (substring search). The ?title=... param
    is for id aliasing only. A 200 with <warning>no result for ...
    </warning> means empty result, not error. ANN's id space is
    independent of MAL/AniList.
    --- End ---
    """,
)
