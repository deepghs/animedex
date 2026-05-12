"""Tests for aggregate search/show Python API helpers."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import responses
import yaml


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[2] / "test" / "fixtures"
_STRIP_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze HTTP-adjacent clocks."""
    from datetime import datetime, timezone

    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 11, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


def _load_fixture(rel_path: str) -> dict:
    return yaml.safe_load((FIXTURES / rel_path).read_text(encoding="utf-8"))


def _register_fixture_path_only(rsps: responses.RequestsMock, fixture: dict) -> None:
    req = fixture["request"]
    resp = fixture["response"]
    parsed = urlsplit(req["url"])
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    url_re = re.compile(re.escape(base) + r"(\?.*)?$")
    headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP_HEADERS}
    kwargs = {"status": resp["status"], "headers": headers}
    if resp.get("body_json") is not None:
        kwargs["json"] = resp["body_json"]
    elif resp.get("body_text") is not None:
        kwargs["body"] = resp["body_text"]
    elif resp.get("body_b64") is not None:
        import base64

        kwargs["body"] = base64.b64decode(resp["body_b64"])
    rsps.add(responses.Response(method=req["method"].upper(), url=url_re, **kwargs))


class TestAggregateSearch:
    def test_native_id_falls_back_to_plain_id_for_unknown_backend(self):
        from animedex.agg.search import _native_id

        assert _native_id({"id": "mystery-1"}, "unknown") == "mystery-1"

    def test_annotates_plain_dict_rows_without_known_prefix(self):
        from animedex.agg.search import _annotate_row

        row = _annotate_row({"id": "local-1", "title": "Local"}, "local")

        assert row == {"id": "local-1", "title": "Local", "_source": "local"}
        assert "_prefix_id" not in row

    def test_annotates_real_rich_rows_with_source_and_prefix_id(self, fake_clock):
        from animedex.agg.search import search

        fixture = _load_fixture("jikan/anime_search/17-frieren-tv-limit2.yaml")
        with responses.RequestsMock() as rsps:
            _register_fixture_path_only(rsps, fixture)
            result = search("anime", "Frieren", limit=2, source="jikan", no_cache=True)

        assert result.sources["jikan"].status == "ok"
        assert len(result.items) == 2
        assert result.items[0]._source == "jikan"
        assert result.items[0]._prefix_id.startswith("mal:")
        assert result.items[0].mal_id is not None

    def test_rejects_bad_limit(self):
        from animedex.agg.search import search
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="limit must be >= 1") as excinfo:
            search("anime", "Frieren", limit=0)
        assert excinfo.value.reason == "bad-args"


class TestAggregateShow:
    def test_rejects_unsupported_pair_before_http(self):
        from animedex.agg.show import show
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="type 'publisher' is not supported by backend 'anilist'") as excinfo:
            show("publisher", "anilist:1")
        assert excinfo.value.reason == "bad-args"

    def test_deferred_anidb_prefix_is_typed(self):
        from animedex.agg.show import show
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="AniDB high-level helpers are not shipped yet") as excinfo:
            show("anime", "anidb:42")
        assert excinfo.value.backend == "anidb"
        assert excinfo.value.reason == "auth-required"
