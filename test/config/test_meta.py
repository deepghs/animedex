"""Smoke tests covering the package metadata module."""

import pytest

from animedex import (
    __AUTHOR__,
    __AUTHOR_EMAIL__,
    __DESCRIPTION__,
    __TITLE__,
    __VERSION__,
)


@pytest.mark.unittest
class TestMeta:
    def test_title(self):
        assert __TITLE__ == "animedex"

    def test_version_is_pep440_like(self):
        # Very loose sanity check - we are not validating the full PEP 440
        # grammar here, just that the literal contains digits and a dot.
        assert any(ch.isdigit() for ch in __VERSION__)
        assert "." in __VERSION__

    def test_description_non_empty(self):
        assert isinstance(__DESCRIPTION__, str)
        assert __DESCRIPTION__.strip()

    def test_author_identity(self):
        assert __AUTHOR__ == "narugo1992"
        assert __AUTHOR_EMAIL__.endswith("@deepghs.org")
