"""
Capture Jikan v4 fixtures.

Multiple path families × 15+ fixtures each. Paced at 1.1 sec to stay
well under the 60/min cap.
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


BASE = "https://api.jikan.moe/v4"
PACE = 1.1


# (path_slug, list of (label, suffix-after-/v4))
PATHS = [
    (
        "anime_by_id",
        [
            ("frieren-52991", "/anime/52991"),
            ("cowboy-bebop-1", "/anime/1"),
            ("naruto-20", "/anime/20"),
            ("one-piece-21", "/anime/21"),
            ("attack-on-titan-16498", "/anime/16498"),
            ("death-note-1535", "/anime/1535"),
            ("steins-gate-9253", "/anime/9253"),
            ("vinland-saga-37521", "/anime/37521"),
            ("demon-slayer-38000", "/anime/38000"),
            ("fma-brotherhood-5114", "/anime/5114"),
            ("k-on-5680", "/anime/5680"),
            ("hellsing-270", "/anime/270"),
            ("nichijou-10165", "/anime/10165"),
            ("madoka-9756", "/anime/9756"),
            ("evangelion-30", "/anime/30"),
            ("404-not-found", "/anime/9999999999"),
        ],
    ),
    (
        "anime_search",
        [
            ("frieren-tv", "/anime?q=Frieren&type=tv&limit=3"),
            ("naruto-tv", "/anime?q=Naruto&type=tv&limit=3"),
            ("berserk", "/anime?q=Berserk&limit=3"),
            ("evangelion-movie", "/anime?q=Evangelion&type=movie&limit=3"),
            ("ghibli-rated-pg", "/anime?q=Ghibli&rating=pg&limit=3"),
            ("ova-format", "/anime?q=Hellsing&type=ova&limit=3"),
            ("by-genre-action", "/anime?genres=1&limit=3"),
            ("by-status-airing", "/anime?status=airing&limit=3"),
            ("by-rating-r", "/anime?rating=r&limit=3"),
            ("min-score-9", "/anime?min_score=9&limit=3&order_by=score&sort=desc"),
            ("year-2023", "/anime?start_date=2023-01-01&end_date=2023-12-31&limit=3"),
            ("page-2", "/anime?q=Naruto&page=2&limit=2"),
            ("with-letter-z", "/anime?letter=z&limit=3"),
            ("sort-popularity", "/anime?order_by=popularity&sort=asc&limit=3"),
            ("empty-search-no-q", "/anime?limit=2"),
            ("safe-for-work", "/anime?sfw=true&limit=2"),
        ],
    ),
    (
        "seasons",
        [
            ("2023-fall", "/seasons/2023/fall?limit=3"),
            ("2024-winter", "/seasons/2024/winter?limit=3"),
            ("2024-spring", "/seasons/2024/spring?limit=3"),
            ("2024-summer", "/seasons/2024/summer?limit=3"),
            ("2024-fall", "/seasons/2024/fall?limit=3"),
            ("2025-winter", "/seasons/2025/winter?limit=3"),
            ("2025-spring", "/seasons/2025/spring?limit=3"),
            ("2025-summer", "/seasons/2025/summer?limit=3"),
            ("2025-fall", "/seasons/2025/fall?limit=3"),
            ("2026-winter", "/seasons/2026/winter?limit=3"),
            ("2026-spring", "/seasons/2026/spring?limit=3"),
            ("now", "/seasons/now?limit=3"),
            ("upcoming", "/seasons/upcoming?limit=3"),
            ("filter-tv-only", "/seasons/2024/spring?filter=tv&limit=3"),
            ("page-2", "/seasons/2024/spring?page=2&limit=2"),
            ("invalid-year-99999", "/seasons/99999/spring?limit=2"),
        ],
    ),
    (
        "anime_characters",
        [
            ("frieren", "/anime/52991/characters"),
            ("cowboy-bebop", "/anime/1/characters"),
            ("naruto", "/anime/20/characters"),
            ("one-piece", "/anime/21/characters"),
            ("attack-on-titan", "/anime/16498/characters"),
            ("death-note", "/anime/1535/characters"),
            ("steins-gate", "/anime/9253/characters"),
            ("vinland-saga", "/anime/37521/characters"),
            ("demon-slayer", "/anime/38000/characters"),
            ("fma-brotherhood", "/anime/5114/characters"),
            ("k-on", "/anime/5680/characters"),
            ("hellsing", "/anime/270/characters"),
            ("nichijou", "/anime/10165/characters"),
            ("madoka", "/anime/9756/characters"),
            ("evangelion", "/anime/30/characters"),
            ("404-not-found", "/anime/9999999999/characters"),
        ],
    ),
    (
        "anime_episodes",
        [
            ("frieren", "/anime/52991/episodes?limit=3"),
            ("cowboy-bebop", "/anime/1/episodes?limit=3"),
            ("naruto", "/anime/20/episodes?limit=3"),
            ("attack-on-titan", "/anime/16498/episodes?limit=3"),
            ("steins-gate", "/anime/9253/episodes?limit=3"),
            ("demon-slayer", "/anime/38000/episodes?limit=3"),
            ("fma-brotherhood", "/anime/5114/episodes?limit=3"),
            ("vinland-saga", "/anime/37521/episodes?limit=3"),
            ("k-on", "/anime/5680/episodes?limit=3"),
            ("hellsing", "/anime/270/episodes?limit=3"),
            ("nichijou", "/anime/10165/episodes?limit=3"),
            ("madoka", "/anime/9756/episodes?limit=3"),
            ("evangelion", "/anime/30/episodes?limit=3"),
            ("death-note-page-2", "/anime/1535/episodes?page=2&limit=3"),
            ("one-piece-page-1", "/anime/21/episodes?limit=3"),
            ("404-not-found", "/anime/9999999999/episodes"),
        ],
    ),
]


def main() -> int:
    total = sum(len(group) for _, group in PATHS)
    print(f"Jikan: {total} fixtures across {len(PATHS)} path families")
    for path_slug, group in PATHS:
        print(f"-- {path_slug} ({len(group)} fixtures)")
        for i, (label, suffix) in enumerate(group, 1):
            url = BASE + suffix
            path = capture(
                backend="jikan",
                path_slug=path_slug,
                label=label,
                method="GET",
                url=url,
                pace_seconds=PACE,
            )
            print(f"  [{i:02d}/{len(group)}] {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
