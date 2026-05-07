"""
Capture Kitsu fixtures (kitsu.io/api/edge canonical, kitsu.app
included as a parity probe). Polite ~1.0 sec pace.
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


BASE_IO = "https://kitsu.io/api/edge"
BASE_APP = "https://kitsu.app/api/edge"
PACE = 1.0
HEADERS = {"Accept": "application/vnd.api+json"}


PATHS = [
    (
        "anime_search",
        [
            ("frieren", "/anime?filter%5Btext%5D=Frieren&page%5Blimit%5D=2"),
            ("naruto", "/anime?filter%5Btext%5D=Naruto&page%5Blimit%5D=2"),
            ("berserk", "/anime?filter%5Btext%5D=Berserk&page%5Blimit%5D=2"),
            ("cowboy-bebop", "/anime?filter%5Btext%5D=Cowboy+Bebop&page%5Blimit%5D=2"),
            ("evangelion", "/anime?filter%5Btext%5D=Evangelion&page%5Blimit%5D=2"),
            ("attack-on-titan", "/anime?filter%5Btext%5D=Attack+on+Titan&page%5Blimit%5D=2"),
            ("demon-slayer", "/anime?filter%5Btext%5D=Demon+Slayer&page%5Blimit%5D=2"),
            ("steins-gate", "/anime?filter%5Btext%5D=Steins+Gate&page%5Blimit%5D=2"),
            ("nichijou", "/anime?filter%5Btext%5D=Nichijou&page%5Blimit%5D=2"),
            ("k-on", "/anime?filter%5Btext%5D=K-On&page%5Blimit%5D=2"),
            ("ghibli-spirited-away", "/anime?filter%5Btext%5D=Spirited+Away&page%5Blimit%5D=2"),
            ("with-include-streaming", "/anime?filter%5Btext%5D=Frieren&include=streamingLinks&page%5Blimit%5D=1"),
            ("with-include-mappings", "/anime?filter%5Btext%5D=Frieren&include=mappings&page%5Blimit%5D=1"),
            ("page-2", "/anime?filter%5Btext%5D=Naruto&page%5Boffset%5D=2&page%5Blimit%5D=2"),
            ("filter-by-year", "/anime?filter%5Bseason_year%5D=2023&page%5Blimit%5D=2"),
            ("subtype-tv", "/anime?filter%5Bsubtype%5D=TV&page%5Blimit%5D=2"),
        ],
    ),
    (
        "anime_by_id",
        [
            ("frieren-46474", "/anime/46474"),
            ("naruto-11", "/anime/11"),
            ("cowboy-bebop-1", "/anime/1"),
            ("attack-on-titan-7442", "/anime/7442"),
            ("steins-gate-6448", "/anime/6448"),
            ("evangelion-3", "/anime/3"),
            ("k-on-3936", "/anime/3936"),
            ("nichijou-5783", "/anime/5783"),
            ("madoka-7311", "/anime/7311"),
            ("hellsing-129", "/anime/129"),
            ("vinland-saga-41370", "/anime/41370"),
            ("demon-slayer-41370-tanjiro", "/anime/42203"),
            ("fma-brotherhood-3936", "/anime/3936"),
            ("monster-1", "/anime/1855"),
            ("one-piece-12", "/anime/12"),
            ("404-not-found", "/anime/9999999999"),
        ],
    ),
    (
        "anime_streaming_links",
        [
            ("frieren-46474", "/anime/46474/streaming-links"),
            ("naruto-11", "/anime/11/streaming-links"),
            ("attack-on-titan-7442", "/anime/7442/streaming-links"),
            ("steins-gate-6448", "/anime/6448/streaming-links"),
            ("evangelion-3", "/anime/3/streaming-links"),
            ("cowboy-bebop-1", "/anime/1/streaming-links"),
            ("madoka-7311", "/anime/7311/streaming-links"),
            ("hellsing-129", "/anime/129/streaming-links"),
            ("k-on-3936", "/anime/3936/streaming-links"),
            ("nichijou-5783", "/anime/5783/streaming-links"),
            ("vinland-saga-41370", "/anime/41370/streaming-links"),
            ("demon-slayer-42203", "/anime/42203/streaming-links"),
            ("monster-1855", "/anime/1855/streaming-links"),
            ("one-piece-12", "/anime/12/streaming-links"),
            ("invalid-id", "/anime/9999999999/streaming-links"),
            ("with-include-streamer", "/anime/46474/streaming-links?include=streamer"),
        ],
    ),
    (
        "anime_mappings",
        [
            ("frieren-46474", "/anime/46474/mappings?page%5Blimit%5D=10"),
            ("naruto-11", "/anime/11/mappings?page%5Blimit%5D=10"),
            ("attack-on-titan-7442", "/anime/7442/mappings?page%5Blimit%5D=10"),
            ("steins-gate-6448", "/anime/6448/mappings?page%5Blimit%5D=10"),
            ("evangelion-3", "/anime/3/mappings?page%5Blimit%5D=10"),
            ("cowboy-bebop-1", "/anime/1/mappings?page%5Blimit%5D=10"),
            ("madoka-7311", "/anime/7311/mappings?page%5Blimit%5D=10"),
            ("hellsing-129", "/anime/129/mappings?page%5Blimit%5D=10"),
            ("k-on-3936", "/anime/3936/mappings?page%5Blimit%5D=10"),
            ("nichijou-5783", "/anime/5783/mappings?page%5Blimit%5D=10"),
            ("vinland-saga-41370", "/anime/41370/mappings?page%5Blimit%5D=10"),
            ("demon-slayer-42203", "/anime/42203/mappings?page%5Blimit%5D=10"),
            ("monster-1855", "/anime/1855/mappings?page%5Blimit%5D=10"),
            ("one-piece-12", "/anime/12/mappings?page%5Blimit%5D=10"),
            ("404-id", "/anime/9999999999/mappings"),
            ("filter-by-external-site", "/mappings?filter%5BexternalSite%5D=anilist%2Fanime&page%5Blimit%5D=2"),
        ],
    ),
    (
        "host_app_parity",
        [
            ("frieren-46474-on-app", "/anime/46474"),
            ("naruto-11-on-app", "/anime/11"),
            ("cowboy-bebop-1-on-app", "/anime/1"),
            ("attack-on-titan-7442-on-app", "/anime/7442"),
            ("steins-gate-6448-on-app", "/anime/6448"),
            ("evangelion-3-on-app", "/anime/3"),
            ("madoka-7311-on-app", "/anime/7311"),
            ("hellsing-129-on-app", "/anime/129"),
            ("k-on-3936-on-app", "/anime/3936"),
            ("nichijou-5783-on-app", "/anime/5783"),
            ("vinland-saga-41370-on-app", "/anime/41370"),
            ("demon-slayer-42203-on-app", "/anime/42203"),
            ("monster-1855-on-app", "/anime/1855"),
            ("one-piece-12-on-app", "/anime/12"),
            ("frieren-streaming-on-app", "/anime/46474/streaming-links"),
            ("frieren-mappings-on-app", "/anime/46474/mappings?page%5Blimit%5D=5"),
        ],
    ),
]


def main() -> int:
    total = sum(len(group) for _, group in PATHS)
    print(f"Kitsu: {total} fixtures")
    for path_slug, group in PATHS:
        print(f"-- {path_slug} ({len(group)} fixtures)")
        base = BASE_APP if path_slug == "host_app_parity" else BASE_IO
        for i, (label, suffix) in enumerate(group, 1):
            capture(
                backend="kitsu",
                path_slug=path_slug,
                label=label,
                method="GET",
                url=base + suffix,
                headers=HEADERS,
                pace_seconds=PACE,
            )
            print(f"  [{i:02d}/{len(group)}] {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
