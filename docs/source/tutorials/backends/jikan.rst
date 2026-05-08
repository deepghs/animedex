``animedex jikan``
==================

Jikan v4 is a REST scraper of MyAnimeList, hosted at
``https://api.jikan.moe/v4``. It is the **deepest catalogue** of the
backends animedex wraps: every anime / manga / character / person /
producer / season / club / user / magazine / genre that MAL knows
about, with score distributions, news threads, forum posts, episode
lists and theme songs. animedex covers **all 87 anonymous v4
endpoints** as 92 high-level Python functions (a few endpoints get
multiple entry points for ergonomic kwargs).

.. image:: /_static/gifs/jikan.gif
   :alt: animedex jikan demo — anime, manga, character, season, top
   :align: center

References
----------

================================ =====================================
Site                             https://jikan.moe/
API documentation                https://docs.api.jikan.moe/
GitHub repo                      https://github.com/jikan-me/jikan-api-docs
MyAnimeList (data source)        https://myanimelist.net/
Python module                    :mod:`animedex.backends.jikan`
Rich models                      :mod:`animedex.backends.jikan.models`
================================ =====================================

* **Backend**: Jikan v4 (api.jikan.moe).
* **Rate limit**: 60 req/min, 3 req/sec.
* **Auth**: never. Jikan is read-only and anonymous by design; there
  is no token concept.

Eleven endpoints, in detail
---------------------------

Anime by MAL ID — :func:`~animedex.backends.jikan.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan show 52991 --jq '.data | {title, score, status, broadcast: .broadcast.string}'
   # => {
   #      "title":     "Sousou no Frieren",
   #      "score":     9.31,
   #      "status":    "Finished Airing",
   #      "broadcast": "Fridays at 23:00 (JST)"
   #    }

Anime search — :func:`~animedex.backends.jikan.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan search "Frieren" --type tv --limit 3 --jq '.[] | {mal_id, title}'

Cast on a show — :func:`~animedex.backends.jikan.anime_characters`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan anime-characters 52991 --jq '.rows[:3] | map({character: .character.name, role})'

Image gallery — :func:`~animedex.backends.jikan.anime_pictures`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan anime-pictures 52991 --jq '.rows[].jpg.large_image_url' | head -3

Manga by MAL ID — :func:`~animedex.backends.jikan.manga_show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan manga-show 2 --jq '.data | {title, score, chapters, status}'
   # => {
   #      "title":    "Berserk",
   #      "score":    9.47,
   #      "chapters": null,    # null = ongoing
   #      "status":   "Publishing"
   #    }

Character lookup — :func:`~animedex.backends.jikan.character_show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan character-show 11 --jq '.data | {name, favourites: .favorites}'
   # => {
   #      "name":       "Edward Elric",
   #      "favourites": 100000
   #    }

Person lookup — :func:`~animedex.backends.jikan.person_show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan person-show 1870 --jq '.data | {name, family_name, given_name, birthday}'

Seasonal grid — :func:`~animedex.backends.jikan.season`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan season 2024 spring --limit 5 --jq '.[].title'

Top by popularity — :func:`~animedex.backends.jikan.top_anime`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan top-anime --filter bypopularity --limit 5 --jq '.[] | {title, members}'

Random pick — :func:`~animedex.backends.jikan.random_anime`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan random-anime --jq '.title'
   # => "<random anime title>"

User profile — :func:`~animedex.backends.jikan.user_show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex jikan user-show "nekomata1037" --jq '.data | {username, joined, statistics: .statistics.anime}'

Endpoint summary
----------------

Nine "core" entities (anime, manga, character, person, producer,
magazine, genre, club, user) have typed dataclass returns; the
long-tail sub-endpoints return
:class:`~animedex.backends.jikan.models.JikanGenericResponse` (a
permissive ``extra='allow'`` envelope). Use ``--jq`` to project the
fields you need.

``/anime/{id}/...``
~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``show <id>``                    :func:`animedex.backends.jikan.show`                                         :class:`~animedex.backends.jikan.models.JikanAnime`
``search <q>``                   :func:`animedex.backends.jikan.search`                                       ``list[JikanAnime]``
``anime-characters <id>``        :func:`animedex.backends.jikan.anime_characters`                             ``JikanGenericResponse``
``anime-staff <id>``             :func:`animedex.backends.jikan.anime_staff`                                  ``JikanGenericResponse``
``anime-episodes <id>``          :func:`animedex.backends.jikan.anime_episodes`                               ``JikanGenericResponse``
``anime-episode <id> <ep>``      :func:`animedex.backends.jikan.anime_episode`                                ``JikanGenericResponse``
``anime-news <id>``              :func:`animedex.backends.jikan.anime_news`                                   ``JikanGenericResponse``
``anime-forum <id>``             :func:`animedex.backends.jikan.anime_forum`                                  ``JikanGenericResponse``
``anime-videos <id>``            :func:`animedex.backends.jikan.anime_videos`                                 ``JikanGenericResponse``
``anime-videos-episodes <id>``   :func:`animedex.backends.jikan.anime_videos_episodes`                        ``JikanGenericResponse``
``anime-pictures <id>``          :func:`animedex.backends.jikan.anime_pictures`                               ``JikanGenericResponse``
``anime-statistics <id>``        :func:`animedex.backends.jikan.anime_statistics`                             ``JikanGenericResponse``
``anime-moreinfo <id>``          :func:`animedex.backends.jikan.anime_moreinfo`                               ``JikanGenericResponse``
``anime-recommendations <id>``   :func:`animedex.backends.jikan.anime_recommendations`                        ``JikanGenericResponse``
``anime-userupdates <id>``       :func:`animedex.backends.jikan.anime_userupdates`                            ``JikanGenericResponse``
``anime-reviews <id>``           :func:`animedex.backends.jikan.anime_reviews`                                ``JikanGenericResponse``
``anime-relations <id>``         :func:`animedex.backends.jikan.anime_relations`                              ``JikanGenericResponse``
``anime-themes <id>``            :func:`animedex.backends.jikan.anime_themes`                                 ``JikanGenericResponse``
``anime-external <id>``          :func:`animedex.backends.jikan.anime_external`                               ``JikanGenericResponse``
``anime-streaming <id>``         :func:`animedex.backends.jikan.anime_streaming`                              ``JikanGenericResponse``
================================ ============================================================================ =================================================================

``/manga/{id}/...``
~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``manga-show <id>``              :func:`animedex.backends.jikan.manga_show`                                   :class:`~animedex.backends.jikan.models.JikanManga`
``manga-search <q>``             :func:`animedex.backends.jikan.manga_search`                                 ``list[JikanManga]``
``manga-characters <id>``        :func:`animedex.backends.jikan.manga_characters`                             ``JikanGenericResponse``
``manga-news <id>``              :func:`animedex.backends.jikan.manga_news`                                   ``JikanGenericResponse``
``manga-forum <id>``             :func:`animedex.backends.jikan.manga_forum`                                  ``JikanGenericResponse``
``manga-pictures <id>``          :func:`animedex.backends.jikan.manga_pictures`                               ``JikanGenericResponse``
``manga-statistics <id>``        :func:`animedex.backends.jikan.manga_statistics`                             ``JikanGenericResponse``
``manga-moreinfo <id>``          :func:`animedex.backends.jikan.manga_moreinfo`                               ``JikanGenericResponse``
``manga-recommendations <id>``   :func:`animedex.backends.jikan.manga_recommendations`                        ``JikanGenericResponse``
``manga-userupdates <id>``       :func:`animedex.backends.jikan.manga_userupdates`                            ``JikanGenericResponse``
``manga-reviews <id>``           :func:`animedex.backends.jikan.manga_reviews`                                ``JikanGenericResponse``
``manga-relations <id>``         :func:`animedex.backends.jikan.manga_relations`                              ``JikanGenericResponse``
``manga-external <id>``          :func:`animedex.backends.jikan.manga_external`                               ``JikanGenericResponse``
================================ ============================================================================ =================================================================

``/characters/{id}/...``
~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``character-show <id>``          :func:`animedex.backends.jikan.character_show`                               :class:`~animedex.backends.jikan.models.JikanCharacter`
``character-search <q>``         :func:`animedex.backends.jikan.character_search`                             ``list[JikanCharacter]``
``character-anime <id>``         :func:`animedex.backends.jikan.character_anime`                              ``JikanGenericResponse``
``character-manga <id>``         :func:`animedex.backends.jikan.character_manga`                              ``JikanGenericResponse``
``character-voices <id>``        :func:`animedex.backends.jikan.character_voices`                             ``JikanGenericResponse``
``character-pictures <id>``      :func:`animedex.backends.jikan.character_pictures`                           ``JikanGenericResponse``
================================ ============================================================================ =================================================================

``/people/{id}/...``
~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``person-show <id>``             :func:`animedex.backends.jikan.person_show`                                  :class:`~animedex.backends.jikan.models.JikanPerson`
``person-search <q>``            :func:`animedex.backends.jikan.person_search`                                ``list[JikanPerson]``
``person-anime <id>``            :func:`animedex.backends.jikan.person_anime`                                 ``JikanGenericResponse``
``person-voices <id>``           :func:`animedex.backends.jikan.person_voices`                                ``JikanGenericResponse``
``person-manga <id>``            :func:`animedex.backends.jikan.person_manga`                                 ``JikanGenericResponse``
``person-pictures <id>``         :func:`animedex.backends.jikan.person_pictures`                              ``JikanGenericResponse``
================================ ============================================================================ =================================================================

``/producers/{id}/...``
~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``producer-show <id>``           :func:`animedex.backends.jikan.producer_show`                                :class:`~animedex.backends.jikan.models.JikanProducer`
``producer-search <q>``          :func:`animedex.backends.jikan.producer_search`                              ``list[JikanProducer]``
``producer-external <id>``       :func:`animedex.backends.jikan.producer_external`                            ``JikanGenericResponse``
================================ ============================================================================ =================================================================

Magazines, genres, clubs
~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``magazines <q>``                :func:`animedex.backends.jikan.magazines`                                    ``list[JikanMagazine]``
``genres-anime``                 :func:`animedex.backends.jikan.genres_anime`                                 ``list[JikanGenre]``
``genres-manga``                 :func:`animedex.backends.jikan.genres_manga`                                 ``list[JikanGenre]``
``clubs <q>``                    :func:`animedex.backends.jikan.clubs`                                        ``JikanGenericResponse``
``club-show <id>``               :func:`animedex.backends.jikan.club_show`                                    :class:`~animedex.backends.jikan.models.JikanClub`
``club-members <id>``            :func:`animedex.backends.jikan.club_members`                                 ``JikanGenericResponse``
``club-staff <id>``              :func:`animedex.backends.jikan.club_staff`                                   ``JikanGenericResponse``
``club-relations <id>``          :func:`animedex.backends.jikan.club_relations`                               ``JikanGenericResponse``
================================ ============================================================================ =================================================================

Users
~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``user-show <name>``             :func:`animedex.backends.jikan.user_show`                                    :class:`~animedex.backends.jikan.models.JikanUser`
``user-basic <name>``            :func:`animedex.backends.jikan.user_basic`                                   :class:`~animedex.backends.jikan.models.JikanUser`
``user-search <q>``              :func:`animedex.backends.jikan.user_search`                                  ``JikanGenericResponse``
``user-by-mal-id <id>``          :func:`animedex.backends.jikan.user_by_mal_id`                               ``JikanGenericResponse``
``user-statistics <name>``       :func:`animedex.backends.jikan.user_statistics`                              ``JikanGenericResponse``
``user-favorites <name>``        :func:`animedex.backends.jikan.user_favorites`                               ``JikanGenericResponse``
``user-userupdates <name>``      :func:`animedex.backends.jikan.user_userupdates`                             ``JikanGenericResponse``
``user-about <name>``            :func:`animedex.backends.jikan.user_about`                                   ``JikanGenericResponse``
``user-history <name>``          :func:`animedex.backends.jikan.user_history`                                 ``JikanGenericResponse``
``user-friends <name>``          :func:`animedex.backends.jikan.user_friends`                                 ``JikanGenericResponse``
``user-reviews <name>``          :func:`animedex.backends.jikan.user_reviews`                                 ``JikanGenericResponse``
``user-recommendations <name>``  :func:`animedex.backends.jikan.user_recommendations`                         ``JikanGenericResponse``
``user-clubs <name>``            :func:`animedex.backends.jikan.user_clubs`                                   ``JikanGenericResponse``
================================ ============================================================================ =================================================================

Seasons / top / schedule / random
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``seasons-list``                 :func:`animedex.backends.jikan.seasons_list`                                 ``JikanGenericResponse``
``seasons-now``                  :func:`animedex.backends.jikan.seasons_now`                                  ``list[JikanAnime]``
``seasons-upcoming``             :func:`animedex.backends.jikan.seasons_upcoming`                             ``list[JikanAnime]``
``season <year> <name>``         :func:`animedex.backends.jikan.season`                                       ``list[JikanAnime]``
``top-anime``                    :func:`animedex.backends.jikan.top_anime`                                    ``list[JikanAnime]``
``top-manga``                    :func:`animedex.backends.jikan.top_manga`                                    ``list[JikanManga]``
``top-characters``               :func:`animedex.backends.jikan.top_characters`                               ``list[JikanCharacter]``
``top-people``                   :func:`animedex.backends.jikan.top_people`                                   ``list[JikanPerson]``
``top-reviews``                  :func:`animedex.backends.jikan.top_reviews`                                  ``JikanGenericResponse``
``schedules``                    :func:`animedex.backends.jikan.schedules`                                    ``JikanGenericResponse``
``random-anime``                 :func:`animedex.backends.jikan.random_anime`                                 :class:`~animedex.backends.jikan.models.JikanAnime`
``random-manga``                 :func:`animedex.backends.jikan.random_manga`                                 :class:`~animedex.backends.jikan.models.JikanManga`
``random-character``             :func:`animedex.backends.jikan.random_character`                             :class:`~animedex.backends.jikan.models.JikanCharacter`
``random-person``                :func:`animedex.backends.jikan.random_person`                                :class:`~animedex.backends.jikan.models.JikanPerson`
``random-user``                  :func:`animedex.backends.jikan.random_user`                                  :class:`~animedex.backends.jikan.models.JikanUser`
================================ ============================================================================ =================================================================

Recommendations / reviews / watch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``recommendations-anime``        :func:`animedex.backends.jikan.recommendations_anime`                        ``JikanGenericResponse``
``recommendations-manga``        :func:`animedex.backends.jikan.recommendations_manga`                        ``JikanGenericResponse``
``reviews-anime``                :func:`animedex.backends.jikan.reviews_anime`                                ``JikanGenericResponse``
``reviews-manga``                :func:`animedex.backends.jikan.reviews_manga`                                ``JikanGenericResponse``
``watch-episodes``               :func:`animedex.backends.jikan.watch_episodes`                               ``JikanGenericResponse``
``watch-episodes-popular``       :func:`animedex.backends.jikan.watch_episodes_popular`                       ``JikanGenericResponse``
``watch-promos``                 :func:`animedex.backends.jikan.watch_promos`                                 ``JikanGenericResponse``
``watch-promos-popular``         :func:`animedex.backends.jikan.watch_promos_popular`                         ``JikanGenericResponse``
================================ ============================================================================ =================================================================

Pagination
----------

Jikan paginates with ``?page=N&limit=M`` and returns a
``pagination`` envelope (``has_next_page``, ``last_visible_page``,
``items``). Iterate explicitly:

.. code-block:: bash

   animedex jikan search "Frieren" --page 1 --limit 10 --jq '.[].title'
   animedex jikan search "Frieren" --page 2 --limit 10 --jq '.[].title'

Gotchas
-------

* **MAL flakiness propagates**: Jikan is a scraper. When MAL itself
  is unreachable, you get a 5xx that surfaces as
  ``ApiError(reason="upstream-error")`` — not a Jikan bug, just
  upstream weather.
* **404 is a real "not found"**: ``animedex jikan show 999999999``
  returns 404 → ``ApiError(reason="not-found")``. The fixture corpus
  pins this.
* **Score divergence**: Jikan's ``score`` is on a 0–10 scale,
  AniList's ``averageScore`` is 0–100. Both are upstream-canonical;
  ``animedex`` does not reconcile them.

The :doc:`../python_library` page covers the same surface from
inside Python.
