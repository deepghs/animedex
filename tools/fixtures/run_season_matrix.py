"""Capture AniList and Jikan season fixtures for merge evaluation.

The matrix covers every anime convention season from 2010 through
2025. It stores the fixtures under backend-specific ``season_matrix``
directories so they do not collide with the smaller smoke fixtures
used by existing tests.
"""

from __future__ import annotations

import argparse
import sys

from animedex.backends.anilist import _queries as anilist_queries
from tools.fixtures.capture import capture


ANILIST_URL = "https://graphql.anilist.co/"
JIKAN_BASE = "https://api.jikan.moe/v4"
SEASONS = ("winter", "spring", "summer", "fall")


def _label(year: int, season: str) -> str:
    return f"{year}-{season}"


def _capture_anilist(year: int, season: str, *, limit: int, overwrite: bool) -> None:
    capture(
        backend="anilist",
        path_slug="season_matrix",
        label=_label(year, season),
        method="POST",
        url=ANILIST_URL,
        headers={"Content-Type": "application/json"},
        json_body={
            "query": anilist_queries.Q_SCHEDULE,
            "variables": {"year": year, "season": season.upper(), "perPage": limit},
        },
        pace_seconds=0.0,
        overwrite=overwrite,
    )


def _capture_jikan(year: int, season: str, *, limit: int, overwrite: bool) -> None:
    capture(
        backend="jikan",
        path_slug="season_matrix",
        label=_label(year, season),
        method="GET",
        url=f"{JIKAN_BASE}/seasons/{year}/{season}?limit={limit}",
        pace_seconds=0.0,
        overwrite=overwrite,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture 2010-2025 season merge matrix fixtures.")
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--backend", choices=("all", "anilist", "jikan"), default="all")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    total = (args.end_year - args.start_year + 1) * len(SEASONS)
    print(f"Capturing {total} season slots per selected backend.")
    for year in range(args.start_year, args.end_year + 1):
        for season in SEASONS:
            label = _label(year, season)
            if args.backend in ("all", "anilist"):
                _capture_anilist(year, season, limit=args.limit, overwrite=args.overwrite)
                print(f"anilist {label}")
            if args.backend in ("all", "jikan"):
                _capture_jikan(year, season, limit=args.limit, overwrite=args.overwrite)
                print(f"jikan {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
