"""Prewarm the local Shikimori cache from committed fixtures.

This helper exists for documentation captures. It lets ``shikimori.tape``
render the real ``animedex shikimori ...`` commands without depending on
live Shikimori availability, rate-limit state, or network egress.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from animedex.api._dispatch import _signature
from animedex.cache.sqlite import SqliteCache


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "test" / "fixtures" / "shikimori"
BASE_URL = "https://shikimori.io"

FixtureSpec = Tuple[str, str, Optional[Dict[str, Any]]]

SPECS: Tuple[FixtureSpec, ...] = (
    ("animes_by_id/01-frieren-52991.yaml", "/api/animes/52991", None),
    ("animes_search/01-frieren.yaml", "/api/animes", {"search": "Frieren", "limit": 2}),
    ("calendar/01-limit-1.yaml", "/api/calendar", {"limit": 1}),
    ("mangas_search/01-berserk.yaml", "/api/mangas", {"search": "Berserk", "limit": 2}),
    ("mangas_by_id/01-berserk-2.yaml", "/api/mangas/2", None),
    ("ranobe_search/01-monogatari.yaml", "/api/ranobe", {"search": "Monogatari", "limit": 2}),
    ("ranobe_by_id/01-monogatari-second-season-23751.yaml", "/api/ranobe/23751", None),
    ("clubs_search/01-anime.yaml", "/api/clubs", {"search": "anime", "limit": 3}),
    ("clubs_by_id/01-site-development-1.yaml", "/api/clubs/1", None),
    ("publishers/01-all.yaml", "/api/publishers", None),
    ("people_search/01-hayao-miyazaki.yaml", "/api/people/search", {"search": "Hayao Miyazaki"}),
    ("people_by_id/01-hayao-miyazaki-1870.yaml", "/api/people/1870", None),
)


def main() -> int:
    """Write Shikimori fixture bodies into the platform-default cache."""
    cache = SqliteCache()
    try:
        count = 0
        for rel_path, path, params in SPECS:
            fixture = yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))
            body = json.dumps(fixture["response"]["body_json"], ensure_ascii=False).encode("utf-8")
            signature = _signature("GET", f"{BASE_URL}{path}", params, None, None)
            cache.set_with_meta(
                "shikimori",
                signature,
                body,
                response_headers=fixture["response"].get("headers") or {},
                ttl_seconds=24 * 3600,
            )
            count += 1
    finally:
        cache_path = cache.path
        cache.close()
    print(f"prewarmed {count} Shikimori fixtures into {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
