``animedex waifu``
==================

Waifu.im is a tagged anime art collection hosted at
``https://api.waifu.im``. It returns a single image (or paginated
list) along with rich tag / artist / dimension metadata. animedex
covers **9 anonymous endpoints** plus **1 authenticated read endpoint**
as 10 high-level Python functions.

.. image:: /_static/gifs/waifu.gif
   :alt: animedex waifu demo — tags, images, artist
   :align: center

References
----------

================================ =====================================
Site                             https://www.waifu.im/
API documentation                https://docs.waifu.im/
Python module                    :mod:`animedex.backends.waifu`
Rich models                      :mod:`animedex.backends.waifu.models`
================================ =====================================

* **Backend**: Waifu.im (api.waifu.im).
* **Rate limit**: not formally published; transport applies a 10
  req/sec ceiling.                                                    
* **Auth**: optional. The ``/users/me`` endpoint needs an
  ``X-Api-Key`` header (note: **n ot** Bearer). Get a personal API     
  key from https://www.waifu.im/d ashboard after signing in with       
  Discord.                                                            

NSFW posture
------------

Waifu.im serves both SFW and NSFW images. The ``/images`` endpoint
defaults to SFW only when the ``isNsfw`` query parameter is omitted;
animedex mirrors this:

* ``--is-nsfw`` is **not** passed by default. The upstream applies
  its SFW-only default.                                               
* Pass ``--is-nsfw true`` to return NSFW only.
* Pass ``--is-nsfw false`` to be explicit about SFW only.
* Each result row carries ``.isNsfw`` so downstream pipelines can
  re-filter.                                                          

The flag is a transparent passthrough — animedex never gates or
warns. See the project README's "Human Agency Principle" section.

Five endpoints, in detail
-------------------------

Tag catalogue — :func:`~animedex.backends.waifu.tags`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex waifu tags --jq '.[] | {slug, imageCount}'                
   # => [{"slug": "waifu", "image Count": 4249}, ...]                  

Tag by slug — :func:`~animedex.backends.waifu.tag_by_slug`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex waifu tag-by-slug wai fu --jq '.description'               

Image search (SFW default) — :func:`~animedex.backends.waifu.images`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex waifu images --includ ed-tags waifu --page-size 3 \        
     --jq '.[] | {id, url, isNsfw }'                                   

Image search (NSFW opt-in) — :func:`~animedex.backends.waifu.images`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex waifu images --is-nsf w true --page-size 3 --jq '.[].url'  

Catalogue stats — :func:`~animedex.backends.waifu.stats_public`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex waifu stats-public -- jq '{totalImages, totalTags, totalArtists}'
   # => {"totalImages": 4287, "to talTags": 19, "totalArtists": 568}   

Authenticated endpoints
-----------------------

The ``/users/me`` endpoint needs an ``X-Api-Key`` header. Provide
via:

.. code-block:: bash

   # Per-call (CLI):                                                  
   animedex waifu me --token "<yo ur-api-key>"                         

   # Per-shell (env var):                                             
   export ANIMEDEX_WAIFU_TOKEN="< your-api-key>"                       
   animedex waifu me                                                  

Authenticated walkthrough
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Current user — :func:`~animedex.backends.waifu.me`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   animedex waifu me --jq '{name,  role, requestCount}'                

Endpoint summary
----------------

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``tags``                         :func:`animedex.backends.waifu.tags`                                         ``list[WaifuTag]``
``tag <id>``                     :func:`animedex.backends.waifu.tag`                                          :class:`~animedex.backends.waifu.models.WaifuTag`
``tag-by-slug <slug>``           :func:`animedex.backends.waifu.tag_by_slug`                                  :class:`~animedex.backends.waifu.models.WaifuTag`
``artists``                      :func:`animedex.backends.waifu.artists`                                      ``list[WaifuArtist]``
``artist <id>``                  :func:`animedex.backends.waifu.artist`                                       :class:`~animedex.backends.waifu.models.WaifuArtist`
``artist-by-name <name>``        :func:`animedex.backends.waifu.artist_by_name`                               :class:`~animedex.backends.waifu.models.WaifuArtist`
``images``                       :func:`animedex.backends.waifu.images`                                       ``list[WaifuImage]``
``image <id>``                   :func:`animedex.backends.waifu.image`                                        :class:`~animedex.backends.waifu.models.WaifuImage`
``stats-public``                 :func:`animedex.backends.waifu.stats_public`                                 :class:`~animedex.backends.waifu.models.WaifuStats`
``me``                           :func:`animedex.backends.waifu.me`                                           :class:`~animedex.backends.waifu.models.WaifuUser`
================================ ============================================================================ =================================================================

Pagination
----------

Waifu.im paginates with ``?pageNumber=N&pageSize=M``. The high-level
helpers expose ``page_number`` / ``page_size`` kwargs:

.. code-block:: bash

   animedex waifu artists --page- size 5                                                                                                                                        
   animedex waifu artists --page- size 5 --page-number 2                                                                                                                        

Gotchas
-------

* **The auth header is ``X-Api-Key``, not Bearer**: the upstream
  rejects ``Authorization: Bearer  ...`` for personal API keys. The                                                                                                             
  high-level helper sets the righ t header automatically; the raw                                                                                                               
  passthrough at ``animedex api w aifu`` requires the caller to set                                                                                                             
  the header themselves.                                                                                                                                                       
* **Cloudflare bot heuristics are dynamic**: high-volume probing
  from a single IP can trigger a 403 HTML "Access Denied" page. If                                                                                                             
  you see the upstream returning HTML rather than JSON, throttle                                                                                                               
  and back off.                                                                                                                                                                
* **The ``/fav/`` endpoint is GET-form write**: bookmarking an
  image is exposed as ``GET /fav/ insert?id=<id>`` upstream — animedex                                                                                                          
  does not wire this because it's  a write operation against a user                                                                                                             
  account (out-of-scope per read- only-by-scope).                                                                                                                               
* **Tag list pagination is undersized by default**: the upstream's
  ``totalCount`` for ``/tags`` is  ~19 but ``defaultPageSize`` is 30,                                                                                                           
  so a single ``animedex waifu ta gs`` call returns the entire taxonomy.                                                                                                        

The :doc:`../python_library` page covers the same surface from
inside Python.
