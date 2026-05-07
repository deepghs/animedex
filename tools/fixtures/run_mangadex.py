"""
Capture MangaDex fixtures. Global cap ~5 req/sec; pace 0.25 sec.
At-Home endpoint has its own 40/min cap; use 1.6 sec pace there.
"""

from __future__ import annotations

import sys
import time

import requests

from tools.fixtures.capture import capture


BASE = "https://api.mangadex.org"
PACE = 0.4
PACE_AT_HOME = 1.6


# Curated by-id list: real MangaDex UUIDs we'll reuse.
MANGA_IDS = [
    ("frieren", "67be7e1c-b2c2-4a73-8d83-3ddca4b1c6fc"),
    ("berserk", "801513ba-a712-498c-8f57-cae55b38cc92"),
    ("one-piece", "32d76d19-8a05-4db0-9fc2-e0b0648fe9d0"),
    ("naruto", "c52b2ce3-7f95-469c-96b0-479524fb7a1a"),
    ("attack-on-titan", "045e6ddf-8a9a-461d-9d56-50f86fcc02c0"),
    ("vagabond", "d1a9fdeb-f713-407f-960c-8326b586e6fd"),
    ("vinland-saga", "61dde0fa-ec1c-4c89-9eb4-0bd24eda28ea"),
    ("oyasumi-punpun", "ca0fcb34-9bc2-49f9-a64e-26e4d65a82e1"),
    ("monster", "a25e46ec-30f7-4db6-89df-cacbc1d9a900"),
    ("20th-century-boys", "b21b1665-50aa-4b32-bb22-e5a1cc4ee09a"),
    ("ousama-ranking", "725a08ce-7da9-4d36-9d12-c8a9da9bd5c9"),
    ("chainsaw-man", "a77742b1-befd-49a4-bff5-1ad4e6b0ef7b"),
    ("look-back", "11d0e2a1-12ed-4b5a-99e7-b3e3bd7cdf48"),
    ("blame", "32fdfe9b-6e11-4a13-9e36-dcd8ea77b4e4"),
    ("dorohedoro", "0f558d10-5466-44e7-b9bd-4055ddff3b7c"),
]


def capture_paths():
    total = 0
    # Family 1: search by title
    print("-- manga_search")
    queries = [
        "Berserk", "Frieren", "Vagabond", "Vinland Saga", "Monster",
        "Oyasumi Punpun", "20th Century Boys", "Naruto", "One Piece", "Attack on Titan",
        "Chainsaw Man", "Spy x Family", "Jujutsu Kaisen", "My Hero Academia", "Blame",
        "Dorohedoro",
    ]
    for i, q in enumerate(queries, 1):
        url = f"{BASE}/manga?title={requests.utils.quote(q)}&limit=2&includes%5B%5D=cover_art"
        capture(backend="mangadex", path_slug="manga_search",
                label=q.lower().replace(" ", "-"),
                method="GET", url=url, pace_seconds=PACE)
        print(f"  [{i:02d}/{len(queries)}] {q}")
        total += 1

    # Family 2: by id
    print("-- manga_by_id")
    cases = list(MANGA_IDS) + [("invalid-uuid", "00000000-0000-0000-0000-000000000000")]
    for i, (label, uuid) in enumerate(cases, 1):
        url = f"{BASE}/manga/{uuid}"
        capture(backend="mangadex", path_slug="manga_by_id",
                label=label, method="GET", url=url, pace_seconds=PACE)
        print(f"  [{i:02d}/{len(cases)}] {label}")
        total += 1

    # Family 3: feed
    print("-- manga_feed")
    feed_cases = [(label, uuid) for label, uuid in MANGA_IDS]
    feed_cases.append(("invalid-feed", "00000000-0000-0000-0000-000000000000"))
    for i, (label, uuid) in enumerate(feed_cases, 1):
        url = f"{BASE}/manga/{uuid}/feed?translatedLanguage%5B%5D=en&limit=2&order%5Bchapter%5D=desc"
        capture(backend="mangadex", path_slug="manga_feed",
                label=label, method="GET", url=url, pace_seconds=PACE)
        print(f"  [{i:02d}/{len(feed_cases)}] {label}")
        total += 1

    # Family 4: tag taxonomy + statistics + cover
    print("-- manga_meta")
    meta_cases = [
        ("tag-taxonomy", f"{BASE}/manga/tag"),
        ("manga-status-aggregate-frieren", f"{BASE}/manga/{MANGA_IDS[0][1]}/aggregate"),
        ("manga-status-aggregate-berserk", f"{BASE}/manga/{MANGA_IDS[1][1]}/aggregate"),
        ("manga-status-aggregate-onepiece", f"{BASE}/manga/{MANGA_IDS[2][1]}/aggregate"),
        ("manga-statistics-frieren", f"{BASE}/statistics/manga/{MANGA_IDS[0][1]}"),
        ("manga-statistics-berserk", f"{BASE}/statistics/manga/{MANGA_IDS[1][1]}"),
        ("manga-cover-frieren", f"{BASE}/cover?manga%5B%5D={MANGA_IDS[0][1]}&limit=3"),
        ("manga-cover-berserk", f"{BASE}/cover?manga%5B%5D={MANGA_IDS[1][1]}&limit=3"),
        ("manga-cover-multi", f"{BASE}/cover?manga%5B%5D={MANGA_IDS[0][1]}&manga%5B%5D={MANGA_IDS[1][1]}&limit=5"),
        ("author-search", f"{BASE}/author?name=Yamada&limit=3"),
        ("scanlation-group-search", f"{BASE}/group?name=MangaDex&limit=3"),
        ("manga-random", f"{BASE}/manga/random"),
        ("manga-status-codes", f"{BASE}/manga?status%5B%5D=ongoing&limit=2"),
        ("manga-by-content-rating", f"{BASE}/manga?contentRating%5B%5D=safe&limit=2"),
        ("manga-by-publication-demographic", f"{BASE}/manga?publicationDemographic%5B%5D=seinen&limit=2"),
        ("manga-with-multiple-includes", f"{BASE}/manga?title=Frieren&includes%5B%5D=cover_art&includes%5B%5D=author&limit=1"),
    ]
    for i, (label, url) in enumerate(meta_cases, 1):
        capture(backend="mangadex", path_slug="manga_meta",
                label=label, method="GET", url=url, pace_seconds=PACE)
        print(f"  [{i:02d}/{len(meta_cases)}] {label}")
        total += 1

    # Family 5: at-home/server (40/min cap; pace 1.6s)
    print("-- at_home_server (paced 1.6s)")
    # Need real chapter ids. Capture a feed first to get them, or use a static set.
    # To keep this offline-deterministic when re-run, hardcode a list of known good
    # chapter UUIDs (collected previously) plus some 404 cases.
    chapter_ids = [
        ("frieren-ch128", "fbd80a96-1e2b-4ace-a5b4-a76b75e05d8a"),  # may 404 if removed
        ("berserk-ch383", "8ceadc31-e41e-4038-8aef-d002aab344a5"),
        ("invalid-zero", "00000000-0000-0000-0000-000000000000"),
        ("invalid-shape-1", "00000000-0000-0000-0000-000000000001"),
        ("invalid-shape-2", "00000000-0000-0000-0000-000000000002"),
    ]
    # Get more by fetching the feed for each canonical manga and pulling chapters.
    # For each manga, request the feed and extract up to 1 chapter id per manga.
    additional = []
    for label, manga_uuid in MANGA_IDS[:11]:
        time.sleep(PACE)
        try:
            r = requests.get(
                f"{BASE}/manga/{manga_uuid}/feed",
                params={"translatedLanguage[]": "en", "limit": "1", "order[chapter]": "desc"},
                headers={"User-Agent": "animedex/0.0.1"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("data"):
                    chapter_uuid = data["data"][0]["id"]
                    additional.append((f"{label}-latest", chapter_uuid))
        except Exception:
            pass
    chapter_ids = additional + chapter_ids
    for i, (label, ch_uuid) in enumerate(chapter_ids, 1):
        url = f"{BASE}/at-home/server/{ch_uuid}"
        capture(backend="mangadex", path_slug="at_home_server",
                label=label, method="GET", url=url, pace_seconds=PACE_AT_HOME)
        print(f"  [{i:02d}/{len(chapter_ids)}] {label}")
        total += 1

    return total


def main() -> int:
    print(f"MangaDex: capturing fixtures (paced for 5/sec global + 40/min for at-home)")
    n = capture_paths()
    print(f"Done: {n} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
