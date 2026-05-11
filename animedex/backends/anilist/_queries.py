"""Canonical AniList GraphQL templates.

These constants are the queries that ship at runtime. The captured
AniList fixtures used by the test suite were recorded against these
exact strings, so changing one here demands a fixture re-capture to
keep replay tests honest.

Each template selects the **full set of fields** the corresponding
mapper consumes. AniList rate-limits (30/min anonymous) and over-
fetching is cheap — selecting a smaller field set per call is not a
project priority.

Templates exposed:

* :data:`Q_MEDIA_BY_ID` — single Media (anime/manga) by id.
* :data:`Q_MEDIA_SEARCH` — Page-wrapped Media search.
* :data:`Q_CHARACTER_BY_ID`, :data:`Q_CHARACTER_SEARCH`.
* :data:`Q_STAFF_BY_ID`, :data:`Q_STAFF_SEARCH`.
* :data:`Q_STUDIO_BY_ID`, :data:`Q_STUDIO_SEARCH`.
* :data:`Q_SCHEDULE` — Page-wrapped Media filtered by season/year.
* :data:`Q_TRENDING` — Page-wrapped Media sorted by TRENDING_DESC.
* :data:`Q_USER_BY_NAME`.
* :data:`Q_GENRE_COLLECTION`, :data:`Q_MEDIA_TAG_COLLECTION`,
  :data:`Q_SITE_STATISTICS`,
  :data:`Q_EXTERNAL_LINK_SOURCE_COLLECTION`.
* :data:`Q_AIRING_SCHEDULE`, :data:`Q_MEDIA_TREND`,
  :data:`Q_REVIEW`, :data:`Q_RECOMMENDATION`,
  :data:`Q_THREAD`, :data:`Q_THREAD_COMMENT`,
  :data:`Q_ACTIVITY`, :data:`Q_ACTIVITY_REPLY`,
  :data:`Q_FOLLOWING`, :data:`Q_FOLLOWER`,
  :data:`Q_MEDIA_LIST_PUBLIC`, :data:`Q_MEDIA_LIST_COLLECTION_PUBLIC`,
  :data:`Q_USER_SEARCH`.
"""

from __future__ import annotations


_MEDIA_FIELDS = """
id idMal
title { romaji english native }
synonyms
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
""".strip()


Q_MEDIA_BY_ID = f"""
query ($id: Int) {{
  Media(id: $id) {{
    {_MEDIA_FIELDS}
  }}
}}
""".strip()


Q_MEDIA_SEARCH = """
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


Q_CHARACTER_BY_ID = """
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


Q_CHARACTER_SEARCH = """
query ($q: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    characters(search: $q, sort: FAVOURITES_DESC) {
      id
      name { full native alternative }
      image { large medium }
      gender favourites
    }
  }
}
""".strip()


Q_STAFF_BY_ID = """
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


Q_STAFF_SEARCH = """
query ($q: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    staff(search: $q) {
      id
      name { full native alternative }
      image { large medium }
      primaryOccupations languageV2 favourites
    }
  }
}
""".strip()


Q_STUDIO_BY_ID = """
query ($id: Int) {
  Studio(id: $id) {
    id name isAnimationStudio favourites
    media(perPage: 5) { edges { isMainStudio node { id title { romaji } } } }
  }
}
""".strip()


Q_STUDIO_SEARCH = """
query ($q: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    studios(search: $q) {
      id name isAnimationStudio favourites
    }
  }
}
""".strip()


Q_SCHEDULE = """
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


Q_TRENDING = """
query ($perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(type: ANIME, sort: TRENDING_DESC) {
      id title { romaji english } status format averageScore popularity trending
      coverImage { large color }
    }
  }
}
""".strip()


Q_USER_BY_NAME = """
query ($name: String) {
  User(name: $name) {
    id name about
    avatar { large medium }
    siteUrl
    statistics {
      anime { count meanScore minutesWatched }
      manga { count meanScore chaptersRead }
    }
  }
}
""".strip()


Q_USER_SEARCH = """
query ($q: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    users(search: $q) { id name avatar { medium } }
  }
}
""".strip()


Q_GENRE_COLLECTION = "{ GenreCollection }"


Q_MEDIA_TAG_COLLECTION = """
{
  MediaTagCollection {
    id name description category isAdult isGeneralSpoiler isMediaSpoiler
  }
}
""".strip()


Q_SITE_STATISTICS = """
{
  SiteStatistics {
    users(perPage: 1) { nodes { date count change } }
    anime(perPage: 1) { nodes { date count change } }
    manga(perPage: 1) { nodes { date count change } }
    characters(perPage: 1) { nodes { date count change } }
    staff(perPage: 1) { nodes { date count change } }
    reviews(perPage: 1) { nodes { date count change } }
  }
}
""".strip()


Q_EXTERNAL_LINK_SOURCE_COLLECTION = """
query ($mediaType: ExternalLinkMediaType, $type: ExternalLinkType) {
  ExternalLinkSourceCollection(mediaType: $mediaType, type: $type) {
    id site type icon language
  }
}
""".strip()


Q_AIRING_SCHEDULE = """
query ($mediaId: Int, $notYetAired: Boolean, $airingAtGreater: Int, $airingAtLesser: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total hasNextPage }
    airingSchedules(
      mediaId: $mediaId,
      notYetAired: $notYetAired,
      airingAt_greater: $airingAtGreater,
      airingAt_lesser: $airingAtLesser,
      sort: TIME
    ) {
      id airingAt episode timeUntilAiring
      media { id title { romaji english } }
    }
  }
}
""".strip()


Q_MEDIA_TREND = """
query ($mediaId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total hasNextPage }
    mediaTrends(mediaId: $mediaId, sort: DATE_DESC) {
      mediaId date trending averageScore popularity inProgress episode
    }
  }
}
""".strip()


Q_REVIEW = """
query ($mediaId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    reviews(mediaId: $mediaId, sort: RATING_DESC) {
      id summary score rating ratingAmount
      user { id name }
      siteUrl
    }
  }
}
""".strip()


Q_RECOMMENDATION = """
query ($mediaId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    pageInfo { total }
    recommendations(mediaId: $mediaId, sort: RATING_DESC) {
      id rating
      media { id title { romaji english } }
      mediaRecommendation { id title { romaji english } }
    }
  }
}
""".strip()


Q_THREAD = """
query ($q: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    threads(search: $q, sort: CREATED_AT_DESC) {
      id title body
      user { id name }
      replyCount viewCount createdAt
    }
  }
}
""".strip()


Q_THREAD_COMMENT = """
query ($threadId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    threadComments(threadId: $threadId) {
      id comment
      user { id name }
      createdAt
    }
  }
}
""".strip()


Q_ACTIVITY = """
query ($perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    activities(sort: ID_DESC) {
      ... on TextActivity { id text user { name } createdAt }
      ... on ListActivity { id status user { name } media { id title { romaji } } createdAt }
    }
  }
}
""".strip()


Q_ACTIVITY_REPLY = """
query ($activityId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    activityReplies(activityId: $activityId) {
      id text user { name } createdAt
    }
  }
}
""".strip()


Q_FOLLOWING = """
query ($userId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    following(userId: $userId) { id name }
  }
}
""".strip()


Q_FOLLOWER = """
query ($userId: Int, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    followers(userId: $userId) { id name }
  }
}
""".strip()


Q_MEDIA_LIST_PUBLIC = """
query ($userName: String, $type: MediaType, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    mediaList(userName: $userName, type: $type) {
      id status score progress
      media { id title { romaji } }
    }
  }
}
""".strip()


Q_MEDIA_LIST_COLLECTION_PUBLIC = """
query ($userName: String, $type: MediaType) {
  MediaListCollection(userName: $userName, type: $type) {
    user { id name }
    lists {
      name status entries { id status score progress media { id title { romaji } } }
    }
  }
}
""".strip()


# Token-required Query roots — registered for completeness; the
# Python API stub raises ApiError(reason="auth-required") rather than
# issuing the request.
Q_VIEWER = "{ Viewer { id name } }"
Q_NOTIFICATION = "{ Notification { ... on AiringNotification { id type contexts media { id title { romaji } } } } }"
Q_MARKDOWN = "query ($markdown: String) { Markdown(markdown: $markdown) { html } }"
Q_ANI_CHART_USER = "{ AniChartUser { user { id name } highlights } }"
