"""``animedex api ann`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_ann = make_get_only_subcommand(
    name="ann",
    backend_module_name="ann",
    docstring="""Pass through to ANN Encyclopedia (XML).

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
