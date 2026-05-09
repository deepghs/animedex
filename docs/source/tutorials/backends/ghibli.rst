``animedex ghibli``
===================

The Ghibli backend is a bundled, offline snapshot of the public Studio Ghibli API. High-level commands read ``animedex/data/ghibli.json`` directly, so they are deterministic, do not need network access, and do not consume upstream capacity. The raw ``animedex api ghibli`` passthrough remains available when a caller explicitly wants the live mirror.

.. image:: /_static/gifs/ghibli.gif
   :alt: animedex ghibli demo — films, people, species, vehicles
   :align: center

References
----------

================================ =====================================
Live API                         https://ghibliapi.vercel.app/
Source repository                https://github.com/janismdhanbad/studio-ghibli-api
Python module                    :mod:`animedex.backends.ghibli`
Rich models                      :mod:`animedex.backends.ghibli.models`
================================ =====================================

* **Backend**: Studio Ghibli API snapshot bundled with animedex.
* **Rate limit**: not applicable for high-level commands; reads are local file reads.
* **Auth**: never. The live mirror and bundled snapshot are anonymous read-only data.
* **Snapshot**: captured on 2026-05-09 UTC from ``https://ghibliapi.vercel.app/{films,people,locations,species,vehicles}``.

Films — :func:`~animedex.backends.ghibli.films`
------------------------------------------------

``films`` lists the 22 bundled film records in snapshot order and supports local filters:

.. code-block:: bash

   animedex ghibli films --director "Hayao Miyazaki" --min-rt-score 95 --jq 'map(.title)'
   # => ["Castle in the Sky", "Kiki's Delivery Service", "Spirited Away"]

   animedex ghibli film 2baf70d1-42bb-4437-b551-e5fed5a87abe --jq '{title, director, rt_score}'
   # => {"title": "Castle in the Sky", "director": "Hayao Miyazaki", "rt_score": "95"}

Film records project to the cross-source :class:`~animedex.models.anime.Anime` shape via :meth:`animedex.backends.ghibli.models.GhibliFilm.to_common`, carrying the Ghibli UUID in ``ids["ghibli"]`` and the Rotten Tomatoes score as a ``0..100`` rating.

People — :func:`~animedex.backends.ghibli.people`
-------------------------------------------------

``people`` lists character/person records and accepts a positional optional name filter plus ``--gender``, ``--film-id``, and ``--species-id``:

.. code-block:: bash

   animedex ghibli people Haku --jq '.[0] | {name, age, eye_color, source: .source_tag.backend}'
   # => {"name": "Haku", "age": "12", "eye_color": "Green", "source": "ghibli"}

   animedex ghibli person 267649ac-fb1b-11eb-9a03-0242ac130003 --jq '{name, gender, films}'

People project to :class:`~animedex.models.character.Character` via :meth:`animedex.backends.ghibli.models.GhibliPerson.to_common`.

Locations, Species, And Vehicles
--------------------------------

The remaining snapshot families are exposed as rich, lossless models:

.. code-block:: bash

   animedex ghibli locations --terrain forest --jq 'map(.name)'
   animedex ghibli species --jq '[.[].name]'
   # => ["Human", "Deer", "Spirit", "God", "Cat", "Totoro", "Dragon"]

   animedex ghibli vehicles --jq '[.[].name]'
   # => ["Air Destroyer Goliath", "Red Wing", "Sosuke's Boat"]

Endpoint Summary
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Command
     - Python entry point
     - Purpose
   * - ``films``
     - :func:`animedex.backends.ghibli.films`
     - list film records with local filters
   * - ``film <film_id>``
     - :func:`animedex.backends.ghibli.film`
     - return one film by Studio Ghibli API UUID
   * - ``people [name]``
     - :func:`animedex.backends.ghibli.people`
     - list people with local filters
   * - ``person <person_id>``
     - :func:`animedex.backends.ghibli.person`
     - return one person by UUID
   * - ``locations``
     - :func:`animedex.backends.ghibli.locations`
     - list location records
   * - ``location <location_id>``
     - :func:`animedex.backends.ghibli.location`
     - return one location by UUID
   * - ``species``
     - :func:`animedex.backends.ghibli.species`
     - list species records
   * - ``species-by-id <species_id>``
     - :func:`animedex.backends.ghibli.species_by_id`
     - return one species by UUID
   * - ``vehicles``
     - :func:`animedex.backends.ghibli.vehicles`
     - list vehicle records
   * - ``vehicle <vehicle_id>``
     - :func:`animedex.backends.ghibli.vehicle`
     - return one vehicle by UUID

Gotchas
-------

* **The high-level backend is intentionally offline**. Use ``animedex api ghibli /films`` only when the user asks for live upstream data.
* **The public mirror is a frozen community data set**. The snapshot reflects the mirror's shape and contents at capture time; it is not a complete filmography database.
* **Source attribution still applies**. TTY rows render ``[src: ghibli]`` and JSON includes the source tag metadata even though the data came from a local file.

The :doc:`../python_library` page covers the same surface from inside Python.
