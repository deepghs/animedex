animedex.backends.waifu.models
========================================================

.. currentmodule:: animedex.backends.waifu.models

.. automodule:: animedex.backends.waifu.models


WaifuTag
-----------------------------------------------------

.. autoclass:: WaifuTag
    :members: id,name,slug,description,imageCount,reviewStatus,creatorId,source_tag


WaifuArtist
-----------------------------------------------------

.. autoclass:: WaifuArtist
    :members: id,name,patreon,pixiv,twitter,deviantArt,reviewStatus,creatorId,imageCount,source_tag


WaifuImageDimensions
-----------------------------------------------------

.. autoclass:: WaifuImageDimensions
    :members: width,height


WaifuImage
-----------------------------------------------------

.. autoclass:: WaifuImage
    :members: to_common,id,url,source,isNsfw,isAnimated,width,height,perceptualHash,extension,dominantColor,uploaderId,uploadedAt,byteSize,favorites,likedAt,addedToAlbumAt,reviewStatus,tags,artists,albums,source_tag


WaifuStats
-----------------------------------------------------

.. autoclass:: WaifuStats
    :members: totalRequests,totalImages,totalTags,totalArtists,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest


