animedex.backends.ghibli.models
========================================================

.. currentmodule:: animedex.backends.ghibli.models

.. automodule:: animedex.backends.ghibli.models


GhibliFilm
-----------------------------------------------------

.. autoclass:: GhibliFilm
    :members: to_common,id,title,original_title,original_title_romanised,image,movie_banner,description,director,producer,release_date,running_time,rt_score,people,species,locations,vehicles,url,source_tag


GhibliPerson
-----------------------------------------------------

.. autoclass:: GhibliPerson
    :members: to_common,id,name,gender,age,eye_color,hair_color,films,species,url,source_tag


GhibliLocation
-----------------------------------------------------

.. autoclass:: GhibliLocation
    :members: id,name,climate,terrain,surface_water,residents,films,url,source_tag


GhibliVehicle
-----------------------------------------------------

.. autoclass:: GhibliVehicle
    :members: id,name,description,vehicle_class,length,pilot,films,url,source_tag


GhibliSpecies
-----------------------------------------------------

.. autoclass:: GhibliSpecies
    :members: id,name,classification,eye_colors,hair_colors,people,films,url,source_tag


selftest
-----------------------------------------------------

.. autofunction:: selftest
