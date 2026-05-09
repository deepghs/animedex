"""``animedex danbooru <subcommand>`` Click group + bindings.

Wraps the anonymous-readable surface on ``danbooru.donmai.us``: the
canonical resources (posts / artists / tags / pools / counts) plus
the long-tail of audit / votes / events / wiki / forum / commentary /
moderation feeds. Every command is a thin wrapper over
:mod:`animedex.backends.danbooru` registered through
:func:`register_subcommand`.
"""

from __future__ import annotations

import click

from animedex.backends import danbooru as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="danbooru")
def danbooru_group() -> None:
    """High-level Danbooru commands (anonymous; tag-DSL search).

    \b
    Docs:
      https://danbooru.donmai.us/wiki_pages/help:api      API help
      https://danbooru.donmai.us/wiki_pages/howto%3Asearch  search DSL guide

    \b
    Examples:
      animedex danbooru search 'touhou marisa rating:g order:score' --limit 5
      animedex danbooru post 1
      animedex danbooru artist 1
      animedex danbooru artist-search "Hayao Miyazaki" --limit 3
      animedex danbooru tag "touhou*" --limit 5
      animedex danbooru pool 1
      animedex danbooru pool-search "Touhou" --limit 5
      animedex danbooru count 'touhou rating:g'
      animedex danbooru autocomplete touh --type tag_query
      animedex danbooru related-tag touhou --limit 5
      animedex danbooru wiki-pages --limit 3
      animedex danbooru notes --limit 3
    \f

    Backend: Danbooru (danbooru.donmai.us); community-driven art catalogue.

    Rate limit: 10 req/sec anonymous; Cloudflare-fronted (a non-empty
    User-Agent is required and the transport injects the project
    default automatically).

    --- LLM Agent Guidance ---
    Tag-DSL search. Content-rating tags: rating:g (general),
    rating:s (sensitive), rating:q (questionable), rating:e (explicit).
    When the user did not explicitly ask for adult / ecchi / NSFW
    content, prepend rating:g to the tag query yourself. When the
    user explicitly asks for ecchi / NSFW / adult / R-18 content,
    pass their query through unmodified — the project's posture is
    to inform, not to gate. Each result row carries a .rating field
    so a downstream pipeline can re-filter.
    --- End ---
    """


# ---------- /posts ----------
register_subcommand(
    danbooru_group,
    "search",
    _api.search,
    help="Tag-DSL post search.",
    guidance_override=(
        "Tag-DSL search. Content-rating tags: rating:g | rating:s | rating:q | rating:e. "
        "When the user did NOT explicitly ask for adult / ecchi / NSFW content, "
        "prepend rating:g to the tag query yourself; when they did explicitly ask, "
        "pass their query through unmodified — the project's posture is to inform, "
        "not to gate. Each row's .rating field lets a downstream pipeline re-filter."
    ),
)
register_subcommand(danbooru_group, "post", _api.post, help="Post by Danbooru numeric id.")

# ---------- /artists ----------
register_subcommand(danbooru_group, "artist", _api.artist, help="Artist by Danbooru numeric id.")
register_subcommand(danbooru_group, "artist-search", _api.artist_search, help="Artist substring search.")
register_subcommand(danbooru_group, "artist-versions", _api.artist_versions, help="Artist edit history feed.")
register_subcommand(
    danbooru_group, "artist-commentaries", _api.artist_commentaries, help="Artist-supplied commentary feed."
)
register_subcommand(danbooru_group, "artist-commentary", _api.artist_commentary, help="One artist commentary by id.")
register_subcommand(
    danbooru_group,
    "artist-commentary-versions",
    _api.artist_commentary_versions,
    help="Commentary edit history feed.",
)

# ---------- /tags ----------
register_subcommand(danbooru_group, "tag", _api.tag, help="Tag lookup (supports wildcards).")
register_subcommand(danbooru_group, "tag-aliases", _api.tag_aliases, help="Tag alias (synonym) feed.")
register_subcommand(
    danbooru_group, "tag-implications", _api.tag_implications, help="Tag implication (parent → child) feed."
)
register_subcommand(danbooru_group, "tag-versions", _api.tag_versions, help="Tag edit history feed.")

# ---------- /wiki_pages ----------
register_subcommand(danbooru_group, "wiki-pages", _api.wiki_pages, help="Wiki page collection.")
register_subcommand(danbooru_group, "wiki-page", _api.wiki_page, help="One wiki page by id.")
register_subcommand(danbooru_group, "wiki-page-versions", _api.wiki_page_versions, help="Wiki-page edit history feed.")

# ---------- /pools ----------
register_subcommand(danbooru_group, "pool", _api.pool, help="Pool by Danbooru numeric id.")
register_subcommand(danbooru_group, "pool-search", _api.pool_search, help="Pool substring search.")
register_subcommand(danbooru_group, "pool-versions", _api.pool_versions, help="Pool edit history feed.")

# ---------- /notes ----------
register_subcommand(danbooru_group, "notes", _api.notes, help="Translation overlay note feed.")
register_subcommand(danbooru_group, "note", _api.note, help="One note by id.")
register_subcommand(danbooru_group, "note-versions", _api.note_versions, help="Note edit history feed.")

# ---------- /comments ----------
register_subcommand(danbooru_group, "comments", _api.comments, help="Post-comment feed.")
register_subcommand(danbooru_group, "comment", _api.comment, help="One comment by id.")
register_subcommand(danbooru_group, "comment-votes", _api.comment_votes, help="Comment vote feed.")

# ---------- /forum ----------
register_subcommand(danbooru_group, "forum-topics", _api.forum_topics, help="Forum topic listing.")
register_subcommand(danbooru_group, "forum-topic-visits", _api.forum_topic_visits, help="Forum topic visit feed.")
register_subcommand(danbooru_group, "forum-posts", _api.forum_posts, help="Forum post listing.")
register_subcommand(danbooru_group, "forum-post-votes", _api.forum_post_votes, help="Forum-post vote feed.")

# ---------- /users ----------
register_subcommand(danbooru_group, "users", _api.users, help="User directory.")
register_subcommand(danbooru_group, "user", _api.user, help="One user by id.")
register_subcommand(danbooru_group, "user-events", _api.user_events, help="User-event feed.")
register_subcommand(danbooru_group, "user-feedbacks", _api.user_feedbacks, help="Moderator feedback feed.")

# ---------- /favorites ----------
register_subcommand(danbooru_group, "favorites", _api.favorites, help="Favourite-record feed.")
register_subcommand(danbooru_group, "favorite-groups", _api.favorite_groups, help="Favourite-group listing.")

# ---------- /uploads ----------
register_subcommand(danbooru_group, "uploads", _api.uploads, help="Upload-record feed.")
register_subcommand(
    danbooru_group, "upload-media-assets", _api.upload_media_assets, help="Upload-attached media-asset feed."
)

# ---------- /post-* (versions / replacements / votes / flags / appeals / approvals / events) ----------
register_subcommand(danbooru_group, "post-versions", _api.post_versions, help="Post edit history feed.")
register_subcommand(danbooru_group, "post-replacements", _api.post_replacements, help="Post-image replacement feed.")
register_subcommand(danbooru_group, "post-disapprovals", _api.post_disapprovals, help="Mod-disapproval feed.")
register_subcommand(danbooru_group, "post-appeals", _api.post_appeals, help="Removal-appeal feed.")
register_subcommand(danbooru_group, "post-flags", _api.post_flags, help="User flag feed.")
register_subcommand(danbooru_group, "post-votes", _api.post_votes, help="Post-vote feed.")
register_subcommand(danbooru_group, "post-approvals", _api.post_approvals, help="Mod-approval feed.")
register_subcommand(danbooru_group, "post-events", _api.post_events, help="Post-event audit feed.")

# ---------- /counts ----------
register_subcommand(danbooru_group, "count", _api.count, help="Count posts matching a tag query.")

# ---------- discovery / autocomplete ----------
register_subcommand(danbooru_group, "autocomplete", _api.autocomplete, help="Tag / artist / user / pool autocomplete.")
register_subcommand(danbooru_group, "related-tag", _api.related_tag, help="Frequently-co-occurring tags for a query.")
register_subcommand(danbooru_group, "iqdb-query", _api.iqdb_query, help="Reverse image lookup (--url or --post-id).")

# ---------- moderation / operational (anonymous-readable) ----------
register_subcommand(danbooru_group, "mod-actions", _api.mod_actions, help="Moderator-action audit feed.")
register_subcommand(danbooru_group, "bans", _api.bans, help="Account-ban feed.")
register_subcommand(
    danbooru_group, "bulk-update-requests", _api.bulk_update_requests, help="Bulk tag-graph change requests."
)
register_subcommand(danbooru_group, "dtext-links", _api.dtext_links, help="DText hyperlink graph feed.")
register_subcommand(danbooru_group, "ai-tags", _api.ai_tags, help="AI-classifier tag suggestions feed.")
register_subcommand(danbooru_group, "media-assets", _api.media_assets, help="Underlying media-asset feed.")
register_subcommand(danbooru_group, "media-metadata", _api.media_metadata, help="Media-asset EXIF / dimensions feed.")
register_subcommand(danbooru_group, "rate-limits", _api.rate_limits, help="Rate-limit ledger feed.")
register_subcommand(danbooru_group, "recommended-posts", _api.recommended_posts, help="Per-user post recommendations.")
register_subcommand(danbooru_group, "reactions", _api.reactions, help="Reaction-emoji record feed.")
register_subcommand(danbooru_group, "jobs", _api.jobs, help="Background-job ledger feed.")
register_subcommand(danbooru_group, "metrics", _api.metrics, help="Operational metric snapshots.")

# ---------- authenticated reads ----------
register_subcommand(danbooru_group, "profile", _api.profile, help="Authenticated user's own profile (requires creds).")
register_subcommand(danbooru_group, "saved-searches", _api.saved_searches, help="Authenticated user's saved searches.")
