animedex.models.aggregate
========================================================

.. currentmodule:: animedex.models.aggregate

.. automodule:: animedex.models.aggregate


AggregateSourceStatus
-----------------------------------------------------

.. autoclass:: AggregateSourceStatus
    :members: ok,backend,status,items,reason,message,http_status,duration_ms


AggregateResult
-----------------------------------------------------

.. autoclass:: AggregateResult
    :members: failed_sources,succeeded_count,all_failed,items,sources,merge_diagnostics


ScheduleCalendarResult
-----------------------------------------------------

.. autoclass:: ScheduleCalendarResult
    :members: timezone,window_start,window_end


MergedAnime
-----------------------------------------------------

.. autoclass:: MergedAnime
    :members: title,ids,sources,records,core,source_details,source_payloads


selftest
-----------------------------------------------------

.. autofunction:: selftest


