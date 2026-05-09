``animedex shikimori``
======================

Shikimori is a Russian-language catalogue with MAL-flavoured IDs, REST resources, and a GraphQL surface. animedex wraps the anonymous REST entity surfaces for anime, manga, ranobe, clubs, publishers, top-level people, taxonomies, and anime rails as high-level commands, while GraphQL remains available through ``animedex api shikimori``.

.. image:: /_static/gifs/shikimori.gif
   :alt: animedex shikimori demo - anime, manga, ranobe, clubs, publishers, and people
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

   animedex shikimori show 52991 --jq '{id, name, status, episodes}'
   # => {
   #      "id": 52991,
   #      "name": "Sousou no Frieren",
   #      "status": "released",
   #      "episodes": 28
   #    }

Search by title — :func:`~animedex.backends.shikimori.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori search Frieren --limit 2 --jq '[.[0].name]'
   # => [
   #      "Sousou no Frieren"
   #    ]

Manga search and detail
~~~~~~~~~~~~~~~~~~~~~~~

Python entry points: :func:`~animedex.backends.shikimori.manga_search`, :func:`~animedex.backends.shikimori.manga_show`.

.. code-block:: bash

   animedex shikimori manga-search Berserk --limit 2 --jq '[.[0] | {id, name, kind, status}]'
   # => [
   #      {
   #        "id": 2,
   #        "name": "Berserk",
   #        "kind": "manga",
   #        "status": "ongoing"
   #      }
   #    ]

   animedex shikimori manga-show 2 --jq '{id, name, kind, status, myanimelist_id}'
   # => {
   #      "id": 2,
   #      "name": "Berserk",
   #      "kind": "manga",
   #      "status": "ongoing",
   #      "myanimelist_id": 2
   #    }

Ranobe
~~~~~~

Python entry points: :func:`~animedex.backends.shikimori.ranobe_search`, :func:`~animedex.backends.shikimori.ranobe_show`.

.. code-block:: bash

   animedex shikimori ranobe-search Monogatari --limit 2 --jq '[.[0] | {id, name, kind}]'
   # => [
   #      {
   #        "id": 23751,
   #        "name": "Monogatari Series: Second Season",
   #        "kind": "light_novel"
   #      }
   #    ]

   animedex shikimori ranobe-show 23751 --jq '{id, name, kind, volumes, chapters}'
   # => {
   #      "id": 23751,
   #      "name": "Monogatari Series: Second Season",
   #      "kind": "light_novel",
   #      "volumes": 6,
   #      "chapters": 199
   #    }

Clubs, publishers, and people
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python entry points: :func:`~animedex.backends.shikimori.club_search`, :func:`~animedex.backends.shikimori.publishers`, :func:`~animedex.backends.shikimori.person`.

.. code-block:: bash

   animedex shikimori club-search anime --limit 3 --jq '[.[0] | {id, name, join_policy}]'
   # => [
   #      {
   #        "id": 746,
   #        "name": "Anime Glitch",
   #        "join_policy": "free"
   #      }
   #    ]

   animedex shikimori publishers --jq '[.[0] | {id, name}]'
   # => [
   #      {
   #        "id": 1510,
   #        "name": "Web Action"
   #      }
   #    ]

   animedex shikimori person 1870 --jq '{id, name, website}'
   # => {
   #      "id": 1870,
   #      "name": "Hayao Miyazaki",
   #      "website": "http://www.ghibli.jp/"
   #    }

Calendar — :func:`~animedex.backends.shikimori.calendar`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex shikimori calendar --limit 3 --jq '.[0:3] | map({episode: .next_episode, title: .anime.name})'

Media rails
~~~~~~~~~~~

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
``manga-search <q>``             :func:`animedex.backends.shikimori.manga_search`                              ``list[ShikimoriManga]``
``manga-show <manga_id>``        :func:`animedex.backends.shikimori.manga_show`                                :class:`~animedex.backends.shikimori.models.ShikimoriManga`
``ranobe-search <q>``            :func:`animedex.backends.shikimori.ranobe_search`                             ``list[ShikimoriManga]``
``ranobe-show <ranobe_id>``      :func:`animedex.backends.shikimori.ranobe_show`                               :class:`~animedex.backends.shikimori.models.ShikimoriManga`
``club-search <q>``              :func:`animedex.backends.shikimori.club_search`                               ``list[ShikimoriClub]``
``club-show <club_id>``          :func:`animedex.backends.shikimori.club_show`                                 :class:`~animedex.backends.shikimori.models.ShikimoriClub`
``publishers``                   :func:`animedex.backends.shikimori.publishers`                                ``list[ShikimoriPublisher]``
``people-search <q>``            :func:`animedex.backends.shikimori.people_search`                             ``list[ShikimoriPerson]``
``person <person_id>``           :func:`animedex.backends.shikimori.person`                                    :class:`~animedex.backends.shikimori.models.ShikimoriPerson`
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
