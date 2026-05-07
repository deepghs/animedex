"""
Per-backend dispatcher tests driven by captured fixtures.

For every (backend, path-slug) combination in ``test/fixtures/``
we replay each fixture through its corresponding
``animedex.api.<backend>.call`` and assert: status matches, body
text matches, and the envelope's request URL matches the captured
URL. This exercises the dispatcher + per-backend shim against
real-world responses without touching the network.
"""

from __future__ import annotations

import pytest
import responses

from test.api._fixture_replay import (
    fixture_response_status,
    list_fixtures,
    load_fixture,
    register_fixture_with_responses,
)


pytestmark = pytest.mark.unittest


# Map (backend, path_slug) → (animedex.api module name, callable factory)
def _anilist_caller(fixture):
    from animedex.api import anilist

    body = fixture["request"]["json_body"]
    return lambda **kw: anilist.call(query=body["query"], variables=body.get("variables"), **kw)


def _jikan_caller(fixture):
    from animedex.api import jikan

    url = fixture["request"]["url"]
    base = "https://api.jikan.moe/v4"
    path = url[len(base) :] if url.startswith(base) else url
    return lambda **kw: jikan.call(path=path, **kw)


def _kitsu_caller(fixture):
    from animedex.api import kitsu

    url = fixture["request"]["url"]
    if url.startswith("https://kitsu.io/api/edge"):
        base = "https://kitsu.io/api/edge"
        return lambda **kw: kitsu.call(path=url[len(base) :], **kw)
    if url.startswith("https://kitsu.app/api/edge"):
        base = "https://kitsu.app/api/edge"
        return lambda **kw: kitsu.call(path=url[len(base) :], base_url="https://kitsu.app/api/edge", **kw)
    raise AssertionError(f"unrecognised kitsu host in fixture URL: {url}")


def _mangadex_caller(fixture):
    from animedex.api import mangadex

    url = fixture["request"]["url"]
    base = "https://api.mangadex.org"
    path = url[len(base) :] if url.startswith(base) else url
    return lambda **kw: mangadex.call(path=path, **kw)


def _trace_caller(fixture):
    from animedex.api import trace

    url = fixture["request"]["url"]
    base = "https://api.trace.moe"
    path = url[len(base) :] if url.startswith(base) else url
    return lambda **kw: trace.call(path=path, **kw)


def _danbooru_caller(fixture):
    from animedex.api import danbooru

    url = fixture["request"]["url"]
    base = "https://danbooru.donmai.us"
    path = url[len(base) :] if url.startswith(base) else url
    return lambda **kw: danbooru.call(path=path, **kw)


def _shikimori_caller(fixture):
    from animedex.api import shikimori

    url = fixture["request"]["url"]
    if url.startswith("https://shikimori.io"):
        base = "https://shikimori.io"
    elif url.startswith("https://shikimori.one"):
        base = "https://shikimori.one"
    else:
        raise AssertionError(f"unrecognised shikimori host: {url}")
    path = url[len(base) :]
    method = fixture["request"]["method"].upper()
    body = fixture["request"].get("json_body")
    if method == "POST":
        return lambda **kw: shikimori.call(path=path, method="POST", json_body=body, base_url=base, **kw)
    return lambda **kw: shikimori.call(path=path, base_url=base, **kw)


def _ann_caller(fixture):
    from animedex.api import ann

    url = fixture["request"]["url"]
    base = "https://cdn.animenewsnetwork.com/encyclopedia"
    path = url[len(base) :] if url.startswith(base) else url
    return lambda **kw: ann.call(path=path, **kw)


# (backend, path_slug, caller_factory)
SUITES = [
    ("anilist", "graphql", _anilist_caller),
    ("jikan", "anime_by_id", _jikan_caller),
    ("jikan", "anime_search", _jikan_caller),
    ("jikan", "seasons", _jikan_caller),
    ("jikan", "anime_characters", _jikan_caller),
    ("jikan", "anime_episodes", _jikan_caller),
    ("kitsu", "anime_search", _kitsu_caller),
    ("kitsu", "anime_by_id", _kitsu_caller),
    ("kitsu", "anime_streaming_links", _kitsu_caller),
    ("kitsu", "anime_mappings", _kitsu_caller),
    ("kitsu", "host_app_parity", _kitsu_caller),
    ("mangadex", "manga_search", _mangadex_caller),
    ("mangadex", "manga_by_id", _mangadex_caller),
    ("mangadex", "manga_feed", _mangadex_caller),
    ("mangadex", "manga_meta", _mangadex_caller),
    ("mangadex", "at_home_server", _mangadex_caller),
    ("trace", "me", _trace_caller),
    ("trace", "search", _trace_caller),
    ("danbooru", "posts_search", _danbooru_caller),
    ("danbooru", "posts_by_id", _danbooru_caller),
    ("danbooru", "tags_search", _danbooru_caller),
    ("danbooru", "artists_search", _danbooru_caller),
    ("danbooru", "counts", _danbooru_caller),
    ("danbooru", "pools_by_id", _danbooru_caller),
    ("shikimori", "animes_by_id", _shikimori_caller),
    ("shikimori", "animes_search", _shikimori_caller),
    ("shikimori", "calendar", _shikimori_caller),
    ("shikimori", "screenshots", _shikimori_caller),
    ("shikimori", "videos", _shikimori_caller),
    ("shikimori", "graphql", _shikimori_caller),
    ("ann", "by_id", _ann_caller),
    ("ann", "substring_search", _ann_caller),
    ("ann", "reports", _ann_caller),
]


def _suite_to_params():
    out = []
    for backend, path_slug, factory in SUITES:
        for fixture_path in list_fixtures(backend, path_slug):
            label = fixture_path.stem
            out.append(pytest.param(backend, path_slug, factory, fixture_path, id=f"{backend}/{path_slug}/{label}"))
    return out


@pytest.mark.parametrize("backend,path_slug,factory,fixture_path", _suite_to_params())
def test_fixture_replay(backend, path_slug, factory, fixture_path):
    """Each captured (backend, path) fixture replays cleanly: the
    dispatcher returns an envelope whose status, body, and URL match
    what the upstream returned at capture time."""
    fixture = load_fixture(fixture_path)
    expected_status = fixture_response_status(fixture)
    expected_url = fixture["request"]["url"]
    expected_body = fixture["response"]
    expected_body_text = expected_body.get("body_text")
    expected_body_json = expected_body.get("body_json")

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        register_fixture_with_responses(rsps, fixture)
        caller = factory(fixture)
        envelope = caller(no_cache=True)

    assert envelope.status == expected_status, f"status mismatch for {fixture_path.name}"
    assert envelope.request.url == expected_url, f"URL mismatch for {fixture_path.name}"
    assert envelope.firewall_rejected is None, f"unexpected firewall reject for {fixture_path.name}"
    assert envelope.cache.hit is False  # we passed no_cache=True

    if expected_body_text is not None:
        assert envelope.body_text == expected_body_text
    elif expected_body_json is not None:
        # responses library will encode our dict to JSON to send back;
        # the dispatcher receives bytes that we then decode. Compare
        # the decoded JSON for structural equality (whitespace varies).
        import json as _json

        assert _json.loads(envelope.body_text) == expected_body_json


class TestPerBackendShimAcceptsTimeoutSeconds:
    """Per review m6: every per-backend shim must accept
    ``timeout_seconds`` and thread it down to
    :func:`animedex.api._dispatch.call`.
    Otherwise a Python caller via
    ``from animedex.api import jikan; jikan.call(path=..., timeout_seconds=5.0)``
    cannot override the 30 s default.
    """

    @pytest.fixture
    def captured(self, monkeypatch):
        """Patch ``_dispatch.call`` so each shim's call records its
        kwargs into a list that the test can inspect."""
        captured: list = []

        def _fake_dispatch_call(**kwargs):
            captured.append(kwargs)

            class _Stub:
                pass

            return _Stub()

        # Patch every per-backend module's bound ``_dispatch_call``.
        for mod_name in ("anilist", "ann", "danbooru", "jikan", "kitsu", "mangadex", "shikimori", "trace"):
            monkeypatch.setattr(f"animedex.api.{mod_name}._dispatch_call", _fake_dispatch_call)
        return captured

    def test_anilist_threads_timeout_seconds(self, captured):
        from animedex.api import anilist

        anilist.call(query="{ ok }", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_jikan_threads_timeout_seconds(self, captured):
        from animedex.api import jikan

        jikan.call(path="/anime/52991", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_kitsu_threads_timeout_seconds(self, captured):
        from animedex.api import kitsu

        kitsu.call(path="/anime/1", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_mangadex_threads_timeout_seconds(self, captured):
        from animedex.api import mangadex

        mangadex.call(path="/manga/abc", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_trace_threads_timeout_seconds(self, captured):
        from animedex.api import trace

        trace.call(path="/me", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_danbooru_threads_timeout_seconds(self, captured):
        from animedex.api import danbooru

        danbooru.call(path="/posts/1.json", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_shikimori_threads_timeout_seconds(self, captured):
        from animedex.api import shikimori

        shikimori.call(path="/api/animes/1", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_ann_threads_timeout_seconds(self, captured):
        from animedex.api import ann

        ann.call(path="/api.xml?id=1", timeout_seconds=5.0)
        assert captured[-1].get("timeout_seconds") == 5.0

    def test_default_omits_timeout_seconds_to_use_dispatcher_default(self, captured):
        """When the caller does not pass ``timeout_seconds``, the shim
        should not pass it down (or should pass ``None``), so the
        dispatcher's 30 s default applies. Either form is acceptable."""
        from animedex.api import jikan

        jikan.call(path="/anime/52991")
        ts = captured[-1].get("timeout_seconds", "not-passed")
        assert ts in ("not-passed", None, 30.0)


class TestSelftestBackendShimHelper:
    """Per review m5 + AGENTS §9.1: each per-backend selftest must
    catch a rename / signature breakage of the module's public ``call``.
    Driven by the shared :func:`animedex.api._dispatch.selftest_backend_shim`
    helper.
    """

    def test_helper_passes_when_call_signature_is_intact(self):
        from animedex.api._dispatch import selftest_backend_shim
        from animedex.api import jikan

        assert selftest_backend_shim("jikan", jikan.call, extra_params=("path",)) is True

    def test_helper_raises_when_call_drops_a_required_param(self):
        from animedex.api._dispatch import selftest_backend_shim

        # Stub callable missing every cross-cutting kwarg.
        def stub_call(path):
            raise NotImplementedError

        with pytest.raises(AssertionError, match="lost expected params"):
            selftest_backend_shim("jikan", stub_call, extra_params=("path",))

    def test_helper_raises_when_extra_param_missing(self):
        from animedex.api._dispatch import selftest_backend_shim

        def call(
            path, no_cache=False, cache_ttl=None, rate="normal", timeout_seconds=None, user_agent=None, cache=None
        ):
            raise NotImplementedError

        # ``query`` is required by the AniList shim but absent here.
        with pytest.raises(AssertionError, match="query"):
            selftest_backend_shim("anilist", call, extra_params=("query", "variables"))
