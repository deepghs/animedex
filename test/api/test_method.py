"""Tests for raw API ``--method/-X`` handling."""

from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner


pytestmark = pytest.mark.unittest


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


def test_explicit_get_method_is_allowed(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={"data": {"mal_id": 52991}})
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime/52991", "-X", "GET", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "GET"


def test_allowed_graphql_post_method_is_sent(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "https://graphql.anilist.co/", json={"data": {"ok": True}})
        result = CliRunner().invoke(cli, ["api", "anilist", "{ Viewer { id } }", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "POST"


def test_explicit_anilist_get_method_is_sent(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://graphql.anilist.co/", json={"data": {"ok": True}})
        result = CliRunner().invoke(cli, ["api", "anilist", "{ Viewer { id } }", "-X", "GET", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "GET"


def test_explicit_anilist_post_method_is_sent(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "https://graphql.anilist.co/", json={"data": {"ok": True}})
        result = CliRunner().invoke(cli, ["api", "anilist", "{ Viewer { id } }", "-X", "POST", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "POST"


def test_delete_rejected_before_network(cli):
    with responses.RequestsMock() as rsps:
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime", "-X", "DELETE", "--no-cache"])

    assert result.exit_code == 2
    assert len(rsps.calls) == 0
    assert "DELETE rejected by animedex's read-only policy for jikan" in result.output
    assert "read-only" in result.output


def test_post_rejected_when_backend_allows_get_only(cli):
    with responses.RequestsMock() as rsps:
        result = CliRunner().invoke(cli, ["api", "mangadex", "/manga", "-X", "POST", "--no-cache"])

    assert result.exit_code == 2
    assert len(rsps.calls) == 0
    assert "POST rejected by animedex's read-only policy for mangadex" in result.output
