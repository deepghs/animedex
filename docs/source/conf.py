"""Sphinx configuration for the animedex documentation build.

The full set of options is documented at
https://www.sphinx-doc.org/en/master/usage/configuration.html.
"""

import os
import re
import sys
from datetime import datetime

from docutils import nodes
from docutils.parsers.rst import roles

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
# Single-backticks render as italic title-references (the reST
# default) rather than being eagerly resolved as cross-refs. Click
# command docstrings carry a lot of plain-text strings wrapped in
# single backticks (`--flag`, `kitsu.io`, `?page=N&limit=M`) — under
# `default_role="any"` every one of those generates a "未找到引用目标"
# warning. Plain identifiers can still cross-link via explicit roles
# (`:class:`, `:func:`, `:mod:`, `:meth:`, `:attr:`).
default_role = None

# Suppress autosummary-emitted warnings for pydantic's auto-generated
# ``model_config`` attribute docstring, which references ``ConfigDict``
# without an explicit role. Those models are pydantic v2 internals,
# not part of animedex's public API surface.
nitpick_ignore = [
    ("any", "ConfigDict"),
]

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


# -- Custom roles ------------------------------------------------------------


def _pypi_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """``:pypi:`name``` -> hyperlink to the package's PyPI page.

    The project's docstrings reference bundled Python wheels with
    the ``:pypi:`` role; without a definition Sphinx logs an
    "Unknown interpreted text role" error for every site of use.
    """
    url = f"https://pypi.org/project/{text}/"
    node = nodes.reference(rawtext, text, refuri=url, **(options or {}))
    return [node], []


roles.register_canonical_role("pypi", _pypi_role)


# -- Click docstring sanitiser ----------------------------------------------


_CLICK_FORMFEED = "\f"  # `\f` cuts off everything after (Click's --help cutoff)
_CLICK_BACKSPACE = "\b"  # `\b` tells Click "do not reflow this paragraph"

# Match `--flag`, `/path/to/x`, `?title=`, `Header: Value`, `func()` and
# similar plain-text strings that Click docstring authors wrap in
# single backticks for emphasis, so we can rewrite them to
# double-backtick inline literals (which `default_role="any"` does not
# try to resolve as cross-references).
#
# A single-backticked string is treated as plain text for our purposes
# whenever it contains *any* character that is not part of a dotted
# Python identifier (so `Anime` and `models.common.SourceTag` pass
# through unchanged and keep their cross-link, while `?page=N&limit=M`,
# `--variables`, `[OK]`, `Content-Type: application/json` get rewritten).
_SINGLE_BACKTICK_PLAINTEXT = re.compile(
    r"(?<!`)`([^`\n]*?[^A-Za-z0-9_.][^`\n]*?)`(?!`)"
)


def _is_click_command(obj):
    """Return ``True`` when ``obj`` is a Click ``Command`` / ``Group``.

    The check is structural rather than a hard import so the docs
    build does not gain a Click runtime dependency it doesn't already
    have via animedex itself.
    """
    try:
        import click
    except ImportError:  # pragma: no cover - click is a runtime dep
        return False
    return isinstance(obj, click.BaseCommand)


def _sanitise_click_docstring(app, what, name, obj, options, lines):
    """Strip Click's `\\b` / `\\f` sentinels from autodoc'd docstrings.

    Click commands embed two control characters in their docstrings:
    ``\\f`` cuts the human ``--help`` short of the policy block, and
    ``\\b`` precedes paragraphs that Click should not reflow. Both
    confuse Sphinx's reST parser — ``\\b`` introduces an indented
    block whose preceding context is empty (so docutils logs
    "Unexpected indentation"), and the policy text after ``\\f`` is
    not reST-shaped to begin with (designed to be read by
    ``inspect.getdoc`` / ``--agent-guide``, not Sphinx).

    This hook truncates each docstring at the first ``\\f`` and
    rewrites lines that begin with ``\\b`` into plain blanks so the
    surviving text parses cleanly. For Click commands specifically
    (where the human help section uses single-backtick plain-text
    strings like ```--flag``` / ```/path``` / ```Header: Value```)
    it also rewrites those into double-backtick inline literals, so
    Sphinx's ``default_role="any"`` does not try to resolve them as
    Python references.
    """
    # Truncate at the first formfeed.
    for i, line in enumerate(lines):
        if _CLICK_FORMFEED in line:
            del lines[i:]
            break

    # Replace each `\\b`-only line with `::` (the reST literal-block
    # intro), and indent the subsequent block (up to the next blank
    # line) so docutils sees a proper literal block. Click's `\\b` is
    # always followed by an indented listing it asked Click not to
    # reflow — converting it to a reST literal block is the closest
    # faithful render Sphinx can produce, and it eliminates the
    # "Unexpected indentation" cascade those listings otherwise
    # trigger.
    #
    # The shape we emit:
    #
    #     <blank>
    #     ::
    #     <blank>
    #         <indented listing>
    #     <blank>
    i = 0
    while i < len(lines):
        if _CLICK_BACKSPACE in lines[i]:
            stripped = lines[i].replace(_CLICK_BACKSPACE, "")
            if stripped.strip():
                # `\\b` mid-line: just drop the control character.
                lines[i] = stripped
                i += 1
                continue
            lines[i] = "::"
            j = i + 1
            # Skip an immediately-following blank (Click writers
            # sometimes leave one between `\\b` and the listing).
            if j < len(lines) and not lines[j].strip():
                j += 1
            # Insert a mandatory blank line after `::` so docutils
            # recognises the literal-block intro.
            lines.insert(j, "")
            j += 1
            # Indent the next non-blank run by 4 spaces.
            while j < len(lines) and lines[j].strip():
                lines[j] = "    " + lines[j]
                j += 1
            # Insert a blank line before `::` to terminate any
            # preceding paragraph cleanly.
            if i > 0 and lines[i - 1].strip():
                lines.insert(i, "")
                i += 1
                j += 1
            i = j
        else:
            i += 1

    # Click-only: turn single-backtick plain-text into double-backtick
    # inline literals so `default_role="any"` does not flag them as
    # broken cross-refs.
    if _is_click_command(obj):
        for i, line in enumerate(lines):
            lines[i] = _SINGLE_BACKTICK_PLAINTEXT.sub(r"``\1``", line)


def setup(app):
    app.connect("autodoc-process-docstring", _sanitise_click_docstring)
