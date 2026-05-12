"""AniList raw payload → typed dataclass mapping helpers.

Each ``map_*`` function takes a parsed JSON dict (the inner
``data.<root>`` block from a GraphQL response) plus a
:class:`~animedex.models.common.SourceTag` and returns the matching
rich dataclass from :mod:`animedex.backends.anilist.models`.

When the upstream returned ``null`` for a single-id query (i.e.
``data.Media is None``), the mapper raises
:class:`~animedex.models.common.ApiError` with
``reason="not-found"`` so the Python API surface presents a
consistent semantic.
"""

from __future__ import annotations

from typing import Any, Dict, List

from animedex.backends.anilist.models import (
    AnilistActivity,
    AnilistActivityReply,
    AnilistAiringSchedule,
    AnilistAniChartUser,
    AnilistAnime,
    AnilistCharacter,
    AnilistExternalLinkSource,
    AnilistFollowEntry,
    AnilistGenreCollection,
    AnilistMarkdown,
    AnilistMediaListCollection,
    AnilistMediaListEntry,
    AnilistMediaListGroup,
    AnilistMediaTag,
    AnilistMediaTrend,
    AnilistNotification,
    AnilistRecommendation,
    AnilistReview,
    AnilistSiteStatistics,
    AnilistStaff,
    AnilistStudio,
    AnilistThread,
    AnilistThreadComment,
    AnilistUser,
    AnilistUserStatistics,
)
from animedex.models.common import ApiError, SourceTag, require_field


def _require(node: Any, what: str) -> Any:
    """Raise ``ApiError(reason="not-found")`` when ``node`` is None.

    Used at the *root* of a single-entity query: AniList returns
    ``data: {Media: null}`` when the id doesn't exist, and we surface
    that as a typed ``not-found`` so callers can distinguish missing
    rows from upstream failure modes.
    """
    if node is None:
        raise ApiError(f"{what} not found", backend="anilist", reason="not-found")
    return node


def _field(row: Dict[str, Any], key: str, what: str) -> Any:
    """AniList-flavoured wrapper around :func:`require_field` —
    pre-applies the backend label so list-mapper call sites stay
    short."""
    return require_field(row, key, backend="anilist", what=what)


def map_media(payload: Dict[str, Any], src: SourceTag) -> AnilistAnime:
    node = _require(payload.get("data", {}).get("Media"), "Media")
    return AnilistAnime.model_validate({**node, "source_tag": src})


def map_media_list(payload: Dict[str, Any], src: SourceTag) -> List[AnilistAnime]:
    page = payload.get("data", {}).get("Page") or {}
    media_list = page.get("media") or []
    return [AnilistAnime.model_validate({**m, "source_tag": src}) for m in media_list]


def map_character(payload: Dict[str, Any], src: SourceTag) -> AnilistCharacter:
    node = _require(payload.get("data", {}).get("Character"), "Character")
    return AnilistCharacter.model_validate({**node, "source_tag": src})


def map_character_list(payload: Dict[str, Any], src: SourceTag) -> List[AnilistCharacter]:
    page = payload.get("data", {}).get("Page") or {}
    chars = page.get("characters") or []
    return [AnilistCharacter.model_validate({**c, "source_tag": src}) for c in chars]


def map_staff(payload: Dict[str, Any], src: SourceTag) -> AnilistStaff:
    node = _require(payload.get("data", {}).get("Staff"), "Staff")
    return AnilistStaff.model_validate({**node, "source_tag": src})


def map_staff_list(payload: Dict[str, Any], src: SourceTag) -> List[AnilistStaff]:
    page = payload.get("data", {}).get("Page") or {}
    staff_list = page.get("staff") or []
    return [AnilistStaff.model_validate({**s, "source_tag": src}) for s in staff_list]


def map_studio(payload: Dict[str, Any], src: SourceTag) -> AnilistStudio:
    node = _require(payload.get("data", {}).get("Studio"), "Studio")
    return AnilistStudio.model_validate({**node, "source_tag": src})


def map_studio_list(payload: Dict[str, Any], src: SourceTag) -> List[AnilistStudio]:
    page = payload.get("data", {}).get("Page") or {}
    studios = page.get("studios") or []
    return [AnilistStudio.model_validate({**s, "source_tag": src}) for s in studios]


def map_user(payload: Dict[str, Any], src: SourceTag) -> AnilistUser:
    node = _require(payload.get("data", {}).get("User"), "User")
    avatar_large = None
    av = node.get("avatar")
    if isinstance(av, dict):
        avatar_large = av.get("large") or av.get("medium")
    statistics = None
    st = node.get("statistics") or {}
    if st:
        a = st.get("anime") or {}
        m = st.get("manga") or {}
        statistics = AnilistUserStatistics(
            anime_count=a.get("count"),
            anime_mean_score=a.get("meanScore"),
            anime_minutes_watched=a.get("minutesWatched"),
            manga_count=m.get("count"),
            manga_mean_score=m.get("meanScore"),
            manga_chapters_read=m.get("chaptersRead"),
        )
    return AnilistUser(
        id=_field(node, "id", "User"),
        name=_field(node, "name", "User"),
        about=node.get("about"),
        avatar_large=avatar_large,
        siteUrl=node.get("siteUrl"),
        statistics=statistics,
        source_tag=src,
    )


def map_user_list(payload: Dict[str, Any], src: SourceTag) -> List[AnilistUser]:
    page = payload.get("data", {}).get("Page") or {}
    users = page.get("users") or []
    out = []
    for u in users:
        avatar_large = None
        av = u.get("avatar")
        if isinstance(av, dict):
            avatar_large = av.get("large") or av.get("medium")
        out.append(
            AnilistUser(
                id=_field(u, "id", "User"),
                name=_field(u, "name", "User"),
                avatar_large=avatar_large,
                source_tag=src,
            )
        )
    return out


def map_genre_collection(payload: Dict[str, Any], src: SourceTag) -> AnilistGenreCollection:
    genres = payload.get("data", {}).get("GenreCollection") or []
    return AnilistGenreCollection(genres=list(genres), source_tag=src)


def map_media_tag_collection(payload: Dict[str, Any], src: SourceTag) -> List[AnilistMediaTag]:
    tags = payload.get("data", {}).get("MediaTagCollection") or []
    return [AnilistMediaTag.model_validate({**t, "source_tag": src}) for t in tags]


def map_site_statistics(payload: Dict[str, Any], src: SourceTag) -> AnilistSiteStatistics:
    block = payload.get("data", {}).get("SiteStatistics") or {}
    out: Dict[str, list] = {}
    for k in ("users", "anime", "manga", "characters", "staff", "reviews"):
        rows = (block.get(k) or {}).get("nodes") or []
        out[k] = rows
    return AnilistSiteStatistics(source_tag=src, **out)


def map_external_link_source(payload: Dict[str, Any], src: SourceTag) -> List[AnilistExternalLinkSource]:
    rows = payload.get("data", {}).get("ExternalLinkSourceCollection") or []
    return [AnilistExternalLinkSource.model_validate({**r, "source_tag": src}) for r in rows]


def map_airing_schedule(payload: Dict[str, Any], src: SourceTag) -> List[AnilistAiringSchedule]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("airingSchedules") or []
    out = []
    for r in rows:
        media = r.get("media") or {}
        title = media.get("title") or {}
        out.append(
            AnilistAiringSchedule(
                id=_field(r, "id", "airingSchedule"),
                airingAt=_field(r, "airingAt", "airingSchedule"),
                episode=_field(r, "episode", "airingSchedule"),
                # ``timeUntilAiring`` is absent for already-aired
                # episodes when the upstream returns a historical
                # window. Default to 0 rather than crashing — the
                # field is informational, not load-bearing.
                timeUntilAiring=r.get("timeUntilAiring", 0),
                media_id=media.get("id"),
                media_title_romaji=title.get("romaji") or title.get("english"),
                raw_payload=r,
                source_tag=src,
            )
        )
    return out


def map_media_trend(payload: Dict[str, Any], src: SourceTag) -> List[AnilistMediaTrend]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("mediaTrends") or []
    return [AnilistMediaTrend.model_validate({**r, "source_tag": src}) for r in rows]


def map_review(payload: Dict[str, Any], src: SourceTag) -> List[AnilistReview]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("reviews") or []
    return [
        AnilistReview(
            id=_field(r, "id", "review"),
            summary=r.get("summary"),
            score=r.get("score"),
            rating=r.get("rating"),
            ratingAmount=r.get("ratingAmount"),
            user_name=(r.get("user") or {}).get("name"),
            siteUrl=r.get("siteUrl"),
            source_tag=src,
        )
        for r in rows
    ]


def map_recommendation(payload: Dict[str, Any], src: SourceTag) -> List[AnilistRecommendation]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("recommendations") or []
    out = []
    for r in rows:
        m = r.get("media") or {}
        rec = r.get("mediaRecommendation") or {}
        out.append(
            AnilistRecommendation(
                id=_field(r, "id", "recommendation"),
                rating=r.get("rating"),
                media_id=m.get("id"),
                media_title=(m.get("title") or {}).get("romaji"),
                recommendation_id=rec.get("id"),
                recommendation_title=(rec.get("title") or {}).get("romaji"),
                source_tag=src,
            )
        )
    return out


def map_thread(payload: Dict[str, Any], src: SourceTag) -> List[AnilistThread]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("threads") or []
    return [
        AnilistThread(
            id=_field(r, "id", "thread"),
            title=r.get("title"),
            body=r.get("body"),
            user_name=(r.get("user") or {}).get("name"),
            replyCount=r.get("replyCount"),
            viewCount=r.get("viewCount"),
            createdAt=r.get("createdAt"),
            source_tag=src,
        )
        for r in rows
    ]


def map_thread_comment(payload: Dict[str, Any], src: SourceTag) -> List[AnilistThreadComment]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("threadComments") or []
    return [
        AnilistThreadComment(
            id=_field(r, "id", "threadComment"),
            comment=r.get("comment"),
            user_name=(r.get("user") or {}).get("name"),
            createdAt=r.get("createdAt"),
            source_tag=src,
        )
        for r in rows
    ]


def map_activity(payload: Dict[str, Any], src: SourceTag) -> List[AnilistActivity]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("activities") or []
    out = []
    for r in rows:
        # Identify variant by the field set returned. r will have
        # `text` for TextActivity; `status`+`media` for ListActivity.
        if "text" in r:
            out.append(
                AnilistActivity(
                    id=_field(r, "id", "activity"),
                    kind="text",
                    text=r.get("text"),
                    user_name=(r.get("user") or {}).get("name"),
                    createdAt=r.get("createdAt"),
                    source_tag=src,
                )
            )
        elif "status" in r:
            media = r.get("media") or {}
            title = (media.get("title") or {}).get("romaji")
            out.append(
                AnilistActivity(
                    id=_field(r, "id", "activity"),
                    kind="list",
                    status=r.get("status"),
                    user_name=(r.get("user") or {}).get("name"),
                    media_title=title,
                    createdAt=r.get("createdAt"),
                    source_tag=src,
                )
            )
    return out


def map_activity_reply(payload: Dict[str, Any], src: SourceTag) -> List[AnilistActivityReply]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("activityReplies") or []
    return [
        AnilistActivityReply(
            id=_field(r, "id", "activityReply"),
            text=r.get("text"),
            user_name=(r.get("user") or {}).get("name"),
            createdAt=r.get("createdAt"),
            source_tag=src,
        )
        for r in rows
    ]


def map_follow(payload: Dict[str, Any], key: str, src: SourceTag) -> List[AnilistFollowEntry]:
    """Shared between :func:`map_following` / :func:`map_follower`."""
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get(key) or []
    return [
        AnilistFollowEntry(
            id=_field(r, "id", "followEntry"),
            name=_field(r, "name", "followEntry"),
            source_tag=src,
        )
        for r in rows
    ]


def map_media_list_public(payload: Dict[str, Any], src: SourceTag) -> List[AnilistMediaListEntry]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("mediaList") or []
    out = []
    for r in rows:
        media = r.get("media") or {}
        out.append(
            AnilistMediaListEntry(
                id=_field(r, "id", "mediaListEntry"),
                status=r.get("status"),
                score=r.get("score"),
                progress=r.get("progress"),
                media_id=media.get("id"),
                media_title=(media.get("title") or {}).get("romaji"),
                source_tag=src,
            )
        )
    return out


# ---------- token-required mappers ----------
#
# Wired now so the captured authenticated fixtures are usable; the
# OAuth flow has not landed yet, so the public callables in
# :mod:`animedex.backends.anilist` raise ``auth-required`` before
# ever reaching these mappers.


def map_viewer(payload: Dict[str, Any], src: SourceTag) -> AnilistUser:
    """Map ``data.Viewer`` (authenticated) to :class:`AnilistUser`.

    Same shape as ``data.User`` from the public ``Q_USER_BY_NAME``
    query, just keyed under ``Viewer``. We delegate to :func:`map_user`
    after relabelling.
    """
    viewer_node = _require(payload.get("data", {}).get("Viewer"), "Viewer")
    return map_user({"data": {"User": viewer_node}}, src)


_NOTIFICATION_KIND_MAP = {
    "AIRING": "airing",
    "ACTIVITY_MESSAGE": "activity-message",
    "ACTIVITY_REPLY": "activity-reply",
    "ACTIVITY_REPLY_LIKE": "activity-reply-like",
    "ACTIVITY_LIKE": "activity-like",
    "ACTIVITY_MENTION": "activity-mention",
    "ACTIVITY_REPLY_SUBSCRIBED": "activity-reply-subscribed",
    "FOLLOWING": "following",
    "RELATED_MEDIA_ADDITION": "related-media-addition",
    "MEDIA_DATA_CHANGE": "media-data-change",
    "MEDIA_MERGE": "media-merge",
    "MEDIA_DELETION": "media-deletion",
    "THREAD_COMMENT_MENTION": "thread-comment-mention",
    "THREAD_COMMENT_REPLY": "thread-comment-reply",
    "THREAD_COMMENT_LIKE": "thread-comment-like",
    "THREAD_SUBSCRIBED": "thread-subscribed",
    "THREAD_LIKE": "thread-like",
}


def map_notification(payload: Dict[str, Any], src: SourceTag) -> List[AnilistNotification]:
    page = payload.get("data", {}).get("Page") or {}
    rows = page.get("notifications") or []
    out: List[AnilistNotification] = []
    for r in rows:
        type_str = r.get("type") or ""
        kind = _NOTIFICATION_KIND_MAP.get(type_str, type_str.lower().replace("_", "-") or "unknown")
        contexts = r.get("contexts") or []
        if not isinstance(contexts, list):
            contexts = []
        user = r.get("user") or {}
        out.append(
            AnilistNotification(
                id=_field(r, "id", "notification"),
                kind=kind,
                type=type_str or None,
                contexts=contexts,
                context=r.get("context"),
                user_name=user.get("name") if isinstance(user, dict) else None,
                createdAt=r.get("createdAt"),
                source_tag=src,
            )
        )
    return out


def map_markdown(payload: Dict[str, Any], src: SourceTag) -> AnilistMarkdown:
    node = _require(payload.get("data", {}).get("Markdown"), "Markdown")
    return AnilistMarkdown(html=node.get("html", ""), source_tag=src)


def map_ani_chart_user(payload: Dict[str, Any], src: SourceTag) -> AnilistAniChartUser:
    node = _require(payload.get("data", {}).get("AniChartUser"), "AniChartUser")
    user = node.get("user") or {}
    return AnilistAniChartUser(
        user_id=user.get("id", 0),
        user_name=user.get("name", ""),
        settings=node.get("settings") or {},
        highlights=node.get("highlights") or {},
        source_tag=src,
    )


def map_media_list_collection_public(payload: Dict[str, Any], src: SourceTag) -> AnilistMediaListCollection:
    block = _require(payload.get("data", {}).get("MediaListCollection"), "MediaListCollection")
    user = block.get("user") or {}
    lists_raw = block.get("lists") or []
    groups: List[AnilistMediaListGroup] = []
    for grp in lists_raw:
        entries = grp.get("entries") or []
        groups.append(
            AnilistMediaListGroup(
                name=grp.get("name") or "(unnamed)",
                status=grp.get("status"),
                entry_count=len(entries),
            )
        )
    return AnilistMediaListCollection(
        user_id=user.get("id"),
        user_name=user.get("name"),
        lists=groups,
        source_tag=src,
    )
