:orphan:

``animedex season`` and ``animedex schedule``
=============================================

The calendar aggregate commands fan out to AniList and Jikan, keep successful rows even when one source fails, and preserve source attribution in both JSON and TTY output.

.. image:: /_static/gifs/aggregate.gif
   :alt: animedex aggregate demo — season and schedule with fallback
   :align: center

Examples
--------

Seasonal listings
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex season 2024 spring --source jikan --limit 3 --json --jq '{count: (.items | length), sources: ._meta.sources_consulted}'
   # => {"count":3,"sources":["jikan"]}

   animedex season --source jikan --limit 3 --json --jq '[.items[].title]'
   # => ["Kimetsu no Yaiba: Hashira Geiko-hen", "Kaijuu 8-gou", "Mushoku Tensei II: Isekai Ittara Honki Dasu Part 2"]

Weekly schedule
~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex schedule --day monday --source jikan --limit 1 --json --jq '{title: .items[0].title, weekday: .items[0].weekday, time: .items[0].local_time, sources: ._meta.sources_consulted}'
   # => {"title":"Shin Nippon History","weekday":"monday","time":"01:00","sources":["jikan"]}

   animedex schedule --day monday --source jikan --limit 1
   # Shin Nippon History  [src: jikan]
   #   Schedule: monday  ·  01:00

Partial failure
~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex season 2024 spring --limit 3 --json
   # source 'anilist' failed: rate-limited (HTTP 429); continuing with other sources
   # {"items":[...],"sources":{"anilist":{"backend":"anilist","status":"failed"},"jikan":{"backend":"jikan","status":"ok"}},"_meta":{"sources_consulted":["jikan"]}}

The failure line appears on stderr, while stdout stays a valid aggregate envelope. That is intentional: the command degrades visibly instead of refusing to return the healthy source's rows.

Notes
-----

* ``season`` defaults to the AniList/MAL quarterly convention: winter = January-March, spring = April-June, summer = July-September, fall = October-December.
* ``schedule`` uses ``--day all`` as the seven-day local window starting today.
* The JSON envelope keeps both successful rows and per-source status entries.
