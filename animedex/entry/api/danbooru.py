"""``animedex api danbooru`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_danbooru = make_get_only_subcommand(
    name="danbooru",
    backend_module_name="danbooru",
    docstring="""Issue a Danbooru GET request.

    Empty UA hits the Cloudflare challenge page; the dispatcher
    injects `animedex/<version>` automatically and that passes.

    \b
    Docs:
      https://danbooru.donmai.us/wiki_pages/help:api          API help
      https://danbooru.donmai.us/wiki_pages/help:cheatsheet   tag DSL cheatsheet
      https://danbooru.donmai.us/wiki_pages/help:posts        /posts endpoint

    \b
    Tag DSL on /posts.json:
      tag                            must include
      -tag                           must exclude
      rating:g|s|q|e                 general/sensitive/questionable/explicit
      score:>100, score:<10          numeric comparators
      order:score|date|random        sort order
      user:NAME                      uploader filter

    \b
    Pagination:
      ?page=N&limit=M                offset-style
      ?page=b<id>                    cursor: posts before <id>
      ?page=a<id>                    cursor: posts after <id>

    \b
    Examples:
      animedex api danbooru '/posts.json?tags=touhou+rating:g+order:score&limit=3'
      animedex api danbooru /posts/11322863.json
      animedex api danbooru '/tags.json?search[name_matches]=touhou*&limit=5'
      animedex api danbooru '/counts/posts.json?tags=touhou+rating:g'
    \f

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
