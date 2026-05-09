animedex.backends.mangadex.models
========================================================

.. currentmodule:: animedex.backends.mangadex.models

.. automodule:: animedex.backends.mangadex.models


MangaDexMangaAttributes
-----------------------------------------------------

.. autoclass:: MangaDexMangaAttributes
    :members: title,altTitles,description,isLocked,links,originalLanguage,lastVolume,lastChapter,publicationDemographic,status,year,contentRating,tags,state,chapterNumbersResetOnNewVolume


MangaDexChapterAttributes
-----------------------------------------------------

.. autoclass:: MangaDexChapterAttributes
    :members: volume,chapter,title,translatedLanguage,externalUrl,isUnavailable,publishAt,readableAt,pages,uploader


MangaDexCoverAttributes
-----------------------------------------------------

.. autoclass:: MangaDexCoverAttributes
    :members: description,volume,fileName,locale


MangaDexManga
-----------------------------------------------------

.. autoclass:: MangaDexManga
    :members: to_common,id,type,attributes,relationships,source_tag


MangaDexChapter
-----------------------------------------------------

.. autoclass:: MangaDexChapter
    :members: to_common,id,type,attributes,relationships,source_tag


MangaDexCover
-----------------------------------------------------

.. autoclass:: MangaDexCover
    :members: id,type,attributes,relationships,source_tag


MangaDexUserAttributes
-----------------------------------------------------

.. autoclass:: MangaDexUserAttributes
    :members: username,roles,avatarFileName,bannerFileName,version


MangaDexUser
-----------------------------------------------------

.. autoclass:: MangaDexUser
    :members: id,type,attributes,relationships,source_tag


MangaDexResource
-----------------------------------------------------

.. autoclass:: MangaDexResource
    :members: id,type,attributes,relationships,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


