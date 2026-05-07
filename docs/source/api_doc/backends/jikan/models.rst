animedex.backends.jikan.models
========================================================

.. currentmodule:: animedex.backends.jikan.models

.. automodule:: animedex.backends.jikan.models


JikanImageJpg
-----------------------------------------------------

.. autoclass:: JikanImageJpg
    :members: image_url,small_image_url,large_image_url


JikanImages
-----------------------------------------------------

.. autoclass:: JikanImages
    :members: jpg,webp


JikanTrailerImages
-----------------------------------------------------

.. autoclass:: JikanTrailerImages
    :members: image_url,small_image_url,medium_image_url,large_image_url,maximum_image_url


JikanTrailer
-----------------------------------------------------

.. autoclass:: JikanTrailer
    :members: youtube_id,url,embed_url,images


JikanTitleEntry
-----------------------------------------------------

.. autoclass:: JikanTitleEntry
    :members: type,title


JikanAiredProp
-----------------------------------------------------

.. autoclass:: JikanAiredProp
    :members: day,month,year


JikanAiredFromTo
-----------------------------------------------------

.. autoclass:: JikanAiredFromTo
    :members: from_,to,model_config


JikanAired
-----------------------------------------------------

.. autoclass:: JikanAired
    :members: from_,to,prop,string,model_config


JikanBroadcast
-----------------------------------------------------

.. autoclass:: JikanBroadcast
    :members: day,time,timezone,string


JikanEntity
-----------------------------------------------------

.. autoclass:: JikanEntity
    :members: mal_id,type,name,url


JikanThemes
-----------------------------------------------------

.. autoclass:: JikanThemes
    :members: openings,endings


JikanExternal
-----------------------------------------------------

.. autoclass:: JikanExternal
    :members: name,url


JikanRelation
-----------------------------------------------------

.. autoclass:: JikanRelation
    :members: relation,entry


JikanAnime
-----------------------------------------------------

.. autoclass:: JikanAnime
    :members: to_common,mal_id,url,images,trailer,approved,titles,title,title_english,title_japanese,title_synonyms,type,source,episodes,status,airing,aired,duration,rating,score,scored_by,rank,popularity,members,favorites,synopsis,background,season,year,broadcast,producers,licensors,studios,genres,explicit_genres,themes,demographics,relations,theme,external,streaming,source_tag


JikanManga
-----------------------------------------------------

.. autoclass:: JikanManga
    :members: mal_id,url,images,approved,titles,title,title_english,title_japanese,title_synonyms,type,chapters,volumes,status,publishing,published,score,scored_by,rank,popularity,members,favorites,synopsis,background,authors,serializations,genres,explicit_genres,themes,demographics,relations,external,source_tag


JikanCharacterAnimeRole
-----------------------------------------------------

.. autoclass:: JikanCharacterAnimeRole
    :members: role,anime


JikanCharacterMangaRole
-----------------------------------------------------

.. autoclass:: JikanCharacterMangaRole
    :members: role,manga


JikanCharacterVoiceActor
-----------------------------------------------------

.. autoclass:: JikanCharacterVoiceActor
    :members: language,person


JikanCharacter
-----------------------------------------------------

.. autoclass:: JikanCharacter
    :members: to_common,mal_id,url,images,name,name_kanji,nicknames,favorites,about,anime,manga,voices,source_tag


JikanPerson
-----------------------------------------------------

.. autoclass:: JikanPerson
    :members: mal_id,url,website_url,images,name,given_name,family_name,alternate_names,birthday,favorites,about,source_tag


JikanProducer
-----------------------------------------------------

.. autoclass:: JikanProducer
    :members: mal_id,url,titles,images,favorites,established,about,count,external,source_tag


JikanMagazine
-----------------------------------------------------

.. autoclass:: JikanMagazine
    :members: mal_id,name,url,count,source_tag


JikanGenre
-----------------------------------------------------

.. autoclass:: JikanGenre
    :members: mal_id,name,url,count,source_tag


JikanClub
-----------------------------------------------------

.. autoclass:: JikanClub
    :members: mal_id,name,url,images,members,category,created,access,source_tag


JikanUser
-----------------------------------------------------

.. autoclass:: JikanUser
    :members: mal_id,username,url,images,last_online,gender,birthday,location,joined,about,source_tag


JikanGenericRow
-----------------------------------------------------

.. autoclass:: JikanGenericRow
    :members: model_config


JikanGenericResponse
-----------------------------------------------------

.. autoclass:: JikanGenericResponse
    :members: rows,pagination,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


