"""Capture AniList full-field fixtures for the high-level backend layer mappers.

the substrate API layer fixtures used **simplified** GraphQL queries (selecting 5-10
fields per Media). the high-level backend layer's mapper layer needs the full surface for
:class:`~animedex.backends.anilist.models.AnilistAnime` / Character /
Staff / Studio. This module captures fresh fixtures with the
canonical the high-level backend layer queries from
:mod:`animedex.backends.anilist._queries`.

Output path slugs:

* ``test/fixtures/anilist/phase2_media``      — full Media x N
* ``test/fixtures/anilist/phase2_character``  — full Character x N
* ``test/fixtures/anilist/phase2_staff``      — full Staff x N
* ``test/fixtures/anilist/phase2_studio``     — full Studio x N
* ``test/fixtures/anilist/phase2_search``     — Page-wrapped Media search
* ``test/fixtures/anilist/phase2_schedule``   — Page-wrapped Media by season
* ``test/fixtures/anilist/phase2_trending``   — Page-wrapped Media TRENDING_DESC

Pacing: 2.5 s between calls (30/min cap = 2.0s minimum, +0.5s buffer).
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


URL = "https://graphql.anilist.co/"
PACE = 2.5

# Centralised so tools and tests can share the exact strings shipped
# at runtime. Kept in this script (not yet imported from
# animedex/backends/anilist/_queries.py) so this capture script can
# run before the backend module exists.
QUERY_MEDIA = """
query ($id: Int) {
  Media(id: $id) {
    id idMal
    title { romaji english native }
    type format status episodes duration
    season seasonYear
    startDate { year month day }
    endDate { year month day }
    genres tags { name rank }
    averageScore meanScore popularity favourites trending
    isAdult countryOfOrigin
    description(asHtml: false)
    source
    coverImage { extraLarge large medium color }
    bannerImage
    trailer { id site thumbnail }
    studios { edges { isMain node { id name isAnimationStudio } } }
    nextAiringEpisode { airingAt timeUntilAiring episode }
    externalLinks { id site type url language }
    streamingEpisodes { title thumbnail url site }
  }
}
""".strip()

QUERY_CHARACTER = """
query ($id: Int) {
  Character(id: $id) {
    id
    name { full native alternative }
    image { large medium }
    description(asHtml: false)
    gender age dateOfBirth { year month day }
    bloodType favourites
    media(perPage: 3) { edges { characterRole node { id title { romaji } } } }
  }
}
""".strip()

QUERY_STAFF = """
query ($id: Int) {
  Staff(id: $id) {
    id
    name { full native alternative }
    image { large medium }
    description(asHtml: false)
    primaryOccupations gender age dateOfBirth { year month day }
    yearsActive homeTown languageV2 favourites
    staffMedia(perPage: 3) { edges { staffRole node { id title { romaji } } } }
    characters(perPage: 3) { nodes { id name { full } } }
  }
}
""".strip()

QUERY_STUDIO = """
query ($id: Int) {
  Studio(id: $id) {
    id name isAnimationStudio favourites
    media(perPage: 5) { edges { isMainStudio node { id title { romaji } } } }
  }
}
""".strip()

QUERY_SEARCH = """
query ($q: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { total currentPage hasNextPage perPage }
    media(search: $q, type: ANIME, sort: SEARCH_MATCH) {
      id idMal
      title { romaji english native }
      type format status episodes
      season seasonYear averageScore popularity isAdult
      coverImage { large color }
    }
  }
}
""".strip()

QUERY_SCHEDULE = """
query ($year: Int, $season: MediaSeason, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    media(seasonYear: $year, season: $season, type: ANIME, sort: POPULARITY_DESC) {
      id title { romaji english } status format episodes season seasonYear
      averageScore nextAiringEpisode { airingAt episode timeUntilAiring }
    }
  }
}
""".strip()

QUERY_TRENDING = """
query ($perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(type: ANIME, sort: TRENDING_DESC) {
      id title { romaji english } status format averageScore popularity trending
      coverImage { large color }
    }
  }
}
""".strip()


# Media — span across status + format + popularity:
MEDIA_CASES = [
    ("media-frieren", 154587),       # TV finished, popular
    ("media-spirited-away", 199),    # movie
    ("media-one-piece", 21),         # long-running airing
    ("media-attack-on-titan", 16498),
    ("media-fma-brotherhood", 5114),
    ("media-made-in-abyss", 97940),
    ("media-cowboy-bebop", 1),
    ("media-naruto", 20),
    ("media-anohana", 9989),
    ("media-demon-slayer", 101922),
]

CHARACTER_CASES = [
    # Edward Elric is AniList character id 11. The earlier draft of
    # this list had id=36 under the same label, which is Phyllo —
    # the mislabel ended up baked into the the high-level backend layer test corpus.
    ("character-edward-elric", 11),
    ("character-phyllo", 36),
    ("character-3", 40),
    ("character-1", 1),
    ("character-178", 178),
]

STAFF_CASES = [
    ("staff-101572", 101572),
    ("staff-117057", 117057),
    ("staff-100186", 100186),
    ("staff-95269", 95269),
]

STUDIO_CASES = [
    ("studio-madhouse", 11),
    ("studio-sunrise", 36),
    ("studio-ufotable", 1),
    ("studio-ghibli", 17),
]


def main() -> int:
    print("Capturing AniList the high-level backend layer fixtures (full-field queries)")
    total = (
        len(MEDIA_CASES) + len(CHARACTER_CASES) + len(STAFF_CASES) + len(STUDIO_CASES) + 5
    )
    print(f"  total ~{total} requests, wall ~{total * PACE:.0f}s")

    i = 0
    for label, mid in MEDIA_CASES:
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_media",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_MEDIA, "variables": {"id": mid}},
            pace_seconds=PACE if i > 1 else 0,
        )
        print(f"  [{i:02d}] {label} -> {path.name}")

    for label, cid in CHARACTER_CASES:
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_character",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_CHARACTER, "variables": {"id": cid}},
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] {label} -> {path.name}")

    for label, sid in STAFF_CASES:
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_staff",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_STAFF, "variables": {"id": sid}},
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] {label} -> {path.name}")

    for label, stid in STUDIO_CASES:
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_studio",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_STUDIO, "variables": {"id": stid}},
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] {label} -> {path.name}")

    # search
    for label, q in (("search-frieren", "Frieren"), ("search-naruto", "Naruto")):
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_search",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_SEARCH, "variables": {"q": q, "page": 1, "perPage": 5}},
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] {label}")

    # schedule
    for label, args in (
        ("schedule-2024-spring", {"year": 2024, "season": "SPRING", "perPage": 8}),
        ("schedule-2023-fall", {"year": 2023, "season": "FALL", "perPage": 8}),
    ):
        i += 1
        path = capture(
            backend="anilist",
            path_slug="phase2_schedule",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body={"query": QUERY_SCHEDULE, "variables": args},
            pace_seconds=PACE,
        )
        print(f"  [{i:02d}] {label}")

    # trending
    i += 1
    path = capture(
        backend="anilist",
        path_slug="phase2_trending",
        label="trending-top8",
        method="POST",
        url=URL,
        headers={"Content-Type": "application/json"},
        json_body={"query": QUERY_TRENDING, "variables": {"perPage": 8}},
        pace_seconds=PACE,
    )
    print(f"  [{i:02d}] trending-top8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
