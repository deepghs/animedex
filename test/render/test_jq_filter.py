"""
Tests for :mod:`animedex.render.jq_filter`.

The ``--jq <expr>`` flag from ``plans/03 §9`` runs a jq expression
over the JSON payload as a subprocess. The behaviour we pin:

* When ``jq`` is available, the expression is applied and the output
  is returned.
* When ``jq`` is missing on the host (especially Windows) we raise a
  typed :class:`ApiError` whose ``reason`` is ``"jq-missing"`` so the
  CLI can render a friendly error rather than letting a Bashism leak
  through.

The subprocess invocation itself is mocked so unit tests stay fast
and platform-independent.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestApplyJq:
    def test_passes_payload_to_subprocess(self, monkeypatch):
        from animedex.render import jq_filter

        seen = {}

        def fake_check(args, **_kwargs):
            seen["args"] = args
            return None

        def fake_run(args, **kwargs):
            seen["args"] = args
            seen["input"] = kwargs.get("input")

            class R:
                returncode = 0
                stdout = b'"frieren"\n'

            return R()

        monkeypatch.setattr("animedex.render.jq_filter._jq_path", lambda: "/usr/bin/jq")
        monkeypatch.setattr("animedex.render.jq_filter._subprocess_run", fake_run)

        out = jq_filter.apply_jq('{"title":"frieren"}', ".title")

        assert out.strip() == '"frieren"'
        assert seen["args"][0] == "/usr/bin/jq"
        assert seen["args"][-1] == ".title"

    def test_missing_jq_raises_typed_error(self, monkeypatch):
        from animedex.models.common import ApiError
        from animedex.render import jq_filter

        monkeypatch.setattr("animedex.render.jq_filter._jq_path", lambda: None)

        with pytest.raises(ApiError) as ei:
            jq_filter.apply_jq("{}", ".x")
        assert ei.value.reason == "jq-missing"


class TestSelftest:
    def test_selftest_runs_without_real_jq(self, monkeypatch):
        from animedex.render import jq_filter

        # selftest must succeed even when jq is absent, because the
        # frozen-binary smoke environment has no jq installed.
        monkeypatch.setattr("animedex.render.jq_filter._jq_path", lambda: None)
        assert jq_filter.selftest() is True
