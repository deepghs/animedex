"""``animedex nekos <subcommand>`` Click group + bindings.

Four subcommands wrapping the JSON-emitting v2 surface:

* ``animedex nekos categories``       — list every category name
* ``animedex nekos categories-full``  — list categories plus format metadata
* ``animedex nekos image``            — fetch random images / GIFs from a category
* ``animedex nekos search``           — metadata search across all categories

All commands are anonymous; nekos.best v2 has no auth tier and no
NSFW tier.
"""

from __future__ import annotations

import click

from animedex.backends import nekos as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="nekos")
def nekos_group() -> None:
    """High-level nekos.best v2 commands (anonymous; SFW image / GIF API).

    \b
    Docs:
      https://docs.nekos.best/                       project docs index
      https://nekos.best/                             project home

    \b
    Examples:
      animedex nekos categories
      animedex nekos image husbando
      animedex nekos image neko --amount 5
      animedex nekos search Frieren
      animedex nekos search "loop" --type 2 --amount 3
    \f

    Backend: nekos.best v2 (nekos.best/api/v2).

    Rate limit: anonymous; no formal cap published (treat ~10 req/sec
    as a soft ceiling).

    --- LLM Agent Guidance ---
    Read-only image / GIF lookup. nekos.best v2 is SFW-only by
    design, so the rich-model rating projection is always 'g'. Use
    ``categories`` first to discover the valid category set; the
    server returns 404 on unknown categories. ``search`` is best-
    effort metadata matching across artist / source / anime_name —
    empty result lists are normal when nothing matches the query.
    --- End ---
    """


register_subcommand(
    nekos_group,
    "categories",
    _api.categories,
    help="List every available category name.",
)
register_subcommand(
    nekos_group,
    "categories-full",
    _api.categories_full,
    help="List categories with per-category format / filename-range metadata.",
)
register_subcommand(
    nekos_group,
    "image",
    _api.image,
    help="Random image(s) from a named category (amount=1..20).",
    guidance_override=(
        "Returns a list of images even when amount=1 (one-element list). Pass "
        "amount=N to ask for up to 20 random images at once. The category name "
        "must come from /endpoints — pass an unknown name and the upstream "
        "responds 404 (surfaces as ApiError reason='not-found')."
    ),
)
register_subcommand(
    nekos_group,
    "search",
    _api.search,
    help="Metadata search across all categories (image or GIF).",
    guidance_override=(
        "Searches anime_name / artist_name / source_url for the query phrase. "
        "type=1 for images (default), type=2 for GIFs. Empty result lists are "
        "normal when nothing matches. nekos.best v2 has no NSFW tier, so the "
        "result rating is always 'g' — agents do not need to add a content filter."
    ),
)
