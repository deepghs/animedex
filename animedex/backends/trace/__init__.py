"""High-level Trace.moe Python API.

Exposes screenshot search (URL or upload bytes) plus the quota probe.
The mapper unconditionally drops the upstream's caller-IP echo from
``/me`` (review M1 vector).
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import List, Optional

from animedex.api import trace as _raw_trace
from animedex.config import Config
from animedex.models.anime import AnimeTitle
from animedex.models.common import ApiError, SourceTag
from animedex.models.trace import TraceHit, TraceQuota


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="trace",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _parse(envelope) -> dict:
    if envelope.firewall_rejected is not None:
        raise ApiError(
            envelope.firewall_rejected.get("message", "request blocked"),
            backend="trace",
            reason=envelope.firewall_rejected.get("reason", "firewall"),
        )
    if envelope.body_text is None:
        raise ApiError("Trace.moe returned a non-text body", backend="trace", reason="upstream-decode")
    return _json.loads(envelope.body_text)


def _coerce_int(v) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v)
    raise ApiError(f"unexpected non-int value: {v!r}", backend="trace", reason="upstream-shape")


def quota(*, config: Optional[Config] = None, **kw) -> TraceQuota:
    """Fetch ``/me``: caller's quota state.

    The upstream's ``id`` field (the caller IP) is unconditionally
    dropped — it never lands in the returned object or the cache row.
    """
    raw = _raw_trace.call(path="/me", config=config, **kw)
    payload = _parse(raw)
    return TraceQuota(
        priority=int(payload["priority"]),
        concurrency=int(payload["concurrency"]),
        quota=int(payload["quota"]),
        quota_used=_coerce_int(payload["quotaUsed"]),
        source=_src(raw),
    )


def search(
    image_url: Optional[str] = None,
    *,
    raw_bytes: Optional[bytes] = None,
    anilist_info: bool = False,
    cut_borders: bool = False,
    anilist_id: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[TraceHit]:
    """Search ``/search``.

    :param image_url: Public URL of the screenshot to identify.
                       Mutually exclusive with ``raw_bytes``.
    :param raw_bytes: Raw image / video bytes to upload.
    :param anilist_info: When ``True``, each hit carries an inline
                          ``AnimeTitle`` from AniList — saves a
                          follow-up round-trip.
    :param cut_borders: When ``True``, trace.moe strips letterboxing
                         before matching.
    :param anilist_id: When set, restrict matches to a specific show
                        (useful when you already know the series).
    """
    if image_url and raw_bytes:
        raise ApiError("provide image_url OR raw_bytes, not both", backend="trace", reason="bad-args")
    if not image_url and not raw_bytes:
        raise ApiError("either image_url or raw_bytes is required", backend="trace", reason="bad-args")

    qs = []
    if anilist_info:
        qs.append("anilistInfo")
    if cut_borders:
        qs.append("cutBorders")
    if anilist_id is not None:
        qs.append(f"anilistID={anilist_id}")

    if image_url:
        from urllib.parse import quote

        qs.append(f"url={quote(image_url, safe='')}")
        path = "/search?" + "&".join(qs)
        raw = _raw_trace.call(path=path, config=config, **kw)
    else:
        path = "/search?" + "&".join(qs) if qs else "/search"
        raw = _raw_trace.call(path=path, method="POST", raw_body=raw_bytes, config=config, **kw)

    payload = _parse(raw)
    src = _src(raw)
    hits: List[TraceHit] = []
    for r in payload.get("result", []) or []:
        anilist_obj = r.get("anilist")
        anilist_id_val = anilist_obj if isinstance(anilist_obj, int) else (anilist_obj or {}).get("id")
        if anilist_id_val is None:
            continue
        title_block = None
        if isinstance(anilist_obj, dict) and isinstance(anilist_obj.get("title"), dict):
            t = anilist_obj["title"]
            romaji = t.get("romaji") or t.get("english") or t.get("native") or ""
            title_block = AnimeTitle(romaji=romaji, english=t.get("english"), native=t.get("native"))
        hits.append(
            TraceHit(
                anilist_id=int(anilist_id_val),
                anilist_title=title_block,
                similarity=float(r.get("similarity", 0.0)),
                episode=str(r["episode"]) if r.get("episode") is not None else None,
                start_at_seconds=float(r.get("from", 0.0)),
                frame_at_seconds=float(r.get("at", r.get("from", 0.0))),
                end_at_seconds=float(r.get("to", 0.0)),
                episode_filename=r.get("filename"),
                episode_duration_seconds=(float(r["duration"]) if r.get("duration") is not None else None),
                preview_video_url=r.get("video"),
                preview_image_url=r.get("image"),
                source=src,
            )
        )
    return hits


def selftest() -> bool:
    """Smoke-test the Trace.moe API (signatures only, no network)."""
    import inspect

    for fn in (quota, search):
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
