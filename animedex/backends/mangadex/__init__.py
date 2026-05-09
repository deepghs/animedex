"""High-level MangaDex Python API.

Wraps the five anonymous JSON read endpoints listed in the
project's mid-tier roadmap: search / show / feed / chapter / cover.
The ``pages`` (At-Home reader) endpoint is intentionally not
wrapped here — it carries short-lived base URLs and HTTP/2
concurrency caps that warrant their own module in a later phase.

MangaDex's catalogue is scanlation-driven, which means legal
posture varies per series. The project's posture is to surface
upstream metadata as-is; downstream consumers decide what to do
with it.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import mangadex as _raw_mangadex
from animedex.backends.mangadex._auth import MangaDexCredentials, get_bearer_token
from animedex.backends.mangadex.models import (
    MangaDexChapter,
    MangaDexCover,
    MangaDexManga,
    MangaDexResource,
    MangaDexUser,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="mangadex",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a MangaDex GET, parse the body, validate the envelope.

    :return: ``(parsed_payload_dict, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` if the body is not
                       text, ``upstream-shape`` when ``result`` is
                       ``"error"``.
    """
    raw = _raw_mangadex.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="mangadex",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - mangadex returns JSON
        raise ApiError("mangadex returned a non-text body", backend="mangadex", reason="upstream-decode")
    if raw.status == 401 or raw.status == 403:
        raise ApiError(
            f"mangadex {raw.status} on {path} (rejected credentials)",
            backend="mangadex",
            reason="auth-required",
        )
    if raw.status == 404:
        raise ApiError(f"mangadex 404 on {path}", backend="mangadex", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"mangadex {raw.status} on {path}", backend="mangadex", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(f"mangadex returned non-JSON body: {exc}", backend="mangadex", reason="upstream-decode") from exc
    # MangaDex wraps the body as {"result": "ok"|"error", "data": ..., "errors": [...]}.
    # Surface result=="error" as a typed ApiError so callers branch on .reason.
    if payload.get("result") == "error":
        msg = "mangadex error"
        errs = payload.get("errors") or []
        if errs and isinstance(errs[0], dict):
            msg = errs[0].get("title") or errs[0].get("detail") or msg
        raise ApiError(f"mangadex: {msg}", backend="mangadex", reason="upstream-shape")
    return payload, _src(raw)


def _data(payload: dict) -> Any:
    """Pull the ``data`` block out of a MangaDex envelope."""
    if "data" not in payload:
        raise ApiError("mangadex response missing 'data' key", backend="mangadex", reason="upstream-shape")
    return payload["data"]


def _list(payload: dict) -> List[dict]:
    """Pull a list-of-resources from the envelope, tolerating
    single-resource responses by wrapping them."""
    rows = _data(payload)
    if rows is None:
        return []
    if isinstance(rows, list):
        return rows
    return [rows]


# ---------- /manga ----------


def show(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexManga:
    """Fetch one manga by its MangaDex UUID via ``/manga/{id}``.

    :param id: MangaDex UUID (string; not numeric).
    :type id: str
    :return: Typed manga resource, lossless against the upstream
              JSON:API ``data`` block.
    :rtype: MangaDexManga
    """
    payload, src = _fetch(f"/manga/{id}", config=config, **kw)
    return MangaDexManga.model_validate({**_data(payload), "source_tag": src})


def search(
    title: str,
    *,
    limit: int = 10,
    offset: int = 0,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexManga]:
    """Search manga by free-text title via ``/manga?title=<title>``.

    :param title: Search phrase.
    :type title: str
    :param limit: Max rows per page (defaults to ``10``).
    :type limit: int
    :param offset: Pagination offset.
    :type offset: int
    :return: List of typed manga resources.
    :rtype: list[MangaDexManga]
    """
    params = {"title": title, "limit": limit, "offset": offset}
    payload, src = _fetch("/manga", params=params, config=config, **kw)
    return [MangaDexManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def feed(
    id: str,
    *,
    limit: int = 20,
    offset: int = 0,
    lang: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexChapter]:
    """List chapters for one manga via ``/manga/{id}/feed``.

    :param id: MangaDex manga UUID.
    :type id: str
    :param limit: Max rows per page (defaults to ``20``).
    :type limit: int
    :param offset: Pagination offset.
    :type offset: int
    :param lang: Optional ISO-639 language filter (e.g. ``"en"``).
                  When set, filters via ``translatedLanguage[]=<lang>``.
    :type lang: str or None
    :return: List of typed chapter resources.
    :rtype: list[MangaDexChapter]
    """
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if lang is not None:
        params["translatedLanguage[]"] = lang
    payload, src = _fetch(f"/manga/{id}/feed", params=params, config=config, **kw)
    return [MangaDexChapter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /chapter ----------


def chapter(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexChapter:
    """Fetch one chapter by its UUID via ``/chapter/{id}``.

    :param id: MangaDex chapter UUID.
    :type id: str
    :return: Typed chapter resource.
    :rtype: MangaDexChapter
    """
    payload, src = _fetch(f"/chapter/{id}", config=config, **kw)
    return MangaDexChapter.model_validate({**_data(payload), "source_tag": src})


# ---------- /cover ----------


def cover(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexCover:
    """Fetch one cover by its UUID via ``/cover/{id}``.

    The returned resource carries a ``fileName`` attribute; the
    public cover URL is composed as
    ``https://uploads.mangadex.org/covers/<manga-id>/<fileName>``.

    :param id: MangaDex cover UUID.
    :type id: str
    :return: Typed cover resource.
    :rtype: MangaDexCover
    """
    payload, src = _fetch(f"/cover/{id}", config=config, **kw)
    return MangaDexCover.model_validate({**_data(payload), "source_tag": src})


# ---------- /manga/<aux> ----------


def aggregate(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """Volume + chapter aggregation tree via ``/manga/{id}/aggregate``.

    Returns the manga's chapters grouped by volume, structured as
    ``volumes -> chapters -> count``. The shape is upstream-specific
    (not a JSON:API resource); surfaces as :class:`MangaDexResource`
    with attributes carrying the aggregation tree.
    """
    payload, src = _fetch(f"/manga/{id}/aggregate", config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)  # envelope wrapper, leave the rest
    return MangaDexResource.model_validate({"id": id, "type": "manga-aggregate", "attributes": body, "source_tag": src})


def recommendation(id: str, *, config: Optional[Config] = None, **kw) -> List[MangaDexResource]:
    """Manga recommendations for one manga via
    ``/manga/{id}/recommendation``.
    """
    payload, src = _fetch(f"/manga/{id}/recommendation", config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def random_manga(*, config: Optional[Config] = None, **kw) -> MangaDexManga:
    """Random manga via ``/manga/random``."""
    payload, src = _fetch("/manga/random", config=config, **kw)
    return MangaDexManga.model_validate({**_data(payload), "source_tag": src})


def manga_tag(*, config: Optional[Config] = None, **kw) -> List[MangaDexResource]:
    """The full tag taxonomy via ``/manga/tag``."""
    payload, src = _fetch("/manga/tag", config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /chapter, /cover (collection search) ----------


def chapter_search(*, limit: int = 10, offset: int = 0, config: Optional[Config] = None, **kw) -> List[MangaDexChapter]:
    """Search chapters via ``/chapter``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    payload, src = _fetch("/chapter", params=params, config=config, **kw)
    return [MangaDexChapter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def cover_search(*, limit: int = 10, offset: int = 0, config: Optional[Config] = None, **kw) -> List[MangaDexCover]:
    """Search covers via ``/cover``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    payload, src = _fetch("/cover", params=params, config=config, **kw)
    return [MangaDexCover.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /author ----------


def author_search(
    *, limit: int = 10, offset: int = 0, name: Optional[str] = None, config: Optional[Config] = None, **kw
) -> List[MangaDexResource]:
    """Search authors via ``/author``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if name:
        params["name"] = name
    payload, src = _fetch("/author", params=params, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def author(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """One author by UUID via ``/author/{id}``."""
    payload, src = _fetch(f"/author/{id}", config=config, **kw)
    return MangaDexResource.model_validate({**_data(payload), "source_tag": src})


# ---------- /group (scanlation group) ----------


def group_search(
    *, limit: int = 10, offset: int = 0, name: Optional[str] = None, config: Optional[Config] = None, **kw
) -> List[MangaDexResource]:
    """Search scanlation groups via ``/group``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if name:
        params["name"] = name
    payload, src = _fetch("/group", params=params, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def group(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """One scanlation group by UUID via ``/group/{id}``."""
    payload, src = _fetch(f"/group/{id}", config=config, **kw)
    return MangaDexResource.model_validate({**_data(payload), "source_tag": src})


# ---------- /list (custom lists) ----------


def list_show(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """One custom list by UUID via ``/list/{id}``.

    Public custom lists are anonymous-readable; private ones return
    403 / 404 without a token.
    """
    payload, src = _fetch(f"/list/{id}", config=config, **kw)
    return MangaDexResource.model_validate({**_data(payload), "source_tag": src})


def list_feed(
    id: str, *, limit: int = 10, offset: int = 0, config: Optional[Config] = None, **kw
) -> List[MangaDexChapter]:
    """Chapter feed for one custom list via ``/list/{id}/feed``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    payload, src = _fetch(f"/list/{id}/feed", params=params, config=config, **kw)
    return [MangaDexChapter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /user (public read) ----------


def user(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """One user by UUID via ``/user/{id}`` (public profile)."""
    payload, src = _fetch(f"/user/{id}", config=config, **kw)
    return MangaDexResource.model_validate({**_data(payload), "source_tag": src})


def user_lists(
    id: str, *, limit: int = 10, offset: int = 0, config: Optional[Config] = None, **kw
) -> List[MangaDexResource]:
    """One user's public custom lists via ``/user/{id}/list``."""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    payload, src = _fetch(f"/user/{id}/list", params=params, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /statistics ----------


def statistics_manga(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """Read / follow / rating stats for one manga via
    ``/statistics/manga/{id}``."""
    payload, src = _fetch(f"/statistics/manga/{id}", config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)
    return MangaDexResource.model_validate(
        {"id": id, "type": "manga-statistics", "attributes": body, "source_tag": src}
    )


def statistics_manga_batch(
    *, manga: Optional[List[str]] = None, config: Optional[Config] = None, **kw
) -> MangaDexResource:
    """Stats for many manga at once via
    ``/statistics/manga?manga[]=<id>&manga[]=...``."""
    params: Dict[str, Any] = {}
    if manga:
        params["manga[]"] = list(manga)
    payload, src = _fetch("/statistics/manga", params=params, config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)
    return MangaDexResource.model_validate(
        {"id": None, "type": "manga-statistics-batch", "attributes": body, "source_tag": src}
    )


def statistics_chapter(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """Read stats for one chapter via ``/statistics/chapter/{id}``."""
    payload, src = _fetch(f"/statistics/chapter/{id}", config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)
    return MangaDexResource.model_validate(
        {"id": id, "type": "chapter-statistics", "attributes": body, "source_tag": src}
    )


def statistics_chapter_batch(
    *, chapter: Optional[List[str]] = None, config: Optional[Config] = None, **kw
) -> MangaDexResource:
    """Stats for many chapters at once via
    ``/statistics/chapter?chapter[]=<id>&chapter[]=...``."""
    params: Dict[str, Any] = {}
    if chapter:
        params["chapter[]"] = list(chapter)
    payload, src = _fetch("/statistics/chapter", params=params, config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)
    return MangaDexResource.model_validate(
        {"id": None, "type": "chapter-statistics-batch", "attributes": body, "source_tag": src}
    )


def statistics_group(id: str, *, config: Optional[Config] = None, **kw) -> MangaDexResource:
    """Stats for one scanlation group via ``/statistics/group/{id}``."""
    payload, src = _fetch(f"/statistics/group/{id}", config=config, **kw)
    body = payload if isinstance(payload, dict) else {}
    body.pop("result", None)
    return MangaDexResource.model_validate(
        {"id": id, "type": "group-statistics", "attributes": body, "source_tag": src}
    )


# ---------- /report ----------


def report_reasons(category: str, *, config: Optional[Config] = None, **kw) -> List[MangaDexResource]:
    """Available report reasons for a category via
    ``/report/reasons/{category}``.

    Categories: ``manga`` / ``chapter`` / ``scanlation_group`` /
    ``user`` / ``author``.
    """
    payload, src = _fetch(f"/report/reasons/{category}", config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /ping ----------


# ---------- /user (authenticated) ----------


def _authed_fetch(
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
):
    """``_fetch()`` variant that injects a Bearer token resolved
    via :func:`animedex.backends.mangadex._auth.get_bearer_token`.

    Token resolution order: explicit ``creds=`` argument →
    ``ANIMEDEX_MANGADEX_CREDS`` env var → ``config``'s token store
    entry under ``"mangadex"``. The token is cached in process memory
    (15-minute lifetime per upstream) so a session of authenticated
    calls does not re-hit the OAuth endpoint per request.
    """
    bearer = get_bearer_token(creds, config=config)
    headers = dict(kw.pop("headers", None) or {})
    headers["Authorization"] = f"Bearer {bearer}"
    return _fetch(path, params=params, config=config, headers=headers, **kw)


def me(*, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw) -> MangaDexUser:
    """Authenticated current user via ``/user/me``.

    :return: Typed user resource.
    :rtype: MangaDexUser
    """
    payload, src = _authed_fetch("/user/me", creds=creds, config=config, **kw)
    return MangaDexUser.model_validate({**_data(payload), "source_tag": src})


def my_follows_manga(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexManga]:
    """Manga the authenticated user is following via
    ``/user/follows/manga``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/follows/manga", params=params, creds=creds, config=config, **kw)
    return [MangaDexManga.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def is_following_manga(
    id: str, *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> bool:
    """Whether the authenticated user follows manga ``id`` via
    ``/user/follows/manga/{id}`` (200 → ``True``; 404 → ``False``)."""
    try:
        _authed_fetch(f"/user/follows/manga/{id}", creds=creds, config=config, **kw)
        return True
    except ApiError as exc:
        if exc.reason == "not-found":
            return False
        raise


def my_follows_group(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexResource]:
    """Scanlation groups the authenticated user is following via
    ``/user/follows/group``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/follows/group", params=params, creds=creds, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def is_following_group(
    id: str, *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> bool:
    """Whether the authenticated user follows scanlation group
    ``id`` via ``/user/follows/group/{id}``."""
    try:
        _authed_fetch(f"/user/follows/group/{id}", creds=creds, config=config, **kw)
        return True
    except ApiError as exc:
        if exc.reason == "not-found":
            return False
        raise


def my_follows_user(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexResource]:
    """Users the authenticated user is following via
    ``/user/follows/user``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/follows/user", params=params, creds=creds, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def is_following_user(
    id: str, *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> bool:
    """Whether the authenticated user follows user ``id`` via
    ``/user/follows/user/{id}``."""
    try:
        _authed_fetch(f"/user/follows/user/{id}", creds=creds, config=config, **kw)
        return True
    except ApiError as exc:
        if exc.reason == "not-found":
            return False
        raise


def my_follows_list(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexResource]:
    """Custom lists the authenticated user is following via
    ``/user/follows/list``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/follows/list", params=params, creds=creds, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def my_follows_manga_feed(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexChapter]:
    """Chapter feed for the manga the authenticated user follows via
    ``/user/follows/manga/feed``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/follows/manga/feed", params=params, creds=creds, config=config, **kw)
    return [MangaDexChapter.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def my_lists(
    *,
    limit: int = 20,
    offset: int = 0,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[MangaDexResource]:
    """The authenticated user's own custom lists via ``/user/list``."""
    params = {"limit": limit, "offset": offset}
    payload, src = _authed_fetch("/user/list", params=params, creds=creds, config=config, **kw)
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def my_history(
    *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> List[MangaDexResource]:
    """The authenticated user's reading history via ``/user/history``.

    The upstream returns a list of ``{chapterId, readDate}`` entries
    wrapped in the standard envelope; the rich shape round-trips them
    via :class:`MangaDexResource`'s catch-all ``attributes``.
    """
    payload, src = _authed_fetch("/user/history", creds=creds, config=config, **kw)
    rows = payload.get("ratings") or _data(payload) or []
    if not isinstance(rows, list):
        rows = [rows]
    return [MangaDexResource.model_validate({**row, "source_tag": src}) for row in rows if isinstance(row, dict)]


def my_manga_status(
    *,
    status: Optional[str] = None,
    creds: Optional[MangaDexCredentials] = None,
    config: Optional[Config] = None,
    **kw,
) -> Dict[str, str]:
    """Reading-status map for every manga the authenticated user has
    interacted with, via ``/manga/status``.

    The upstream returns ``{result, statuses: {manga-uuid: status}}``;
    this helper returns the inner ``statuses`` map directly. Pass
    ``status="reading"`` (or ``"on_hold"`` / ``"plan_to_read"`` /
    ``"dropped"`` / ``"re_reading"`` / ``"completed"``) to filter.

    :return: Dict mapping manga UUID → reading-status label.
    :rtype: dict[str, str]
    """
    params: Dict[str, Any] = {}
    if status:
        params["status"] = status
    payload, _src_tag = _authed_fetch("/manga/status", params=params or None, creds=creds, config=config, **kw)
    statuses = payload.get("statuses")
    if statuses is None:
        return {}
    # MangaDex sometimes returns ``statuses: []`` for an empty result
    # (a JSON-list-as-empty-object idiom from PHP-style serialisers);
    # normalise that to the dict shape callers expect.
    if isinstance(statuses, list) and not statuses:
        return {}
    if not isinstance(statuses, dict):
        raise ApiError("mangadex /manga/status returned non-dict statuses", backend="mangadex", reason="upstream-shape")
    return statuses


def my_manga_status_by_id(
    id: str, *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> Optional[str]:
    """Reading status for one manga via ``/manga/{id}/status``.

    :return: The status string, or ``None`` when the user has never
              interacted with this manga.
    :rtype: str or None
    """
    payload, _src_tag = _authed_fetch(f"/manga/{id}/status", creds=creds, config=config, **kw)
    return payload.get("status")


def my_manga_read_markers(
    id: str, *, creds: Optional[MangaDexCredentials] = None, config: Optional[Config] = None, **kw
) -> List[str]:
    """Chapter-IDs the authenticated user has marked read for one
    manga, via ``/manga/{id}/read``.

    :return: List of chapter UUIDs.
    :rtype: list[str]
    """
    payload, _src_tag = _authed_fetch(f"/manga/{id}/read", creds=creds, config=config, **kw)
    rows = payload.get("data") or []
    if not isinstance(rows, list):
        return []
    return [str(x) for x in rows]


def ping(*, config: Optional[Config] = None, **kw) -> str:
    """Liveness probe via ``/ping``. Returns the upstream's plain
    text body (typically ``"pong"``) so callers can confirm the
    upstream is reachable cheaply."""
    raw = _raw_mangadex.call(path="/ping", config=config, **kw)
    if raw.body_text is None:  # pragma: no cover - ping always returns text
        return ""
    return raw.body_text.strip()


def selftest() -> bool:
    """Smoke-test the public MangaDex Python API (signatures only,
    no network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [
        show,
        search,
        feed,
        chapter,
        cover,
        aggregate,
        recommendation,
        random_manga,
        manga_tag,
        chapter_search,
        cover_search,
        author_search,
        author,
        group_search,
        group,
        list_show,
        list_feed,
        user,
        user_lists,
        me,
        my_follows_manga,
        is_following_manga,
        my_follows_group,
        is_following_group,
        my_follows_user,
        is_following_user,
        my_follows_list,
        my_follows_manga_feed,
        my_lists,
        my_history,
        my_manga_status,
        my_manga_status_by_id,
        my_manga_read_markers,
        statistics_manga,
        statistics_manga_batch,
        statistics_chapter,
        statistics_chapter_batch,
        statistics_group,
        report_reasons,
        ping,
    ]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
