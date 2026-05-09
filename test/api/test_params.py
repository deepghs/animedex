"""Tests for raw API query-parameter helpers."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


def test_add_query_pair_promotes_repeated_keys_to_lists():
    from animedex.api._params import add_query_pair

    params = {}
    add_query_pair(params, "tag", "one")
    add_query_pair(params, "tag", "two")
    add_query_pair(params, "tag", "three")

    assert params == {"tag": ["one", "two", "three"]}


def test_merge_params_copies_lists_and_tuples():
    from animedex.api._params import merge_params

    original = {"a": ["1"], "b": ("2", "3")}
    merged = merge_params(original, {"c": ("4", "5")})

    assert merged == {"a": ["1"], "b": ["2", "3"], "c": ["4", "5"]}
    assert merged["a"] is not original["a"]


def test_split_path_query_preserves_repeated_values_and_fragments():
    from animedex.api._params import split_path_query

    path, params = split_path_query("/posts.json?tag=a&tag=b#top", {"page": 2})

    assert path == "/posts.json#top"
    assert params == {"tag": ["a", "b"], "page": 2}


def test_split_path_query_normalises_query_only_path():
    from animedex.api._params import split_path_query

    path, params = split_path_query("?q=Frieren")

    assert path == "/"
    assert params == {"q": "Frieren"}


def test_first_int_uses_last_list_value_and_falls_back():
    from animedex.api._params import first_int

    assert first_int({"page": ["bad", "3"]}, ("page",), 1) == 3
    assert first_int({"page": "bad"}, ("page", "offset"), 7) == 7
