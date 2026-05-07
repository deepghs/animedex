"""
Capture Shikimori fixtures (5 RPS / 90 RPM). Pace 0.6 sec.
"""

from __future__ import annotations

import json
import sys

from tools.fixtures.capture import capture


BASE = "https://shikimori.io"
PACE = 0.6


# 16 Shikimori anime ids covering different statuses / formats / years.
ANIME_IDS = [
    ("frieren-52991", 52991),
    ("cowboy-bebop-1", 1),
    ("naruto-20", 20),
    ("attack-on-titan-16498", 16498),
    ("steins-gate-9253", 9253),
    ("vinland-saga-37521", 37521),
    ("demon-slayer-38000", 38000),
    ("fma-brotherhood-5114", 5114),
    ("k-on-5680", 5680),
    ("hellsing-270", 270),
    ("nichijou-10165", 10165),
    ("madoka-9756", 9756),
    ("evangelion-30", 30),
    ("death-note-1535", 1535),
    ("one-piece-21", 21),
    ("invalid-99999999", 99999999),
]

SEARCH_TERMS = [
    ("frieren", "Frieren"),
    ("naruto", "Naruto"),
    ("attack-on-titan", "Attack+on+Titan"),
    ("evangelion", "Evangelion"),
    ("steins-gate", "Steins+Gate"),
    ("ghibli", "Ghibli"),
    ("cowboy-bebop", "Cowboy+Bebop"),
    ("demon-slayer", "Demon+Slayer"),
    ("fma", "Fullmetal+Alchemist"),
    ("k-on", "K-On"),
    ("hellsing", "Hellsing"),
    ("monster", "Monster"),
    ("madoka", "Madoka"),
    ("nichijou", "Nichijou"),
    ("aria", "Aria"),
    ("nonexistent-zzzz", "ZZZZNonexistent"),
]


def main() -> int:
    total = 0

    print("-- animes_by_id (16)")
    for i, (label, aid) in enumerate(ANIME_IDS, 1):
        capture(backend="shikimori", path_slug="animes_by_id",
                label=label, method="GET", url=f"{BASE}/api/animes/{aid}",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/16] {label}")

    print("-- animes_search (16)")
    for i, (label, term) in enumerate(SEARCH_TERMS, 1):
        capture(backend="shikimori", path_slug="animes_search",
                label=label, method="GET",
                url=f"{BASE}/api/animes?search={term}&limit=2",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/16] {label}")

    print("-- calendar (16 with limit/page variation)")
    calendar_cases = [
        ("limit-1", "?limit=1"),
        ("limit-2", "?limit=2"),
        ("limit-3", "?limit=3"),
        ("limit-5", "?limit=5"),
        ("limit-7", "?limit=7"),
        ("limit-10", "?limit=10"),
        ("limit-15", "?limit=15"),
        ("limit-20", "?limit=20"),
        ("limit-25", "?limit=25"),
        ("limit-30", "?limit=30"),
        ("limit-50", "?limit=50"),
        ("page-1", "?page=1&limit=3"),
        ("page-2", "?page=2&limit=3"),
        ("censored-true", "?censored=true&limit=3"),
        ("censored-false", "?censored=false&limit=3"),
        ("default", ""),
    ]
    for i, (label, qs) in enumerate(calendar_cases, 1):
        capture(backend="shikimori", path_slug="calendar",
                label=label, method="GET",
                url=f"{BASE}/api/calendar{qs}",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/{len(calendar_cases)}] {label}")

    print("-- screenshots (16)")
    for i, (label, aid) in enumerate(ANIME_IDS, 1):
        capture(backend="shikimori", path_slug="screenshots",
                label=label, method="GET",
                url=f"{BASE}/api/animes/{aid}/screenshots",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/16] {label}")

    print("-- videos (16)")
    for i, (label, aid) in enumerate(ANIME_IDS, 1):
        capture(backend="shikimori", path_slug="videos",
                label=label, method="GET",
                url=f"{BASE}/api/animes/{aid}/videos",
                pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/16] {label}")

    print("-- graphql (16)")
    graphql_cases = [
        ("animes-frieren", '{ animes(ids:"52991"){ id name score status episodes }}'),
        ("animes-naruto", '{ animes(ids:"20"){ id name score status episodes }}'),
        ("animes-aot", '{ animes(ids:"16498"){ id name score status }}'),
        ("animes-multi", '{ animes(ids:"1,20,30"){ id name }}'),
        ("animes-search", '{ animes(search:"Frieren",limit:3){ id name }}'),
        ("animes-by-genre", '{ animes(genre:"Comedy",limit:3){ id name }}'),
        ("animes-by-year", '{ animes(season:"2023_fall",limit:3){ id name season status }}'),
        ("animes-list-tv", '{ animes(kind:"tv",limit:3){ id name kind }}'),
        ("animes-list-movie", '{ animes(kind:"movie",limit:3){ id name kind }}'),
        ("animes-by-status-released", '{ animes(status:"released",limit:3){ id name status }}'),
        ("animes-by-status-ongoing", '{ animes(status:"ongoing",limit:3){ id name status }}'),
        ("animes-with-related", '{ animes(ids:"52991"){ id name related{ relation anime { id name }}}}'),
        ("animes-with-genres-field", '{ animes(ids:"52991"){ id name genres { id name kind }}}'),
        ("animes-with-studios", '{ animes(ids:"52991"){ id name studios { id name }}}'),
        ("schema-introspection", '{ __schema { queryType { name } } }'),
        ("bad-query", '{ NotARealField }'),
    ]
    for i, (label, query) in enumerate(graphql_cases, 1):
        capture(
            backend="shikimori",
            path_slug="graphql",
            label=label,
            method="POST",
            url=f"{BASE}/api/graphql",
            headers={"Content-Type": "application/json"},
            json_body={"query": query},
            pace_seconds=PACE,
        )
        total += 1
        print(f"  [{i:02d}/{len(graphql_cases)}] {label}")

    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
