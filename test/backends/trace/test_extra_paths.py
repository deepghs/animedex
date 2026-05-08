"""Coverage-oriented edge-case tests for :mod:`animedex.backends.trace`.

The Phase-2 fixture corpus exercises the canonical paths; this module
fills in the conditional branches and error paths the corpus doesn't
naturally hit (cutBorders flag, anilist_id filter, raw-bytes upload,
firewall rejection, decode error, bad-args branches)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import responses

from animedex.backends import trace as trace_api
from animedex.models.common import ApiError


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


class TestSearchBadArgs:
    def test_neither_url_nor_bytes(self):
        with pytest.raises(ApiError) as exc_info:
            trace_api.search(no_cache=True)
        assert exc_info.value.reason == "bad-args"

    def test_both_url_and_bytes(self):
        with pytest.raises(ApiError) as exc_info:
            trace_api.search(
                image_url="https://x.invalid/x.jpg",
                raw_bytes=b"\xff\xd8\xff",
                no_cache=True,
            )
        assert exc_info.value.reason == "bad-args"


class TestSearchOptionalFlags:
    """Cover the conditional flag branches in ``search``."""

    @pytest.fixture
    def stub_search(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.GET, "https://api.trace.moe/search", json={"result": []}, status=200)
            yield rsps

    def test_cut_borders_flag(self, stub_search):
        trace_api.search(image_url="https://x.invalid/x.jpg", cut_borders=True, no_cache=True)

    def test_anilist_id_filter(self, stub_search):
        trace_api.search(image_url="https://x.invalid/x.jpg", anilist_id=42, no_cache=True)

    def test_anilist_info_flag(self, stub_search):
        trace_api.search(image_url="https://x.invalid/x.jpg", anilist_info=True, no_cache=True)


class TestSearchUploadPath:
    """Cover the ``raw_bytes`` POST branch."""

    def test_raw_bytes_upload(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.POST, "https://api.trace.moe/search", json={"result": []}, status=200)
            result = trace_api.search(raw_bytes=b"\xff\xd8\xff\xe0fakejpeg", no_cache=True)
        assert result == []

    def test_raw_bytes_with_no_qs_options(self, fake_clock):
        """When no flags are set and raw bytes are uploaded, the URL is
        plain ``/search`` (no query string). Exercises the ``else``
        branch."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.POST, "https://api.trace.moe/search", json={"result": []}, status=200)
            trace_api.search(raw_bytes=b"\xff\xd8\xff", no_cache=True)


class TestSearchHitFiltering:
    """The mapper drops hits whose ``anilist`` carries no id."""

    def test_drops_hit_with_no_anilist_id(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/search",
                json={
                    "result": [
                        {"anilist": None, "similarity": 0.9, "from": 0, "at": 0, "to": 1},
                        {"anilist": 154587, "similarity": 0.95, "from": 0, "at": 0, "to": 1},
                    ]
                },
                status=200,
            )
            result = trace_api.search(image_url="https://x.invalid/x.jpg", no_cache=True)
        assert len(result) == 1
        assert result[0].anilist_id == 154587

    def test_anilist_object_with_title_dict(self, fake_clock):
        """When ``anilist`` is a nested dict with a ``title`` block,
        the mapper attaches an :class:`AnimeTitle`."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/search",
                json={
                    "result": [
                        {
                            "anilist": {
                                "id": 154587,
                                "title": {"romaji": "Sousou no Frieren", "english": "Frieren"},
                            },
                            "similarity": 0.95,
                            "from": 0,
                            "at": 0,
                            "to": 1,
                        }
                    ]
                },
                status=200,
            )
            result = trace_api.search(image_url="https://x.invalid/x.jpg", anilist_info=True, no_cache=True)
        assert len(result) == 1
        assert result[0].anilist_title is not None
        assert result[0].anilist_title.romaji == "Sousou no Frieren"


class TestRawTraceHitToCommonBranches:
    """Cover the int/object branches in
    :meth:`RawTraceHit.to_common`."""

    def _src(self):
        from animedex.models.common import SourceTag

        return SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))

    def test_anilist_as_bare_int(self):
        """When anilistInfo=False, ``anilist`` is a bare int.
        ``to_common()`` reads it directly (no nested object)."""
        from animedex.backends.trace.models import RawTraceHit

        hit = RawTraceHit.model_validate(
            {
                "anilist": 154587,
                "similarity": 0.95,
                "from": 0.0,
                "at": 1.0,
                "to": 2.0,
                "source_tag": self._src(),
            }
        )
        common = hit.to_common()
        assert common.anilist_id == 154587
        assert common.anilist_title is None

    def test_anilist_as_object_without_title(self):
        """anilist as nested object without ``title`` block."""
        from animedex.backends.trace.models import RawTraceHit

        hit = RawTraceHit.model_validate(
            {
                "anilist": {"id": 154587, "idMal": 52991},
                "similarity": 0.95,
                "from": 0.0,
                "at": 1.0,
                "to": 2.0,
                "source_tag": self._src(),
            }
        )
        common = hit.to_common()
        assert common.anilist_id == 154587

    def test_anilist_as_object_with_title(self):
        """anilist as nested object WITH ``title`` block — title
        gets attached on the common projection."""
        from animedex.backends.trace.models import RawTraceHit

        hit = RawTraceHit.model_validate(
            {
                "anilist": {
                    "id": 154587,
                    "idMal": 52991,
                    "title": {"romaji": "Frieren", "english": "F", "native": "葬送"},
                },
                "similarity": 0.95,
                "from": 0.0,
                "at": 1.0,
                "to": 2.0,
                "source_tag": self._src(),
            }
        )
        common = hit.to_common()
        assert common.anilist_title is not None
        assert common.anilist_title.romaji == "Frieren"


class TestParseHelpers:
    """Cover ``_parse`` error branches and ``_coerce_int`` paths via
    HTTP transport only (test discipline §9bis)."""

    def test_body_text_none(self, fake_clock):
        """A response body that fails UTF-8 decode produces
        ``body_text=None`` at the dispatcher; ``_parse`` raises
        ``upstream-decode``."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                body=b"\xff\xfe\x00\xc3\x28binary garbage\xff",
                status=200,
                content_type="application/octet-stream",
            )
            with pytest.raises(ApiError) as exc_info:
                trace_api.quota(no_cache=True)
        assert exc_info.value.reason == "upstream-decode"

    def test_coerce_int_int(self, fake_clock):
        # The internal _coerce_int handles int + str + raises on others.
        # Reach it via quotaUsed=int directly.
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={"priority": 0, "concurrency": 1, "quota": 100, "quotaUsed": 25},
                status=200,
            )
            q = trace_api.quota(no_cache=True)
        assert q.quota_used == 25

    def test_selftest(self):
        assert trace_api.selftest() is True

    def test_quota_missing_priority_raises_upstream_shape(self, fake_clock):
        """A ``/me`` body missing ``priority`` (or any other required
        field) must raise ``upstream-shape`` rather than leaking a
        bare KeyError. Same audit shape as the AniList mappers'
        ``_field`` guard."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={"concurrency": 1, "quota": 100, "quotaUsed": 0},  # no priority
                status=200,
            )
            with pytest.raises(ApiError) as exc_info:
                trace_api.quota(no_cache=True)
        assert exc_info.value.reason == "upstream-shape"
        assert "priority" in exc_info.value.message

    def test_coerce_int_other_raises(self, fake_clock):
        """A ``null`` ``quotaUsed`` is neither int nor str —
        ``_coerce_int`` raises ``upstream-shape``."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={"priority": 0, "concurrency": 1, "quota": 100, "quotaUsed": None},
                status=200,
            )
            with pytest.raises(ApiError) as exc_info:
                trace_api.quota(no_cache=True)
        assert exc_info.value.reason == "upstream-shape"
