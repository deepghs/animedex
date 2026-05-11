:orphan:

``animedex season`` and ``animedex schedule``
=============================================

The calendar aggregate commands fan out to AniList and Jikan, keep successful rows even when one source fails, and preserve source attribution in both JSON and TTY output.

.. image:: /_static/gifs/aggregate.gif
   :alt: animedex aggregate demo - season and schedule with fallback
   :align: center

Examples
--------

Seasonal listings
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex season 2024 spring --json --jq '.items[0] | {title: .title.romaji, sources: (.sources | map(.backend))}'
   # => {"title":"Kaijuu 8-gou","sources":["anilist","jikan"]}

   animedex season 2024 spring --source jikan --limit 3 --json --jq '[.items[].title.romaji]'
   # => ["Kimetsu no Yaiba: Hashira Geiko-hen", "Kaijuu 8-gou", "Mushoku Tensei II: Isekai Ittara Honki Dasu Part 2"]

Weekly schedule
~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex schedule --day monday --source jikan --timezone Asia/Tokyo --json --jq '.items[0] | {title, weekday, time: .local_time}'
   # => {"title":"Shin Nippon History","weekday":"monday","time":"01:00"}

   animedex schedule --day monday --source jikan --timezone +08:00 --limit 3
   # Schedule (+08:00)
   # Window: 2026-05-11 to 2026-05-12 (exclusive)
   #
   # Monday, 2026-05-11
   #   00:00  Shin Nippon History  [src: jikan]
   #   17:25  Puzzle & Dragon  [src: jikan]

Partial failure
~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex season 2024 spring --limit 3 --json
   # source 'anilist' failed: rate-limited (HTTP 429); continuing with other sources
   # {"items":[...],"sources":{"anilist":{"backend":"anilist","status":"failed"},"jikan":{"backend":"jikan","status":"ok"}},"_meta":{"sources_consulted":["jikan"]}}

The failure line appears on stderr, while stdout stays a valid aggregate envelope. That is intentional: the command degrades visibly instead of refusing to return the healthy source's rows.

Notes
-----

* ``season`` defaults to the AniList/MAL quarterly convention: winter = January-March, spring = April-June, summer = July-September, fall = October-December, and the merge path now combines likely identical AniList/Jikan rows into one item with per-backend records.
* ``schedule`` uses ``--day all`` as the seven-day window starting today in the selected timezone, defaulting to local.
* The JSON envelope keeps both successful rows and per-source status entries.
