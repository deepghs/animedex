"""Prewarm the local Quote cache from committed AnimeChan fixtures.

This helper exists for documentation captures. It lets ``quote.tape``
render the real ``animedex quote ...`` commands without consuming the
anonymous AnimeChan hourly quota.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from animedex.api._dispatch import _signature
from animedex.cache.sqlite import SqliteCache


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "test" / "fixtures" / "quote"

FixtureSpec = Tuple[str, str, Optional[Dict[str, Any]]]

SPECS: Tuple[FixtureSpec, ...] = (
    ("random/01-random.yaml", "https://api.animechan.io/v1/quotes/random", None),
    ("random_by_anime/01-naruto.yaml", "https://api.animechan.io/v1/quotes/random", {"anime": "Naruto"}),
    (
        "random_by_character/01-saitama.yaml",
        "https://api.animechan.io/v1/quotes/random",
        {"character": "Saitama"},
    ),
    ("quotes_by_anime/01-naruto-page-1.yaml", "https://api.animechan.io/v1/quotes", {"anime": "Naruto", "page": 1}),
    (
        "quotes_by_character/01-saitama-page-1.yaml",
        "https://api.animechan.io/v1/quotes",
        {"character": "Saitama", "page": 1},
    ),
    ("anime/01-one-punch-man-188.yaml", "https://api.animechan.io/v1/anime/188", None),
)


def main() -> int:
    """Write Quote fixture bodies into the platform-default cache."""
    cache = SqliteCache()
    try:
        count = 0
        for rel_path, full_url, params in SPECS:
            fixture = yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))
            body = json.dumps(fixture["response"]["body_json"], ensure_ascii=False).encode("utf-8")
            signature = _signature("GET", full_url, params, None, None)
            cache.set_with_meta(
                "quote",
                signature,
                body,
                response_headers=fixture["response"].get("headers") or {},
                ttl_seconds=24 * 3600,
            )
            count += 1
    finally:
        cache_path = cache.path
        cache.close()
    print(f"prewarmed {count} Quote fixtures into {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
