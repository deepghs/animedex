"""Tests for the PyInstaller spec generator."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unittest


def test_transliterator_runtime_tables_are_collected_for_freezing():
    from tools import generate_spec

    assert "anyascii._data" in generate_spec.HIDDEN_IMPORTS
    assert "unidecode" in generate_spec.HIDDEN_IMPORTS
    assert "unidecode.util" in generate_spec.HIDDEN_IMPORTS
    assert "anyascii" in generate_spec.PACKAGE_DATAS
    assert "unidecode" in generate_spec.PACKAGE_DATAS
