animedex.backends.danbooru.models
========================================================

.. currentmodule:: animedex.backends.danbooru.models

.. automodule:: animedex.backends.danbooru.models


DanbooruPost
-----------------------------------------------------

.. autoclass:: DanbooruPost
    :members: to_common,id,rating,score,md5,file_url,large_file_url,preview_file_url,tag_string,tag_string_artist,source,image_width,image_height,fav_count,source_tag


DanbooruArtist
-----------------------------------------------------

.. autoclass:: DanbooruArtist
    :members: id,name,group_name,other_names,is_deleted,is_banned,source_tag


DanbooruTag
-----------------------------------------------------

.. autoclass:: DanbooruTag
    :members: id,name,post_count,category,is_deprecated,words,source_tag


DanbooruPool
-----------------------------------------------------

.. autoclass:: DanbooruPool
    :members: id,name,description,post_ids,post_count,category,is_active,is_deleted,source_tag


DanbooruProfile
-----------------------------------------------------

.. autoclass:: DanbooruProfile
    :members: id,name,level,inviter_id,created_at,updated_at,last_logged_in_at,last_forum_read_at,post_upload_count,post_update_count,note_update_count,is_deleted,favorite_tags,blacklisted_tags,comment_threshold,default_image_size,source_tag


DanbooruSavedSearch
-----------------------------------------------------

.. autoclass:: DanbooruSavedSearch
    :members: id,user_id,query,labels,created_at,updated_at,source_tag


DanbooruRecord
-----------------------------------------------------

.. autoclass:: DanbooruRecord
    :members: id,source_tag


DanbooruRelatedTag
-----------------------------------------------------

.. autoclass:: DanbooruRelatedTag
    :members: query,category,related_tags,tag,source_tag


DanbooruIQDBQuery
-----------------------------------------------------

.. autoclass:: DanbooruIQDBQuery
    :members: post,post_id,score,source_tag


DanbooruCount
-----------------------------------------------------

.. autoclass:: DanbooruCount
    :members: total,counts,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


