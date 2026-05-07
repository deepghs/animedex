"""
Capture ANN fixtures. 1 req/sec on api.xml; pace 1.1 sec.
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


BASE = "https://cdn.animenewsnetwork.com/encyclopedia"
PACE = 1.1


def main() -> int:
    total = 0

    print("-- by_anime_id (16)")
    by_id_cases = [
        ("id-1-angel-links", "?anime=1"),
        ("id-4-gatchaman", "?anime=4"),
        ("id-30-evangelion", "?anime=30"),
        ("id-100", "?anime=100"),
        ("id-500", "?anime=500"),
        ("id-1000", "?anime=1000"),
        ("id-2000", "?anime=2000"),
        ("id-5000", "?anime=5000"),
        ("id-10000", "?anime=10000"),
        ("id-15000", "?anime=15000"),
        ("id-20000", "?anime=20000"),
        ("id-25000", "?anime=25000"),
        ("id-30000", "?anime=30000"),
        ("id-38838-frieren", "?anime=38838"),
        ("id-99999999-missing", "?anime=99999999"),
        ("multi-id", "?anime=4&anime=30&anime=100"),
    ]
    for i, (label, qs) in enumerate(by_id_cases, 1):
        capture(backend="ann", path_slug="by_id",
                label=label, method="GET",
                url=f"{BASE}/api.xml{qs}",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/{len(by_id_cases)}] {label}")

    print("-- substring_search (16)")
    substring_cases = [
        ("frieren", "?anime=~Frieren"),
        ("naruto", "?anime=~Naruto"),
        ("ghibli", "?anime=~Ghibli"),
        ("cowboy-bebop", "?anime=~Cowboy+Bebop"),
        ("evangelion", "?anime=~Evangelion"),
        ("steins-gate", "?anime=~Steins+Gate"),
        ("k-on", "?anime=~K-On"),
        ("nichijou", "?anime=~Nichijou"),
        ("madoka", "?anime=~Madoka"),
        ("hellsing", "?anime=~Hellsing"),
        ("monster", "?anime=~Monster"),
        ("aria", "?anime=~Aria"),
        ("attack-on-titan", "?anime=~Attack"),
        ("demon-slayer", "?anime=~Demon+Slayer"),
        ("vinland-saga", "?anime=~Vinland"),
        ("nonexistent", "?anime=~ZZZZNonexistent"),
    ]
    for i, (label, qs) in enumerate(substring_cases, 1):
        capture(backend="ann", path_slug="substring_search",
                label=label, method="GET",
                url=f"{BASE}/api.xml{qs}",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/{len(substring_cases)}] {label}")

    print("-- reports (16)")
    report_cases = [
        ("anime-recently-modified-2", "?id=155&type=anime&nlist=2"),
        ("anime-recently-modified-5", "?id=155&type=anime&nlist=5"),
        ("anime-recently-modified-10", "?id=155&type=anime&nlist=10"),
        ("anime-recently-modified-20", "?id=155&type=anime&nlist=20"),
        ("anime-skip-5", "?id=155&type=anime&nlist=5&nskip=5"),
        ("anime-skip-10", "?id=155&type=anime&nlist=5&nskip=10"),
        ("manga-recently-modified", "?id=155&type=manga&nlist=5"),
        ("anime-search-frieren", "?id=155&type=anime&nlist=5&search=Frieren"),
        ("anime-search-naruto", "?id=155&type=anime&nlist=5&search=Naruto"),
        ("anime-search-evangelion", "?id=155&type=anime&nlist=5&search=Evangelion"),
        ("anime-recent-titles", "?id=148&nlist=10"),
        ("anime-by-name-prefix", "?id=155&type=anime&name=A&nlist=5"),
        ("anime-by-name-prefix-b", "?id=155&type=anime&name=B&nlist=5"),
        ("anime-licensed-true", "?id=155&type=anime&licensed=true&nlist=5"),
        ("anime-licensed-false", "?id=155&type=anime&licensed=false&nlist=5"),
        ("invalid-report-id", "?id=99999999&type=anime&nlist=2"),
    ]
    for i, (label, qs) in enumerate(report_cases, 1):
        capture(backend="ann", path_slug="reports",
                label=label, method="GET",
                url=f"{BASE}/reports.xml{qs}",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/{len(report_cases)}] {label}")

    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
