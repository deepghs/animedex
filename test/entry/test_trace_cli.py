"""Coverage for ``animedex/entry/trace.py`` Click bindings."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


@pytest.fixture
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def cli():
    from animedex.entry import animedex_cli

    return animedex_cli


def _src():
    from animedex.models.common import SourceTag

    return SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


class TestTraceSearchCmd:
    def test_url_path(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk

        monkeypatch.setattr(bk, "search", lambda **kw: [])
        result = cli_runner.invoke(cli, ["trace", "search", "--url", "https://x.invalid/a.jpg", "--json"])
        assert result.exit_code == 0, result.output

    def test_input_file_path(self, cli_runner, cli, monkeypatch, tmp_path):
        from animedex.backends import trace as bk

        captured = {}

        def fake_search(**kw):
            captured.update(kw)
            return []

        monkeypatch.setattr(bk, "search", fake_search)

        img = tmp_path / "shot.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")
        result = cli_runner.invoke(cli, ["trace", "search", "--input", str(img), "--json"])
        assert result.exit_code == 0, result.output
        assert captured["raw_bytes"] == b"\xff\xd8\xff\xe0"

    def test_input_dash_reads_stdin(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk

        captured = {}

        def fake_search(**kw):
            captured.update(kw)
            return []

        monkeypatch.setattr(bk, "search", fake_search)

        # Patch the entry module's sys reference for stdin reads.
        import io
        import types

        from animedex.entry import trace as trace_entry

        fake_sys = types.SimpleNamespace(stdin=types.SimpleNamespace(buffer=io.BytesIO(b"\x89PNG\r\n")))
        monkeypatch.setattr(trace_entry, "sys", fake_sys)

        result = cli_runner.invoke(cli, ["trace", "search", "--input", "-", "--json"])
        assert result.exit_code == 0, result.output
        assert captured["raw_bytes"] == b"\x89PNG\r\n"

    def test_search_propagates_api_error(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk
        from animedex.models.common import ApiError

        def boom(**kw):
            raise ApiError("upstream gone", backend="trace", reason="upstream-error")

        monkeypatch.setattr(bk, "search", boom)
        result = cli_runner.invoke(cli, ["trace", "search", "--url", "https://x.invalid/a.jpg"])
        assert result.exit_code != 0
        assert "upstream gone" in result.output


class TestTraceQuotaCmd:
    def test_quota_renders(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk
        from animedex.models.trace import TraceQuota

        monkeypatch.setattr(
            bk,
            "quota",
            lambda **kw: TraceQuota(priority=0, concurrency=1, quota=100, quota_used=42, source=_src()),
        )
        result = cli_runner.invoke(cli, ["trace", "quota", "--json"])
        assert result.exit_code == 0
        assert "42" in result.output

    def test_quota_propagates_error(self, cli_runner, cli, monkeypatch):
        from animedex.backends import trace as bk
        from animedex.models.common import ApiError

        def boom(**kw):
            raise ApiError("rate limited", backend="trace", reason="rate-limited")

        monkeypatch.setattr(bk, "quota", boom)
        result = cli_runner.invoke(cli, ["trace", "quota"])
        assert result.exit_code != 0
        assert "rate limited" in result.output
