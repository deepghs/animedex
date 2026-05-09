"""Tests for raw API ``--method/-X`` handling."""

from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner


pytestmark = pytest.mark.unittest


REST_BACKEND_METHOD_CASES = [
    ("ann", "/api.xml", "https://cdn.animenewsnetwork.com/encyclopedia/api.xml"),
    ("danbooru", "/posts.json", "https://danbooru.donmai.us/posts.json"),
    ("ghibli", "/films", "https://ghibliapi.vercel.app/films"),
    ("jikan", "/anime", "https://api.jikan.moe/v4/anime"),
    ("kitsu", "/anime/1", "https://kitsu.io/api/edge/anime/1"),
    ("mangadex", "/manga", "https://api.mangadex.org/manga"),
    ("nekos", "/endpoints", "https://nekos.best/api/v2/endpoints"),
    ("quote", "/quotes/random", "https://api.animechan.io/v1/quotes/random"),
    ("shikimori", "/api/animes/1", "https://shikimori.io/api/animes/1"),
    ("waifu", "/tags", "https://api.waifu.im/tags"),
]


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


def test_delete_method_is_forwarded(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.DELETE, "https://api.jikan.moe/v4/anime", json={"upstream": "saw-delete"}, status=405)
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime", "-X", "DELETE", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 4
    assert method == "DELETE"
    assert "saw-delete" in result.output


def test_post_method_is_forwarded_for_rest_backend(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "https://api.mangadex.org/manga", json={"upstream": "saw-post"}, status=202)
        result = CliRunner().invoke(cli, ["api", "mangadex", "/manga", "-X", "POST", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "POST"
    assert "saw-post" in result.output


@pytest.mark.parametrize("backend,path,url", REST_BACKEND_METHOD_CASES)
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_rest_backends_forward_mutating_looking_methods(cli, backend, path, url, method):
    with responses.RequestsMock() as rsps:
        rsps.add(method, url, json={"backend": backend, "method": method}, status=200)
        result = CliRunner().invoke(cli, ["api", backend, path, "-X", method, "--no-cache"])
        sent_method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert sent_method == method
    assert f'"backend": "{backend}"' in result.output
    assert f'"method": "{method}"' in result.output


def test_trace_input_respects_explicit_method(cli, tmp_path):
    img = tmp_path / "shot.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0")
    with responses.RequestsMock() as rsps:
        rsps.add(responses.PUT, "https://api.trace.moe/search", json={"upstream": "saw-put"}, status=200)
        result = CliRunner().invoke(cli, ["api", "trace", "/search", "--input", str(img), "-X", "PUT", "--no-cache"])
        method = rsps.calls[0].request.method
        body = rsps.calls[0].request.body

    assert result.exit_code == 0, result.output
    assert method == "PUT"
    assert body == b"\xff\xd8\xff\xe0"
    assert "saw-put" in result.output


def test_shikimori_graphql_respects_explicit_method(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.DELETE, "https://shikimori.io/api/graphql", json={"upstream": "saw-delete"}, status=200)
        result = CliRunner().invoke(
            cli,
            [
                "api",
                "shikimori",
                "/api/graphql",
                "--graphql",
                '{ animes(ids:"1"){ id } }',
                "-X",
                "DELETE",
                "--no-cache",
            ],
        )
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "DELETE"
    assert "saw-delete" in result.output


def test_paginate_does_not_block_anilist_passthrough(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "https://graphql.anilist.co/", json={"data": {"ok": True}}, status=200)
        result = CliRunner().invoke(cli, ["api", "anilist", "{ Viewer { id } }", "--paginate", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "POST"


def test_paginate_does_not_block_trace_passthrough(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.trace.moe/me", json={"quota": 100}, status=200)
        result = CliRunner().invoke(cli, ["api", "trace", "/me", "--paginate", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "GET"


def test_paginate_does_not_block_explicit_non_get_method(cli):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "https://api.jikan.moe/v4/anime", json={"upstream": "saw-post"}, status=200)
        result = CliRunner().invoke(cli, ["api", "jikan", "/anime", "--paginate", "-X", "POST", "--no-cache"])
        method = rsps.calls[0].request.method

    assert result.exit_code == 0, result.output
    assert method == "POST"
    assert "saw-post" in result.output
