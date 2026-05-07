animedex.models.common
========================================================

.. currentmodule:: animedex.models.common

.. automodule:: animedex.models.common


AnimedexModel
-----------------------------------------------------

.. autoclass:: AnimedexModel
    :members: model_config


SourceTag
-----------------------------------------------------

.. autoclass:: SourceTag
    :members: backend,fetched_at,cached,rate_limited


Pagination
-----------------------------------------------------

.. autoclass:: Pagination
    :members: page,per_page,total,has_next


RateLimit
-----------------------------------------------------

.. autoclass:: RateLimit
    :members: remaining,reset_at


ApiError
-----------------------------------------------------

.. autoclass:: ApiError
    :members: __init__,__str__


selftest
-----------------------------------------------------

.. autofunction:: selftest


