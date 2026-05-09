animedex.backends.shikimori.models
========================================================

.. currentmodule:: animedex.backends.shikimori.models

.. automodule:: animedex.backends.shikimori.models


ShikimoriImage
-----------------------------------------------------

.. autoclass:: ShikimoriImage
    :members: original,preview,x96,x48


ShikimoriEntity
-----------------------------------------------------

.. autoclass:: ShikimoriEntity
    :members: id,name,russian,image,url,kind,entry_type,source_tag


ShikimoriStudio
-----------------------------------------------------

.. autoclass:: ShikimoriStudio
    :members: to_common,id,name,filtered_name,real,image,source_tag


ShikimoriVideo
-----------------------------------------------------

.. autoclass:: ShikimoriVideo
    :members: id,url,image_url,player_url,name,kind,hosting,source_tag


ShikimoriScreenshot
-----------------------------------------------------

.. autoclass:: ShikimoriScreenshot
    :members: original,preview,source_tag


ShikimoriCharacter
-----------------------------------------------------

.. autoclass:: ShikimoriCharacter
    :members: to_common,id,name,russian,image,url,source_tag


ShikimoriPerson
-----------------------------------------------------

.. autoclass:: ShikimoriPerson
    :members: to_common,id,name,russian,image,url,source_tag


ShikimoriRole
-----------------------------------------------------

.. autoclass:: ShikimoriRole
    :members: roles,roles_russian,character,person,source_tag


ShikimoriAnime
-----------------------------------------------------

.. autoclass:: ShikimoriAnime
    :members: to_common,id,name,russian,image,url,kind,score,status,episodes,episodes_aired,aired_on,released_on,rating,english,japanese,synonyms,duration,description,description_html,franchise,favoured,anons,ongoing,myanimelist_id,rates_scores_stats,rates_statuses_stats,updated_at,next_episode_at,fansubbers,fandubbers,licensors,genres,studios,videos,screenshots,source_tag


ShikimoriCalendarEntry
-----------------------------------------------------

.. autoclass:: ShikimoriCalendarEntry
    :members: to_common,next_episode,next_episode_at,duration,anime,source_tag


ShikimoriTopic
-----------------------------------------------------

.. autoclass:: ShikimoriTopic
    :members: id,topic_title,body,html_body,type,linked_id,linked_type,source_tag


ShikimoriResource
-----------------------------------------------------

.. autoclass:: ShikimoriResource
    :members: id,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest
