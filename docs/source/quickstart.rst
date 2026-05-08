Quickstart
==========

Five progressive examples that take you from "I just installed
animedex" to "I have automation that uses it as a Python library."
Each example is runnable as-is; each shows the actual output you
should see.

.. image:: _static/gifs/quickstart.gif
   :alt: animedex quickstart walkthrough — help, anilist show, nekos image
   :align: center

Install
-------

.. code-block:: bash

   pip install -e .
   animedex --version

The version banner prints two lines: the package title plus version,
then a build-info summary (commit short hash + ``built …`` timestamp
for a frozen binary, or the literal sentinel ``build info not
generated`` for a fresh checkout).

Step 1 — A first lookup
-----------------------

Pull AniList's record for *Sousou no Frieren* (AniList ID ``154587``).
The default output mode is human-readable when stdout is a terminal,
and JSON when piped:

.. code-block:: bash

   animedex anilist show 154587

You should see a multi-line block beginning with the romaji title, the
season year, and the score, each line carrying ``[src: anilist]``. The
``[src: …]`` marker is the project's promise that nothing on screen is
"merged from somewhere we won't tell you about" — every datum names
its origin.

Step 2 — Project a single field with ``--jq``
---------------------------------------------

When you only want one field, the bundled jq wheel filters the JSON
output. ``--jq`` forces JSON mode and applies the expression:

.. code-block:: bash

   animedex anilist show 154587 --jq '.title.romaji'
   # => "Sousou no Frieren"

   animedex anilist show 154587 --jq '{romaji: .title.romaji, year: .seasonYear, score: .averageScore}'
   # => {
   #      "romaji": "Sousou no Frieren",
   #      "year":   2023,
   #      "score":  90
   #    }

The wheel ships with the package — no host ``jq`` binary required, no
PATH lookup, no platform drift. A bad expression surfaces as a clean
``ApiError`` with a typed reason, not a Python traceback.

Step 3 — Cross the same anime against Jikan
-------------------------------------------

The same show has a different MyAnimeList ID (``52991``). Fetching it
via Jikan gives you the deeper catalogue (broadcast schedule,
streaming links, theme songs):

.. code-block:: bash

   animedex jikan show 52991 --jq '.data.title'
   # => "Sousou no Frieren"

   animedex jikan show 52991 --jq '.data | {title, score, status, broadcast}'

You now have two **independent** sources for the same show, each
source-attributed. There is no merging step that picks one and hides
the other; if AniList's score and Jikan's score disagree, both are
visible. The :doc:`tutorials/output_modes` page covers the JSON
projection rules in detail.

Step 4 — Discover the SFW art collection
----------------------------------------

nekos.best v2 is a curated SFW image / GIF API. Start with the
category list, then pull a few images:

.. code-block:: bash

   animedex nekos categories | head
   # baka
   # bite
   # blush
   # bored
   # cry
   # cuddle
   # ...

   animedex nekos image husbando --jq '.[0].url'
   # => "https://nekos.best/api/v2/husbando/<uuid>.png"

   animedex nekos search "Frieren" --amount 5 --jq '.[].source_url'

Caveat: ``nekos search`` is fuzzy. The upstream always returns up to
``amount`` results, falling through to a near-random ranking when
nothing closely matches — so callers cannot rely on an empty result
list as a "no match" signal.

Step 5 — Use animedex as a Python library
-----------------------------------------

The CLI is a thin presentation layer over an installable package.
Anything you can do at the prompt is one ``from animedex.backends.X
import …`` away:

.. code-block:: python

   from animedex.backends import anilist, jikan, nekos

   a = anilist.show(154587)
   print(a.title.romaji, a.season_year, a.average_score, a.source.backend)
   # Sousou no Frieren 2023 90 anilist

   m = jikan.show(52991)
   print(m.title, m.score, m.source_tag.backend)
   # Sousou no Frieren 9.31 jikan

   for img in nekos.image("husbando", amount=3):
       print(img.url, img.artist_name, img.source_tag.backend)

Each function accepts an optional ``config: Config`` keyword and
forwards transport-level keyword arguments (``no_cache``, ``rate``,
``timeout_seconds``, …) — see :doc:`tutorials/python_library` for
the complete contract.

Where to go next
----------------

* :doc:`tutorials/index` — systematic tutorials per backend, per
  output mode, the raw passthrough, the Python library, and the
  ``--agent-guide`` flag.
* :doc:`api_doc/index` — auto-generated reference for every public
  module, class, and function.
