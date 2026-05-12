"""Prewarm the local cache for the aggregate calendar demo.

This helper exists for documentation captures. It lets
``docs/source/_static/gifs/aggregate.tape`` render the real
``animedex season`` and ``animedex schedule`` commands without
depending on live AniList or Jikan availability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from animedex.api._dispatch import resolve_base_url
from animedex.api._dispatch import _signature
from animedex.backends.anilist._queries import Q_SCHEDULE
from animedex.cache.sqlite import SqliteCache, default_ttl_seconds


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "test" / "fixtures"

FixtureSpec = Tuple[str, str, str, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int]]


def _crop_json_body(body_json: Dict[str, Any], *, backend: str, kind: str, limit: int) -> Dict[str, Any]:
    out = json.loads(json.dumps(body_json))
    if backend == "anilist" and kind == "season":
        page = out.get("data", {}).get("Page") or {}
        media = page.get("media")
        if isinstance(media, list):
            page["media"] = media[:limit]
    elif backend == "jikan" and kind == "season":
        data = out.get("data")
        if isinstance(data, list):
            out["data"] = data[:limit]
        pagination = out.get("pagination")
        if isinstance(pagination, dict):
            items = pagination.get("items")
            if isinstance(items, dict):
                items["count"] = min(int(items.get("count", limit) or limit), limit)
                items["per_page"] = limit
    elif backend == "jikan" and kind == "schedules":
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


def _load_fixture(rel_path: str) -> Dict[str, Any]:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


SPECS: Tuple[FixtureSpec, ...] = (
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


def main() -> int:
    """Write aggregate demo fixtures into the platform cache."""
    cache = SqliteCache()
    try:
        count = 0
        for rel_path, backend, kind, path, params, json_body, limit in SPECS:
            fixture = _load_fixture(rel_path)
            body_json = fixture["response"]["body_json"]
            if limit is not None:
                body_json = _crop_json_body(body_json, backend=backend, kind=kind, limit=limit)
            body = json.dumps(body_json, ensure_ascii=False).encode("utf-8")
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
                body,
                response_headers=fixture["response"].get("headers") or {},
                ttl_seconds=default_ttl_seconds("list" if kind == "season" else "schedule"),
            )
            count += 1
    finally:
        cache_path = cache.path
        cache.close()
    print(f"prewarmed {count} aggregate fixtures into {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
