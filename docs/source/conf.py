"""Sphinx configuration for the animedex documentation build.

The full set of options is documented at
https://www.sphinx-doc.org/en/master/usage/configuration.html.
"""

import os
import sys
from datetime import datetime

_DOC_PATH = os.path.dirname(os.path.abspath(__file__))
_PROJ_PATH = os.path.abspath(os.path.join(_DOC_PATH, "..", ".."))

# Make the local source tree importable so autodoc reads the working
# copy rather than any pre-installed version of the package.
sys.path.insert(0, _PROJ_PATH)
for _modname in [m for m in list(sys.modules) if m == "animedex" or m.startswith("animedex.")]:
    del sys.modules[_modname]

from animedex.config.meta import (  # noqa: E402
    __AUTHOR__,
    __TITLE__,
    __VERSION__,
)

# -- Project information -----------------------------------------------------

project = __TITLE__
author = __AUTHOR__
copyright = f"{datetime.now().year}, {author}"
version = __VERSION__
release = __VERSION__

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns: list = []
master_doc = "index"
language = "en"
default_role = "any"

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_show_sourcelink = True

# -- Autodoc -----------------------------------------------------------------

autodoc_member_order = "bysource"
# ``tools/auto_rst.py`` emits an explicit ``.. autodata:: NAME`` /
# ``.. autofunction:: NAME`` / ``.. autoclass:: NAME`` directive for
# every public member, so we deliberately leave ``members`` out of the
# default options to keep ``automodule`` from re-documenting members
# at the module-page level. (The Sphinx default with no ``members``
# key is "show only the module docstring", which is what we want.
# Setting ``members: False`` explicitly is a known Sphinx footgun -
# autodoc internally iterates the value and crashes on the boolean.)
autodoc_default_options = {
    "undoc-members": False,
    "show-inheritance": True,
}
autosummary_generate = True

# -- Napoleon ----------------------------------------------------------------
# We use reST docstrings, but enabling Napoleon keeps occasional Google /
# NumPy-style snippets (typically copied from upstream documentation)
# from breaking the build.
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "click": ("https://click.palletsprojects.com/en/stable/", None),
}

# -- Todo --------------------------------------------------------------------

todo_include_todos = True
