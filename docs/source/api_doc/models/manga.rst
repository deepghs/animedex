animedex.models.manga
========================================================

.. currentmodule:: animedex.models.manga

.. automodule:: animedex.models.manga


MangaStatus
-----------------------------------------------------

.. autodata:: MangaStatus


MangaFormat
-----------------------------------------------------

.. autodata:: MangaFormat


Chapter
-----------------------------------------------------

.. autoclass:: Chapter
    :members: id,number,title,language,pages,source


Manga
-----------------------------------------------------

.. autoclass:: Manga
    :members: id,title,cover_url,chapters,languages,description,status,format,genres,tags,ids,source


AtHomeServer
-----------------------------------------------------

.. autoclass:: AtHomeServer
    :members: base_url,chapter_hash,data,data_saver,source


selftest
-----------------------------------------------------

.. autofunction:: selftest


