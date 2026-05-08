animedex.backends.anilist.models
========================================================

.. currentmodule:: animedex.backends.anilist.models

.. automodule:: animedex.backends.anilist.models


AnilistAnime
-----------------------------------------------------

.. autoclass:: AnilistAnime
    :members: to_common,id,idMal,title,synonyms,type,format,status,episodes,duration,season,seasonYear,startDate,endDate,genres,tags,averageScore,meanScore,popularity,favourites,trending,isAdult,countryOfOrigin,description,source,coverImage,bannerImage,trailer,studios,nextAiringEpisode,externalLinks,streamingEpisodes,source_tag


AnilistCharacter
-----------------------------------------------------

.. autoclass:: AnilistCharacter
    :members: to_common,id,name,image,description,gender,age,dateOfBirth,bloodType,favourites,media,source_tag


AnilistStaff
-----------------------------------------------------

.. autoclass:: AnilistStaff
    :members: to_common,id,name,image,description,primaryOccupations,gender,age,dateOfBirth,yearsActive,homeTown,languageV2,favourites,source_tag


AnilistStudio
-----------------------------------------------------

.. autoclass:: AnilistStudio
    :members: to_common,id,name,isAnimationStudio,favourites,source_tag


AnilistMediaTrend
-----------------------------------------------------

.. autoclass:: AnilistMediaTrend
    :members: mediaId,date,trending,averageScore,popularity,inProgress,episode,source_tag


AnilistAiringSchedule
-----------------------------------------------------

.. autoclass:: AnilistAiringSchedule
    :members: id,airingAt,episode,timeUntilAiring,media_id,media_title_romaji,source_tag


AnilistReview
-----------------------------------------------------

.. autoclass:: AnilistReview
    :members: id,summary,score,rating,ratingAmount,user_name,siteUrl,source_tag


AnilistRecommendation
-----------------------------------------------------

.. autoclass:: AnilistRecommendation
    :members: id,rating,media_id,media_title,recommendation_id,recommendation_title,source_tag


AnilistThread
-----------------------------------------------------

.. autoclass:: AnilistThread
    :members: id,title,body,user_name,replyCount,viewCount,createdAt,source_tag


AnilistThreadComment
-----------------------------------------------------

.. autoclass:: AnilistThreadComment
    :members: id,comment,user_name,createdAt,source_tag


AnilistActivity
-----------------------------------------------------

.. autoclass:: AnilistActivity
    :members: id,kind,text,status,user_name,media_title,createdAt,source_tag


AnilistActivityReply
-----------------------------------------------------

.. autoclass:: AnilistActivityReply
    :members: id,text,user_name,createdAt,source_tag


AnilistFollowEntry
-----------------------------------------------------

.. autoclass:: AnilistFollowEntry
    :members: id,name,source_tag


AnilistMediaListEntry
-----------------------------------------------------

.. autoclass:: AnilistMediaListEntry
    :members: id,status,score,progress,media_id,media_title,source_tag


AnilistMediaListGroup
-----------------------------------------------------

.. autoclass:: AnilistMediaListGroup
    :members: name,status,entry_count


AnilistMediaListCollection
-----------------------------------------------------

.. autoclass:: AnilistMediaListCollection
    :members: user_id,user_name,lists,source_tag


AnilistGenreCollection
-----------------------------------------------------

.. autoclass:: AnilistGenreCollection
    :members: genres,source_tag


AnilistMediaTag
-----------------------------------------------------

.. autoclass:: AnilistMediaTag
    :members: id,name,description,category,isAdult,isGeneralSpoiler,isMediaSpoiler,source_tag


AnilistSiteStatBucket
-----------------------------------------------------

.. autoclass:: AnilistSiteStatBucket
    :members: date,count,change


AnilistSiteStatistics
-----------------------------------------------------

.. autoclass:: AnilistSiteStatistics
    :members: users,anime,manga,characters,staff,reviews,source_tag


AnilistExternalLinkSource
-----------------------------------------------------

.. autoclass:: AnilistExternalLinkSource
    :members: id,site,type,icon,language,source_tag


AnilistUserStatistics
-----------------------------------------------------

.. autoclass:: AnilistUserStatistics
    :members: anime_count,anime_mean_score,anime_minutes_watched,manga_count,manga_mean_score,manga_chapters_read


AnilistUser
-----------------------------------------------------

.. autoclass:: AnilistUser
    :members: id,name,about,avatar_large,siteUrl,statistics,source_tag


AnilistNotification
-----------------------------------------------------

.. autoclass:: AnilistNotification
    :members: id,kind,type,contexts,context,user_name,createdAt,source_tag


AnilistMarkdown
-----------------------------------------------------

.. autoclass:: AnilistMarkdown
    :members: html,source_tag


AnilistAniChartUser
-----------------------------------------------------

.. autoclass:: AnilistAniChartUser
    :members: user_id,user_name,settings,highlights,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


