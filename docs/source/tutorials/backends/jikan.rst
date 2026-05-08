``animedex jikan``
==================

Jikan v4 is a REST scraper of MyAnimeList, hosted at
``https://api.jikan.moe/v4``. It is the **deepest catalogue** of the
backends animedex wraps: every anime / manga / character / person /
producer / season / club / user / magazine / genre that MAL knows
about, with score distributions, news threads, forum posts, episode
lists and theme songs. animedex covers **all 87 anonymous v4
endpoints**.

* **Backend**: Jikan v4 (api.jikan.moe).
* **Rate limit**: 60 req/min, 3 req/sec (no per-second cap is
  documented but the project applies a conservative sustained ceiling).
* **Auth**: never. Jikan is read-only and anonymous by design; there
  is no token concept.

Core entities (typed dataclasses)
---------------------------------

Nine "core" entities have typed rich-dataclass returns: ``anime``,
``manga``, ``character``, ``person``, ``producer``, ``magazine``,
``genre``, ``club``, ``user``. The ``show`` and ``search`` commands
on each entity return a typed result.

.. code-block:: bash

   animedex jikan show 52991 --jq '.data | {title, score, status, broadcast.string}'
   # => {
   #      "title":           "Sousou no Frieren",
   #      "score":           9.31,
   #      "status":          "Finished Airing",
   #      "broadcast.string": "Fridays at 23:00 (JST)"
   #    }

   animedex jikan search "Frieren" --type tv --limit 3 --jq '.[].title'

   animedex jikan character-show 11 --jq '.data.name'
   # => "Edward Elric"

   animedex jikan person-show 1870 --jq '.data.name'
   # => "Hayao Miyazaki"

Long tail (``JikanGenericResponse``)
------------------------------------

The remaining ~70 endpoints (news / forum / videos / pictures /
statistics / moreinfo / recommendations / userupdates / reviews /
relations / themes / external / streaming / episodes / watch /
schedules / random / top / seasons) return a permissive
``JikanGenericResponse`` envelope with ``rows`` + ``pagination`` +
``source_tag``. The shape is intentionally unstructured because Jikan
varies by endpoint; use ``--jq`` to project the fields you need:

.. code-block:: bash

   animedex jikan anime-news 52991 --jq '.rows[].title'
   animedex jikan anime-recommendations 52991 --jq '.rows[].entry.title'
   animedex jikan top-anime --filter bypopularity --limit 5 --jq '.[].title'

Common patterns
---------------

**Seasonal grid**:

.. code-block:: bash

   animedex jikan season 2024 spring --limit 10 --jq '.[].title'

**Random**:

.. code-block:: bash

   animedex jikan random-anime --jq '.title'

**Watch / schedule**:

.. code-block:: bash

   animedex jikan watch-episodes --jq '.rows[0].entry.title'
   animedex jikan schedules --filter monday --limit 5 --jq '.rows[].title'

**User profiles**:

.. code-block:: bash

   animedex jikan user-show "nekomata1037" --jq '.data.username'

   animedex jikan user-favorites "nekomata1037" --jq '.rows | map(.entry.title) | .[:5]'

Pagination
----------

Jikan paginates with ``?page=N&limit=M`` and returns a ``pagination``
envelope (``has_next_page``, ``last_visible_page``, ``items``).
Iterate explicitly:

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
* **Score divergence**: Jikan's ``score`` is on a 0–10 scale, AniList's
  ``averageScore`` is 0–100. Both are upstream-canonical;
  ``animedex`` does not reconcile them.

The :doc:`../python_library` page covers the same surface from
inside Python.
