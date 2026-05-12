"""Evaluate the deterministic season merge rule against adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from animedex.agg import calendar
from animedex.backends.anilist import _mapper as anilist_mapper
from animedex.backends.jikan.models import JikanAnime
from animedex.models.common import SourceTag


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "test" / "fixtures"
EXPECTED = FIXTURES / "aggregate" / "season_matrix" / "expected_matches.json"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _fixture_by_label(backend: str, label: str) -> Path:
    matches = sorted((FIXTURES / backend / "season_matrix").glob(f"*-{label}.yaml"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one {backend} fixture for {label}, found {len(matches)}")
    return matches[0]


def _src(backend: str, payload: dict) -> SourceTag:
    from datetime import datetime, timezone

    captured_at = payload.get("metadata", {}).get("captured_at")
    if isinstance(captured_at, str):
        fetched_at = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    else:
        fetched_at = datetime.now(timezone.utc)
    return SourceTag(backend=backend, fetched_at=fetched_at)


def _rows(label: str):
    anilist_payload = _load_yaml(_fixture_by_label("anilist", label))
    jikan_payload = _load_yaml(_fixture_by_label("jikan", label))
    anilist_rows = anilist_mapper.map_media_list(anilist_payload["response"]["body_json"], _src("anilist", anilist_payload))
    jikan_rows = [
        JikanAnime.model_validate({**row, "source_tag": _src("jikan", jikan_payload)})
        for row in jikan_payload["response"]["body_json"]["data"]
    ]
    return [row.to_common() for row in anilist_rows], [row.to_common() for row in jikan_rows]


def _predicted_pairs(anilist_rows, jikan_rows):
    pairs = set()
    for ai, left in enumerate(anilist_rows):
        best = None
        best_score = 0
        for ji, right in enumerate(jikan_rows):
            score = calendar._anime_match_score(left, right)
            if score > best_score:
                best = ji
                best_score = score
        if best is not None and best_score > 0:
            pairs.add((ai, best))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate season merge scoring against expected matches.")
    parser.add_argument("--limit-details", type=int, default=40)
    args = parser.parse_args(argv)

    expected_payload = json.loads(EXPECTED.read_text(encoding="utf-8"))
    false_negative = []
    false_positive = []
    total_expected = 0
    total_predicted = 0
    for season in expected_payload["seasons"]:
        label = f"{season['year']}-{season['season']}"
        anilist_rows, jikan_rows = _rows(label)
        expected = {(match["anilist_index"], match["jikan_index"]) for match in season["matches"]}
        predicted = _predicted_pairs(anilist_rows, jikan_rows)
        total_expected += len(expected)
        total_predicted += len(predicted)
        for pair in sorted(expected - predicted):
            false_negative.append((label, pair, anilist_rows[pair[0]].title.romaji, jikan_rows[pair[1]].title.romaji))
        for pair in sorted(predicted - expected):
            false_positive.append((label, pair, anilist_rows[pair[0]].title.romaji, jikan_rows[pair[1]].title.romaji))
    print(f"expected={total_expected} predicted={total_predicted}")
    print(f"false_negative={len(false_negative)} false_positive={len(false_positive)}")
    for label, pair, left, right in false_negative[: args.limit_details]:
        print(f"FN {label} {pair}: {left!r} <> {right!r}")
    for label, pair, left, right in false_positive[: args.limit_details]:
        print(f"FP {label} {pair}: {left!r} <> {right!r}")
    return 0 if not false_negative and not false_positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
