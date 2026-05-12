"""Prewarm the local aggregate-command cache from committed fixtures.

This helper exists for documentation captures. It lets the aggregate
demo tapes render real ``animedex search``, ``animedex show``,
``animedex season``, and ``animedex schedule`` commands without
depending on live upstream availability, rate-limit state, or network
egress during recording.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from animedex.api._dispatch import _signature, resolve_base_url
from animedex.backends.anilist._queries import Q_SCHEDULE
from animedex.cache.sqlite import SqliteCache, default_ttl_seconds


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "test" / "fixtures"

SearchShowSpec = Tuple[str, str]
CalendarSpec = Tuple[str, str, str, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int]]


SEARCH_SHOW_SPECS: Tuple[SearchShowSpec, ...] = (
    ("anilist/graphql/23-search-frieren-type-anime.yaml", "anilist"),
    ("jikan/anime_search/17-frieren-tv-limit2.yaml", "jikan"),
    ("kitsu/anime_search/17-frieren-limit2.yaml", "kitsu"),
    ("shikimori/animes_search/17-frieren-limit2.yaml", "shikimori"),
    ("anilist/graphql/28-manga-search-berserk.yaml", "anilist"),
    ("mangadex/manga_search/01-berserk.yaml", "mangadex"),
    ("shikimori/mangas_search/02-berserk-limit2.yaml", "shikimori"),
    ("anilist/graphql/26-staff-search-yamada.yaml", "anilist"),
    ("jikan/people_search/02-miyazaki-limit2.yaml", "jikan"),
    ("shikimori/people_search/02-miyazaki-limit2.yaml", "shikimori"),
    ("jikan/anime_full/01-frieren-52991.yaml", "jikan"),
    ("shikimori/characters_by_id/01-frieren-184947.yaml", "shikimori"),
    ("shikimori/studios/01-all.yaml", "shikimori"),
    ("shikimori/publishers/01-all.yaml", "shikimori"),
)


CALENDAR_SPECS: Tuple[CalendarSpec, ...] = (
    (
        "anilist/season_matrix/58-2024-spring.yaml",
        "anilist",
        "season",
        "/",
        None,
        {"query": Q_SCHEDULE, "variables": {"year": 2024, "season": "SPRING", "perPage": 5}},
        5,
    ),
    (
        "jikan/season_matrix/58-2024-spring.yaml",
        "jikan",
        "season",
        "/seasons/2024/spring",
        {"limit": 5},
        None,
        5,
    ),
    (
        "jikan/schedules/03-schedule-sunday.yaml",
        "jikan",
        "schedules",
        "/schedules",
        {"filter": "sunday", "limit": 3},
        None,
        3,
    ),
    (
        "jikan/schedules/01-schedule-monday.yaml",
        "jikan",
        "schedules",
        "/schedules",
        {"filter": "monday", "limit": 3},
        None,
        3,
    ),
    (
        "jikan/schedules/04-schedule-tuesday.yaml",
        "jikan",
        "schedules",
        "/schedules",
        {"filter": "tuesday", "limit": 3},
        None,
        3,
    ),
)


def _load_fixture(rel_path: str) -> Dict[str, Any]:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


def _body_bytes(response: Dict[str, Any]) -> bytes:
    if response.get("body_text") is not None:
        return response["body_text"].encode("utf-8")
    if response.get("body_json") is not None:
        return json.dumps(response["body_json"], ensure_ascii=False).encode("utf-8")
    if response.get("body_b64") is not None:
        return base64.b64decode(response["body_b64"])
    return b""


def _request_body(request: Dict[str, Any]) -> Optional[bytes]:
    if request.get("raw_body_b64") is not None:
        return base64.b64decode(request["raw_body_b64"])
    return None


def _crop_json_body(body_json: Dict[str, Any], *, backend: str, kind: str, limit: int) -> Dict[str, Any]:
    out = json.loads(json.dumps(body_json))
    if backend == "anilist" and kind == "season":
        page = out.get("data", {}).get("Page") or {}
        media = page.get("media")
        if isinstance(media, list):
            page["media"] = media[:limit]
    elif backend == "jikan" and kind in {"season", "schedules"}:
        data = out.get("data")
        if isinstance(data, list):
            out["data"] = data[:limit]
        pagination = out.get("pagination")
        if isinstance(pagination, dict):
            items = pagination.get("items")
            if isinstance(items, dict):
                items["count"] = min(int(items.get("count", limit) or limit), limit)
                items["per_page"] = limit
    return out


def _prewarm_search_show(cache: SqliteCache) -> int:
    count = 0
    for rel_path, backend in SEARCH_SHOW_SPECS:
        fixture = _load_fixture(rel_path)
        request = fixture["request"]
        response = fixture["response"]
        signature = _signature(
            request["method"],
            request["url"],
            request.get("params"),
            request.get("json_body"),
            _request_body(request),
        )
        cache.set_with_meta(
            backend,
            signature,
            _body_bytes(response),
            response_headers=response.get("headers") or {},
            ttl_seconds=24 * 3600,
        )
        count += 1
    return count


def _prewarm_calendar(cache: SqliteCache) -> int:
    count = 0
    for rel_path, backend, kind, path, params, json_body, limit in CALENDAR_SPECS:
        fixture = _load_fixture(rel_path)
        body_json = fixture["response"]["body_json"]
        if limit is not None:
            body_json = _crop_json_body(body_json, backend=backend, kind=kind, limit=limit)
        full_url = resolve_base_url(backend).rstrip("/") + path
        signature = _signature(
            "POST" if backend == "anilist" else "GET",
            full_url,
            params,
            json_body,
            None,
        )
        cache.set_with_meta(
            backend,
            signature,
            json.dumps(body_json, ensure_ascii=False).encode("utf-8"),
            response_headers=fixture["response"].get("headers") or {},
            ttl_seconds=default_ttl_seconds("list" if kind == "season" else "schedule"),
        )
        count += 1
    return count


def main() -> int:
    """Write aggregate demo fixtures into the platform-default cache."""
    cache = SqliteCache()
    try:
        count = _prewarm_search_show(cache) + _prewarm_calendar(cache)
    finally:
        cache_path = cache.path
        cache.close()
    print(f"prewarmed {count} aggregate fixtures into {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
