"""
Capture AniList GraphQL fixtures.

15+ distinct queries against the single ``POST /`` GraphQL endpoint,
varying media id, search term, query shape, type filter, and error
cases. Paced at 2.1 sec between calls to stay well under the
30/min degraded rate limit.
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


URL = "https://graphql.anilist.co/"
PACE = 2.1  # seconds between requests; 30/min cap = 2.0s minimum, +0.1 buffer


CASES = [
    # (label, query, variables)
    ("media-frieren-by-id", '{ Media(id:154587){ id idMal title{romaji english native} genres status format season seasonYear episodes duration } }', None),
    ("media-cowboy-bebop", '{ Media(id:1){ id idMal title{romaji english} genres status format episodes } }', None),
    ("media-naruto", '{ Media(id:1735){ id title{romaji} episodes status } }', None),
    ("media-attack-on-titan", '{ Media(id:16498){ id title{romaji} episodes status studios{nodes{name}} } }', None),
    ("media-one-piece-airing", '{ Media(id:21){ id title{romaji} status nextAiringEpisode{episode airingAt timeUntilAiring} } }', None),
    ("media-made-in-abyss", '{ Media(id:97986){ id title{romaji english} isAdult genres tags{name rank} } }', None),
    ("media-spirited-away-movie", '{ Media(id:199){ id title{romaji} format duration } }', None),
    ("media-fma-brotherhood", '{ Media(id:5114){ id title{romaji} averageScore meanScore popularity favourites } }', None),
    ("media-not-found", '{ Media(id:99999999){ id } }', None),
    ("media-with-cover-and-banner", '{ Media(id:154587){ coverImage{extraLarge large medium color} bannerImage } }', None),
    ("search-frieren", '{ Page(perPage:5){ pageInfo{total currentPage hasNextPage} media(search:"Frieren",type:ANIME){ id title{romaji} } } }', None),
    ("search-naruto-page2", '{ Page(page:2,perPage:3){ pageInfo{currentPage hasNextPage} media(search:"Naruto",type:ANIME){ id title{romaji} } } }', None),
    ("search-manga-berserk", '{ Page(perPage:3){ media(search:"Berserk",type:MANGA){ id title{romaji} chapters volumes status } } }', None),
    ("character-frieren", '{ Character(id:169158){ id name{first last full native} description } }', None),
    ("staff-yamada-naoko", '{ Staff(id:103963){ id name{full} primaryOccupations } }', None),
    ("studio-madhouse", '{ Studio(id:11){ id name isAnimationStudio media{nodes{title{romaji}}} } }', None),
    ("genres-collection", '{ GenreCollection }', None),
    ("schema-introspection-small", '{ __schema{ queryType{ name } types{ name kind } } }', None),
    ("bad-query-error-envelope", '{ NotARealField }', None),
    ("query-with-variables", "query ($search: String) { Page(perPage:2){ media(search:$search,type:ANIME){ id title{romaji} } } }", {"search": "Demon Slayer"}),
    ("trending-anime", '{ Page(perPage:5){ media(sort:TRENDING_DESC,type:ANIME){ id title{romaji} popularity } } }', None),
    ("airing-schedule-window", '{ Page(perPage:5){ airingSchedules(notYetAired:true,sort:TIME){ id airingAt episode media{title{romaji}} } } }', None),
]


def main() -> int:
    print(f"AniList: {len(CASES)} fixtures, ~{len(CASES) * PACE:.0f}s wall time")
    for i, (label, query, variables) in enumerate(CASES, 1):
        body = {"query": query}
        if variables is not None:
            body["variables"] = variables
        path = capture(
            backend="anilist",
            path_slug="graphql",
            label=label,
            method="POST",
            url=URL,
            headers={"Content-Type": "application/json"},
            json_body=body,
            pace_seconds=PACE if i > 1 else 0,
        )
        print(f"  [{i:02d}/{len(CASES)}] {label} -> {path.relative_to(path.parents[3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
