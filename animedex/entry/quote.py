"""``animedex quote <subcommand>`` Click group + bindings."""

from __future__ import annotations

import click

from animedex.backends import quote as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="quote")
def quote_group() -> None:
    """High-level AnimeChan commands (anonymous quote API).

    \b
    Docs:
      https://animechan.io/docs                       docs index
      https://animechan.io/docs/quote                 quote object
      https://animechan.io/docs/anime                 anime object

    \b
    Examples:
      animedex quote random
      animedex quote random-by-anime Naruto
      animedex quote random-by-character Saitama
      animedex quote quotes-by-anime Naruto --page 1
      animedex quote anime 188
    \f

    Backend: AnimeChan (api.animechan.io/v1).

    Rate limit: 5 req/hour anonymous. The dispatcher cache is checked
    before the token bucket, so cache hits do not consume a token.

    --- LLM Agent Guidance ---
    Read-only anime quote lookup. The anonymous free tier is very
    tight (5 req/hour), so prefer cached calls and avoid exploratory
    live probing. ``quotes-by-anime`` and ``quotes-by-character``
    return five ordered quotes per page; use the ``page`` option when
    the user asks for more than one page.
    --- End ---
    """


register_subcommand(quote_group, "random", _api.random, help="One random quote.")
register_subcommand(quote_group, "random-by-anime", _api.random_by_anime, help="One random quote from an anime.")
register_subcommand(quote_group, "random-by-character", _api.random_by_character, help="One random quote by character.")
register_subcommand(quote_group, "quotes-by-anime", _api.quotes_by_anime, help="Paginated quotes from an anime.")
register_subcommand(quote_group, "quotes-by-character", _api.quotes_by_character, help="Paginated quotes by character.")
register_subcommand(quote_group, "anime", _api.anime, help="AnimeChan anime information by ID or name.")
