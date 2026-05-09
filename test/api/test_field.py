"""Tests for raw API ``-f`` and ``-F`` field handling."""

from __future__ import annotations

import json

import pytest
import responses
import yaml
from click.testing import CliRunner


pytestmark = pytest.mark.unittest


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


def test_rest_field_values_land_in_query_string(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime?count=10&published=True&tag=true", json={"data": []})
        result = CliRunner().invoke(
            cli,
            [
                "api",
                "jikan",
                "/anime",
                "-f",
                "count=10",
                "-f",
                "published=true",
                "-F",
                "tag=true",
                "--no-cache",
            ],
        )
        called_url = rsps.calls[0].request.url

    assert result.exit_code == 0, result.output
    query = called_url.split("?", 1)[1]
    assert "count=10" in query
    assert "published=True" in query
    assert "tag=true" in query


def test_field_and_raw_field_same_key_use_cli_order(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime?count=10", json={"data": []})
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime", "-f", "count=1", "-F", "count=10", "--no-cache"])
        called_url = rsps.calls[0].request.url

    assert result.exit_code == 0, result.output
    assert called_url.endswith("count=10")

    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime?count=10", json={"data": []})
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime", "-F", "count=1", "-f", "count=10", "--no-cache"])
        called_url = rsps.calls[0].request.url

    assert result.exit_code == 0, result.output
    assert called_url.endswith("count=10")


def test_path_query_and_fields_use_last_write_wins(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime?q=Naruto&limit=2", json={"data": []})
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime?q=Naruto&limit=1", "-f", "limit=2", "--no-cache"])
        called_url = rsps.calls[0].request.url

    assert result.exit_code == 0, result.output
    assert called_url == "https://api.jikan.moe/v4/anime?q=Naruto&limit=2"


def test_anilist_fields_merge_into_graphql_variables(cli):
    fixture_path = "test/fixtures/anilist/graphql/20-query-with-variables.yaml"
    fixture = yaml.safe_load(open(fixture_path, "r", encoding="utf-8"))
    query = fixture["request"]["json_body"]["query"]

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://graphql.anilist.co/",
            json=fixture["response"]["body_json"],
            status=200,
        )
        result = CliRunner().invoke(
            cli,
            [
                "api",
                "anilist",
                query,
                "--variables",
                '{"search":"Naruto"}',
                "-f",
                "page=2",
                "-F",
                "search=Demon Slayer",
                "--no-cache",
            ],
        )
        request_body = rsps.calls[0].request.body

    assert result.exit_code == 0, result.output
    body = json.loads(request_body.decode("utf-8"))
    assert body["variables"] == {"search": "Demon Slayer", "page": 2}
