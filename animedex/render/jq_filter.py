"""
``--jq <expr>`` post-filter via the jq subprocess.

Per ``plans/03 §9`` the CLI exposes the same ``--jq`` semantics as
``gh``. We do not vendor a jq Python wheel because (a) cross-platform
wheel availability is uneven, (b) the user experience matches what
they already have on their host, and (c) jq's spec is large enough
that we do not want to keep two parsers in sync.

When jq is absent (typically on Windows where it is not part of the
default install), we raise a typed :class:`ApiError` with
``reason="jq-missing"``. The CLI surfaces a friendly message; we do
not block on it during the diagnostic, because the frozen-binary
smoke environment may not include jq.

The subprocess call goes through :data:`_subprocess_run` and the
binary lookup goes through :data:`_jq_path` so unit tests can drop
in deterministic fakes.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from animedex.models.common import ApiError


def _default_jq_path() -> Optional[str]:
    return shutil.which("jq")


_jq_path = _default_jq_path
_subprocess_run = subprocess.run


def apply_jq(payload: str, expression: str) -> str:
    """Run ``jq <expression>`` over ``payload`` as a subprocess.

    :param payload: JSON text fed to jq via stdin.
    :type payload: str
    :param expression: jq filter expression
                        (e.g. ``".title.romaji"``).
    :type expression: str
    :return: jq's stdout, decoded as UTF-8.
    :rtype: str
    :raises ApiError: ``reason="jq-missing"`` when ``jq`` is not on
                       the PATH; ``reason="jq-failed"`` when the
                       subprocess exits non-zero.
    """
    binary = _jq_path()
    if binary is None:
        raise ApiError(
            "jq not found on PATH; install jq (https://jqlang.github.io/jq/) to use the --jq flag",
            reason="jq-missing",
        )
    completed = _subprocess_run(
        [binary, expression],
        input=payload.encode("utf-8") if isinstance(payload, str) else payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise ApiError(
            f"jq exited with code {completed.returncode}",
            reason="jq-failed",
        )
    out = completed.stdout
    return out.decode("utf-8") if isinstance(out, (bytes, bytearray)) else str(out)


def selftest() -> bool:
    """Smoke-test the jq filter wiring.

    Tolerates a host without jq installed: we only verify that the
    binary-resolver and the error path are sound. The frozen-binary
    smoke environment may not include jq.

    :return: ``True`` on success.
    :rtype: bool
    """
    if _jq_path() is None:
        try:
            apply_jq("{}", ".x")
        except ApiError as exc:
            assert exc.reason == "jq-missing"
        else:  # pragma: no cover - defensive selftest assertion
            raise AssertionError("expected ApiError on missing jq")
    return True
