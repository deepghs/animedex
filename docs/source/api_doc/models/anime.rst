animedex.models.anime
========================================================

.. currentmodule:: animedex.models.anime

.. automodule:: animedex.models.anime


AnimeStatus
-----------------------------------------------------

.. autodata:: AnimeStatus


AnimeFormat
-----------------------------------------------------

.. autodata:: AnimeFormat


AnimeSeason
-----------------------------------------------------

.. autodata:: AnimeSeason


AnimeTitle
-----------------------------------------------------

.. autoclass:: AnimeTitle
    :members: romaji,english,native


AnimeRating
-----------------------------------------------------

.. autoclass:: AnimeRating
    :members: score,scale,votes


AnimeStreamingLink
-----------------------------------------------------

.. autoclass:: AnimeStreamingLink
    :members: provider,url


Anime
-----------------------------------------------------

.. autoclass:: Anime
    :members: id,title,score,episodes,studios,streaming,description,genres,tags,status,format,season,season_year,aired_from,aired_to,duration_minutes,cover_image_url,banner_image_url,trailer_url,source_material,country_of_origin,is_adult,age_rating,popularity,ids,source


selftest
-----------------------------------------------------

.. autofunction:: selftest


