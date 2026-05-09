animedex.backends.ann.models
========================================================

.. currentmodule:: animedex.backends.ann.models

.. automodule:: animedex.backends.ann.models


AnnXmlNode
-----------------------------------------------------

.. autoclass:: AnnXmlNode
    :members: from_adapter,by_tag,first_text,tag,attrs,text,tail,children,children_by_tag


AnnInfo
-----------------------------------------------------

.. autoclass:: AnnInfo
    :members: type,attrs,text,children


AnnPersonRef
-----------------------------------------------------

.. autoclass:: AnnPersonRef
    :members: to_common_staff,id,name


AnnCompanyRef
-----------------------------------------------------

.. autoclass:: AnnCompanyRef
    :members: id,name


AnnStaff
-----------------------------------------------------

.. autoclass:: AnnStaff
    :members: to_common,attrs,task,person


AnnCast
-----------------------------------------------------

.. autoclass:: AnnCast
    :members: to_common,attrs,role,person


AnnCredit
-----------------------------------------------------

.. autoclass:: AnnCredit
    :members: attrs,task,company


AnnLink
-----------------------------------------------------

.. autoclass:: AnnLink
    :members: attrs,text


AnnEpisode
-----------------------------------------------------

.. autoclass:: AnnEpisode
    :members: attrs,titles


AnnRelation
-----------------------------------------------------

.. autoclass:: AnnRelation
    :members: direction,attrs


AnnAnime
-----------------------------------------------------

.. autoclass:: AnnAnime
    :members: info_by_type,first_info_text,to_common,id,gid,type,name,precision,generated_on,info,staff,cast,credits,episodes,reviews,releases,news,relations,raw,source_tag


AnnAnimeResponse
-----------------------------------------------------

.. autoclass:: AnnAnimeResponse
    :members: warnings,anime,raw,source_tag


AnnReportItem
-----------------------------------------------------

.. autoclass:: AnnReportItem
    :members: fields,raw,source_tag


AnnReport
-----------------------------------------------------

.. autoclass:: AnnReport
    :members: attrs,args,items,warnings,raw,source_tag


anime\_from\_node
-----------------------------------------------------

.. autofunction:: anime_from_node


anime\_response\_from\_root
-----------------------------------------------------

.. autofunction:: anime_response_from_root


report\_from\_root
-----------------------------------------------------

.. autofunction:: report_from_root


selftest
-----------------------------------------------------

.. autofunction:: selftest
