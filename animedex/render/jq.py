"""``--jq <expr>`` post-filter via the native :pypi:`jq` Python wheel.

The :pypi:`jq` wheel statically links libjq, so the engine version
is pinned at install time rather than inherited from whatever the
host distribution ships. This means:

* The frozen-binary distribution (PyInstaller ``make build``) ships
  with jq linked in — Windows users no longer need to install
  :program:`jq` separately to use ``--jq``.
* Per-call cost is in-process — no subprocess spawn, no UTF-8 round
  trip, no Windows ``cp1252`` trap.
* :func:`selftest` does a real round-trip in well under 100 ms, so
  the offline diagnostic catches binding regressions.

The output of :meth:`jq.compile.input_text(payload).text` matches the
default :program:`jq` shape (one JSON value per line for multi-emit
filters), so callers see the same string a host :program:`jq` would
produce.
"""

from __future__ import annotations

from animedex.models.common import ApiError


def apply_jq(payload: str, expression: str) -> str:
    """Filter ``payload`` (JSON text) through ``expression``.

    :param payload: JSON text to filter.
    :type payload: str
    :param expression: jq filter expression
                        (e.g. ``".title.romaji"``).
    :type expression: str
    :return: jq's stringified output. Multi-emit filters produce one
              value per line, matching the default :program:`jq`
              shape.
    :rtype: str
    :raises ApiError: ``reason="jq-missing"`` when the wheel is not
                       importable. With ``jq>=1.11`` listed as a hard
                       runtime dependency, this is reachable only if
                       a user has deliberately broken their install
                       (``pip uninstall jq``) — the typed error gives
                       them a friendlier message than a raw
                       :class:`ImportError`. ``reason="jq-failed"``
                       when the expression fails to compile or
                       execute, or when ``payload`` is not valid JSON
                       (libjq raises ``ValueError`` from
                       ``input_text`` in that case too).
    """
    try:
        import jq as _jq  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ApiError(
            "the jq Python wheel is not importable on this interpreter; "
            "reinstall animedex (or `pip install jq>=1.11`) to enable --jq",
            reason="jq-missing",
        ) from exc
    try:
        program = _jq.compile(expression)
    except (ValueError, RuntimeError) as exc:
        raise ApiError(
            f"jq expression failed to compile: {exc}",
            reason="jq-failed",
        ) from exc
    try:
        return program.input_text(payload).text()
    except (ValueError, RuntimeError) as exc:
        raise ApiError(
            f"jq runtime error: {exc}",
            reason="jq-failed",
        ) from exc


def selftest() -> bool:
    """Smoke-test the binding with a real ``.input_text`` round-trip."""
    out = apply_jq('{"x": 42}', ".x")
    assert out.strip() == "42", f"unexpected jq native output: {out!r}"
    return True
