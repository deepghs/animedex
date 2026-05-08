"""Capture Jikan ``/anime/{id}/full`` + ``/seasons/now`` + ``/top/anime`` +
``/random/anime`` + ``/schedules`` fixtures for the high-level backend layer mappers.

the substrate API layer already captured ``/anime/{id}`` (without /full); the
``/full`` variant exposes the Jikan-specific signals (rank, members,
broadcast, openings/endings, producers, licensors, demographics) that
land in :class:`animedex.backends.jikan.models.JikanAnime` per Issue
#5 §2.3.

Pace: 1.1 s between requests (60/min cap = 1.0s minimum).
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


URL = "https://api.jikan.moe/v4"
PACE = 1.1


# Same MAL ids covered by phase 1 anime_by_id, so mapper tests can
# cross-validate /anime/{id} vs /anime/{id}/full.
FULL_CASES = [
    ("frieren", 52991),
    ("steins-gate", 9253),
    ("attack-on-titan", 16498),
    ("fma-brotherhood", 5114),
    ("cowboy-bebop", 1),
    ("naruto", 20),
    ("one-piece", 21),
    ("demon-slayer", 38000),
    ("anohana", 9989),
    ("spirited-away", 199),
]


SCHEDULE_CASES = [
    ("schedule-monday", "monday"),
    ("schedule-friday", "friday"),
]


def main() -> int:
    i = 0
    for label, mal_id in FULL_CASES:
        i += 1
        path = capture(
            backend="jikan",
            path_slug="anime_full",
            label=f"{label}-{mal_id}",
            method="GET",
            url=f"{URL}/anime/{mal_id}/full",
            pace_seconds=PACE if i > 1 else 0,
        )
        print(f"  [{i:02d}] /anime/{mal_id}/full -> {path.name}")

    i += 1
    path = capture(
        backend="jikan",
        path_slug="seasons_now",
        label="now",
        method="GET",
        url=f"{URL}/seasons/now?limit=10",
        pace_seconds=PACE,
    )
    print(f"  [{i:02d}] /seasons/now")

    i += 1
    path = capture(
        backend="jikan",
        path_slug="top_anime",
        label="top10",
        method="GET",
        url=f"{URL}/top/anime?limit=10",
        pace_seconds=PACE,
    )
    print(f"  [{i:02d}] /top/anime")

    # /random/anime is non-deterministic; capture twice to cover the
    # mapper across two random rolls.
    for n in range(1, 3):
        i += 1
        path = capture(
            backend="jikan",
            path_slug="random_anime",
            label=f"random-{n:02d}",
            method="GET",
            url=f"{URL}/random/anime",
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] /random/anime ({n})")

    for label, day in SCHEDULE_CASES:
        i += 1
        path = capture(
            backend="jikan",
            path_slug="schedules",
            label=label,
            method="GET",
            url=f"{URL}/schedules?filter={day}&limit=5",
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] /schedules?filter={day}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
