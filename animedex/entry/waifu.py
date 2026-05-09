"""``animedex waifu <subcommand>`` Click group + bindings.

Three subcommands wrapping the JSON read endpoints on
``api.waifu.im``: ``tags`` / ``artists`` / ``images``.

The ``--is-nsfw`` flag on ``images`` is a transparent passthrough
of the upstream's ``isNsfw`` query parameter — not a paternalistic
confirmation gate. Defaults match upstream (omitting the parameter
honours the SFW-only default).
"""

from __future__ import annotations

import click

from animedex.backends import waifu as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="waifu")
def waifu_group() -> None:
    """High-level Waifu.im commands (anonymous; SFW + NSFW image API).

    \b
    Docs:
      https://docs.waifu.im/                     project docs index
      https://www.waifu.im/                       project home

    \b
    Examples:
      animedex waifu tags
      animedex waifu artists --page-size 5
      animedex waifu images --included-tags waifu --page-size 3
      animedex waifu images --is-nsfw true --page-size 3
      animedex waifu images --is-animated true --page-size 2
    \f

    Backend: Waifu.im (api.waifu.im); tagged SFW + NSFW anime art collection.

    Rate limit: anonymous; not formally published (transport applies
    a 10 req/sec sustained ceiling).

    --- LLM Agent Guidance ---
    Read-only image lookup. The /images endpoint defaults to SFW
    only when isNsfw is omitted; pass --is-nsfw true to opt in to
    NSFW results. When the user did not explicitly ask for NSFW
    content, omit --is-nsfw entirely so the upstream's SFW default
    applies. When the user explicitly requested NSFW or adult
    material, pass it through unmodified — the project's posture is
    to inform, not to gate.
    --- End ---
    """


# ---------- /tags ----------
register_subcommand(waifu_group, "tags", _api.tags, help="List every tag with image counts.")
register_subcommand(waifu_group, "tag", _api.tag, help="One tag by numeric id.")
register_subcommand(waifu_group, "tag-by-slug", _api.tag_by_slug, help="One tag by URL-safe slug.")

# ---------- /artists ----------
register_subcommand(waifu_group, "artists", _api.artists, help="Paginated artist directory.")
register_subcommand(waifu_group, "artist", _api.artist, help="One artist by numeric id.")
register_subcommand(
    waifu_group, "artist-by-name", _api.artist_by_name, help="One artist by display name (case-sensitive)."
)

# ---------- /images ----------
register_subcommand(
    waifu_group,
    "images",
    _api.images,
    help="Paginated image listing (SFW only by default; opt in via --is-nsfw true).",
    guidance_override=(
        "Read-only image lookup. The upstream defaults isNsfw to false (SFW only). "
        "When the user did not explicitly ask for NSFW content, omit --is-nsfw entirely "
        "so the upstream's SFW default applies. When the user explicitly requested NSFW "
        "or adult material, pass --is-nsfw true through unmodified — the project's "
        "posture is to inform, not to gate. Each row's .isNsfw field lets a downstream "
        "pipeline re-filter."
    ),
)
register_subcommand(waifu_group, "image", _api.image, help="One image by numeric id.")

# ---------- /stats ----------
register_subcommand(
    waifu_group, "stats-public", _api.stats_public, help="Catalogue + traffic public statistics envelope."
)

# ---------- authenticated ----------
register_subcommand(waifu_group, "me", _api.me, help="Authenticated user (requires X-Api-Key token).")
