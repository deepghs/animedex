"""
``--json field1,field2`` field projection.

The CLI's ``--json field1,field2`` flag (``plans/03 §9``) is a
post-processor over the JSON renderer's output: it keeps only the
named top-level fields. Unknown fields raise a typed
:class:`ApiError` so a typo at the call site is loud, not silent.
"""

from __future__ import annotations

from typing import Any, Dict, List

from animedex.models.common import ApiError


def parse_field_string(spec: str) -> List[str]:
    """Split a comma-separated field spec into a list of field names.

    Strips whitespace, drops empty entries.

    :param spec: Comma-separated field spec
                  (e.g. ``"id, title, episodes"``).
    :type spec: str
    :return: List of field names; empty list when ``spec`` is
             empty.
    :rtype: list of str
    """
    if not spec:
        return []
    return [token.strip() for token in spec.split(",") if token.strip()]


def project_fields(payload: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """Return a dict containing only ``fields`` keys from ``payload``.

    An empty ``fields`` list returns ``payload`` unchanged. An
    unknown field raises :class:`ApiError` with
    ``reason="unknown-field"`` naming the offending field.

    :param payload: A dict-shaped JSON-decoded payload.
    :type payload: dict
    :param fields: Top-level field names to keep.
    :type fields: list of str
    :return: The projected dict.
    :rtype: dict
    :raises ApiError: When ``fields`` names a key not present in
                       ``payload``.
    """
    if not fields:
        return payload
    out: Dict[str, Any] = {}
    for field in fields:
        if field not in payload:
            raise ApiError(
                f"unknown field: {field!r}",
                reason="unknown-field",
            )
        out[field] = payload[field]
    return out


def selftest() -> bool:
    """Smoke-test field projection.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert parse_field_string("a, b ,c") == ["a", "b", "c"]
    assert project_fields({"a": 1, "b": 2}, ["a"]) == {"a": 1}
    return True
