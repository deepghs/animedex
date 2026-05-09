``animedex danbooru``
=====================

Danbooru is a community-driven anime art catalogue hosted at
``https://danbooru.donmai.us``. It is the **deepest tag-DSL surface**
animedex wraps: every post / artist / tag / pool / wiki page /
forum thread / commentary / vote / version / moderation event.
animedex covers **57 anonymous endpoints** plus **2 authenticated
read endpoints** as 59 high-level Python functions.

.. image:: /_static/gifs/danbooru.gif
   :alt: animedex danbooru demo — search, post, artist, tag
   :align: center

References
----------

================================ =====================================
Site                             https://danbooru.donmai.us/
API help                         https://danbooru.donmai.us/wiki_pages/help:api
Tag DSL guide                    https://danbooru.donmai.us/wiki_pages/howto%3Asearch
Python module                    :mod:`animedex.backends.danbooru`
Rich models                      :mod:`animedex.backends.danbooru.models`
================================ =====================================

* **Backend**: Danbooru (danbooru.donmai.us).
* **Rate limit**: 10 req/sec anonymous; transport bucket matches.
* **Auth**: optional. Most endpoints work without credentials; the
  user-private surface (``/profil e``, ``/saved_searches``) needs an   
  HTTP Basic ``username:api_key``  pair from the user's account        
  Settings → API Keys page.                                           

NSFW posture
------------

Danbooru's tag DSL exposes content ratings via ``rating:g`` (general),
``rating:s`` (sensitive), ``rating:q`` (questionable), and ``rating:e``
(explicit). The project's posture per the Human Agency Principle:

* **animedex never injects rating filters** on the user's behalf. A
  query like ``touhou marisa`` go es through unchanged; the upstream   
  decides what to return.                                             
* **LLM agents using this CLI as a tool** should prepend ``rating:g``
  to the tag query when the user has not explicitly asked for adult   
  / ecchi / NSFW content. When th e user explicitly asks for it,       
  pass the query through unmodifi ed.                                  
* Every result row carries a ``.rating`` field so a downstream
  pipeline can re-filter.                                             

This advice ships in the Click command's docstring + the
``--agent-guide`` extraction; see the
the project README's "Human Agency Principle" section page for the broader policy.

Eight endpoints, in detail
--------------------------

Tag-DSL search — :func:`~animedex.backends.danbooru.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru search 'touh ou marisa rating:g order:score' --limit 3 \
     --jq '.[] | {id, score, rati ng, file_url}'                       

One post — :func:`~animedex.backends.danbooru.post`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru post 1 --jq '{id, rating, score, source}'        

Artist lookup — :func:`~animedex.backends.danbooru.artist`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru artist-searc h "Hayao Miyazaki" --limit 3 --jq '.[].name'

Tag wildcard — :func:`~animedex.backends.danbooru.tag`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru tag "touhou* " --limit 5 --jq '.[] | {name, post_count}'

Tag autocomplete — :func:`~animedex.backends.danbooru.autocomplete`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru autocomplete  touh --type tag_query --jq '.[].label'

Related tags — :func:`~animedex.backends.danbooru.related_tag`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru related-tag touhou --limit 5 --jq '.related_tags[][:2]'

Post count — :func:`~animedex.backends.danbooru.count`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru count 'touho u rating:g' --jq '.counts.posts'     

Reverse image lookup — :func:`~animedex.backends.danbooru.iqdb_query`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex danbooru iqdb-query - -post-id 1 --jq '.[] | {post_id, score}'

Authenticated endpoints
-----------------------

Two reads need the caller's own HTTP Basic credentials. Get an API
key from https://danbooru.donmai.us/profile → "API Key" section
(create a new key with read-only scope). Provide via:

.. code-block:: bash

   # Per-call (CLI):                                                  
   animedex danbooru profile --cr eds "username:api_key"               

   # Per-shell (env var):                                             
   export ANIMEDEX_DANBOORU_CREDS ="username:api_key"                  
   animedex danbooru profile                                          

Authenticated walkthrough
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Own profile — :func:`~animedex.backends.danbooru.profile`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   animedex danbooru profile --jq  '{name, level, post_upload_count, blacklisted_tags}'

Saved searches — :func:`~animedex.backends.danbooru.saved_searches`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   animedex danbooru saved-search es --limit 5 --jq '.[].query'        

Endpoint summary
----------------

Posts / artists / tags / pools / counts (canonical 8)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``search <tags>``                :func:`animedex.backends.danbooru.search`                                    ``list[DanbooruPost]``
``post <id>``                    :func:`animedex.backends.danbooru.post`                                      :class:`~animedex.backends.danbooru.models.DanbooruPost`
``artist <id>``                  :func:`animedex.backends.danbooru.artist`                                    :class:`~animedex.backends.danbooru.models.DanbooruArtist`
``artist-search <name>``         :func:`animedex.backends.danbooru.artist_search`                             ``list[DanbooruArtist]``
``tag <name>``                   :func:`animedex.backends.danbooru.tag`                                       ``list[DanbooruTag]``
``pool <id>``                    :func:`animedex.backends.danbooru.pool`                                      :class:`~animedex.backends.danbooru.models.DanbooruPool`
``pool-search <name>``           :func:`animedex.backends.danbooru.pool_search`                               ``list[DanbooruPool]``
``count <tags>``                 :func:`animedex.backends.danbooru.count`                                     :class:`~animedex.backends.danbooru.models.DanbooruCount`
================================ ============================================================================ =================================================================

Discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``autocomplete <q>``             :func:`animedex.backends.danbooru.autocomplete`                              ``list[DanbooruRecord]``
``related-tag <q>``              :func:`animedex.backends.danbooru.related_tag`                               :class:`~animedex.backends.danbooru.models.DanbooruRelatedTag`
``iqdb-query``                   :func:`animedex.backends.danbooru.iqdb_query`                                ``list[DanbooruIQDBQuery]``
================================ ============================================================================ =================================================================

Long-tail feeds (catch-all ``DanbooruRecord``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``artist-versions``              :func:`animedex.backends.danbooru.artist_versions`                           ``list[DanbooruRecord]``
``artist-commentaries``          :func:`animedex.backends.danbooru.artist_commentaries`                       ``list[DanbooruRecord]``
``artist-commentary <id>``       :func:`animedex.backends.danbooru.artist_commentary`                         ``DanbooruRecord``
``artist-commentary-versions``   :func:`animedex.backends.danbooru.artist_commentary_versions`                ``list[DanbooruRecord]``
``tag-aliases``                  :func:`animedex.backends.danbooru.tag_aliases`                               ``list[DanbooruRecord]``
``tag-implications``             :func:`animedex.backends.danbooru.tag_implications`                          ``list[DanbooruRecord]``
``tag-versions``                 :func:`animedex.backends.danbooru.tag_versions`                              ``list[DanbooruRecord]``
``wiki-pages``                   :func:`animedex.backends.danbooru.wiki_pages`                                ``list[DanbooruRecord]``
``wiki-page <id>``               :func:`animedex.backends.danbooru.wiki_page`                                 ``DanbooruRecord``
``wiki-page-versions``           :func:`animedex.backends.danbooru.wiki_page_versions`                        ``list[DanbooruRecord]``
``pool-versions``                :func:`animedex.backends.danbooru.pool_versions`                             ``list[DanbooruRecord]``
``notes``                        :func:`animedex.backends.danbooru.notes`                                     ``list[DanbooruRecord]``
``note <id>``                    :func:`animedex.backends.danbooru.note`                                      ``DanbooruRecord``
``note-versions``                :func:`animedex.backends.danbooru.note_versions`                             ``list[DanbooruRecord]``
``comments``                     :func:`animedex.backends.danbooru.comments`                                  ``list[DanbooruRecord]``
``comment <id>``                 :func:`animedex.backends.danbooru.comment`                                   ``DanbooruRecord``
``comment-votes``                :func:`animedex.backends.danbooru.comment_votes`                             ``list[DanbooruRecord]``
``forum-topics``                 :func:`animedex.backends.danbooru.forum_topics`                              ``list[DanbooruRecord]``
``forum-topic-visits``           :func:`animedex.backends.danbooru.forum_topic_visits`                        ``list[DanbooruRecord]``
``forum-posts``                  :func:`animedex.backends.danbooru.forum_posts`                               ``list[DanbooruRecord]``
``forum-post-votes``             :func:`animedex.backends.danbooru.forum_post_votes`                          ``list[DanbooruRecord]``
``users``                        :func:`animedex.backends.danbooru.users`                                     ``list[DanbooruRecord]``
``user <id>``                    :func:`animedex.backends.danbooru.user`                                      ``DanbooruRecord``
``user-events``                  :func:`animedex.backends.danbooru.user_events`                               ``list[DanbooruRecord]``
``user-feedbacks``               :func:`animedex.backends.danbooru.user_feedbacks`                            ``list[DanbooruRecord]``
``favorites``                    :func:`animedex.backends.danbooru.favorites`                                 ``list[DanbooruRecord]``
``favorite-groups``              :func:`animedex.backends.danbooru.favorite_groups`                           ``list[DanbooruRecord]``
``uploads``                      :func:`animedex.backends.danbooru.uploads`                                   ``list[DanbooruRecord]``
``upload-media-assets``          :func:`animedex.backends.danbooru.upload_media_assets`                       ``list[DanbooruRecord]``
``post-versions``                :func:`animedex.backends.danbooru.post_versions`                             ``list[DanbooruRecord]``
``post-replacements``            :func:`animedex.backends.danbooru.post_replacements`                         ``list[DanbooruRecord]``
``post-disapprovals``            :func:`animedex.backends.danbooru.post_disapprovals`                         ``list[DanbooruRecord]``
``post-appeals``                 :func:`animedex.backends.danbooru.post_appeals`                              ``list[DanbooruRecord]``
``post-flags``                   :func:`animedex.backends.danbooru.post_flags`                                ``list[DanbooruRecord]``
``post-votes``                   :func:`animedex.backends.danbooru.post_votes`                                ``list[DanbooruRecord]``
``post-approvals``               :func:`animedex.backends.danbooru.post_approvals`                            ``list[DanbooruRecord]``
``post-events``                  :func:`animedex.backends.danbooru.post_events`                               ``list[DanbooruRecord]``
``mod-actions``                  :func:`animedex.backends.danbooru.mod_actions`                               ``list[DanbooruRecord]``
``bans``                         :func:`animedex.backends.danbooru.bans`                                      ``list[DanbooruRecord]``
``bulk-update-requests``         :func:`animedex.backends.danbooru.bulk_update_requests`                      ``list[DanbooruRecord]``
``dtext-links``                  :func:`animedex.backends.danbooru.dtext_links`                               ``list[DanbooruRecord]``
``ai-tags``                      :func:`animedex.backends.danbooru.ai_tags`                                   ``list[DanbooruRecord]``
``media-assets``                 :func:`animedex.backends.danbooru.media_assets`                              ``list[DanbooruRecord]``
``media-metadata``               :func:`animedex.backends.danbooru.media_metadata`                            ``list[DanbooruRecord]``
``rate-limits``                  :func:`animedex.backends.danbooru.rate_limits`                               ``list[DanbooruRecord]``
``recommended-posts``            :func:`animedex.backends.danbooru.recommended_posts`                         ``list[DanbooruRecord]``
``reactions``                    :func:`animedex.backends.danbooru.reactions`                                 ``list[DanbooruRecord]``
``jobs``                         :func:`animedex.backends.danbooru.jobs`                                      ``list[DanbooruRecord]``
``metrics``                      :func:`animedex.backends.danbooru.metrics`                                   ``list[DanbooruRecord]``
================================ ============================================================================ =================================================================

Authenticated reads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``profile``                      :func:`animedex.backends.danbooru.profile`                                   :class:`~animedex.backends.danbooru.models.DanbooruProfile`
``saved-searches``               :func:`animedex.backends.danbooru.saved_searches`                            ``list[DanbooruSavedSearch]``
================================ ============================================================================ =================================================================

Pagination
----------

Danbooru paginates with ``?limit=M&page=N`` (1-indexed). The
high-level helpers expose ``limit`` / ``page`` kwargs:

.. code-block:: bash

   animedex danbooru search "touh ou rating:g" --limit 5 --page 1                                                                                                               
   animedex danbooru search "touh ou rating:g" --limit 5 --page 2                                                                                                               

Gotchas
-------

* **The catch-all ``DanbooruRecord``** type covers the long tail of
  versions / votes / events / for um / commentary / moderation feeds                                                                                                            
  with a single rich shape. Its ` `id`` field is typed as                                                                                                                       
  :class:`~typing.Any` because op erational endpoints (``/jobs``,                                                                                                               
  ``/metrics``) use UUID strings while the typical ones use ints —                                                                                                             
  ``extra='allow'`` round-trips b oth.                                                                                                                                          
* **Empty result is an empty list, not 404**: a tag search with no
  hits returns ``[]`` with HTTP 2 00.                                                                                                                                           
* **``iqdb-query`` requires ``--url`` or ``--post-id``**: passing
  neither raises ``ApiError(reaso n="bad-args")``.                                                                                                                              
* **403 on``/dmails`` is not an animedex bug**: that endpoint requires
  Gold-tier upstream membership. animedex surfaces the upstream's                                                                                                              
  reason directly.                                                                                                                                                             

The :doc:`../python_library` page covers the same surface from
inside Python.
