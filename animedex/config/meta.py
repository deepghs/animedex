"""
Project metadata for the :mod:`animedex` package.

This module defines immutable, public metadata constants used throughout the
project and by packaging tools such as ``setup.py``. These values provide the
project title, version, description, and author contact information.

The module exposes the following public attributes:

* :data:`__TITLE__` - Project name
* :data:`__VERSION__` - Current project version
* :data:`__DESCRIPTION__` - Short project description
* :data:`__AUTHOR__` - Author name
* :data:`__AUTHOR_EMAIL__` - Author contact email

Example::

    >>> from animedex.config import meta
    >>> meta.__TITLE__
    'animedex'

.. note::
   These values are intended to be constants and should not be modified at
   runtime. They are consumed by packaging and documentation tools.

"""

#: Title of this project (should be `animedex`).
__TITLE__: str = "animedex"

#: Version of this project.
__VERSION__: str = "0.0.1"

#: Short description of the project, will be included in ``setup.py``.
__DESCRIPTION__: str = (
    "A read-only, multi-source, gh-flavored command-line interface for anime "
    "and manga metadata, designed for both humans and LLM agents."
)

#: Author of this project.
__AUTHOR__: str = "narugo1992"

#: Email of the author.
__AUTHOR_EMAIL__: str = "narugo1992@deepghs.org"
