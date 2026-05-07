animedex.transport.ratelimit
========================================================

.. currentmodule:: animedex.transport.ratelimit

.. automodule:: animedex.transport.ratelimit


TokenBucket
-----------------------------------------------------

.. autoclass:: TokenBucket
    :members: __init__,try_acquire,acquire,with_rate


RateLimitRegistry
-----------------------------------------------------

.. autoclass:: RateLimitRegistry
    :members: __init__,register,get


default\_registry
-----------------------------------------------------

.. autofunction:: default_registry


selftest
-----------------------------------------------------

.. autofunction:: selftest


