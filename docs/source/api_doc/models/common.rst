animedex.models.common
========================================================

.. currentmodule:: animedex.models.common

.. automodule:: animedex.models.common


REASONS
-----------------------------------------------------

.. autodata:: REASONS


AnimedexModel
-----------------------------------------------------

.. autoclass:: AnimedexModel
    :members: model_config


BackendRichModel
-----------------------------------------------------

.. autoclass:: BackendRichModel
    :members: model_config


SourceTag
-----------------------------------------------------

.. autoclass:: SourceTag
    :members: backend,fetched_at,cached,rate_limited


PartialDate
-----------------------------------------------------

.. autoclass:: PartialDate
    :members: year,month,day


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


require\_field
-----------------------------------------------------

.. autofunction:: require_field


selftest
-----------------------------------------------------

.. autofunction:: selftest


