"""``animedex api danbooru`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_danbooru = make_get_only_subcommand(
    name="danbooru",
    backend_module_name="danbooru",
    docstring="""Pass through to Danbooru.

    Backend: Danbooru (danbooru.donmai.us).

    Rate limit: 10 req/sec for reads.

    --- LLM Agent Guidance ---
    UA mandatory (Cloudflare-enforced; empty UA gets a challenge HTML).
    Tag DSL on /posts.json: positional tags include, -tag excludes,
    rating:g|s|q|e selects content class, score:>N / score:<N filter,
    order:score|date|random sets order. Pagination ?page=N&limit=M
    plus cursor variants ?page=b<id> (before) and ?page=a<id> (after).
    Common reads: /posts.json?tags=..., /posts/{id}.json,
    /tags.json?search[name_matches]=touhou*, /counts/posts.json?tags=...
    --- End ---
    """,
)
