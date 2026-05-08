``animedex trace``
==================

Trace.moe identifies an anime scene from a screenshot or short clip
and returns the matching show, episode, and timestamp. It is hosted
at ``https://api.trace.moe`` and exposes two anonymous endpoints
that animedex wraps as ``trace search`` and ``trace quota``.

* **Backend**: Trace.moe (api.trace.moe).
* **Rate limit**: anonymous concurrency 1, **quota 100 / month**
  (down from the older 1000 / month tier — the upstream tightened
  in 2025). The per-call quota cost surfaces in
  ``trace quota``.
* **Auth**: anonymous tier covers everyday use; authenticated tiers
  raise the quota and are not yet wired into animedex.

Identify a scene
----------------

Two input shapes:

**By URL** — pass a publicly fetchable image URL via ``--url``:

.. code-block:: bash

   animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info \
     --jq '.[0] | {anime: .anilist.title.romaji, episode, time: .from}'
   # => {
   #      "anime":   "Moonlight Mile",
   #      "episode": 4,
   #      "time":    367.99
   #    }

**By upload** — pass image bytes via ``--input <path>`` (or ``-`` for
stdin):

.. code-block:: bash

   animedex trace search --input ./screenshot.jpg --anilist-info
   cat screenshot.jpg | animedex trace search --input -

The ``--anilist-info`` flag inlines the matching AniList Media on each
hit, so you can chain into ``animedex anilist show`` without an extra
round-trip.

The result is a list of hits sorted by similarity (highest first).
Each hit carries ``anilist`` (numeric ID + optional inlined Media),
``episode``, ``from`` / ``to`` timestamps, ``similarity`` (0..1), and
preview asset URLs.

Quota check
-----------

.. code-block:: bash

   animedex trace quota
   # Trace.moe quota  [src: trace]
   #   Tier priority:    0  (anonymous)
   #   Concurrency:      1
   #   Used / quota:     5 / 100  (5.0% used)
   #   Remaining:        95

The TTY rendering uses the cross-source ``TraceQuota`` projection
which **does not surface the upstream's ``id`` field**. The reason:
``id`` on ``/me`` is the caller's egress IP, which is the caller's
own datum but not something the project surfaces by default. The
rich shape ``RawTraceQuota`` carries it for callers who want it
(``model_dump(by_alias=True)`` round-trips losslessly).

Crossing into AniList
---------------------

A typical workflow:

1. Take a screenshot of an anime scene.
2. ``animedex trace search --input scene.png --anilist-info``.
3. Pull the AniList ID from the top hit.
4. ``animedex anilist show <id>`` for the full show metadata.

With ``--anilist-info`` set, step 3 is essentially free — the AniList
title is inlined.

Gotchas
-------

* **Quota is shared with anyone on the same egress IP**. A shared NAT
  or a busy office network may already have spent the daily allowance
  before you start; ``trace quota`` is the cheap (no-quota-cost)
  check.
* **Concurrency 1**: don't run ``trace search`` in parallel.
  animedex's per-backend rate-limit bucket caps concurrency at 1
  automatically; if you bypass the CLI and hit the API directly,
  obey the same cap.
* **Public-image-URL caveat**: ``--url`` requires the image to be
  fetchable by Trace.moe's servers. If your image is on a host that
  blocks data-centre egress, upload via ``--input`` instead.

The :doc:`../python_library` page covers the same surface from
inside Python.
