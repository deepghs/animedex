"""Replay tests for the four token-required AniList mappers.

The fixtures under ``test/fixtures/anilist/phase2_authenticated_*``
were captured against a real OAuth-issued token (cookie-driven flow,
2026-05-08). Authorization headers in those fixtures are scrubbed by
``capture.py``'s ``_redact_request_headers`` helper so no real token
ever entered git.

Phase 2 keeps the public ``viewer`` / ``notification`` / ``markdown``
/ ``ani_chart_user`` Python functions as ``auth-required`` stubs;
Phase 8 will wire them to ``Config.token_store`` and they will then
call into these mappers with the response from a real GraphQL POST.

These tests confirm the mappers can already parse a real upstream
response so Phase 8 only has to plumb tokens, not invent shapes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from animedex.backends.anilist import _mapper as mp
from animedex.backends.anilist.models import (
    AnilistAniChartUser,
    AnilistMarkdown,
    AnilistNotification,
    AnilistUser,
)
from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "anilist"


def _src() -> SourceTag:
    return SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


def _load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))["response"]["body_json"]


class TestViewer:
    def test_real_viewer_payload_parses(self):
        path = FIXTURES / "authenticated_viewer" / "01-viewer.yaml"
        payload = _load(path)
        result = mp.map_viewer(payload, _src())
        assert isinstance(result, AnilistUser)
        assert result.id > 0
        assert result.name
        assert result.statistics is not None

    def test_authorization_header_was_scrubbed_in_fixture(self):
        path = FIXTURES / "authenticated_viewer" / "01-viewer.yaml"
        fix = yaml.safe_load(path.read_text(encoding="utf-8"))
        auth = fix["request"]["headers"].get("Authorization", "")
        # Fingerprint form: "Bearer eyJ0...XXXX (len=N)"
        assert auth.startswith("Bearer ")
        assert "(len=" in auth
        # Raw token middle should never appear; the header is short.
        assert len(auth) < 60


class TestNotification:
    def test_real_notification_payload_parses(self):
        path = FIXTURES / "authenticated_notification" / "01-notification.yaml"
        payload = _load(path)
        result = mp.map_notification(payload, _src())
        assert isinstance(result, list)
        # The capture user has zero notifications; the mapper still
        # returns an empty list (not None / not error).
        for n in result:
            assert isinstance(n, AnilistNotification)

    def test_synthetic_polymorphic_rows_classify_correctly(self):
        """Build a fake Page.notifications with one of each variant."""
        payload = {
            "data": {
                "Page": {
                    "notifications": [
                        {"id": 1, "type": "AIRING", "contexts": ["ep 1 of"], "createdAt": 100},
                        {
                            "id": 2,
                            "type": "FOLLOWING",
                            "context": "started following you",
                            "user": {"id": 1, "name": "alice"},
                            "createdAt": 200,
                        },
                        {
                            "id": 3,
                            "type": "ACTIVITY_REPLY",
                            "context": "replied to your activity",
                            "user": {"id": 2, "name": "bob"},
                            "createdAt": 300,
                        },
                    ]
                }
            }
        }
        rows = mp.map_notification(payload, _src())
        assert [r.kind for r in rows] == ["airing", "following", "activity-reply"]
        assert rows[0].contexts == ["ep 1 of"]
        assert rows[1].user_name == "alice"
        assert rows[2].context == "replied to your activity"


class TestMarkdown:
    def test_real_markdown_payload_parses(self):
        path = FIXTURES / "authenticated_markdown" / "01-markdown-render.yaml"
        payload = _load(path)
        result = mp.map_markdown(payload, _src())
        assert isinstance(result, AnilistMarkdown)
        assert result.html.startswith("<p>")
        assert "<strong>hello</strong>" in result.html
        assert "<em>world</em>" in result.html


class TestAniChartUser:
    def test_real_ani_chart_user_payload_parses(self):
        path = FIXTURES / "authenticated_ani_chart_user" / "01-ani-chart-user.yaml"
        payload = _load(path)
        result = mp.map_ani_chart_user(payload, _src())
        assert isinstance(result, AnilistAniChartUser)
        assert result.user_id > 0
        assert result.user_name


class TestSelftestStillRaises:
    """Phase 2's public Python API for the four token-required commands
    still raises ``auth-required`` until Phase 8 wires token storage."""

    def test_viewer_raises_auth_required(self):
        from animedex.backends import anilist
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc:
            anilist.viewer()
        assert exc.value.reason == "auth-required"

    def test_notification_raises_auth_required(self):
        from animedex.backends import anilist
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc:
            anilist.notification()
        assert exc.value.reason == "auth-required"

    def test_markdown_raises_auth_required(self):
        from animedex.backends import anilist
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc:
            anilist.markdown("hello")
        assert exc.value.reason == "auth-required"

    def test_ani_chart_user_raises_auth_required(self):
        from animedex.backends import anilist
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc:
            anilist.ani_chart_user()
        assert exc.value.reason == "auth-required"
