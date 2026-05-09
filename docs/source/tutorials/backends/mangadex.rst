``animedex mangadex``
=====================

MangaDex is a scanlation aggregator hosted at
``https://api.mangadex.org``. It is the **deepest manga
catalogue** the project wraps: every series / chapter / cover /
scanlation group / author / custom list, plus an authenticated
``/user`` surface for the caller's own follows / lists / reading
history. animedex covers **26 anonymous endpoints** plus **13
authenticated read endpoints** as 39 high-level Python functions.

.. image:: /_static/gifs/mangadex.gif
   :alt: animedex mangadex demo — search, show, feed, chapter
   :align: center

References
----------

================================ =====================================
Site                             https://mangadex.org/
API documentation                https://api.mangadex.org/docs/
Auth flow (Personal Client)      https://api.mangadex.org/docs/02-authentication/personal-clients/
Python module                    :mod:`animedex.backends.mangadex`
Rich models                      :mod:`animedex.backends.mangadex.models`
================================ =====================================

* **Backend**: MangaDex (api.mangadex.org).
* **Rate limit**: 5 req/sec anonymous; transport bucket matches.
* **Auth**: optional. Anonymous endpoints work without credentials;
  the ``/user/*`` and ``/manga/*/ status`` surface needs an OAuth2     
  Bearer token via Personal Clien t password grant. See "Authenticated 
  endpoints" below for the exact flow.                                

Six anonymous endpoints, in detail
----------------------------------

Manga by UUID — :func:`~animedex.backends.mangadex.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex show 801513b a-a712-498c-8f57-cae55b38cc92 \      
     --jq '.attributes | {title: .title.en, status, year}'            
   # => {                                                             
   #      "title":  "Berserk",                                        
   #      "status": "ongoing",                                        
   #      "year":   1989                                              
   #    }                                                             

Title search — :func:`~animedex.backends.mangadex.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex search "Bers erk" --limit 3 --jq '.[].attributes.title.en'

Chapter feed — :func:`~animedex.backends.mangadex.feed`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex feed 801513b a-a712-498c-8f57-cae55b38cc92 \      
     --lang en --limit 5 --jq '.[ ].attributes | {chapter, title}'     

One chapter — :func:`~animedex.backends.mangadex.chapter`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex chapter <cha pter-uuid> \                         
     --jq '.attributes | {chapter , title, translatedLanguage, pages}' 

Cover record — :func:`~animedex.backends.mangadex.cover`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex cover <cover -uuid> --jq '.attributes.fileName'   
   # The full image URL is compos ed as                                
   # https://uploads.mangadex.org /covers/<manga-id>/<fileName>        

Random manga — :func:`~animedex.backends.mangadex.random_manga`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex random-manga  --jq '.attributes.title.en'         

Authenticated endpoints
-----------------------

The ``/user/*`` and ``/manga/*/status`` surface requires an OAuth2
Bearer token. MangaDex's Personal Client flow exchanges
``client_id:client_secret:username:password`` for a 15-minute access
token; animedex caches the token in process memory keyed on
``client_id``.

**Setup**

1. Visit https://mangadex.org/settings → API Clients → "Create".
2. Note the ``client_id`` (looks like
   ``personal-client-<uuid>-<suff ix>``) and ``client_secret``.        
3. Provide credentials to animedex via *one* of:

   .. code-block:: bash                                               

      # Per-call (CLI):                                               
      animedex mangadex me --cred s "<client_id>:<client_secret>:<username>:<password>"

      # Per-shell (env var):                                          
      export ANIMEDEX_MANGADEX_CR EDS="<client_id>:<client_secret>:<username>:<password>"
      animedex mangadex me                                            

      # Persistent (token store):                                      
      animedex auth set mangadex \                                    
        "<client_id>:<client_secr et>:<username>:<password>"           
      animedex mangadex me                                            

The four-tuple is colon-separated. The token store goes through the
OS keyring per the project's secret-handling convention.

**Authenticated walkthrough**

Current user — :func:`~animedex.backends.mangadex.me`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex me --jq '.at tributes | {username, roles}'        

My follows — :func:`~animedex.backends.mangadex.my_follows_manga`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex my-follows-m anga --limit 5 \                     
     --jq '.[].attributes.title.e n'                                   

Reading history — :func:`~animedex.backends.mangadex.my_history`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex my-history - -jq '.[]'                            

Read markers per manga — :func:`~animedex.backends.mangadex.my_manga_read_markers`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex mangadex my-manga-rea d-markers \                          
     801513ba-a712-498c-8f57-cae5 5b38cc92 --jq '.[]'                  

Endpoint summary
----------------

Anonymous reads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``search <q>``                   :func:`animedex.backends.mangadex.search`                                    ``list[MangaDexManga]``
``show <id>``                    :func:`animedex.backends.mangadex.show`                                      :class:`~animedex.backends.mangadex.models.MangaDexManga`
``feed <id>``                    :func:`animedex.backends.mangadex.feed`                                      ``list[MangaDexChapter]``
``chapter <id>``                 :func:`animedex.backends.mangadex.chapter`                                   :class:`~animedex.backends.mangadex.models.MangaDexChapter`
``chapter-search``               :func:`animedex.backends.mangadex.chapter_search`                            ``list[MangaDexChapter]``
``cover <id>``                   :func:`animedex.backends.mangadex.cover`                                     :class:`~animedex.backends.mangadex.models.MangaDexCover`
``cover-search``                 :func:`animedex.backends.mangadex.cover_search`                              ``list[MangaDexCover]``
``aggregate <id>``               :func:`animedex.backends.mangadex.aggregate`                                 ``MangaDexResource``
``recommendation <id>``          :func:`animedex.backends.mangadex.recommendation`                            ``list[MangaDexResource]``
``random-manga``                 :func:`animedex.backends.mangadex.random_manga`                              :class:`~animedex.backends.mangadex.models.MangaDexManga`
``manga-tag``                    :func:`animedex.backends.mangadex.manga_tag`                                 ``list[MangaDexResource]``
``author <id>``                  :func:`animedex.backends.mangadex.author`                                    ``MangaDexResource``
``author-search``                :func:`animedex.backends.mangadex.author_search`                             ``list[MangaDexResource]``
``group <id>``                   :func:`animedex.backends.mangadex.group`                                     ``MangaDexResource``
``group-search``                 :func:`animedex.backends.mangadex.group_search`                              ``list[MangaDexResource]``
``list-show <id>``               :func:`animedex.backends.mangadex.list_show`                                 ``MangaDexResource``
``list-feed <id>``               :func:`animedex.backends.mangadex.list_feed`                                 ``list[MangaDexChapter]``
``user <id>``                    :func:`animedex.backends.mangadex.user`                                      ``MangaDexResource``
``user-lists <id>``              :func:`animedex.backends.mangadex.user_lists`                                ``list[MangaDexResource]``
``statistics-manga <id>``        :func:`animedex.backends.mangadex.statistics_manga`                          ``MangaDexResource``
``statistics-manga-batch``       :func:`animedex.backends.mangadex.statistics_manga_batch`                    ``MangaDexResource``
``statistics-chapter <id>``      :func:`animedex.backends.mangadex.statistics_chapter`                        ``MangaDexResource``
``statistics-chapter-batch``     :func:`animedex.backends.mangadex.statistics_chapter_batch`                  ``MangaDexResource``
``statistics-group <id>``        :func:`animedex.backends.mangadex.statistics_group`                          ``MangaDexResource``
``report-reasons <category>``    :func:`animedex.backends.mangadex.report_reasons`                            ``list[MangaDexResource]``
``ping``                         :func:`animedex.backends.mangadex.ping`                                      ``str``
================================ ============================================================================ =================================================================

Authenticated reads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================ ============================================================================ =================================================================
Command                          Python entry point                                                           Returns
================================ ============================================================================ =================================================================
``me``                           :func:`animedex.backends.mangadex.me`                                        :class:`~animedex.backends.mangadex.models.MangaDexUser`
``my-follows-manga``             :func:`animedex.backends.mangadex.my_follows_manga`                          ``list[MangaDexManga]``
``is-following-manga <id>``      :func:`animedex.backends.mangadex.is_following_manga`                        ``bool``
``my-follows-group``             :func:`animedex.backends.mangadex.my_follows_group`                          ``list[MangaDexResource]``
``is-following-group <id>``      :func:`animedex.backends.mangadex.is_following_group`                        ``bool``
``my-follows-user``              :func:`animedex.backends.mangadex.my_follows_user`                           ``list[MangaDexResource]``
``is-following-user <id>``       :func:`animedex.backends.mangadex.is_following_user`                         ``bool``
``my-follows-list``              :func:`animedex.backends.mangadex.my_follows_list`                           ``list[MangaDexResource]``
``my-follows-manga-feed``        :func:`animedex.backends.mangadex.my_follows_manga_feed`                     ``list[MangaDexChapter]``
``my-lists``                     :func:`animedex.backends.mangadex.my_lists`                                  ``list[MangaDexResource]``
``my-history``                   :func:`animedex.backends.mangadex.my_history`                                ``list[MangaDexResource]``
``my-manga-status``              :func:`animedex.backends.mangadex.my_manga_status`                           ``dict[str, str]``
``my-manga-status-by-id <id>``   :func:`animedex.backends.mangadex.my_manga_status_by_id`                     ``str or None``
``my-manga-read-markers <id>``   :func:`animedex.backends.mangadex.my_manga_read_markers`                     ``list[str]``
================================ ============================================================================ =================================================================

Pagination
----------

MangaDex paginates with ``?limit=M&offset=N`` (JSON:API style). The
high-level helpers expose ``limit`` / ``offset`` kwargs:

.. code-block:: bash

   animedex mangadex search "Bers erk" --limit 5 --jq '.[].attributes.title.en'                                                                                                 
   animedex mangadex search "Bers erk" --limit 5 --offset 5 --jq '.[].attributes.title.en'                                                                                      

Gotchas
-------

* **Title is language-keyed**: ``manga.attributes.title`` is a
  ``{lang: text}`` map; the ``to_ common()`` projection picks ``en``                                                                                                            
  first, then ``ja-ro``, then any  non-empty entry. Use ``--jq                                                                                                                  
  .attributes.title.ja`` if you s pecifically want the Japanese title.                                                                                                          
* **Bearer tokens expire in 15 minutes**: animedex caches per
  ``client_id`` and re-runs the p assword grant when the cache is                                                                                                               
  stale; long-running shells will  see one extra round-trip every                                                                                                               
  ~14 minutes.                                                                                                                                                                 
* **404 on follow-checks is a feature**: ``is-following-manga`` /
  ``is-following-group`` / ``is-f ollowing-user`` return ``false`` on                                                                                                           
  404 (the upstream's "you are no t following" response shape) and                                                                                                              
  raise ``ApiError`` only on othe r failure modes.                                                                                                                              
* **The ``/at-home/server`` endpoint is not wired**: the page-image
  fetcher has its own short-lived  base URLs and HTTP/2 concurrency                                                                                                             
  caps; it's a deferred follow-up .                                                                                                                                             

The :doc:`../python_library` page covers the same surface from
inside Python.
