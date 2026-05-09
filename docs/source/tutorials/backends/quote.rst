``animedex quote``
==================

The Quote backend wraps AnimeChan's anonymous quote API. The free tier is intentionally small, so high-level commands use the existing SQLite cache by default; repeat calls that hit the cache return before the token bucket and do not consume a live request.

.. image:: /_static/gifs/quote.gif
   :alt: animedex quote demo — cached random quote, Saitama quotes, anime information
   :align: center

References
----------

================================ =====================================
API documentation                https://animechan.io/docs
Authentication and limits        https://animechan.io/docs/auth
Python module                    :mod:`animedex.backends.quote`
Rich models                      :mod:`animedex.backends.quote.models`
================================ =====================================

* **Backend**: AnimeChan (``api.animechan.io/v1``).
* **Rate limit**: 5 requests per hour on the anonymous free tier, confirmed from the official docs on 2026-05-09 UTC.
* **Auth**: not needed for the free anonymous endpoints that animedex exposes here.
* **Cache**: enabled by default for high-level commands. Pass ``--no-cache`` only when the user explicitly needs a fresh live result.

Random Quotes — :func:`~animedex.backends.quote.random`
-------------------------------------------------------

``random`` returns one quote:

.. code-block:: bash

   animedex quote random --jq '{quote: .content, anime: .anime.name, character: .character.name}'
   # => {
   #      "quote": "Become strong not just for your own sake, but for your friends.",
   #      "anime": "Bleach",
   #      "character": "Kurosaki Ichigo"
   #    }

Filter variants use AnimeChan's documented query parameters:

.. code-block:: bash

   animedex quote random-by-anime Naruto --jq '{quote: .content, character: .character.name}'
   animedex quote random-by-character Saitama --jq '{quote: .content, anime: .anime.name}'

Quote Lists — :func:`~animedex.backends.quote.quotes_by_anime`
--------------------------------------------------------------

The list endpoints return one page of five quote records:

.. code-block:: bash

   animedex quote quotes-by-anime Naruto --page 1 --jq '[.[].character.name]'
   animedex quote quotes-by-character Saitama --jq '.[0] | {quote: .content, anime: .anime.name, character: .character.name}'
   # => {"quote": "Prophecies don't ever come true.", "anime": "One Punch Man", "character": "Saitama"}

Use ``--page`` when the user asks for another page. Do not loop through pages speculatively on the anonymous tier; five live requests exhaust the hourly free budget.

Anime Information — :func:`~animedex.backends.quote.anime`
----------------------------------------------------------

AnimeChan also exposes anime metadata by ID or name. ID lookup is more precise:

.. code-block:: bash

   animedex quote anime 188 --jq '{id, name, episodeCount}'
   # => {"id": 188, "name": "One Punch Man", "episodeCount": 12}

Endpoint Summary
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Command
     - Python entry point
     - Purpose
   * - ``random``
     - :func:`animedex.backends.quote.random`
     - one random quote
   * - ``random-by-anime <title>``
     - :func:`animedex.backends.quote.random_by_anime`
     - one random quote filtered by anime title
   * - ``random-by-character <name>``
     - :func:`animedex.backends.quote.random_by_character`
     - one random quote filtered by character name
   * - ``quotes-by-anime <title>``
     - :func:`animedex.backends.quote.quotes_by_anime`
     - one paginated quote list filtered by anime title
   * - ``quotes-by-character <name>``
     - :func:`animedex.backends.quote.quotes_by_character`
     - one paginated quote list filtered by character name
   * - ``anime <identifier>``
     - :func:`animedex.backends.quote.anime`
     - AnimeChan anime information by ID or name

Cross-Source Projection
-----------------------

The rich :class:`~animedex.backends.quote.models.AnimeChanQuote` projects onto :class:`~animedex.models.quote.Quote` via :meth:`~animedex.backends.quote.models.AnimeChanQuote.to_common`. The projection maps ``content`` to ``text`` and carries nested anime and character names when present.

Gotchas
-------

* **Cache first, rate limit second**: the dispatcher checks the cache before acquiring a Quote token. Cached high-level calls do not spend the hourly quota.
* **Use ``--no-cache`` sparingly**: it is a normal transport option, not a safety prompt, but it forces a live request.
* **Fixture capture should be paced**: ``tools/fixtures/run_quote.py`` documents a conservative capture cadence for extending the fixture corpus.

The :doc:`../python_library` page covers the same surface from inside Python.
