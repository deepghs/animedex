animedex.api.\_envelope
========================================================

.. currentmodule:: animedex.api._envelope

.. automodule:: animedex.api._envelope


RawRequest
-----------------------------------------------------

.. autoclass:: RawRequest
    :members: method,url,headers,body_preview


RawRedirectHop
-----------------------------------------------------

.. autoclass:: RawRedirectHop
    :members: status,headers,from_url,to_url,elapsed_ms


RawTiming
-----------------------------------------------------

.. autoclass:: RawTiming
    :members: total_ms,rate_limit_wait_ms,request_ms


RawCacheInfo
-----------------------------------------------------

.. autoclass:: RawCacheInfo
    :members: hit,key,ttl_remaining_s,fetched_at


RawResponse
-----------------------------------------------------

.. autoclass:: RawResponse
    :members: backend,request,redirects,status,response_headers,body_bytes,body_text,body_truncated_at_bytes,timing,cache,firewall_rejected


redact\_credential\_value
-----------------------------------------------------

.. autofunction:: redact_credential_value


redact\_headers
-----------------------------------------------------

.. autofunction:: redact_headers


selftest
-----------------------------------------------------

.. autofunction:: selftest


