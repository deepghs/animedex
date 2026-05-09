``animedex ann``
================

Anime News Network's encyclopedia API is XML-only. animedex parses that XML through the generic adapter in :mod:`animedex.render.xml`, then validates ANN-specific rich models that preserve warning rows, attributes, text, child order, and repeated tags.

.. image:: /_static/gifs/ann.gif
   :alt: animedex ann demo — show, search, reports, warning response
   :align: center

References
----------

================================ =====================================
Site                             https://www.animenewsnetwork.com/
API documentation                https://www.animenewsnetwork.com/encyclopedia/api.php
Browsable encyclopedia           https://www.animenewsnetwork.com/encyclopedia/
Python module                    :mod:`animedex.backends.ann`
Rich models                      :mod:`animedex.backends.ann.models`
XML adapter                      :mod:`animedex.render.xml`
================================ =====================================

* **Backend**: ANN Encyclopedia via ``cdn.animenewsnetwork.com``.
* **Rate limit**: 1 req/sec on ``api.xml``; ``nodelay.api.xml`` allows 5 reqs/5sec but returns 503 on overshoot.
* **Auth**: never required.

Core lookups
------------

Anime by ANN ID — :func:`~animedex.backends.ann.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex ann show 38838 --jq '.anime[0] | {id, name, type}'
   # => {
   #      "id": "38838",
   #      "name": "Frieren: Beyond Journey's End",
   #      "type": "TV"
   #    }

Title substring search — :func:`~animedex.backends.ann.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex ann search Frieren --jq '[.anime[] | {id, name}]'

The search command uses ANN's ``?anime=~substring`` parameter. The ``?title=`` parameter is for ID aliasing, not fuzzy title search.

Curated reports — :func:`~animedex.backends.ann.reports`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex ann reports --id 155 --type anime --nlist 2 --jq '.items[].fields.name'

Warnings are data
-----------------

ANN can return HTTP 200 with a ``<warning>`` element for empty results. animedex keeps that as a typed ``warnings`` list and does not raise an error:

.. code-block:: bash

   animedex ann show 99999999 --jq '{warnings, anime}'
   # => {
   #      "warnings": ["no result for anime=99999999"],
   #      "anime": []
   #    }

Endpoint summary
----------------

============================== ============================================================================ =================================================================
Command                        Python entry point                                                           Returns
============================== ============================================================================ =================================================================
``show <anime_id>``            :func:`animedex.backends.ann.show`                                            :class:`~animedex.backends.ann.models.AnnAnimeResponse`
``search <q>``                 :func:`animedex.backends.ann.search`                                          :class:`~animedex.backends.ann.models.AnnAnimeResponse`
``reports``                    :func:`animedex.backends.ann.reports`                                         :class:`~animedex.backends.ann.models.AnnReport`
============================== ============================================================================ =================================================================

Use ``animedex api ann`` when you need the raw XML envelope or a lower-level endpoint variation:

.. code-block:: bash

   animedex api ann '/api.xml?anime=38838'
   animedex api ann '/reports.xml?id=155&type=anime&nlist=5'

The :doc:`../python_library` page covers the same surface from inside Python.
