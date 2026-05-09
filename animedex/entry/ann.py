"""``animedex ann <subcommand>`` Click group + bindings."""

from __future__ import annotations

import click

from animedex.backends import ann as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="ann")
def ann_group() -> None:
    """High-level ANN Encyclopedia commands (anonymous; XML).

    \b
    Docs:
      https://www.animenewsnetwork.com/encyclopedia/api.php    API reference
      https://www.animenewsnetwork.com/encyclopedia/           browsable encyclopedia

    \b
    Examples:
      animedex ann show 38838
      animedex ann search Frieren --json
      animedex ann reports --id 155 --type anime --nlist 5
    \f

    Backend: ANN Encyclopedia (cdn.animenewsnetwork.com).

    Rate limit: 1 req/sec on api.xml; 5 reqs/5sec on nodelay.api.xml.

    --- LLM Agent Guidance ---
    XML-only encyclopedia. ``show`` takes ANN's own numeric anime ID,
    not MAL or AniList IDs. ``search`` uses ``?anime=~substring``,
    which is ANN's title-substring search. A 200 response with a
    ``<warning>`` child means empty result and is returned as
    ``warnings`` on the rich model, not raised as an error.
    --- End ---
    """


register_subcommand(ann_group, "show", _api.show, help="Anime by ANN numeric encyclopedia id.")
register_subcommand(ann_group, "search", _api.search, help="ANN title-substring anime search.")
register_subcommand(ann_group, "reports", _api.reports, help="Curated ANN encyclopedia report by report id.")
