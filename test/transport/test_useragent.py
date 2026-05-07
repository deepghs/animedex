"""
Tests for :mod:`animedex.transport.useragent`.

The User-Agent string is a P1 protocol contract for several upstreams
(MangaDex, Shikimori, Danbooru, AniDB - see ``plans/02 §7``). The
transport layer must inject a single, honest, project-identifying UA
on every request. These tests pin the UA's structure so changes are
intentional and reviewable.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestDefaultUserAgent:
    def test_includes_project_name(self):
        from animedex.transport.useragent import default_user_agent

        ua = default_user_agent()
        assert "animedex" in ua

    def test_includes_version(self):
        from animedex.config.meta import __VERSION__
        from animedex.transport.useragent import default_user_agent

        ua = default_user_agent()
        assert __VERSION__ in ua

    def test_includes_contact_email(self):
        from animedex.transport.useragent import default_user_agent

        ua = default_user_agent()
        assert "@" in ua

    def test_does_not_pretend_to_be_browser(self):
        """Per ``plans/02`` Danbooru contract: no Mozilla / browser spoofing."""
        from animedex.transport.useragent import default_user_agent

        ua = default_user_agent().lower()
        assert "mozilla" not in ua
        assert "chrome" not in ua
        assert "webkit" not in ua


class TestComposeUserAgent:
    def test_custom_overrides_default(self):
        from animedex.transport.useragent import compose_user_agent

        ua = compose_user_agent(custom="my-bot/2.0 (+contact@example.invalid)")
        assert ua == "my-bot/2.0 (+contact@example.invalid)"

    def test_custom_none_returns_default(self):
        from animedex.transport.useragent import compose_user_agent, default_user_agent

        assert compose_user_agent(custom=None) == default_user_agent()

    def test_custom_empty_string_returns_default(self):
        from animedex.transport.useragent import compose_user_agent, default_user_agent

        assert compose_user_agent(custom="") == default_user_agent()


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.transport import useragent

        assert useragent.selftest() is True
