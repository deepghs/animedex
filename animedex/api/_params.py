"""
Query-string parameter helpers for raw API requests.

The raw passthrough accepts paths that already contain a query string
and also accepts structured field injections from the CLI. This module
keeps the merge rules in one place so single requests and paginated
requests compose parameters the same way.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import parse_qsl, urlsplit, urlunsplit


def _copy_params(params: Optional[dict]) -> Dict[str, Any]:
    """Return a shallow, list-preserving copy of ``params``.

    :param params: Optional query parameter mapping.
    :type params: dict or None
    :return: Mutable copy suitable for further merging.
    :rtype: dict
    """
    out: Dict[str, Any] = {}
    for key, value in (params or {}).items():
        if isinstance(value, list):
            out[key] = list(value)
        elif isinstance(value, tuple):
            out[key] = list(value)
        else:
            out[key] = value
    return out


def add_query_pair(params: Dict[str, Any], key: str, value: Any) -> None:
    """Append one query-string pair to ``params``.

    Repeated keys become lists so requests can render them as repeated
    query parameters.

    :param params: Mutable query parameter mapping.
    :type params: dict
    :param key: Parameter name.
    :type key: str
    :param value: Parameter value.
    :type value: Any
    :return: ``None``.
    :rtype: None
    """
    if key not in params:
        params[key] = value
        return
    current = params[key]
    if isinstance(current, list):
        current.append(value)
    else:
        params[key] = [current, value]


def merge_params(base: Optional[dict], overlay: Optional[dict]) -> Dict[str, Any]:
    """Merge two query-parameter mappings with last-write-wins keys.

    :param base: Existing parameters.
    :type base: dict or None
    :param overlay: Parameters that override ``base``.
    :type overlay: dict or None
    :return: Merged mutable mapping.
    :rtype: dict
    """
    out = _copy_params(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, tuple):
            out[key] = list(value)
        else:
            out[key] = value
    return out


def split_path_query(path: str, params: Optional[dict] = None) -> Tuple[str, Dict[str, Any]]:
    """Split a path's query string and merge it with explicit params.

    Query parameters embedded in ``path`` are decoded into a mapping.
    Repeated keys become list values. Explicit ``params`` then
    override those decoded values, matching gh-style last-write-wins
    field semantics.

    :param path: Relative or absolute URL path.
    :type path: str
    :param params: Explicit query parameters.
    :type params: dict or None
    :return: ``(path_without_query, merged_params)``.
    :rtype: tuple[str, dict]
    """
    parts = urlsplit(path)
    out: Dict[str, Any] = {}
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        add_query_pair(out, key, value)

    clean_path = urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))
    if not clean_path:
        clean_path = path.split("?", 1)[0] or "/"
    return clean_path, merge_params(out, params)


def first_int(params: dict, keys: Iterable[str], default: int) -> int:
    """Return the first integer-like parameter from ``keys``.

    :param params: Query parameter mapping.
    :type params: dict
    :param keys: Candidate parameter names in priority order.
    :type keys: iterable[str]
    :param default: Value used when no candidate is present or
                    integer-like.
    :type default: int
    :return: Parsed integer or ``default``.
    :rtype: int
    """
    for key in keys:
        value = params.get(key)
        if isinstance(value, list):
            value = value[-1] if value else None
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default
