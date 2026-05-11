"""Build season merge candidate files from captured fixtures.

The output is a compact JSON document per year/season containing
AniList and Jikan rows plus likely candidate pairs. Human or model
adjudicators can review these files without loading the full fixture
payloads.
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "test" / "fixtures"
OUT_DIR = FIXTURES / "aggregate" / "season_matrix" / "candidates"
SEASONS = ("winter", "spring", "summer", "fall")
TITLE_KEY_RE = re.compile(r"[^0-9a-z]+")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _fixture_by_label(backend: str, label: str) -> Path:
    matches = sorted((FIXTURES / backend / "season_matrix").glob(f"*-{label}.yaml"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one {backend} season_matrix fixture for {label}, found {len(matches)}")
    return matches[0]


def _title_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lowered = value.casefold().replace("&", " and ").replace("×", " x ")
    collapsed = TITLE_KEY_RE.sub(" ", lowered).strip()
    return " ".join(collapsed.split()) or None


def _title_values(row: dict, backend: str) -> List[str]:
    if backend == "anilist":
        title = row.get("title") or {}
        values = [title.get("romaji"), title.get("english"), title.get("native")]
        values.extend(row.get("synonyms") or [])
        return [value for value in values if value]
    values = [row.get("title"), row.get("title_english"), row.get("title_japanese")]
    values.extend(row.get("title_synonyms") or [])
    for title in row.get("titles") or []:
        if isinstance(title, dict) and title.get("title"):
            values.append(title["title"])
    return [value for value in values if value]


def _title_keys(row: dict, backend: str) -> List[str]:
    keys = []
    for value in _title_values(row, backend):
        key = _title_key(value)
        if key and key not in keys:
            keys.append(key)
    return keys


def _best_ratio(left_keys: Iterable[str], right_keys: Iterable[str]) -> float:
    best = 0.0
    for left in left_keys:
        for right in right_keys:
            best = max(best, SequenceMatcher(None, left, right).ratio())
    return best


def _anilist_rows(payload: dict) -> List[dict]:
    return payload["response"]["body_json"]["data"]["Page"]["media"]


def _jikan_rows(payload: dict) -> List[dict]:
    return payload["response"]["body_json"]["data"]


def _anime_row(row: dict, backend: str, idx: int) -> Dict[str, Any]:
    if backend == "anilist":
        title = row.get("title") or {}
        return {
            "backend": "anilist",
            "index": idx,
            "id": row.get("id"),
            "mal_id": row.get("idMal"),
            "title": title.get("romaji") or title.get("english") or title.get("native"),
            "english": title.get("english"),
            "native": title.get("native"),
            "synonyms": row.get("synonyms") or [],
            "format": row.get("format"),
            "episodes": row.get("episodes"),
            "season": row.get("season"),
            "year": row.get("seasonYear"),
            "start_date": row.get("startDate"),
            "status": row.get("status"),
        }
    return {
        "backend": "jikan",
        "index": idx,
        "id": row.get("mal_id"),
        "mal_id": row.get("mal_id"),
        "title": row.get("title"),
        "english": row.get("title_english"),
        "native": row.get("title_japanese"),
        "synonyms": row.get("title_synonyms") or [],
        "format": row.get("type"),
        "episodes": row.get("episodes"),
        "season": (row.get("season") or "").upper() or None,
        "year": row.get("year"),
        "start_date": ((row.get("aired") or {}).get("prop") or {}).get("from"),
        "status": row.get("status"),
    }


def _candidate_score(left: dict, right: dict) -> float:
    if left.get("idMal") and left.get("idMal") == right.get("mal_id"):
        return 10.0
    left_keys = _title_keys(left, "anilist")
    right_keys = _title_keys(right, "jikan")
    overlap = set(left_keys) & set(right_keys)
    ratio = _best_ratio(left_keys, right_keys)
    score = ratio
    if overlap:
        score += 2.0
    if left.get("seasonYear") == right.get("year"):
        score += 0.2
    if (left.get("season") or "").upper() == (right.get("season") or "").upper():
        score += 0.2
    if left.get("format") and right.get("type") and left.get("format") == str(right.get("type")).upper().replace(" ", "_"):
        score += 0.1
    return score


def build_one(year: int, season: str) -> Dict[str, Any]:
    label = f"{year}-{season}"
    anilist_fixture = _load(_fixture_by_label("anilist", label))
    jikan_fixture = _load(_fixture_by_label("jikan", label))
    anilist = _anilist_rows(anilist_fixture)
    jikan = _jikan_rows(jikan_fixture)
    candidates = []
    for ai, left in enumerate(anilist):
        scored = []
        for ji, right in enumerate(jikan):
            score = _candidate_score(left, right)
            if score >= 0.86:
                scored.append((score, ji, right))
        for score, ji, right in sorted(scored, reverse=True)[:5]:
            candidates.append(
                {
                    "anilist_index": ai,
                    "jikan_index": ji,
                    "score": round(score, 4),
                    "anilist": _anime_row(left, "anilist", ai),
                    "jikan": _anime_row(right, "jikan", ji),
                }
            )
    return {
        "year": year,
        "season": season,
        "anilist": [_anime_row(row, "anilist", idx) for idx, row in enumerate(anilist)],
        "jikan": [_anime_row(row, "jikan", idx) for idx, row in enumerate(jikan)],
        "candidates": candidates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build season merge candidate JSON files.")
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for year in range(args.start_year, args.end_year + 1):
        for season in SEASONS:
            payload = build_one(year, season)
            path = OUT_DIR / f"{year}-{season}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
