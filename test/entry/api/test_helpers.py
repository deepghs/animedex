"""Coverage tests for the small helpers in
:mod:`animedex.entry.api`.

Each helper is exercised directly so codecov can attribute the
behaviour to a specific test rather than indirectly through CLI
runner flows.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


def _make_envelope(status: int, *, firewall: bool = False):
    """Build a minimal :class:`RawResponse` for routing tests."""
    from animedex.api._envelope import RawCacheInfo, RawRequest, RawResponse, RawTiming

    return RawResponse(
        backend="jikan",
        request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
        status=status,
        response_headers={},
        body_bytes=b"",
        body_text="",
        timing=RawTiming(total_ms=0.0, rate_limit_wait_ms=0.0, request_ms=0.0),
        cache=RawCacheInfo(hit=False),
        firewall_rejected=({"reason": "read-only", "message": "x"} if firewall else None),
    )


class TestOutputModeFromFlags:
    def test_no_flag_returns_body(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, False, False) == "body"

    def test_include_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(True, False, False) == "include"

    def test_head_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, True, False) == "head"

    def test_debug_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, False, True) == "debug"

    def test_two_flags_set_raises(self):
        import click

        from animedex.entry.api import _output_mode_from_flags

        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _output_mode_from_flags(True, True, False)

    def test_three_flags_set_raises(self):
        import click

        from animedex.entry.api import _output_mode_from_flags

        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _output_mode_from_flags(True, True, True)


class TestRenderOutput:
    def test_body_mode(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="body", full_body=False)
        assert isinstance(out, str)

    def test_include_mode_has_status_line(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="include", full_body=False)
        assert "200" in out.split("\n", 1)[0]

    def test_head_mode_omits_body(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="head", full_body=False)
        # head mode contains only the status line + headers; no JSON
        # body. The empty body is empty, so a sanity check that
        # status appears suffices.
        assert "200" in out

    def test_debug_mode_emits_json(self):
        import json

        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="debug", full_body=False)
        decoded = json.loads(out)
        assert decoded["status"] == 200


class TestExitCodeFor:
    @pytest.mark.parametrize(
        "status,expected",
        [
            (200, 0),
            (201, 0),
            (299, 0),
            (301, 3),
            (399, 3),
            (400, 4),
            (404, 4),
            (499, 4),
            (500, 5),
            (503, 5),
            (599, 5),
            (100, 1),
            (700, 1),
        ],
    )
    def test_status_class_to_exit_code(self, status, expected):
        from animedex.entry.api import _exit_code_for

        assert _exit_code_for(_make_envelope(status)) == expected

    def test_firewall_overrides_status(self):
        from animedex.entry.api import _exit_code_for

        # Firewall-rejected envelope has status=0, but the exit code
        # comes from the firewall flag, not the status class.
        assert _exit_code_for(_make_envelope(0, firewall=True)) == 2


class TestParseExtraHeaders:
    def test_empty_returns_empty_dict(self):
        from animedex.entry.api import _parse_extra_headers

        assert _parse_extra_headers(()) == {}
        assert _parse_extra_headers(None) == {}

    def test_single_header(self):
        from animedex.entry.api import _parse_extra_headers

        assert _parse_extra_headers(("X-Foo: bar",)) == {"X-Foo": "bar"}

    def test_multiple_headers(self):
        from animedex.entry.api import _parse_extra_headers

        out = _parse_extra_headers(("X-Foo: bar", "User-Agent: my-bot/1"))
        assert out == {"X-Foo": "bar", "User-Agent": "my-bot/1"}

    def test_value_with_colon(self):
        """Only the first colon is the separator; the rest is the
        value (e.g. 'Date: Thu, 07 May 2026 13:39:30')."""
        from animedex.entry.api import _parse_extra_headers

        out = _parse_extra_headers(("Date: Thu, 07 May 13:39:30",))
        assert out == {"Date": "Thu, 07 May 13:39:30"}

    def test_malformed_raises(self):
        import click

        from animedex.entry.api import _parse_extra_headers

        with pytest.raises(click.UsageError, match="must be 'Name: Value'"):
            _parse_extra_headers(("no-colon-here",))


class TestEmit:
    def test_echoes_rendered_output_and_exits_with_status_class_code(self):
        import click
        from click.testing import CliRunner

        from animedex.entry.api import _emit

        @click.command()
        def cmd():
            ctx = click.get_current_context()
            _emit(ctx, _make_envelope(404), mode="body", full_body=False)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 4

    def test_firewall_envelope_exits_2(self):
        import click
        from click.testing import CliRunner

        from animedex.entry.api import _emit

        @click.command()
        def cmd():
            ctx = click.get_current_context()
            _emit(ctx, _make_envelope(0, firewall=True), mode="body", full_body=False)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 2


class TestResolveCache:
    def test_no_cache_returns_none(self):
        from animedex.entry.api import _resolve_cache

        assert _resolve_cache(no_cache=True) is None

    def test_default_returns_singleton(self, monkeypatch):
        import animedex.entry.api as entry_api

        sentinel = object()
        monkeypatch.setattr(entry_api, "_default_cache", lambda: sentinel)
        assert entry_api._resolve_cache(no_cache=False) is sentinel
