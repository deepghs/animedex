"""``animedex api quote`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_quote = make_get_only_subcommand(
    name="quote",
    backend_module_name="quote",
    docstring="""Issue an AnimeChan GET request (anonymous quote API).

    PATH is the URL path under `https://api.animechan.io/v1`.

    \b
    Docs:
      https://animechan.io/docs                       docs index
      https://animechan.io/docs/quote                 quote object

    \b
    Common paths:
      /quotes/random
      /quotes/random?anime=Naruto
      /quotes/random?character=Saitama
      /quotes?anime=Naruto&page=1
      /quotes?character=Saitama&page=1
      /anime/188

    \b
    Examples:
      animedex api quote /quotes/random
      animedex api quote '/quotes?anime=Naruto&page=1' -i
      animedex api quote /anime/188 --debug | jq '.status'
    \f

    Backend: AnimeChan (api.animechan.io/v1).

    Rate limit: 5 req/hour anonymous. The dispatcher cache is checked
    before the token bucket, so cache hits do not consume a token.

    --- LLM Agent Guidance ---
    PATH is the URL path under /v1. The anonymous free tier is very
    tight (5 req/hour); prefer high-level cached commands and avoid
    exploratory live probing unless the user explicitly needs fresh
    quotes.
    --- End ---
    """,
)
