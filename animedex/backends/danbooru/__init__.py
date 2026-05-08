"""High-level Danbooru Python API.

Eight commands wrapping the most-used anonymous read endpoints on
``danbooru.donmai.us``: search / post / artist / artist-search /
tag / pool / pool-search / count.

The Danbooru tag-DSL surface is rich (rating filters, score
comparators, ``order:`` sorting, exclusion via ``-tag``); the high-
level :func:`search` accepts the raw tag string verbatim and forwards
it to the upstream. The project's posture per the Human Agency
Principle: when the user did not explicitly ask for adult content,
LLM agents should prepend ``rating:g`` to the tag query themselves;
the CLI / library never injects a content filter on the user's
behalf.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import danbooru as _raw_danbooru
from animedex.backends.danbooru.models import (
    DanbooruArtist,
    DanbooruCount,
    DanbooruIQDBQuery,
    DanbooruPool,
    DanbooruPost,
    DanbooruRecord,
    DanbooruRelatedTag,
    DanbooruTag,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="danbooru",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Danbooru GET, parse the body, validate the envelope.

    :return: ``(parsed_payload, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` for non-text or
                       non-JSON bodies.
    """
    raw = _raw_danbooru.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="danbooru",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - danbooru returns JSON
        raise ApiError("danbooru returned a non-text body", backend="danbooru", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"danbooru 404 on {path}", backend="danbooru", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"danbooru {raw.status} on {path}", backend="danbooru", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(
            f"danbooru returned non-JSON body: {exc}",
            backend="danbooru",
            reason="upstream-decode",
        ) from exc
    return payload, _src(raw)


def _list(payload: Any) -> List[dict]:
    """Coerce a payload that should be a list-of-records into one,
    tolerating Danbooru's occasional single-row return."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    return [payload]


# ---------- /posts ----------


def search(
    tags: Optional[str] = None,
    *,
    limit: int = 20,
    page: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[DanbooruPost]:
    """Tag-DSL search via ``/posts.json``.

    :param tags: Space-separated tag query (the upstream's DSL).
                  ``rating:g``, ``order:score``, ``score:>100``,
                  ``-tag`` (exclusion) and ``user:<name>`` are all
                  honoured by the upstream. When ``None``, the
                  upstream returns the latest posts unfiltered.
    :type tags: str or None
    :param limit: Max rows per page.
    :type limit: int
    :param page: 1-indexed page number.
    :type page: int
    :return: List of typed posts.
    :rtype: list[DanbooruPost]
    """
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if tags:
        params["tags"] = tags
    payload, src = _fetch("/posts.json", params=params, config=config, **kw)
    return [DanbooruPost.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def post(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruPost:
    """Fetch one post by its numeric Danbooru ID via
    ``/posts/{id}.json``.

    :param id: Danbooru post ID.
    :type id: int
    :return: Typed post.
    :rtype: DanbooruPost
    """
    payload, src = _fetch(f"/posts/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /posts/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruPost.model_validate({**payload, "source_tag": src})


# ---------- /artists ----------


def artist(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruArtist:
    """Fetch one artist by ID via ``/artists/{id}.json``.

    :param id: Danbooru artist ID.
    :type id: int
    :return: Typed artist.
    :rtype: DanbooruArtist
    """
    payload, src = _fetch(f"/artists/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /artists/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruArtist.model_validate({**payload, "source_tag": src})


def artist_search(name: str, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[DanbooruArtist]:
    """Search artists by name (substring match) via
    ``/artists.json?search[any_name_or_url_matches]=<name>``.

    :param name: Substring to match against name / alias / URL.
    :type name: str
    :param limit: Max rows per page.
    :type limit: int
    :return: List of typed artists.
    :rtype: list[DanbooruArtist]
    """
    params = {"search[any_name_or_url_matches]": name, "limit": limit}
    payload, src = _fetch("/artists.json", params=params, config=config, **kw)
    return [DanbooruArtist.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /tags ----------


def tag(name: str, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[DanbooruTag]:
    """Look up a tag by exact or prefix-match name via
    ``/tags.json?search[name_matches]=<name>``.

    Returns a list because the upstream's ``name_matches`` accepts
    wildcards (e.g. ``touhou*``); pass an exact name to get a
    single-element list.

    :param name: Tag name (or wildcard pattern).
    :type name: str
    :param limit: Max rows per page.
    :type limit: int
    :return: List of typed tags.
    :rtype: list[DanbooruTag]
    """
    params = {"search[name_matches]": name, "limit": limit}
    payload, src = _fetch("/tags.json", params=params, config=config, **kw)
    return [DanbooruTag.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /pools ----------


def pool(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruPool:
    """Fetch one pool by ID via ``/pools/{id}.json``.

    :param id: Danbooru pool ID.
    :type id: int
    :return: Typed pool.
    :rtype: DanbooruPool
    """
    payload, src = _fetch(f"/pools/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /pools/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruPool.model_validate({**payload, "source_tag": src})


def pool_search(
    name: Optional[str] = None,
    *,
    limit: int = 20,
    page: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[DanbooruPool]:
    """Search pools by name substring via
    ``/pools.json?search[name_matches]=<name>``.

    :param name: Pool name substring; ``None`` lists all pools.
    :type name: str or None
    :param limit: Max rows per page.
    :type limit: int
    :param page: 1-indexed page number.
    :type page: int
    :return: List of typed pools.
    :rtype: list[DanbooruPool]
    """
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if name:
        params["search[name_matches]"] = name
    payload, src = _fetch("/pools.json", params=params, config=config, **kw)
    return [DanbooruPool.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /counts ----------


def count(tags: Optional[str] = None, *, config: Optional[Config] = None, **kw) -> DanbooruCount:
    """Count posts matching a tag query via
    ``/counts/posts.json?tags=<tags>``.

    :param tags: Space-separated tag query (same DSL as
                  :func:`search`); ``None`` counts the entire
                  catalogue.
    :type tags: str or None
    :return: Typed count envelope; access ``.total()`` for the int.
    :rtype: DanbooruCount
    """
    params: Dict[str, Any] = {}
    if tags:
        params["tags"] = tags
    payload, src = _fetch("/counts/posts.json", params=params, config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /counts/posts.json did not return an object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruCount.model_validate({**payload, "source_tag": src})


# ---------- generic record search / show helpers ----------


def _record_search(
    slug: str, *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Fetch a paginated list of records from ``/<slug>.json``.

    Used by every long-tail endpoint that returns a uniform
    ``[{id, ...}, ...]`` shape (versions, votes, events, etc.).
    Callers prefer the named wrappers below; this helper keeps
    the per-endpoint Python surface tiny.
    """
    payload, src = _fetch(f"/{slug}.json", params={"limit": limit, "page": page}, config=config, **kw)
    return [DanbooruRecord.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def _record_show(slug: str, id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """Fetch one record by id from ``/<slug>/{id}.json``."""
    payload, src = _fetch(f"/{slug}/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            f"danbooru /{slug}/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruRecord.model_validate({**payload, "source_tag": src})


# ---------- /artists ----------


def artist_versions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Edit history for artist records via ``/artist_versions.json``."""
    return _record_search("artist_versions", limit=limit, page=page, config=config, **kw)


def artist_commentaries(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Artist-supplied commentary text for posts via
    ``/artist_commentaries.json``."""
    return _record_search("artist_commentaries", limit=limit, page=page, config=config, **kw)


def artist_commentary(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """One artist commentary by id via ``/artist_commentaries/{id}.json``."""
    return _record_show("artist_commentaries", id, config=config, **kw)


def artist_commentary_versions(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Edit history for commentaries via ``/artist_commentary_versions.json``."""
    return _record_search("artist_commentary_versions", limit=limit, page=page, config=config, **kw)


# ---------- /tags ----------


def tag_aliases(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Tag aliases (synonyms) via ``/tag_aliases.json``."""
    return _record_search("tag_aliases", limit=limit, page=page, config=config, **kw)


def tag_implications(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Tag implications (parent → child) via ``/tag_implications.json``."""
    return _record_search("tag_implications", limit=limit, page=page, config=config, **kw)


def tag_versions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Edit history for tag records via ``/tag_versions.json``."""
    return _record_search("tag_versions", limit=limit, page=page, config=config, **kw)


# ---------- /wiki_pages ----------


def wiki_pages(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Tag wiki page collection via ``/wiki_pages.json``."""
    return _record_search("wiki_pages", limit=limit, page=page, config=config, **kw)


def wiki_page(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """One wiki page by id via ``/wiki_pages/{id}.json``."""
    return _record_show("wiki_pages", id, config=config, **kw)


def wiki_page_versions(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Wiki-page edit history via ``/wiki_page_versions.json``."""
    return _record_search("wiki_page_versions", limit=limit, page=page, config=config, **kw)


# ---------- /pools ----------


def pool_versions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Pool edit history via ``/pool_versions.json``."""
    return _record_search("pool_versions", limit=limit, page=page, config=config, **kw)


# ---------- /notes ----------


def notes(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Translation overlay notes on posts via ``/notes.json``."""
    return _record_search("notes", limit=limit, page=page, config=config, **kw)


def note(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """One note by id via ``/notes/{id}.json``."""
    return _record_show("notes", id, config=config, **kw)


def note_versions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Note edit history via ``/note_versions.json``."""
    return _record_search("note_versions", limit=limit, page=page, config=config, **kw)


# ---------- /comments ----------


def comments(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Post comments via ``/comments.json``."""
    return _record_search("comments", limit=limit, page=page, config=config, **kw)


def comment(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """One comment by id via ``/comments/{id}.json``."""
    return _record_show("comments", id, config=config, **kw)


def comment_votes(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Comment vote feed via ``/comment_votes.json``."""
    return _record_search("comment_votes", limit=limit, page=page, config=config, **kw)


# ---------- /forum_* ----------


def forum_topics(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Forum topic listing via ``/forum_topics.json``."""
    return _record_search("forum_topics", limit=limit, page=page, config=config, **kw)


def forum_topic_visits(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Forum topic visit feed via ``/forum_topic_visits.json``."""
    return _record_search("forum_topic_visits", limit=limit, page=page, config=config, **kw)


def forum_posts(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Forum post listing via ``/forum_posts.json``."""
    return _record_search("forum_posts", limit=limit, page=page, config=config, **kw)


def forum_post_votes(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Forum-post vote feed via ``/forum_post_votes.json``."""
    return _record_search("forum_post_votes", limit=limit, page=page, config=config, **kw)


# ---------- /users ----------


def users(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """User directory via ``/users.json``."""
    return _record_search("users", limit=limit, page=page, config=config, **kw)


def user(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruRecord:
    """One user by id via ``/users/{id}.json``."""
    return _record_show("users", id, config=config, **kw)


def user_events(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """User-event feed via ``/user_events.json``."""
    return _record_search("user_events", limit=limit, page=page, config=config, **kw)


def user_feedbacks(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Moderator-recorded user feedback via ``/user_feedbacks.json``."""
    return _record_search("user_feedbacks", limit=limit, page=page, config=config, **kw)


# ---------- /favorites ----------


def favorites(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Favourite-record feed via ``/favorites.json`` (anonymous-readable
    on the public subset)."""
    return _record_search("favorites", limit=limit, page=page, config=config, **kw)


def favorite_groups(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Favourite-group listing via ``/favorite_groups.json``."""
    return _record_search("favorite_groups", limit=limit, page=page, config=config, **kw)


# ---------- /uploads ----------


def uploads(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Upload-record feed via ``/uploads.json``."""
    return _record_search("uploads", limit=limit, page=page, config=config, **kw)


def upload_media_assets(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Media assets attached to uploads via
    ``/upload_media_assets.json``."""
    return _record_search("upload_media_assets", limit=limit, page=page, config=config, **kw)


# ---------- /post_* (versions, replacements, votes, flags, appeals, ...) ----------


def post_versions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Post edit history via ``/post_versions.json``."""
    return _record_search("post_versions", limit=limit, page=page, config=config, **kw)


def post_replacements(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Post-image replacement records via ``/post_replacements.json``."""
    return _record_search("post_replacements", limit=limit, page=page, config=config, **kw)


def post_disapprovals(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Mod-disapproval records via ``/post_disapprovals.json``."""
    return _record_search("post_disapprovals", limit=limit, page=page, config=config, **kw)


def post_appeals(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Removal-appeal records via ``/post_appeals.json``."""
    return _record_search("post_appeals", limit=limit, page=page, config=config, **kw)


def post_flags(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """User-submitted post flag records via ``/post_flags.json``."""
    return _record_search("post_flags", limit=limit, page=page, config=config, **kw)


def post_votes(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Post-vote feed via ``/post_votes.json``."""
    return _record_search("post_votes", limit=limit, page=page, config=config, **kw)


def post_approvals(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Mod-approval records via ``/post_approvals.json``."""
    return _record_search("post_approvals", limit=limit, page=page, config=config, **kw)


def post_events(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Post-event audit log via ``/post_events.json``."""
    return _record_search("post_events", limit=limit, page=page, config=config, **kw)


# ---------- discovery / autocomplete ----------


def autocomplete(
    query: str, *, type: str = "tag_query", limit: int = 10, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Tag / artist autocomplete via
    ``/autocomplete.json?search[query]=<q>&search[type]=<type>``.

    :param query: Prefix to autocomplete.
    :type query: str
    :param type: Autocomplete dictionary; common values are
                  ``tag_query`` (default), ``artist``, ``pool``,
                  ``user``, ``wiki_page``.
    :type type: str
    :param limit: Max suggestions.
    :type limit: int
    """
    params = {"search[query]": query, "search[type]": type, "limit": limit}
    payload, src = _fetch("/autocomplete.json", params=params, config=config, **kw)
    return [DanbooruRecord.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def related_tag(query: str, *, limit: int = 20, config: Optional[Config] = None, **kw) -> DanbooruRelatedTag:
    """Tag-graph navigation via ``/related_tag.json?query=<q>``.

    Returns a list of tags that frequently co-occur with the input
    on Danbooru posts. Useful for query refinement.
    """
    params = {"query": query, "limit": limit}
    payload, src = _fetch("/related_tag.json", params=params, config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /related_tag.json did not return an object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruRelatedTag.model_validate({**payload, "source_tag": src})


def iqdb_query(
    *, url: Optional[str] = None, post_id: Optional[int] = None, config: Optional[Config] = None, **kw
) -> List[DanbooruIQDBQuery]:
    """Reverse image lookup via ``/iqdb_queries.json?url=<u>`` or
    ``?post_id=<id>``.

    Use ``url=`` for an external image URL or ``post_id=`` to find
    Danbooru posts visually similar to an existing one.
    """
    if not url and post_id is None:
        raise ApiError(
            "iqdb_query needs either url= or post_id=",
            backend="danbooru",
            reason="bad-args",
        )
    params: Dict[str, Any] = {}
    if url:
        params["url"] = url
    if post_id is not None:
        params["post_id"] = post_id
    payload, src = _fetch("/iqdb_queries.json", params=params, config=config, **kw)
    return [DanbooruIQDBQuery.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- moderation / operational (anonymous-readable) ----------


def mod_actions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Moderator-action audit log via ``/mod_actions.json``."""
    return _record_search("mod_actions", limit=limit, page=page, config=config, **kw)


def bans(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Account-ban records via ``/bans.json``."""
    return _record_search("bans", limit=limit, page=page, config=config, **kw)


def bulk_update_requests(
    *, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw
) -> List[DanbooruRecord]:
    """Bulk-update tag-graph requests via ``/bulk_update_requests.json``."""
    return _record_search("bulk_update_requests", limit=limit, page=page, config=config, **kw)


def dtext_links(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """DText hyperlink graph via ``/dtext_links.json``."""
    return _record_search("dtext_links", limit=limit, page=page, config=config, **kw)


def ai_tags(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """AI-classifier tag suggestions via ``/ai_tags.json``."""
    return _record_search("ai_tags", limit=limit, page=page, config=config, **kw)


def media_assets(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Underlying media-asset records via ``/media_assets.json``."""
    return _record_search("media_assets", limit=limit, page=page, config=config, **kw)


def media_metadata(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Media-asset EXIF / dimensions metadata via ``/media_metadata.json``."""
    return _record_search("media_metadata", limit=limit, page=page, config=config, **kw)


def rate_limits(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Per-user / per-IP rate-limit-ledger via ``/rate_limits.json``."""
    return _record_search("rate_limits", limit=limit, page=page, config=config, **kw)


def recommended_posts(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Per-user post recommendations via ``/recommended_posts.json``."""
    return _record_search("recommended_posts", limit=limit, page=page, config=config, **kw)


def reactions(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Reaction-emoji records via ``/reactions.json``."""
    return _record_search("reactions", limit=limit, page=page, config=config, **kw)


def jobs(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Background-job ledger via ``/jobs.json``."""
    return _record_search("jobs", limit=limit, page=page, config=config, **kw)


def metrics(*, limit: int = 20, page: int = 1, config: Optional[Config] = None, **kw) -> List[DanbooruRecord]:
    """Operational metric snapshots via ``/metrics.json``."""
    return _record_search("metrics", limit=limit, page=page, config=config, **kw)


def selftest() -> bool:
    """Smoke-test the public Danbooru Python API (signatures only,
    no network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [
        search,
        post,
        artist,
        artist_search,
        tag,
        pool,
        pool_search,
        count,
        artist_versions,
        artist_commentaries,
        artist_commentary,
        artist_commentary_versions,
        tag_aliases,
        tag_implications,
        tag_versions,
        wiki_pages,
        wiki_page,
        wiki_page_versions,
        pool_versions,
        notes,
        note,
        note_versions,
        comments,
        comment,
        comment_votes,
        forum_topics,
        forum_topic_visits,
        forum_posts,
        forum_post_votes,
        users,
        user,
        user_events,
        user_feedbacks,
        favorites,
        favorite_groups,
        uploads,
        upload_media_assets,
        post_versions,
        post_replacements,
        post_disapprovals,
        post_appeals,
        post_flags,
        post_votes,
        post_approvals,
        post_events,
        autocomplete,
        related_tag,
        iqdb_query,
        mod_actions,
        bans,
        bulk_update_requests,
        dtext_links,
        ai_tags,
        media_assets,
        media_metadata,
        rate_limits,
        recommended_posts,
        reactions,
        jobs,
        metrics,
    ]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
