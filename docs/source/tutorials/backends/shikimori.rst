``animedex shikimori``
======================

Shikimori is a Russian-language anime catalogue with MAL-flavoured IDs, REST resources, and a GraphQL surface. animedex wraps the anonymous anime REST endpoints as high-level commands and leaves GraphQL available through ``animedex api shikimori``.

.. image:: /_static/gifs/shikimori.gif
   :alt: animedex shikimori demo — show, search, calendar, screenshots, videos
   :align: center

References
----------

================================ =====================================
Site                             https://shikimori.io/
API documentation v2             https://shikimori.io/api/doc/2.0
API documentation v1             https://shikimori.io/api/doc/1.0
GraphQL documentation            https://shikimori.io/api/doc/graphql
Python module                    :mod:`animedex.backends.shikimori`
Rich models                      :mod:`animedex.backends.shikimori.models`
================================ =====================================

* **Backend**: Shikimori (``shikimori.io`` canonical; ``shikimori.one`` remains a transport alias).
* **Rate limit**: 5 RPS / 90 RPM.
* **Auth**: not required for the commands on this page.

Core lookups
------------

Anime by Shikimori ID — :func:`~animedex.backends.shikimori.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori show 52991 --jq '{id, name, russian, status, episodes}'
   # => {
   #      "id": 52991,
   #      "name": "Sousou no Frieren",
   #      "russian": "Провожающая в последний путь Фрирен",
   #      "status": "released",
   #      "episodes": 28
   #    }

Search by title — :func:`~animedex.backends.shikimori.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori search Frieren --limit 2 --jq '[.[].name]'
   # => [
   #      "Sousou no Frieren",
   #      "Sousou no Frieren: ●● no Mahou"
   #    ]

Calendar — :func:`~animedex.backends.shikimori.calendar`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori calendar --limit 3 --jq '.[0:3] | map({episode: .next_episode, title: .anime.name})'

Media rails — :func:`~animedex.backends.shikimori.screenshots` and :func:`~animedex.backends.shikimori.videos`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori screenshots 52991 --jq '.[0:3] | map(.preview)'
   animedex shikimori videos 52991 --jq '[.[0:3][] | {name, kind, url}]'

Relationship and taxonomy commands
----------------------------------

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``calendar``                     :func:`animedex.backends.shikimori.calendar`                                  ``list[ShikimoriCalendarEntry]``
``search <q>``                   :func:`animedex.backends.shikimori.search`                                    ``list[ShikimoriAnime]``
``show <anime_id>``              :func:`animedex.backends.shikimori.show`                                      :class:`~animedex.backends.shikimori.models.ShikimoriAnime`
``screenshots <anime_id>``       :func:`animedex.backends.shikimori.screenshots`                               ``list[ShikimoriScreenshot]``
``videos <anime_id>``            :func:`animedex.backends.shikimori.videos`                                    ``list[ShikimoriVideo]``
``roles <anime_id>``             :func:`animedex.backends.shikimori.roles`                                     ``list[ShikimoriResource]``
``characters <anime_id>``        :func:`animedex.backends.shikimori.characters`                                ``list[ShikimoriCharacter]``
``staff <anime_id>``             :func:`animedex.backends.shikimori.staff`                                     ``list[ShikimoriPerson]``
``similar <anime_id>``           :func:`animedex.backends.shikimori.similar`                                   ``list[ShikimoriAnime]``
``related <anime_id>``           :func:`animedex.backends.shikimori.related`                                   ``list[ShikimoriResource]``
``external-links <anime_id>``    :func:`animedex.backends.shikimori.external_links`                            ``list[ShikimoriResource]``
``topics <anime_id>``            :func:`animedex.backends.shikimori.topics`                                    ``list[ShikimoriTopic]``
``studios``                      :func:`animedex.backends.shikimori.studios`                                   ``list[ShikimoriStudio]``
``genres``                       :func:`animedex.backends.shikimori.genres`                                    ``list[ShikimoriResource]``
================================ ============================================================================ =================================================================

GraphQL remains available through the raw passthrough:

.. code-block:: bash

   animedex api shikimori /api/graphql --graphql '{ animes(ids:"52991"){ id name score } }'

The :doc:`../python_library` page covers the same surface from inside Python.
