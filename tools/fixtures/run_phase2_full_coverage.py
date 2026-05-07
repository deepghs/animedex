"""Capture every remaining read-only endpoint for Phase 2 full coverage.

After ``run_anilist_phase2.py`` (core 7 query templates × 27 fixtures)
and ``run_jikan_phase2.py`` (Jikan core 16 fixtures across full /
seasons / top / random / schedules), this script captures the **long
tail**: every other anonymous Query root in AniList + the 70+
remaining Jikan endpoints + the four trace.moe endpoints.

Each endpoint gets at least 1 fixture (per Phase 2 plan in #5
follow-up). Higher-traffic endpoints get a few. Captures are paced
per upstream's rate-limit budget.
"""

from __future__ import annotations

import sys
import time
from typing import List, Tuple

import requests

from tools.fixtures.capture import capture


ANILIST_URL = "https://graphql.anilist.co/"
ANILIST_PACE = 2.5  # 30/min cap
JIKAN_BASE = "https://api.jikan.moe/v4"
JIKAN_PACE = 1.1  # 60/min cap


# ---------- AniList long-tail Query roots ----------
# (Phase 2 covers Media/Character/Staff/Studio/Page/search/schedule/trending
# already; this list is the remaining 15 anonymous Query types.)

ANILIST_LONGTAIL: List[Tuple[str, str, dict]] = [
    (
        "media-trend-frieren",
        "{ Page(page:1,perPage:5){ mediaTrends(mediaId:154587, sort:DATE_DESC){ date trending averageScore popularity inProgress episode } } }",
        {},
    ),
    (
        "airing-schedule-by-media",
        "{ Page(page:1,perPage:5){ airingSchedules(mediaId:21, sort:TIME){ id airingAt episode timeUntilAiring media{ title{romaji} } } } }",
        {},
    ),
    (
        "airing-schedule-not-yet-aired",
        "{ Page(page:1,perPage:5){ airingSchedules(notYetAired:true, sort:TIME){ id airingAt episode media{ id title{romaji} } } } }",
        {},
    ),
    (
        "review-by-media",
        "{ Page(page:1,perPage:5){ reviews(mediaId:154587, sort:RATING_DESC){ id summary score rating ratingAmount user{ name } } } }",
        {},
    ),
    (
        "recommendation-by-media",
        "{ Page(page:1,perPage:5){ recommendations(mediaId:154587, sort:RATING_DESC){ id rating media{ id title{romaji} } mediaRecommendation{ id title{romaji} } } } }",
        {},
    ),
    (
        "media-tag-collection",
        "{ MediaTagCollection { id name description category isAdult } }",
        {},
    ),
    (
        "user-by-name",
        "{ User(name:\"AniList\"){ id name about avatar{ large } siteUrl statistics{ anime{ count meanScore } manga{ count meanScore } } } }",
        {},
    ),
    (
        "activity-page",
        "{ Page(page:1,perPage:5){ activities(sort:ID_DESC){ ... on TextActivity{ id text user{ name } } ... on ListActivity{ id status user{ name } media{ title{romaji} } } } } }",
        {},
    ),
    (
        "activity-reply",
        "{ Page(page:1,perPage:5){ activityReplies(activityId:1){ id text user{ name } } } }",
        {},
    ),
    (
        "thread-by-search",
        "{ Page(page:1,perPage:5){ threads(search:\"Frieren\", sort:CREATED_AT_DESC){ id title body user{ name } } } }",
        {},
    ),
    (
        "thread-comment-by-thread",
        "{ Page(page:1,perPage:3){ threadComments(threadId:1){ id comment user{ name } } } }",
        {},
    ),
    (
        "following-by-user",
        "{ Page(page:1,perPage:5){ following(userId:1){ id name } } }",
        {},
    ),
    (
        "follower-by-user",
        "{ Page(page:1,perPage:5){ followers(userId:1){ id name } } }",
        {},
    ),
    (
        "site-statistics",
        "{ SiteStatistics{ users(perPage:1){ nodes{ date count change } } anime(perPage:1){ nodes{ date count change } } manga(perPage:1){ nodes{ date count change } } } }",
        {},
    ),
    (
        "external-link-source-collection",
        "{ ExternalLinkSourceCollection(mediaType:ANIME, type:STREAMING){ id site type } }",
        {},
    ),
    (
        "media-list-public",
        "{ Page(page:1,perPage:5){ mediaList(userName:\"AniList\", type:ANIME){ id score progress status media{ title{romaji} } } } }",
        {},
    ),
    (
        "media-list-collection-public",
        "{ MediaListCollection(userName:\"AniList\", type:ANIME){ user{ name } lists{ name entries{ id status score } } } }",
        {},
    ),
    (
        "user-search",
        "{ Page(page:1,perPage:3){ users(search:\"a\"){ id name } } }",
        {},
    ),
    (
        "genre-collection-singleton",
        "{ GenreCollection }",
        {},
    ),
    (
        "studio-search",
        "{ Page(page:1,perPage:3){ studios(search:\"Madhouse\"){ id name isAnimationStudio } } }",
        {},
    ),
    (
        "character-search",
        "{ Page(page:1,perPage:3){ characters(search:\"Frieren\", sort:FAVOURITES_DESC){ id name{ full } favourites } } }",
        {},
    ),
    (
        "staff-search",
        "{ Page(page:1,perPage:3){ staff(search:\"Yamada\"){ id name{ full } primaryOccupations } } }",
        {},
    ),
]


# ---------- Jikan long-tail endpoints ----------

JIKAN_LONGTAIL: List[Tuple[str, str, str]] = [
    # (path_slug, label, url_path)
    ("anime_staff", "frieren-52991", "/anime/52991/staff"),
    ("anime_news", "frieren-52991", "/anime/52991/news?page=1"),
    ("anime_forum", "frieren-52991", "/anime/52991/forum?filter=all"),
    ("anime_videos", "frieren-52991", "/anime/52991/videos"),
    ("anime_videos_episodes", "frieren-52991", "/anime/52991/videos/episodes"),
    ("anime_pictures", "frieren-52991", "/anime/52991/pictures"),
    ("anime_statistics", "frieren-52991", "/anime/52991/statistics"),
    ("anime_moreinfo", "frieren-52991", "/anime/52991/moreinfo"),
    ("anime_recommendations", "frieren-52991", "/anime/52991/recommendations"),
    ("anime_userupdates", "frieren-52991", "/anime/52991/userupdates"),
    ("anime_reviews", "frieren-52991", "/anime/52991/reviews?page=1"),
    ("anime_relations", "frieren-52991", "/anime/52991/relations"),
    ("anime_themes", "frieren-52991", "/anime/52991/themes"),
    ("anime_external", "frieren-52991", "/anime/52991/external"),
    ("anime_streaming", "frieren-52991", "/anime/52991/streaming"),

    # Manga
    ("manga_search", "berserk", "/manga?q=Berserk&limit=3"),
    ("manga_by_id", "berserk-2", "/manga/2"),
    ("manga_full", "berserk-2", "/manga/2/full"),
    ("manga_characters", "berserk-2", "/manga/2/characters"),
    ("manga_news", "berserk-2", "/manga/2/news?page=1"),
    ("manga_forum", "berserk-2", "/manga/2/forum"),
    ("manga_pictures", "berserk-2", "/manga/2/pictures"),
    ("manga_statistics", "berserk-2", "/manga/2/statistics"),
    ("manga_moreinfo", "berserk-2", "/manga/2/moreinfo"),
    ("manga_recommendations", "berserk-2", "/manga/2/recommendations"),
    ("manga_userupdates", "berserk-2", "/manga/2/userupdates"),
    ("manga_reviews", "berserk-2", "/manga/2/reviews?page=1"),
    ("manga_relations", "berserk-2", "/manga/2/relations"),
    ("manga_external", "berserk-2", "/manga/2/external"),

    # Characters
    ("characters_search", "frieren", "/characters?q=Frieren&limit=3"),
    ("characters_by_id", "edward-elric-11", "/characters/11"),
    ("characters_full", "edward-elric-11", "/characters/11/full"),
    ("characters_anime", "edward-elric-11", "/characters/11/anime"),
    ("characters_manga", "edward-elric-11", "/characters/11/manga"),
    ("characters_voices", "edward-elric-11", "/characters/11/voices"),
    ("characters_pictures", "edward-elric-11", "/characters/11/pictures"),

    # People
    ("people_search", "miyazaki", "/people?q=Miyazaki&limit=3"),
    ("people_by_id", "miyazaki-1870", "/people/1870"),
    ("people_full", "miyazaki-1870", "/people/1870/full"),
    ("people_anime", "miyazaki-1870", "/people/1870/anime"),
    ("people_voices", "miyazaki-1870", "/people/1870/voices"),
    ("people_manga", "miyazaki-1870", "/people/1870/manga"),
    ("people_pictures", "miyazaki-1870", "/people/1870/pictures"),

    # Producers
    ("producers_search", "aniplex", "/producers?q=Aniplex&limit=3"),
    ("producers_by_id", "aniplex-17", "/producers/17"),
    ("producers_full", "aniplex-17", "/producers/17/full"),
    ("producers_external", "aniplex-17", "/producers/17/external"),

    # Magazines
    ("magazines_list", "search-shonen", "/magazines?q=Shonen&limit=3"),

    # Genres
    ("genres_anime", "all", "/genres/anime"),
    ("genres_manga", "all", "/genres/manga"),

    # Clubs
    ("clubs_search", "fma", "/clubs?q=fma&limit=3"),
    ("clubs_by_id", "club-1", "/clubs/1"),
    ("clubs_members", "club-1", "/clubs/1/members?page=1"),
    ("clubs_staff", "club-1", "/clubs/1/staff"),
    ("clubs_relations", "club-1", "/clubs/1/relations"),

    # Users
    ("users_by_name", "nekomata1037", "/users/nekomata1037"),
    ("users_full", "nekomata1037", "/users/nekomata1037/full"),
    ("users_statistics", "nekomata1037", "/users/nekomata1037/statistics"),
    ("users_favorites", "nekomata1037", "/users/nekomata1037/favorites"),
    ("users_userupdates", "nekomata1037", "/users/nekomata1037/userupdates"),
    ("users_about", "nekomata1037", "/users/nekomata1037/about"),
    ("users_history", "nekomata1037", "/users/nekomata1037/history"),
    ("users_friends", "nekomata1037", "/users/nekomata1037/friends?page=1"),
    ("users_reviews", "nekomata1037", "/users/nekomata1037/reviews?page=1"),
    ("users_recommendations", "nekomata1037", "/users/nekomata1037/recommendations?page=1"),
    ("users_clubs", "nekomata1037", "/users/nekomata1037/clubs"),
    ("users_search", "nekomata", "/users?q=nekomata&limit=3"),
    ("users_userbyid", "by-mal-id-39", "/users/userbyid/39"),

    # Seasons
    ("seasons_list", "all", "/seasons"),
    ("seasons_by_year", "2023-fall", "/seasons/2023/fall?limit=5"),
    ("seasons_upcoming", "list", "/seasons/upcoming?limit=5"),

    # Top
    ("top_manga", "list", "/top/manga?limit=5"),
    ("top_characters", "list", "/top/characters?limit=5"),
    ("top_people", "list", "/top/people?limit=5"),
    ("top_reviews", "anime", "/top/reviews?type=anime"),

    # Random remaining
    ("random_manga", "single", "/random/manga"),
    ("random_characters", "single", "/random/characters"),
    ("random_people", "single", "/random/people"),
    ("random_users", "single", "/random/users"),

    # Recommendations
    ("recommendations_anime", "list", "/recommendations/anime?page=1"),
    ("recommendations_manga", "list", "/recommendations/manga?page=1"),

    # Reviews
    ("reviews_anime", "list", "/reviews/anime?page=1"),
    ("reviews_manga", "list", "/reviews/manga?page=1"),

    # Watch
    ("watch_episodes", "today", "/watch/episodes"),
    ("watch_episodes_popular", "popular", "/watch/episodes/popular"),
    ("watch_promos", "today", "/watch/promos"),
    ("watch_promos_popular", "popular", "/watch/promos/popular"),
]


# ---------- Trace.moe ----------

def capture_trace_endpoints(i: int) -> int:
    # Probe me + search by URL. Skip POST upload to preserve quota.
    i += 1
    capture(
        backend="trace",
        path_slug="me",
        label="phase2-coverage",
        method="GET",
        url="https://api.trace.moe/me",
        pace_seconds=1.0,
    )
    print(f"  [{i:03d}] trace /me")

    # search by URL — use a stable image URL
    i += 1
    capture(
        backend="trace",
        path_slug="search_by_url",
        label="frieren-key-image",
        method="GET",
        url="https://api.trace.moe/search?anilistInfo&url=https%3A%2F%2Fs4.anilist.co%2Ffile%2Fanilistcdn%2Fmedia%2Fanime%2Fcover%2Fextralarge%2Fbx154587-zVbalZSKBnDz.jpg",
        pace_seconds=2.0,
    )
    print(f"  [{i:03d}] trace /search by URL")
    return i


# ---------- Run ----------

def main() -> int:
    i = 0
    print(f"AniList long-tail: {len(ANILIST_LONGTAIL)} fixtures, ~{len(ANILIST_LONGTAIL) * ANILIST_PACE:.0f}s")
    for label, query, variables in ANILIST_LONGTAIL:
        i += 1
        body = {"query": query}
        if variables:
            body["variables"] = variables
        # Group by query type for cleaner directories - we'll lump
        # everything into anilist/phase2_longtail/.
        capture(
            backend="anilist",
            path_slug="phase2_longtail",
            label=label,
            method="POST",
            url=ANILIST_URL,
            headers={"Content-Type": "application/json"},
            json_body=body,
            pace_seconds=ANILIST_PACE if i > 1 else 0,
        )
        print(f"  [{i:03d}] anilist longtail: {label}")

    print(f"\nJikan long-tail: {len(JIKAN_LONGTAIL)} fixtures, ~{len(JIKAN_LONGTAIL) * JIKAN_PACE:.0f}s")
    for path_slug, label, url_path in JIKAN_LONGTAIL:
        i += 1
        capture(
            backend="jikan",
            path_slug=path_slug,
            label=label,
            method="GET",
            url=JIKAN_BASE + url_path,
            pace_seconds=JIKAN_PACE,
        )
        print(f"  [{i:03d}] jikan {path_slug}: {label}")

    i = capture_trace_endpoints(i)

    print(f"\nTotal: {i} fixtures captured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
