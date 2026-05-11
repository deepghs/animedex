``animedex search`` and ``animedex show``
=========================================

The top-level aggregate commands are the normal entry point when the user has not chosen a backend yet. ``animedex search`` fans out to every catalogue that supports the requested entity type, while ``animedex show`` routes one ``prefix:id`` reference back to the owning backend.

.. image:: /_static/gifs/aggregate.gif
   :alt: animedex aggregate demo - multi-source search and prefix-id show
   :align: center

References
----------

================================ =====================================================================
Python search module              :mod:`animedex.agg.search`
Python show module                :mod:`animedex.agg.show`
Prefix parser                     :mod:`animedex.agg._prefix_id`
Type routes                       :mod:`animedex.agg._type_routes`
Aggregate result model            :mod:`animedex.models.aggregate`
================================ =====================================================================

* **Backend**: aggregate orchestration over AniList, Anime News Network, Jikan, Kitsu, MangaDex, and Shikimori where the selected entity type is supported.
* **Rate limit**: inherited from each selected backend; the fan-out helper calls sources independently and records each source's status.
* **Output contract**: JSON keeps the rich backend row plus ``_source`` and ``_prefix_id``. TTY output projects rows only for readability and still prints ``[src: ...]``.

Search across catalogues
------------------------

``TYPE`` is required and must be one of ``anime``, ``manga``, ``character``, ``person``, ``studio``, or ``publisher``. The ``--limit`` option is per source, not global, because source rankings are not comparable.

.. code-block:: bash

   animedex search anime Frieren --limit 2 --source jikan,kitsu,shikimori --jq '.items[] | {_prefix_id, _source}'
   # => {"_prefix_id":"mal:63816","_source":"jikan"}
   # => {"_prefix_id":"mal:52991","_source":"jikan"}
   # => {"_prefix_id":"kitsu:46474","_source":"kitsu"}
   # => {"_prefix_id":"kitsu:49240","_source":"kitsu"}
   # => {"_prefix_id":"shikimori:52991","_source":"shikimori"}
   # => {"_prefix_id":"shikimori:56885","_source":"shikimori"}

Manga search includes MangaDex, whose IDs are UUID strings:

.. code-block:: bash

   animedex search manga Berserk --limit 2 --source mangadex,shikimori --jq '.items[] | {_prefix_id, _source}'
   # => {"_prefix_id":"mangadex:801513ba-a712-498c-8f57-cae55b38cc92","_source":"mangadex"}
   # => {"_prefix_id":"mangadex:30196491-8fc2-4961-8886-a58f898b1b3e","_source":"mangadex"}
   # => {"_prefix_id":"shikimori:2","_source":"shikimori"}
   # => {"_prefix_id":"shikimori:92299","_source":"shikimori"}

Publisher search is currently single-source because Shikimori is the only shipped backend with a publisher catalogue:

.. code-block:: bash

   animedex search publisher Kodansha --limit 2 --json --jq '{sources: .sources, ids: [.items[]._prefix_id]}'
   # => {
   #      "sources": {"shikimori": {"status": "ok", "items": 1, "reason": null, "message": null, "http_status": null, "duration_ms": 0}},
   #      "ids": ["shikimori:456"]
   #    }

Show from a prefixed ID
-----------------------

Use the ``_prefix_id`` from search output as the second argument to ``show``. The type remains explicit because upstream ID spaces often reuse the same numeric ID for different entity kinds.

.. code-block:: bash

   animedex show anime mal:52991 --jq '{title, score, status}'
   # => {
   #      "title": "Sousou no Frieren",
   #      "score": 9.31,
   #      "status": "Finished Airing"
   #    }

   animedex show manga mangadex:801513ba-a712-498c-8f57-cae55b38cc92 --jq '{id, title: (.attributes.title.en // .attributes.title["ja-ro"]), status: .attributes.status}'
   # => {
   #      "id": "801513ba-a712-498c-8f57-cae55b38cc92",
   #      "title": "Berserk",
   #      "status": "ongoing"
   #    }

   animedex show character shikimori:184947 --jq '{id, name}'
   # => {
   #      "id": 184947,
   #      "name": "Frieren"
   #    }

Prefix map
----------

================================ ========================================================================
Prefix                           Backend and ID shape
================================ ========================================================================
``anilist:154587``               AniList numeric ID
``mal:52991`` / ``jikan:52991``  Jikan over MyAnimeList numeric ID
``myanimelist:52991``            Long-form alias for ``mal:``
``kitsu:46474``                  Kitsu numeric ID
``shikimori:52991``              Shikimori numeric ID
``mangadex:<uuid>``              MangaDex UUID
``ann:38838``                    Anime News Network encyclopedia ID
``anidb:...``                    Recognised as deferred until AniDB high-level helpers ship
================================ ========================================================================

Source availability by type
---------------------------

================================ ========================================================================
Type                             Default sources
================================ ========================================================================
``anime``                        AniList, Anime News Network, Jikan, Kitsu, Shikimori
``manga``                        AniList, Jikan, Kitsu, MangaDex, Shikimori
``character``                    AniList, Jikan, Kitsu, Shikimori
``person``                       AniList, Jikan, Kitsu, Shikimori
``studio``                       AniList, Jikan, Kitsu, Shikimori
``publisher``                    Shikimori
================================ ========================================================================

At capture time for this tutorial, the AniList typed ``Frieren`` anime search fixture returned an empty ``media`` list and Kitsu's free-text people endpoint returned an upstream ``400`` for the captured Miyazaki probe. The stable examples above therefore use the sources with captured positive rows, and those upstream observations are recorded as source availability notes rather than hidden by the aggregate layer.

Failure-mode example
--------------------

This example is intentionally a failure-mode example. A failed source stays in the structured ``sources`` map and on stderr, while healthy sources still return rows. The command exits with status 0 when at least one selected source succeeds.

.. code-block:: bash

   animedex search anime Frieren --source ann,jikan,kitsu,shikimori --limit 2 --json --jq '{items: [.items[]._source], sources: .sources}'
   # stderr => source 'ann' failed: upstream-error: ann 503 on /api.xml; continuing with other sources
   # => {
   #      "items": ["jikan", "jikan", "kitsu", "kitsu", "shikimori", "shikimori"],
   #      "sources": {
   #        "ann": {"status": "failed", "items": 0, "reason": "upstream-error", "message": "upstream-error: ann 503 on /api.xml", "http_status": 503, "duration_ms": 0},
   #        "jikan": {"status": "ok", "items": 2, "reason": null, "message": null, "http_status": null, "duration_ms": 0},
   #        "kitsu": {"status": "ok", "items": 2, "reason": null, "message": null, "http_status": null, "duration_ms": 0},
   #        "shikimori": {"status": "ok", "items": 2, "reason": null, "message": null, "http_status": null, "duration_ms": 0}
   #      }
   #    }

The :doc:`output_modes` page covers the JSON, TTY, and ``--jq`` projection rules used by both aggregate commands.
