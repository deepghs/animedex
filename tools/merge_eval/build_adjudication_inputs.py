"""Build compact inputs for season merge adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "test" / "fixtures" / "aggregate" / "season_matrix" / "candidates"
OUT_DIR = ROOT / "test" / "fixtures" / "aggregate" / "season_matrix" / "adjudication_inputs"


def _compact_row(row: dict) -> dict:
    return {
        "index": row.get("index"),
        "id": row.get("id"),
        "mal_id": row.get("mal_id"),
        "title": row.get("title"),
        "english": row.get("english"),
        "native": row.get("native"),
        "synonyms": row.get("synonyms") or [],
        "format": row.get("format"),
        "episodes": row.get("episodes"),
        "season": row.get("season"),
        "year": row.get("year"),
        "start_date": row.get("start_date"),
        "status": row.get("status"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build compact codex adjudication shard inputs.")
    parser.add_argument("--shards", type=int, default=8)
    args = parser.parse_args(argv)

    paths = sorted(CANDIDATES.glob("*.json"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for shard in range(args.shards):
        seasons = []
        for path in paths[shard:: args.shards]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            seasons.append(
                {
                    "year": payload["year"],
                    "season": payload["season"],
                    "anilist": [_compact_row(row) for row in payload["anilist"]],
                    "jikan": [_compact_row(row) for row in payload["jikan"]],
                }
            )
        out = {"shard": shard, "seasons": seasons}
        out_path = OUT_DIR / f"shard-{shard:02d}.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(out_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
