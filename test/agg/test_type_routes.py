"""Tests for aggregate entity type routing."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestTypeRoutes:
    @pytest.mark.parametrize(
        "entity_type,expected",
        [
            ("anime", {"anilist", "ann", "jikan", "kitsu", "shikimori"}),
            ("manga", {"anilist", "jikan", "kitsu", "mangadex", "shikimori"}),
            ("character", {"anilist", "jikan", "kitsu", "shikimori"}),
            ("person", {"anilist", "jikan", "kitsu", "shikimori"}),
            ("studio", {"anilist", "jikan", "kitsu", "shikimori"}),
            ("publisher", {"shikimori"}),
        ],
    )
    def test_search_backends_cover_supported_sources(self, entity_type, expected):
        from animedex.agg._type_routes import backends_for_type

        assert set(backends_for_type(entity_type)) == expected

    def test_validate_entity_type_lists_supported_types(self):
        from animedex.agg._type_routes import validate_entity_type
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="supported types: anime, manga, character, person, studio, publisher"):
            validate_entity_type("badtype")

    def test_show_route_rejects_unsupported_pair_before_http(self):
        from animedex.agg._type_routes import show_route_for
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="supported backends: shikimori") as excinfo:
            show_route_for("publisher", "anilist")
        assert excinfo.value.reason == "bad-args"

    def test_mangadex_show_route_uses_uuid_string_id(self):
        from animedex.agg._type_routes import show_route_for

        route = show_route_for("manga", "mangadex")

        assert route.function_name == "show"
        assert route.id_arg == "id"

    def test_filter_rows_keeps_rows_when_query_is_empty(self):
        from animedex.agg._type_routes import _filter_rows

        rows = [{"title": "A"}, {"title": "B"}]

        assert _filter_rows(rows, "") is rows

    def test_filter_rows_matches_nested_list_values(self):
        from animedex.agg._type_routes import _filter_rows

        rows = [{"title": "No match", "aliases": ["Sousou no Frieren"]}, {"title": "Other", "aliases": []}]

        assert _filter_rows(rows, "frieren") == [rows[0]]
