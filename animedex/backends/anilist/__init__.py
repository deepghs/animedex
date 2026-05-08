"""High-level AniList Python API.

Each public function corresponds to a subcommand of
``animedex anilist``. The function takes typed arguments, calls
:func:`animedex.api.anilist.call` to issue the GraphQL request,
parses the body, and returns a typed dataclass from
:mod:`animedex.backends.anilist.models`.

Token-required Query roots (``Viewer``, ``Notification``,
``Markdown``, ``AniChartUser``) are exposed as functions that
unconditionally raise :class:`ApiError(reason="auth-required")`
until the OAuth flow lands; the corresponding CLI subcommands
surface that as a clean error.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import anilist as _raw_anilist
from animedex.backends.anilist import _mapper as _mp
from animedex.backends.anilist import _queries as _q
from animedex.backends.anilist.models import (
    AnilistActivity,
    AnilistActivityReply,
    AnilistAiringSchedule,
    AnilistAnime,
    AnilistCharacter,
    AnilistExternalLinkSource,
    AnilistFollowEntry,
    AnilistGenreCollection,
    AnilistMediaListCollection,
    AnilistMediaListEntry,
    AnilistMediaTag,
    AnilistMediaTrend,
    AnilistRecommendation,
    AnilistReview,
    AnilistSiteStatistics,
    AnilistStaff,
    AnilistStudio,
    AnilistThread,
    AnilistThreadComment,
    AnilistUser,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


def _src(envelope) -> SourceTag:
    """Compose a :class:`SourceTag` from a dispatcher envelope."""
    return SourceTag(
        backend="anilist",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _gql(query: str, variables: Optional[Dict[str, Any]] = None, *, config: Optional[Config] = None, **kw):
    """Issue a raw GraphQL call and parse the body.

    :return: ``(parsed_payload_dict, source_tag)``.
    :raises ApiError: When the firewall rejected the call, the body
                       is non-decodable, or AniList returned a
                       top-level GraphQL error.
    """
    raw = _raw_anilist.call(query=query, variables=variables, config=config, **kw)
    if raw.firewall_rejected is not None:
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="anilist",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:
        raise ApiError("AniList returned a non-text body", backend="anilist", reason="upstream-decode")
    # Gate on HTTP status BEFORE parsing the body. AniList is
    # well-behaved on 200 (a 200 with ``errors[]`` and ``data: null``
    # is the legitimate GraphQL-error shape), but on 5xx the body may
    # be a Cloudflare HTML error page or a non-GraphQL JSON like
    # ``{"error": "internal"}``. Without this gate, HTML would crash
    # ``_json.loads`` with an uncaught ``JSONDecodeError``; non-
    # GraphQL JSON would fall into the mapper and surface as a
    # misleading ``not-found`` ("Media not found" when the server is
    # actually 5xx-ing).
    if raw.status >= 500:
        raise ApiError(
            f"AniList {raw.status}",
            backend="anilist",
            reason="upstream-error",
        )
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        # 4xx (or anything else) with a non-JSON body: still
        # preferable to a raw decode error.
        raise ApiError(
            f"AniList returned a non-JSON body (status {raw.status})",
            backend="anilist",
            reason="upstream-decode",
        ) from exc
    if "errors" in payload and payload.get("data") is None:
        msg = (payload["errors"][0] or {}).get("message", "GraphQL error")
        raise ApiError(msg, backend="anilist", reason="graphql-error")
    return payload, _src(raw)


# ---------- core entities ----------


def show(id: int, *, config: Optional[Config] = None, **kw) -> AnilistAnime:
    """Fetch a single AniList Media (anime/manga) by id.

    :param id: AniList Media id.
    :type id: int
    :param config: Optional :class:`Config` overrides.
    :type config: Config or None
    :return: Rich AniList record.
    :rtype: AnilistAnime
    :raises ApiError: ``reason='not-found'`` when the id is unknown.
    """
    payload, src = _gql(_q.Q_MEDIA_BY_ID, {"id": id}, config=config, **kw)
    return _mp.map_media(payload, src)


def search(q: str, *, page: int = 1, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistAnime]:
    """Search anime by title.

    :param q: Free-text query.
    :type q: str
    :param page: 1-based page index.
    :type page: int
    :param per_page: Page size; AniList caps at 50.
    :type per_page: int
    :return: List of matching AniList records.
    :rtype: list[AnilistAnime]
    """
    payload, src = _gql(_q.Q_MEDIA_SEARCH, {"q": q, "page": page, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_media_list(payload, src)


def character(id: int, *, config: Optional[Config] = None, **kw) -> AnilistCharacter:
    """Fetch a single AniList Character by id."""
    payload, src = _gql(_q.Q_CHARACTER_BY_ID, {"id": id}, config=config, **kw)
    return _mp.map_character(payload, src)


def character_search(q: str, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistCharacter]:
    """Search AniList characters by name."""
    payload, src = _gql(_q.Q_CHARACTER_SEARCH, {"q": q, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_character_list(payload, src)


def staff(id: int, *, config: Optional[Config] = None, **kw) -> AnilistStaff:
    """Fetch a single AniList Staff by id."""
    payload, src = _gql(_q.Q_STAFF_BY_ID, {"id": id}, config=config, **kw)
    return _mp.map_staff(payload, src)


def staff_search(q: str, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistStaff]:
    """Search AniList staff by name."""
    payload, src = _gql(_q.Q_STAFF_SEARCH, {"q": q, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_staff_list(payload, src)


def studio(id: int, *, config: Optional[Config] = None, **kw) -> AnilistStudio:
    """Fetch a single AniList Studio by id."""
    payload, src = _gql(_q.Q_STUDIO_BY_ID, {"id": id}, config=config, **kw)
    return _mp.map_studio(payload, src)


def studio_search(q: str, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistStudio]:
    """Search AniList studios by name."""
    payload, src = _gql(_q.Q_STUDIO_SEARCH, {"q": q, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_studio_list(payload, src)


def schedule(
    year: int, season: str, *, per_page: int = 10, config: Optional[Config] = None, **kw
) -> List[AnilistAnime]:
    """List anime airing in the given season.

    :param year: Calendar year.
    :type year: int
    :param season: One of ``"WINTER"``, ``"SPRING"``, ``"SUMMER"``,
                    ``"FALL"`` (case-insensitive).
    :type season: str
    """
    season_up = season.upper()
    if season_up not in ("WINTER", "SPRING", "SUMMER", "FALL"):
        raise ApiError(
            f"unknown season: {season!r}; expected WINTER/SPRING/SUMMER/FALL",
            backend="anilist",
            reason="bad-args",
        )
    payload, src = _gql(
        _q.Q_SCHEDULE,
        {"year": year, "season": season_up, "perPage": min(per_page, 50)},
        config=config,
        **kw,
    )
    return _mp.map_media_list(payload, src)


def trending(*, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistAnime]:
    """List currently-trending AniList anime."""
    payload, src = _gql(_q.Q_TRENDING, {"perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_media_list(payload, src)


def user(name: str, *, config: Optional[Config] = None, **kw) -> AnilistUser:
    """Fetch an AniList user profile by name (public endpoint)."""
    payload, src = _gql(_q.Q_USER_BY_NAME, {"name": name}, config=config, **kw)
    return _mp.map_user(payload, src)


def user_search(q: str, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistUser]:
    """Search AniList users by name."""
    payload, src = _gql(_q.Q_USER_SEARCH, {"q": q, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_user_list(payload, src)


# ---------- collections ----------


def genre_collection(*, config: Optional[Config] = None, **kw) -> AnilistGenreCollection:
    """The full AniList genre vocabulary."""
    payload, src = _gql(_q.Q_GENRE_COLLECTION, None, config=config, **kw)
    return _mp.map_genre_collection(payload, src)


def media_tag_collection(*, config: Optional[Config] = None, **kw) -> List[AnilistMediaTag]:
    """The full AniList tag taxonomy with categories + spoiler flags."""
    payload, src = _gql(_q.Q_MEDIA_TAG_COLLECTION, None, config=config, **kw)
    return _mp.map_media_tag_collection(payload, src)


def site_statistics(*, config: Optional[Config] = None, **kw) -> AnilistSiteStatistics:
    """AniList-wide entity counts (latest snapshot row per category)."""
    payload, src = _gql(_q.Q_SITE_STATISTICS, None, config=config, **kw)
    return _mp.map_site_statistics(payload, src)


def external_link_source_collection(
    media_type: str = "ANIME", type: str = "STREAMING", *, config: Optional[Config] = None, **kw
) -> List[AnilistExternalLinkSource]:
    """List the registered external sites (streaming, info, social).

    :param media_type: ``"ANIME"`` or ``"MANGA"``.
    :param type: ``"STREAMING"``, ``"INFO"``, or ``"SOCIAL"``.
    """
    payload, src = _gql(
        _q.Q_EXTERNAL_LINK_SOURCE_COLLECTION,
        {"mediaType": media_type, "type": type},
        config=config,
        **kw,
    )
    return _mp.map_external_link_source(payload, src)


# ---------- long tail ----------


def airing_schedule(
    *,
    media_id: Optional[int] = None,
    not_yet_aired: Optional[bool] = None,
    per_page: int = 10,
    config: Optional[Config] = None,
    **kw,
) -> List[AnilistAiringSchedule]:
    """Upcoming-episode schedule, optionally filtered."""
    payload, src = _gql(
        _q.Q_AIRING_SCHEDULE,
        {"mediaId": media_id, "notYetAired": not_yet_aired, "perPage": min(per_page, 50)},
        config=config,
        **kw,
    )
    return _mp.map_airing_schedule(payload, src)


def media_trend(media_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistMediaTrend]:
    """Daily score / popularity trend rows for one Media."""
    payload, src = _gql(_q.Q_MEDIA_TREND, {"mediaId": media_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_media_trend(payload, src)


def review(media_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistReview]:
    """User reviews for a given Media id."""
    payload, src = _gql(_q.Q_REVIEW, {"mediaId": media_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_review(payload, src)


def recommendation(
    media_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw
) -> List[AnilistRecommendation]:
    """Media-to-media recommendations rooted at ``media_id``."""
    payload, src = _gql(_q.Q_RECOMMENDATION, {"mediaId": media_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_recommendation(payload, src)


def thread(q: str, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistThread]:
    """Search forum threads."""
    payload, src = _gql(_q.Q_THREAD, {"q": q, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_thread(payload, src)


def thread_comment(
    thread_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw
) -> List[AnilistThreadComment]:
    """Comments on a single forum thread."""
    payload, src = _gql(_q.Q_THREAD_COMMENT, {"threadId": thread_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_thread_comment(payload, src)


def activity(*, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistActivity]:
    """Recent global activity (text + list)."""
    payload, src = _gql(_q.Q_ACTIVITY, {"perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_activity(payload, src)


def activity_reply(
    activity_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw
) -> List[AnilistActivityReply]:
    """Replies to a public activity item."""
    payload, src = _gql(
        _q.Q_ACTIVITY_REPLY, {"activityId": activity_id, "perPage": min(per_page, 50)}, config=config, **kw
    )
    return _mp.map_activity_reply(payload, src)


def following(user_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistFollowEntry]:
    """Users a given user follows."""
    payload, src = _gql(_q.Q_FOLLOWING, {"userId": user_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_follow(payload, "following", src)


def follower(user_id: int, *, per_page: int = 10, config: Optional[Config] = None, **kw) -> List[AnilistFollowEntry]:
    """Users following a given user."""
    payload, src = _gql(_q.Q_FOLLOWER, {"userId": user_id, "perPage": min(per_page, 50)}, config=config, **kw)
    return _mp.map_follow(payload, "followers", src)


def media_list_public(
    user_name: str, *, type: str = "ANIME", per_page: int = 10, config: Optional[Config] = None, **kw
) -> List[AnilistMediaListEntry]:
    """A public user's MediaList rows (read-only).

    :param user_name: AniList username.
    :param type: ``"ANIME"`` or ``"MANGA"``.
    """
    payload, src = _gql(
        _q.Q_MEDIA_LIST_PUBLIC,
        {"userName": user_name, "type": type, "perPage": min(per_page, 50)},
        config=config,
        **kw,
    )
    return _mp.map_media_list_public(payload, src)


def media_list_collection_public(
    user_name: str, *, type: str = "ANIME", config: Optional[Config] = None, **kw
) -> AnilistMediaListCollection:
    """A public user's full list grouped by status."""
    payload, src = _gql(
        _q.Q_MEDIA_LIST_COLLECTION_PUBLIC,
        {"userName": user_name, "type": type},
        config=config,
        **kw,
    )
    return _mp.map_media_list_collection_public(payload, src)


# ---------- token-required stubs ----------
#
# These four AniList Query roots require an OAuth token. The token
# flow has not landed yet; until then each function raises a typed
# ``ApiError(reason="auth-required")`` so callers can branch on the
# typed reason rather than parsing a free-text message.


def viewer(*, config: Optional[Config] = None, **kw):
    """Current user profile. Requires authentication.

    :raises ApiError: Always, until the OAuth flow lands.
    """
    raise ApiError(
        "Viewer requires authentication; the OAuth flow has not landed yet.",
        backend="anilist",
        reason="auth-required",
    )


def notification(*, config: Optional[Config] = None, **kw):
    """Notifications. Token-required."""
    raise ApiError(
        "Notification requires authentication; the OAuth flow has not landed yet.",
        backend="anilist",
        reason="auth-required",
    )


def markdown(text: str, *, config: Optional[Config] = None, **kw):
    """AniList-markdown to HTML. Token-required."""
    raise ApiError(
        "Markdown requires authentication; the OAuth flow has not landed yet.",
        backend="anilist",
        reason="auth-required",
    )


def ani_chart_user(*, config: Optional[Config] = None, **kw):
    """AniChart user state. Token-required."""
    raise ApiError(
        "AniChartUser requires authentication; the OAuth flow has not landed yet.",
        backend="anilist",
        reason="auth-required",
    )


def selftest() -> bool:
    """Smoke-test the AniList Python API.

    Without hitting the network: confirms every public callable
    exists and the auth-required stubs raise correctly.
    """
    import inspect

    public = [
        show,
        search,
        character,
        character_search,
        staff,
        staff_search,
        studio,
        studio_search,
        schedule,
        trending,
        user,
        user_search,
        genre_collection,
        media_tag_collection,
        site_statistics,
        external_link_source_collection,
        airing_schedule,
        media_trend,
        review,
        recommendation,
        thread,
        thread_comment,
        activity,
        activity_reply,
        following,
        follower,
        media_list_public,
        media_list_collection_public,
    ]
    for fn in public:
        assert callable(fn), f"missing function: {fn}"
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"

    # Token-required stubs raise auth-required.
    for fn in (viewer, notification, ani_chart_user):
        try:
            fn()
        except ApiError as exc:
            assert exc.reason == "auth-required"
        else:
            raise AssertionError(f"{fn.__name__} should have raised auth-required")
    try:
        markdown("hello")
    except ApiError as exc:
        assert exc.reason == "auth-required"
    return True
