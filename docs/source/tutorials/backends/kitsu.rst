``animedex kitsu``
==================

Kitsu is a JSON:API anime / manga aggregator hosted at
``https://kitsu.io/api/edge``. It is the **broadest "library-style"
backend** animedex wraps: every show / chapter / character /
production company / streaming link, plus a clean cross-source
mapping graph (``/mappings``) that ties Kitsu IDs to AniList, MAL,
AniDB, and similar peers. animedex covers **38 anonymous endpoints**
as 38 high-level Python functions.

.. image:: /_static/gifs/kitsu.gif
   :alt: animedex kitsu demo — show, search, mappings, trending
   :align: center

References
----------

================================ =====================================
Site                             https://kitsu.app/
API documentation                https://kitsu.docs.apiary.io/
Hosted base URL                  https://kitsu.io/api/edge
Python module                    :mod:`animedex.backends.kitsu`
Rich models                      :mod:`animedex.backends.kitsu.models`
================================ =====================================

* **Backend**: Kitsu (kitsu.io / kitsu.app).
* **Rate limit**: not formally published; transport applies a polite
  10 req/sec ceiling.                                                 
* **Auth**: never required for read. Library-write endpoints exist
  upstream but are out-of-scope p er read-only-by-scope.               

Six endpoints, in detail
------------------------

Anime by Kitsu ID — :func:`~animedex.backends.kitsu.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu show 7442 --jq '.attributes | {title: .canonicalTitle, status, averageRating}'
   # => {                                                             
   #      "title":         "Attac k on Titan",                         
   #      "status":        "finis hed",                                
   #      "averageRating": "84.50 "                                    
   #    }                                                             

Anime title search — :func:`~animedex.backends.kitsu.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu search "Frieren " --limit 3 --jq '.[].attributes.canonicalTitle'

Cross-source ID graph — :func:`~animedex.backends.kitsu.mappings`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu mappings 7442 - -jq '.[] | {externalSite: .attributes.externalSite, externalId: .attributes.externalId}'
   # => links Kitsu 7442 to its A niList / MAL / AniDB / TheTVDB peers 

Streaming links — :func:`~animedex.backends.kitsu.streaming`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu streaming 7442 --jq '.[].attributes.url'            
   # => ["https://www.crunchyroll .com/...", ...]                      

Trending shows — :func:`~animedex.backends.kitsu.trending`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu trending --limi t 5 --jq '.[].attributes.canonicalTitle'

Manga by Kitsu ID — :func:`~animedex.backends.kitsu.manga_show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex kitsu manga-show 39 - -jq '.attributes | {title: .canonicalTitle, status, chapterCount}'

Endpoint summary
----------------

Anime — top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``show <id>``                    :func:`animedex.backends.kitsu.show`                                         :class:`~animedex.backends.kitsu.models.KitsuAnime`
``search <q>``                   :func:`animedex.backends.kitsu.search`                                       ``list[KitsuAnime]``
``streaming <id>``               :func:`animedex.backends.kitsu.streaming`                                    ``list[KitsuStreamingLink]``
``mappings <id>``                :func:`animedex.backends.kitsu.mappings`                                     ``list[KitsuMapping]``
``trending``                     :func:`animedex.backends.kitsu.trending`                                     ``list[KitsuAnime]``
``categories``                   :func:`animedex.backends.kitsu.categories`                                   ``list[KitsuCategory]``
================================ ============================================================================ =================================================================

Anime — sub-relationships
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``anime-characters <id>``        :func:`animedex.backends.kitsu.anime_characters`                             ``list[KitsuRelatedResource]``
``anime-staff <id>``             :func:`animedex.backends.kitsu.anime_staff`                                  ``list[KitsuRelatedResource]``
``anime-episodes <id>``          :func:`animedex.backends.kitsu.anime_episodes`                               ``list[KitsuRelatedResource]``
``anime-reviews <id>``           :func:`animedex.backends.kitsu.anime_reviews`                                ``list[KitsuRelatedResource]``
``anime-genres <id>``            :func:`animedex.backends.kitsu.anime_genres`                                 ``list[KitsuGenre]``
``anime-categories <id>``        :func:`animedex.backends.kitsu.anime_categories`                             ``list[KitsuCategory]``
``anime-relations <id>``         :func:`animedex.backends.kitsu.anime_relations`                              ``list[KitsuRelatedResource]``
``anime-productions <id>``       :func:`animedex.backends.kitsu.anime_productions`                            ``list[KitsuRelatedResource]``
================================ ============================================================================ =================================================================

Manga
~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``manga-show <id>``              :func:`animedex.backends.kitsu.manga_show`                                   :class:`~animedex.backends.kitsu.models.KitsuManga`
``manga-search <q>``             :func:`animedex.backends.kitsu.manga_search`                                 ``list[KitsuManga]``
``trending-manga``               :func:`animedex.backends.kitsu.trending_manga`                               ``list[KitsuManga]``
``manga-characters <id>``        :func:`animedex.backends.kitsu.manga_characters`                             ``list[KitsuRelatedResource]``
``manga-staff <id>``             :func:`animedex.backends.kitsu.manga_staff`                                  ``list[KitsuRelatedResource]``
``manga-chapters <id>``          :func:`animedex.backends.kitsu.manga_chapters`                               ``list[KitsuRelatedResource]``
``manga-genres <id>``            :func:`animedex.backends.kitsu.manga_genres`                                 ``list[KitsuGenre]``
================================ ============================================================================ =================================================================

People (characters / persons / producers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``character <id>``               :func:`animedex.backends.kitsu.character`                                    :class:`~animedex.backends.kitsu.models.KitsuCharacter`
``character-search <q>``         :func:`animedex.backends.kitsu.character_search`                             ``list[KitsuCharacter]``
``person <id>``                  :func:`animedex.backends.kitsu.person`                                       :class:`~animedex.backends.kitsu.models.KitsuPerson`
``person-search <q>``            :func:`animedex.backends.kitsu.person_search`                                ``list[KitsuPerson]``
``person-voices <id>``           :func:`animedex.backends.kitsu.person_voices`                                ``list[KitsuRelatedResource]``
``person-castings <id>``         :func:`animedex.backends.kitsu.person_castings`                              ``list[KitsuRelatedResource]``
``producer <id>``                :func:`animedex.backends.kitsu.producer`                                     :class:`~animedex.backends.kitsu.models.KitsuProducer`
``producers``                    :func:`animedex.backends.kitsu.producers`                                    ``list[KitsuProducer]``
================================ ============================================================================ =================================================================

Taxonomy / discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``genre <id>``                   :func:`animedex.backends.kitsu.genre`                                        :class:`~animedex.backends.kitsu.models.KitsuGenre`
``genres``                       :func:`animedex.backends.kitsu.genres`                                       ``list[KitsuGenre]``
``category <id>``                :func:`animedex.backends.kitsu.category`                                     :class:`~animedex.backends.kitsu.models.KitsuCategory`
``streamers``                    :func:`animedex.backends.kitsu.streamers`                                    ``list[KitsuStreamer]``
``franchise <id>``               :func:`animedex.backends.kitsu.franchise`                                    :class:`~animedex.backends.kitsu.models.KitsuFranchise`
``franchises``                   :func:`animedex.backends.kitsu.franchises`                                   ``list[KitsuFranchise]``
================================ ============================================================================ =================================================================

User profiles (anonymous-readable)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``user <id>``                    :func:`animedex.backends.kitsu.user`                                         :class:`~animedex.backends.kitsu.models.KitsuUser`
``user-library <id>``            :func:`animedex.backends.kitsu.user_library`                                 ``list[KitsuRelatedResource]``
``user-stats <id>``              :func:`animedex.backends.kitsu.user_stats`                                   ``list[KitsuRelatedResource]``
================================ ============================================================================ =================================================================

Pagination
----------

Kitsu paginates with ``?page[limit]=M&page[offset]=N`` (JSON:API
convention). The high-level helpers expose ``limit`` and ``page``
kwargs that translate into the ``page[limit]`` / ``page[offset]``
JSON:API query params:

.. code-block:: bash

   animedex kitsu search "Frieren " --limit 5 --jq '.[].attributes.canonicalTitle'                                                                                              
   animedex kitsu search "Frieren " --limit 5 --page 2 --jq '.[].attributes.canonicalTitle'                                                                                     

Gotchas
-------

* **The ``status`` literal differs from MangaDex**: Kitsu emits
  ``"finished"`` / ``"current"`` / ``"tba"``; MangaDex uses                                                                                                                    
  ``"completed"`` / ``"ongoing"`` . The cross-source ``Manga.status``                                                                                                           
  literal is normalised by the ri ch model's ``to_common()`` so callers                                                                                                         
  see a single vocabulary across upstreams.                                                                                                                                    
* **Mappings are the joint** between Kitsu and the rest of the
  ecosystem. If you have an AniLi st ID and want the Kitsu peer, fetch                                                                                                          
  ``mappings`` on the Kitsu show and look for ``externalSite ==                                                                                                                
  "anilist/anime"``.                                                                                                                                                           
* **``averageRating`` is a string**: Kitsu returns it as ``"84.50"``,
  not ``84.5``. The rich model pr eserves it lossless; cast at the                                                                                                              
  call site if you want a float.                                                                                                                                               

The :doc:`../python_library` page covers the same surface from
inside Python.
