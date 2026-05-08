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
from animedex.backends.mangadex.models import (
    MangaDexChapter,
    MangaDexCover,
    MangaDexManga,
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


def selftest() -> bool:
    """Smoke-test the public MangaDex Python API (signatures only,
    no network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [show, search, feed, chapter, cover]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
