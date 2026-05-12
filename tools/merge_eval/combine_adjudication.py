"""Combine codex adjudication shard outputs into one expected file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "test" / "fixtures" / "aggregate" / "season_matrix" / "expected_matches.json"


def _season_key(season: dict) -> str:
    return f"{season['year']}-{season['season']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Combine adjudicated season match shards.")
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    seasons = {}
    for input_path in args.inputs:
        payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
        for season in payload.get("seasons", []):
            key = _season_key(season)
            if key in seasons:
                raise ValueError(f"duplicate adjudicated season: {key}")
            seen_anilist = set()
            seen_jikan = set()
            for match in season.get("matches", []):
                pair = (match["anilist_index"], match["jikan_index"])
                if match["anilist_index"] in seen_anilist:
                    raise ValueError(f"{key} has duplicate AniList index {match['anilist_index']}")
                if match["jikan_index"] in seen_jikan:
                    raise ValueError(f"{key} has duplicate Jikan index {match['jikan_index']}")
                seen_anilist.add(match["anilist_index"])
                seen_jikan.add(match["jikan_index"])
                if pair[0] < 0 or pair[1] < 0:
                    raise ValueError(f"{key} has negative index pair {pair}")
            seasons[key] = {
                "year": season["year"],
                "season": season["season"],
                "matches": sorted(season.get("matches", []), key=lambda item: (item["anilist_index"], item["jikan_index"])),
            }
    if len(seasons) != 64:
        raise ValueError(f"expected 64 adjudicated seasons, got {len(seasons)}")
    output = {"seasons": [seasons[key] for key in sorted(seasons)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.relative_to(ROOT))
    print(f"seasons={len(output['seasons'])} matches={sum(len(s['matches']) for s in output['seasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
