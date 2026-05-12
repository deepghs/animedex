animedex.backends.kitsu.models
========================================================

.. currentmodule:: animedex.backends.kitsu.models

.. automodule:: animedex.backends.kitsu.models


KitsuAnimeAttributes
-----------------------------------------------------

.. autoclass:: KitsuAnimeAttributes
    :members: canonicalTitle,titles,abbreviatedTitles,synopsis,description,averageRating,userCount,favoritesCount,startDate,endDate,ageRating,ageRatingGuide,subtype,status,episodeCount,episodeLength,showType,youtubeVideoId,nsfw


KitsuMangaAttributes
-----------------------------------------------------

.. autoclass:: KitsuMangaAttributes
    :members: canonicalTitle,titles,abbreviatedTitles,synopsis,description,averageRating,userCount,favoritesCount,startDate,endDate,status,chapterCount,volumeCount,mangaType,serialization


KitsuMappingAttributes
-----------------------------------------------------

.. autoclass:: KitsuMappingAttributes
    :members: externalSite,externalId


KitsuStreamingLinkAttributes
-----------------------------------------------------

.. autoclass:: KitsuStreamingLinkAttributes
    :members: url,subs,dubs


KitsuCategoryAttributes
-----------------------------------------------------

.. autoclass:: KitsuCategoryAttributes
    :members: title,description,slug,nsfw,childCount


KitsuCharacterAttributes
-----------------------------------------------------

.. autoclass:: KitsuCharacterAttributes
    :members: slug,name,description,malId


KitsuPersonAttributes
-----------------------------------------------------

.. autoclass:: KitsuPersonAttributes
    :members: name,description,malId


KitsuProducerAttributes
-----------------------------------------------------

.. autoclass:: KitsuProducerAttributes
    :members: slug,name


KitsuGenreAttributes
-----------------------------------------------------

.. autoclass:: KitsuGenreAttributes
    :members: name,slug,description


KitsuStreamerAttributes
-----------------------------------------------------

.. autoclass:: KitsuStreamerAttributes
    :members: siteName,logo,streamingLinksCount


KitsuFranchiseAttributes
-----------------------------------------------------

.. autoclass:: KitsuFranchiseAttributes
    :members: slug,titles,canonicalTitle


KitsuUserAttributes
-----------------------------------------------------

.. autoclass:: KitsuUserAttributes
    :members: name,pastNames,slug,about,location,waifuOrHusbando,followersCount,followingCount,lifeSpentOnAnime,birthday,gender


KitsuAnime
-----------------------------------------------------

.. autoclass:: KitsuAnime
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuManga
-----------------------------------------------------

.. autoclass:: KitsuManga
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuMapping
-----------------------------------------------------

.. autoclass:: KitsuMapping
    :members: id,type,attributes,relationships,links,source_tag


KitsuStreamingLink
-----------------------------------------------------

.. autoclass:: KitsuStreamingLink
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuCategory
-----------------------------------------------------

.. autoclass:: KitsuCategory
    :members: id,type,attributes,relationships,links,source_tag


KitsuCharacter
-----------------------------------------------------

.. autoclass:: KitsuCharacter
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuPerson
-----------------------------------------------------

.. autoclass:: KitsuPerson
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuProducer
-----------------------------------------------------

.. autoclass:: KitsuProducer
    :members: to_common,id,type,attributes,relationships,links,source_tag


KitsuGenre
-----------------------------------------------------

.. autoclass:: KitsuGenre
    :members: id,type,attributes,relationships,links,source_tag


KitsuStreamer
-----------------------------------------------------

.. autoclass:: KitsuStreamer
    :members: id,type,attributes,relationships,links,source_tag


KitsuFranchise
-----------------------------------------------------

.. autoclass:: KitsuFranchise
    :members: id,type,attributes,relationships,links,source_tag


KitsuUser
-----------------------------------------------------

.. autoclass:: KitsuUser
    :members: id,type,attributes,relationships,links,source_tag


KitsuRelatedResource
-----------------------------------------------------

.. autoclass:: KitsuRelatedResource
    :members: id,type,attributes,relationships,links,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


