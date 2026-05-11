"""Prewarm the local aggregate-command cache from committed fixtures.

This helper exists for documentation captures. It lets ``aggregate.tape``
render real ``animedex search`` and ``animedex show`` commands without
depending on live upstream availability, rate-limit state, or network
egress during the recording.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Optional

import yaml

from animedex.api._dispatch import _signature
from animedex.cache.sqlite import SqliteCache


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "test" / "fixtures"


SPECS = (
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


def _body_bytes(response: dict[str, Any]) -> bytes:
    if response.get("body_text") is not None:
        return response["body_text"].encode("utf-8")
    if response.get("body_json") is not None:
        import json

        return json.dumps(response["body_json"], ensure_ascii=False).encode("utf-8")
    if response.get("body_b64") is not None:
        return base64.b64decode(response["body_b64"])
    return b""


def _request_body(request: dict[str, Any]) -> Optional[bytes]:
    if request.get("raw_body_b64") is not None:
        return base64.b64decode(request["raw_body_b64"])
    return None


def main() -> int:
    """Write aggregate demo fixture bodies into the platform-default cache."""
    cache = SqliteCache()
    try:
        count = 0
        for rel_path, backend in SPECS:
            fixture = yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))
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
    finally:
        cache_path = cache.path
        cache.close()
    print(f"prewarmed {count} aggregate fixtures into {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
