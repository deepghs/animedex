"""Tests for :mod:`animedex.agg.calendar` merge helpers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unittest


def test_title_key_variants_use_multiple_transliterators():
    from animedex.agg import calendar

    japanese_keys = calendar._title_key_variants(
        "\u30bd\u30fc\u30c9\u30a2\u30fc\u30c8\u30fb\u30aa\u30f3\u30e9\u30a4\u30f3"
    )
    assert "so doa to onrain" in japanese_keys
    assert "sodoato onrain" in japanese_keys

    accented_keys = calendar._title_key_variants("Pok\u00e9mon")
    assert "pokemon" in accented_keys


def test_short_transliteration_keys_are_not_strong():
    from animedex.agg import calendar

    assert "8" in calendar._title_key_variants("\u602a\u7363\uff18\u53f7")
    assert not calendar._is_strong_title_key("8")
    assert not calendar._is_strong_title_key("no")


def test_season_merge_rule_matches_adjudicated_2010_2025_baseline():
    from animedex.agg import calendar
    from tools.merge_eval import evaluate_rule

    assert calendar.selftest() is True
    assert evaluate_rule.main(["--limit-details", "5"]) == 0
