``animedex nekos``
==================

nekos.best v2 is a curated **SFW** image / GIF API. animedex wraps
its three JSON-emitting endpoints as four high-level commands. The
collection is split into ~60 categories of which roughly half are
PNG portraits (``husbando``, ``neko``, ``waifu``, ``kitsune``,
``kemonomimi``, …) and the rest are GIF reactions (``baka``,
``cuddle``, ``hug``, ``kiss``, ``laugh``, …).

.. image:: /_static/gifs/nekos.gif
   :alt: animedex nekos demo — categories, image fetch, search, projection
   :align: center

References
----------

================================ =====================================
Site                             https://nekos.best/
API documentation                https://docs.nekos.best/
v2 endpoint reference            https://docs.nekos.best/getting-started/api-endpoints.html
Python module                    :mod:`animedex.backends.nekos`
Rich models                      :mod:`animedex.backends.nekos.models`
================================ =====================================

* **Backend**: nekos.best v2.
* **Rate limit**: 200 req/min anonymous, visible in the
  ``x-rate-limit-limit`` and ``x-rate-limit-remaining`` response
  headers. The transport applies a 3 req/sec sustained ceiling with
  a 10-token burst budget to stay comfortably under the cap.
* **Auth**: never. The collection is fully anonymous.
* **NSFW**: none. v2 dropped the NSFW tier; every record's
  cross-source projection sets ``rating='g'`` unconditionally.

Discover the catalogue — :func:`~animedex.backends.nekos.categories`
--------------------------------------------------------------------

The alphabetised list of category names. The TTY render is one name
per line (no ``[src: …]`` marker because the result is a plain
``list[str]``):

.. code-block:: bash

   animedex nekos categories | head
   # baka
   # bite
   # blush
   # bored
   # cry
   # cuddle
   # ...

   animedex nekos categories --json | jq 'length'
   # 60   (or however many categories nekos.best v2 currently exposes)

Per-category format — :func:`~animedex.backends.nekos.categories_full`
----------------------------------------------------------------------

Same data, plus the asset format (``"png"`` / ``"gif"``) per category:

.. code-block:: bash

   animedex nekos categories-full --json --jq '."husbando"'
   # => {
   #      "format": "png"
   #    }

   # Filter to GIF categories only:
   animedex nekos categories-full --json \
     --jq 'with_entries(select(.value.format == "gif")) | keys'
   # => ["baka", "bite", "blush", "bored", ...]

Fetch random images — :func:`~animedex.backends.nekos.image`
------------------------------------------------------------

``image <category> [--amount N]`` returns ``N`` random rows from the
named category (``1 <= N <= 20``):

.. code-block:: bash

   animedex nekos image husbando --jq '.[0] | {url, artist: .artist_name, source_url}'
   # => {
   #      "url":        "https://nekos.best/api/v2/husbando/<uuid>.png",
   #      "artist":     "<artist name>",
   #      "source_url": "<gallery URL>"
   #    }

   animedex nekos image neko --amount 3 --jq '[.[].url]'
   # => [
   #      "https://nekos.best/api/v2/neko/<uuid>.png",
   #      "https://nekos.best/api/v2/neko/<uuid>.png",
   #      "https://nekos.best/api/v2/neko/<uuid>.png"
   #    ]

   # GIF-format category — the asset URL ends in .gif
   animedex nekos image baka --jq '.[0].url'
   # => "https://nekos.best/api/v2/baka/<uuid>.gif"

Each row carries ``url``, ``dimensions`` (``width`` × ``height`` in
pixels), and best-effort attribution (``anime_name`` /
``artist_name`` / ``artist_href`` / ``source_url``).

Metadata search — :func:`~animedex.backends.nekos.search`
---------------------------------------------------------

``search <query> [--type 1|2] [--category <name>] [--amount N]``
matches the query against ``anime_name`` / ``artist_name`` /
``source_url``:

.. code-block:: bash

   animedex nekos search "Frieren" --amount 3 --jq '[.[].source_url]'

   # GIF results only (type=2):
   animedex nekos search "Frieren" --type 2 --amount 3 --jq '.[].url'

   # Restrict to one category:
   animedex nekos search "Frieren" --category husbando --amount 5

**Important**: ``/search`` is fuzzy. The upstream **always returns up
to ``amount`` results**, falling through to a near-random ranking
when nothing closely matches — so callers cannot rely on an empty
result list as a "no match" signal. Treat low-similarity results as
hints, not as positives.

Endpoint summary
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Command
     - Python entry point
     - Purpose
   * - ``categories``
     - :func:`animedex.backends.nekos.categories`
     - list every category name (alphabetised)
   * - ``categories-full``
     - :func:`animedex.backends.nekos.categories_full`
     - list categories with per-category format metadata
   * - ``image <category>``
     - :func:`animedex.backends.nekos.image`
     - random images / GIFs from one category
   * - ``search <query>``
     - :func:`animedex.backends.nekos.search`
     - fuzzy metadata search across all categories

Cross-source projection
-----------------------

The rich :class:`~animedex.backends.nekos.models.NekosImage` projects
onto the cross-source :class:`~animedex.models.art.ArtPost` shape
(also used for Danbooru and Waifu.im records) via
:meth:`~animedex.backends.nekos.models.NekosImage.to_common`. The
projection is deterministic:

* ``rating`` → always ``"g"`` (v2 is SFW-only).
* ``id`` → ``"nekos:<filename>"`` derived from the asset URL
  (nekos.best has no numeric ID column).
* ``tags`` → ``[anime_name]`` when present, else empty list.
* ``width`` / ``height`` → propagated from the upstream's
  ``dimensions`` block.

This makes it trivial to dedupe nekos images alongside Danbooru posts
in a downstream pipeline:

.. code-block:: python

   from animedex.backends.nekos import image
   for img in image("husbando", amount=5):
       common = img.to_common()
       print(common.id, common.rating, common.url)

Gotchas
-------

* **Headers-only direct-asset retrieval**: the v2 endpoint
  ``/<category>/<filename>.<format>`` returns the raw asset bytes
  with metadata in URL-encoded HTTP headers. animedex's high-level
  layer does not surface this — pass through via ``animedex api
  nekos /<category>/<filename>.<format>`` if you need the bytes.
* **Rate ceiling visible in headers**: every response carries
  ``x-rate-limit-remaining`` so you can budget calls explicitly.
* **No content filter is needed at the agent layer**. The
  Agent-Guidance block on every nekos subcommand notes this so an
  LLM agent shelling out does not redundantly apply a SFW filter on
  top of an already-SFW collection.

The :doc:`../python_library` page covers the same surface from
inside Python.
