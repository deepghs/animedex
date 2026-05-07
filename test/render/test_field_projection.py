"""
Tests for :mod:`animedex.render.field_projection`.

The ``--json field1,field2,...`` flag from ``plans/03 §9`` returns
only the requested top-level fields from a JSON payload. Unknown
fields raise a typed :class:`ApiError` so a typo at the call site
fails loudly.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestProjectFields:
    def test_keeps_only_requested(self):
        from animedex.render.field_projection import project_fields

        data = {"a": 1, "b": 2, "c": 3}
        out = project_fields(data, ["a", "c"])

        assert out == {"a": 1, "c": 3}

    def test_unknown_field_rejected(self):
        from animedex.models.common import ApiError
        from animedex.render.field_projection import project_fields

        with pytest.raises(ApiError) as ei:
            project_fields({"a": 1}, ["b"])
        assert ei.value.reason == "unknown-field"

    def test_empty_field_list_returns_full(self):
        from animedex.render.field_projection import project_fields

        data = {"a": 1, "b": 2}
        assert project_fields(data, []) == data


class TestParseFieldString:
    def test_comma_split(self):
        from animedex.render.field_projection import parse_field_string

        assert parse_field_string("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        from animedex.render.field_projection import parse_field_string

        assert parse_field_string("a, b ,c") == ["a", "b", "c"]

    def test_empty_string_yields_empty_list(self):
        from animedex.render.field_projection import parse_field_string

        assert parse_field_string("") == []


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import field_projection

        assert field_projection.selftest() is True
