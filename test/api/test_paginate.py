"""Tests for raw API pagination substrate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses
from click.testing import CliRunner

from animedex.api._envelope import RawCacheInfo, RawRequest, RawResponse, RawTiming
from test.api._fixture_replay import load_fixture, register_fixture_with_responses


pytestmark = pytest.mark.unittest


def _raw_response(*, body_bytes: bytes, body_text, status: int = 200, backend: str = "jikan"):
    return RawResponse(
        backend=backend,
        request=RawRequest(method="GET", url="https://x.invalid/page", headers={}),
        redirects=[],
        status=status,
        response_headers={},
        body_bytes=body_bytes,
        body_text=body_text,
        timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0.0, request_ms=0.1),
        cache=RawCacheInfo(hit=False),
    )


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


def _fixture_paths(backend: str):
    return sorted(Path("test/fixtures").joinpath(backend, "pagination").glob("*.yaml"))


def _invoke(cli, args):
    runner = CliRunner()
    return runner.invoke(cli, args)


def _json_output(result):
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_jikan_paginate_max_pages(cli):
    with responses.RequestsMock() as rsps:
        for path in _fixture_paths("jikan")[:3]:
            register_fixture_with_responses(rsps, load_fixture(path))
        result = _invoke(
            cli,
            ["api", "jikan", "/anime?q=Naruto&limit=2", "--paginate", "--max-pages", "3", "--no-cache"],
        )
        called_urls = [call.request.url for call in rsps.calls]
    payload = _json_output(result)

    assert payload["pagination"]["pages_fetched"] == 3
    assert payload["pagination"]["items_fetched"] == 6
    assert payload["pagination"]["terminated_by"] == "max-pages"
    assert called_urls == [
        "https://api.jikan.moe/v4/anime?q=Naruto&limit=2&page=1",
        "https://api.jikan.moe/v4/anime?q=Naruto&limit=2&page=2",
        "https://api.jikan.moe/v4/anime?q=Naruto&limit=2&page=3",
    ]


def test_mangadex_paginate_max_items(cli):
    with responses.RequestsMock() as rsps:
        for path in _fixture_paths("mangadex")[:3]:
            register_fixture_with_responses(rsps, load_fixture(path))
        result = _invoke(
            cli,
            [
                "api",
                "mangadex",
                "/manga?title=Berserk&limit=2&includes[]=cover_art",
                "--paginate",
                "--max-items",
                "5",
                "--no-cache",
            ],
        )
        called_urls = [call.request.url for call in rsps.calls]
    payload = _json_output(result)

    assert payload["pagination"]["pages_fetched"] == 3
    assert payload["pagination"]["items_fetched"] == 5
    assert payload["pagination"]["terminated_by"] == "max-items"
    assert called_urls == [
        "https://api.mangadex.org/manga?title=Berserk&limit=2&includes%5B%5D=cover_art&offset=0",
        "https://api.mangadex.org/manga?title=Berserk&limit=2&includes%5B%5D=cover_art&offset=2",
        "https://api.mangadex.org/manga?title=Berserk&limit=2&includes%5B%5D=cover_art&offset=4",
    ]


def test_danbooru_short_page_terminates(cli):
    fixtures = []
    for fixture_path in _fixture_paths("danbooru")[:3]:
        fixture = load_fixture(fixture_path)
        fixtures.append(fixture)
    fixtures[-1]["response"]["body_json"] = fixtures[-1]["response"]["body_json"][:1]
    with responses.RequestsMock() as rsps:
        for fixture in fixtures:
            register_fixture_with_responses(rsps, fixture)
        result = _invoke(
            cli,
            [
                "api",
                "danbooru",
                "/posts.json?tags=touhou+rating:g+order:score&limit=2",
                "--paginate",
                "--max-pages",
                "10",
                "--no-cache",
            ],
        )
    payload = _json_output(result)

    assert payload["pagination"]["pages_fetched"] == 3
    assert payload["pagination"]["items_fetched"] == 5
    assert payload["pagination"]["terminated_by"] == "short-page"


def test_shikimori_paginate_max_pages(cli):
    with responses.RequestsMock() as rsps:
        for path in _fixture_paths("shikimori")[:3]:
            register_fixture_with_responses(rsps, load_fixture(path))
        result = _invoke(
            cli,
            ["api", "shikimori", "/api/animes?search=Naruto&limit=2", "--paginate", "--max-pages", "3", "--no-cache"],
        )
    payload = _json_output(result)

    assert payload["pagination"]["pages_fetched"] == 3
    assert payload["pagination"]["items_fetched"] == 6
    assert payload["pagination"]["terminated_by"] == "max-pages"


def test_quote_paginate_max_pages(cli):
    with responses.RequestsMock() as rsps:
        for path in sorted(Path("test/fixtures/quote/quotes_by_anime").glob("0[123]-naruto-page-*.yaml")):
            register_fixture_with_responses(rsps, load_fixture(path))
        result = _invoke(
            cli,
            ["api", "quote", "/quotes?anime=Naruto", "--paginate", "--max-pages", "3", "--no-cache"],
        )
    payload = _json_output(result)

    assert payload["pagination"]["pages_fetched"] == 3
    assert payload["pagination"]["items_fetched"] == 15
    assert payload["pagination"]["terminated_by"] == "max-pages"


def test_paginated_cache_is_per_page(cli):
    with responses.RequestsMock() as rsps:
        for path in _fixture_paths("jikan")[:2]:
            register_fixture_with_responses(rsps, load_fixture(path))
        first = _invoke(
            cli,
            ["api", "jikan", "/anime?q=Naruto&limit=2", "--paginate", "--max-pages", "2"],
        )
        assert first.exit_code == 0, first.output
        assert len(rsps.calls) == 2

        second = _invoke(
            cli,
            ["api", "jikan", "/anime?q=Naruto&limit=2", "--paginate", "--max-pages", "2"],
        )
        assert len(rsps.calls) == 2
    payload = _json_output(second)

    assert [page["cache_hit"] for page in payload["pagination"]["pages"]] == [True, True]


def test_paginate_rejects_invalid_bounds():
    from animedex.api._paginate import call_paginated, get_strategy
    from animedex.models.common import ApiError

    with pytest.raises(ApiError, match="does not support raw --paginate"):
        get_strategy("anilist")
    with pytest.raises(ApiError, match="--max-pages must be >= 1"):
        call_paginated(backend="jikan", path="/anime", max_pages=0)
    with pytest.raises(ApiError, match="--max-items must be >= 1"):
        call_paginated(backend="jikan", path="/anime", max_items=0)
    with pytest.raises(ApiError, match="supports GET"):
        call_paginated(backend="jikan", path="/anime", method="POST")


def test_decode_json_page_rejects_binary_and_malformed_json():
    from animedex.api._paginate import _decode_json_page
    from animedex.models.common import ApiError

    with pytest.raises(ApiError, match="not UTF-8 text"):
        _decode_json_page(_raw_response(body_bytes=b"\xff", body_text=None))
    with pytest.raises(ApiError, match="not JSON"):
        _decode_json_page(_raw_response(body_bytes=b"{", body_text="{"))


def test_paginate_stops_on_non_2xx_response():
    from animedex.api._paginate import call_paginated

    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.jikan.moe/v4/anime?page=1&limit=25", json={"error": "boom"}, status=500)
        env = call_paginated(backend="jikan", path="/anime", no_cache=True)

    payload = json.loads(env.body_text)
    assert env.status == 500
    assert payload["items"] == []
    assert payload["pagination"]["pages_fetched"] == 1
    assert payload["pagination"]["terminated_by"] == "non-2xx-response"


def test_strategy_decoders_reject_bad_shapes():
    from animedex.api._paginate import PageRequest, _decode_jikan, _decode_mangadex, _decode_quote
    from animedex.models.common import ApiError

    with pytest.raises(ApiError, match="jikan paginated response was not an object"):
        _decode_jikan([], PageRequest("/", {}))
    with pytest.raises(ApiError, match="jikan pagination field was not an object"):
        _decode_jikan({"data": [], "pagination": [1]}, PageRequest("/", {}))
    with pytest.raises(ApiError, match="mangadex paginated response was not an object"):
        _decode_mangadex([], PageRequest("/", {}))
    with pytest.raises(ApiError, match="quote paginated response was not an object"):
        _decode_quote([], PageRequest("/", {}))
    with pytest.raises(ApiError, match="quote paginated response did not contain a list"):
        _decode_quote({"data": {}}, PageRequest("/", {}))
