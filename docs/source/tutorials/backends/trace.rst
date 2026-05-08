``animedex trace``
==================

Trace.moe identifies an anime scene from a screenshot or short clip
and returns the matching show, episode, and timestamp. animedex
wraps its two anonymous endpoints as the ``trace search`` and
``trace quota`` subcommands.

.. image:: /_static/gifs/trace.gif
   :alt: animedex trace demo — quota check, URL search, similarity projection
   :align: center

References
----------

================================ =====================================
Site                             https://trace.moe/
API documentation                https://soruly.github.io/trace.moe-api/
Project repo                     https://github.com/soruly/trace.moe-api
Python module                    :mod:`animedex.backends.trace`
Rich models                      :mod:`animedex.backends.trace.models`
================================ =====================================

* **Backend**: Trace.moe (api.trace.moe).
* **Rate limit**: anonymous concurrency 1, **quota 100 / month**
  (down from the older 1000 / month tier — the upstream tightened
  in 2025). Per-call cost surfaces in ``trace quota``.
* **Auth**: anonymous tier covers everyday use; authenticated tiers
  raise the quota and are not yet wired into animedex.

Identify a scene — :func:`~animedex.backends.trace.search`
----------------------------------------------------------

Two input shapes:

**By URL** — pass a publicly fetchable image URL via ``--url``:

.. code-block:: bash

   animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info \
     --jq '.[0] | {anime: .anilist_title.romaji, episode, time: .start_at_seconds}'
   # => {
   #      "anime":   "Moonlight Mile",
   #      "episode": 4,
   #      "time":    367.99
   #    }

**By upload** — pass image bytes via ``--input <path>`` (or ``-`` for
stdin):

.. code-block:: bash

   animedex trace search --input ./screenshot.jpg --anilist-info \
     --jq '.[0].anilist_title.romaji'

   cat screenshot.jpg | animedex trace search --input - --anilist-info

The ``--anilist-info`` flag inlines the matching AniList Media on
each hit, so you can chain into ``animedex anilist show`` without an
extra round-trip.

The result is a list of hits sorted by similarity (highest first).
Each hit carries:

The high-level CLI emits the **common-shape**
:class:`~animedex.models.trace.TraceHit` (flat fields, easier to
diff across backends). The rich nested
:class:`~animedex.backends.trace.models.RawTraceHit` is available
to Python callers via :mod:`animedex.api.trace` for upstream-faithful
key names (``from`` / ``to`` / ``video`` / ``image`` / nested
``anilist``).

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field (common shape)
     - Meaning
   * - ``anilist_id``
     - Numeric AniList ID for the matched Media.
   * - ``anilist_title``
     - With ``--anilist-info``: full
       :class:`~animedex.models.anime.AnimeTitle` (``romaji`` /
       ``english`` / ``native``); ``null`` otherwise.
   * - ``episode``
     - Episode number (integer; 0 for movies / OVAs).
   * - ``start_at_seconds`` / ``end_at_seconds``
     - Match window in seconds within the episode.
   * - ``frame_at_seconds``
     - Frame inside the window the upstream considers most diagnostic.
   * - ``episode_filename``
     - Source filename hint (uploader-supplied, often shortened).
   * - ``episode_duration_seconds``
     - Full episode runtime in seconds.
   * - ``similarity``
     - Match confidence, ``0..1``. ``>= 0.85`` is a strong match.
   * - ``preview_video_url``
     - Preview MP4 URL (5-second clip around the match).
   * - ``preview_image_url``
     - Preview thumbnail URL.

Quota check — :func:`~animedex.backends.trace.quota`
----------------------------------------------------

The ``/me`` endpoint costs nothing and is the cheap way to confirm
your tier and budget:

.. code-block:: bash

   animedex trace quota
   # Trace.moe quota  [src: trace]
   #   Tier priority:    0  (anonymous)
   #   Concurrency:      1
   #   Used / quota:     5 / 100  (5.0% used)
   #   Remaining:        95

   animedex trace quota --json --jq '{tier: .priority, used: .quota_used, total: .quota}'
   # => {
   #      "tier":  0,
   #      "used":  5,
   #      "total": 100
   #    }

The TTY rendering uses the cross-source
:class:`~animedex.models.trace.TraceQuota` projection which **does
not surface the upstream's ``id`` field**. The reason: ``id`` on
``/me`` is the caller's egress IP, which is the caller's own datum
but not something the project surfaces by default. The rich shape
:class:`~animedex.backends.trace.models.RawTraceQuota` carries it
for callers who want it (``model_dump(by_alias=True)`` round-trips
losslessly).

Endpoint summary
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Command
     - Python entry point
     - Purpose
   * - ``trace search [--url|--input]``
     - :func:`animedex.backends.trace.search`
     - identify an anime scene from a screenshot, URL or stdin
   * - ``trace quota``
     - :func:`animedex.backends.trace.quota`
     - zero-cost tier / quota check via ``/me``

Crossing into AniList
---------------------

A typical workflow:

1. Take a screenshot of an anime scene.
2. ``animedex trace search --input scene.png --anilist-info``.
3. Pull the AniList ID from the top hit.
4. ``animedex anilist show <id>`` for the full show metadata.

With ``--anilist-info`` set, step 3 is essentially free — the
AniList title is inlined.

Gotchas
-------

* **Quota is shared with anyone on the same egress IP**. A shared
  NAT or a busy office network may already have spent the daily
  allowance before you start; ``trace quota`` is the cheap
  (no-quota-cost) check.
* **Concurrency 1**: don't run ``trace search`` in parallel.
  animedex's per-backend rate-limit bucket caps concurrency at 1
  automatically; if you bypass the CLI and hit the API directly,
  obey the same cap.
* **Public-image-URL caveat**: ``--url`` requires the image to be
  fetchable by Trace.moe's servers. If your image is on a host that
  blocks data-centre egress, upload via ``--input`` instead.

The :doc:`../python_library` page covers the same surface from
inside Python.
