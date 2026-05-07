"""
Capture Trace.moe fixtures.

The /me endpoint does not consume monthly quota and is captured 15
times to vary the quotaUsed snapshot. The /search endpoint consumes
quota; we capture 15 times against varied imgur URLs (anonymous tier
allows ~100/month, so 15 is well within budget).
"""

from __future__ import annotations

import sys
import time

import requests

from tools.fixtures.capture import capture


BASE = "https://api.trace.moe"
PACE = 1.5  # very polite; concurrency 1 only allows 1 in flight


# Imgur images known to map to anime frames (collected via prior probes
# and trace.moe README). 15 distinct URLs → 15 distinct results.
IMGUR_PROBES = [
    ("zLxHIeo", "moonlight-mile-frame"),
    ("qIKgDwS", "anime-frame-2"),
    ("aD7tA3W", "anime-frame-3"),
    ("9G1aRAH", "anime-frame-4"),
    ("3NDdfek", "anime-frame-5"),
    ("rZWzMaZ", "anime-frame-6"),
    ("SwIcUbT", "anime-frame-7"),
    ("d0KkQ3d", "anime-frame-8"),
    ("GVHbQGc", "anime-frame-9"),
    ("X2DfqdR", "anime-frame-10"),
    ("ScYzcSq", "anime-frame-11"),
    ("4G3O9hl", "anime-frame-12"),
    ("Z4yt5UA", "anime-frame-13"),
    ("CWoDQt3", "anime-frame-14"),
    ("kNbGNs9", "anime-frame-15"),
    ("nonexistent-xyz", "image-fetch-fail"),
]


def main() -> int:
    total = 0

    print("-- /me (15 fixtures, no quota cost)")
    for i in range(1, 16):
        capture(
            backend="trace",
            path_slug="me",
            label=f"call-{i:02d}",
            method="GET",
            url=f"{BASE}/me",
            pace_seconds=PACE,
        )
        total += 1
        print(f"  [{i:02d}/15] /me snapshot")

    print("-- /search (consumes ~15 quota)")
    for i, (imgur_id, label) in enumerate(IMGUR_PROBES, 1):
        url = f"{BASE}/search?anilistInfo&url=https%3A%2F%2Fi.imgur.com%2F{imgur_id}.jpg"
        capture(
            backend="trace",
            path_slug="search",
            label=label,
            method="GET",
            url=url,
            pace_seconds=PACE,
        )
        total += 1
        print(f"  [{i:02d}/{len(IMGUR_PROBES)}] {label}")

    # /me one more time to capture the post-search quota state.
    capture(
        backend="trace",
        path_slug="me",
        label="post-search-quota",
        method="GET",
        url=f"{BASE}/me",
        pace_seconds=PACE,
    )
    total += 1

    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
