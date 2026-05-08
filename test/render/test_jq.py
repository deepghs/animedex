"""Tests for :mod:`animedex.render.jq`.

The ``--jq <expr>`` flag runs a jq expression over the JSON payload
via the native :pypi:`jq` Python wheel. Behaviour the test suite pins:

* When the expression is valid, the output matches the default
  :program:`jq` shape (one JSON value per line for multi-emit
  filters).
* A bad expression raises typed :class:`ApiError` with
  ``reason="jq-failed"`` (compile-time) — no leaked
  :class:`ValueError` from the C extension.
* When the wheel can't be imported (exotic platform / deliberate
  ``pip uninstall jq``), :func:`apply_jq` raises
  :class:`ApiError` with ``reason="jq-missing"``.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestApplyJq:
    def test_single_value_filter(self):
        from animedex.render.jq import apply_jq

        out = apply_jq('{"title":"frieren"}', ".title")
        assert out.strip() == '"frieren"'

    def test_multi_emit_filter_yields_newline_separated(self):
        """``.[]`` over a list emits one value per line — matches the
        default :program:`jq` shape, so a downstream pipeline can
        ``read``-loop over the output."""
        from animedex.render.jq import apply_jq

        out = apply_jq("[1, 2, 3]", ".[]")
        assert out.strip().splitlines() == ["1", "2", "3"]

    def test_unicode_round_trip(self):
        """Japanese / Chinese characters round-trip correctly. libjq
        escapes non-ASCII to ``\\uXXXX`` in its serialised output by
        default (the same behaviour the upstream :program:`jq`
        binary has), but the value decodes back to the original
        characters — which is the user-facing contract that matters
        and the one the Windows ``cp1252`` subprocess trap broke."""
        import json

        from animedex.render.jq import apply_jq

        out = apply_jq('{"t":"葬送のフリーレン"}', ".t")
        # JSON-decode both sides — the wire form may escape, but the
        # decoded string must match.
        assert json.loads(out) == "葬送のフリーレン"

    def test_compile_error_raises_typed_error(self):
        """Syntactically invalid expression — typed ``jq-failed``,
        not a leaked ``ValueError``."""
        from animedex.models.common import ApiError
        from animedex.render.jq import apply_jq

        with pytest.raises(ApiError) as ei:
            apply_jq("{}", "{[malformed")
        assert ei.value.reason == "jq-failed"

    def test_runtime_error_raises_typed_error(self):
        """A jq expression that compiles cleanly but errors at run
        time (division by zero, ``error()`` call) also surfaces as
        typed ``jq-failed`` rather than a leaked ``ValueError`` from
        libjq."""
        from animedex.models.common import ApiError
        from animedex.render.jq import apply_jq

        with pytest.raises(ApiError) as ei:
            apply_jq("null", "1/0")
        assert ei.value.reason == "jq-failed"
        assert "runtime" in ei.value.message.lower()

    def test_missing_wheel_raises_typed_error(self, monkeypatch):
        """When ``import jq`` raises :class:`ImportError` (exotic
        platform, sdist build failure, ``pip uninstall jq``), the
        wrapper raises typed ``jq-missing`` rather than letting the
        ImportError propagate."""
        from animedex.models.common import ApiError
        from animedex.render import jq as _jq

        # Patch the local-import inside ``apply_jq`` by killing the
        # ``jq`` entry in ``sys.modules`` and arranging for re-import
        # to fail. Setting ``sys.modules["jq"] = None`` causes
        # subsequent ``import jq`` to raise ``ModuleNotFoundError``.
        import sys

        monkeypatch.setitem(sys.modules, "jq", None)
        with pytest.raises(ApiError) as ei:
            _jq.apply_jq("{}", ".x")
        assert ei.value.reason == "jq-missing"


class TestEngineInfo:
    def test_engine_label_is_stable(self):
        from animedex.render.jq import engine_info

        label = engine_info()
        assert isinstance(label, str)
        assert "jq" in label.lower()


class TestSelftest:
    def test_selftest_runs(self):
        """The wheel is a required runtime dep, so ``selftest()`` must
        do a real round-trip in production."""
        from animedex.render.jq import selftest

        assert selftest() is True
