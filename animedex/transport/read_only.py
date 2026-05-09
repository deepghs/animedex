"""
Advisory method classification for raw API calls.

The raw ``animedex api`` passthrough does not block HTTP methods on
the user's behalf. This module keeps a small, non-enforcing classifier
for documentation, diagnostics, and callers that want to label a
request before sending it. A result of ``False`` is information only;
the transport layer still forwards the user's chosen method and path.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional


def _allow(_path: str) -> bool:
    return True


def _deny(_path: str) -> bool:
    return False


def _path_equals(target: str) -> Callable[[str], bool]:
    def matcher(path: str) -> bool:
        return path == target

    return matcher


_ADVISORY_RULES: Dict[str, Dict[str, Callable[[str], bool]]] = {
    "anilist": {
        "GET": _allow,
        "POST": _path_equals("/"),
    },
    "jikan": {
        "GET": _allow,
        "POST": _deny,
    },
    "kitsu": {
        "GET": _allow,
        "POST": _deny,
    },
    "mangadex": {
        "GET": _allow,
        "POST": _deny,
    },
    "danbooru": {
        "GET": _allow,
        "POST": _deny,
    },
    "shikimori": {
        "GET": _allow,
        "POST": _path_equals("/api/graphql"),
    },
    "ann": {
        "GET": _allow,
        "POST": _deny,
    },
    "trace": {
        "GET": _allow,
        "POST": _path_equals("/search"),
    },
    "nekos": {
        "GET": _allow,
        "POST": _deny,
    },
    "waifu": {
        "GET": _allow,
        "POST": _deny,
    },
    "ghibli": {
        "GET": _allow,
        "POST": _deny,
    },
    "quote": {
        "GET": _allow,
        "POST": _deny,
    },
}


def known_backends() -> tuple:
    """Return the tuple of backends known to the advisory classifier.

    :return: Ordered tuple of backend identifiers.
    :rtype: tuple
    """
    return tuple(_ADVISORY_RULES.keys())


def classify_read_only(backend: str, method: str, path: str) -> Optional[bool]:
    """Classify whether a method/path pair is known to be read-only.

    ``True`` means the pair is a known read, ``False`` means the pair
    is not known to be read-only, and ``None`` means the backend is not
    in the advisory registry. The classifier never raises and never
    blocks transport.

    :param backend: Backend identifier (e.g. ``"anilist"``).
    :type backend: str
    :param method: HTTP method.
    :type method: str
    :param path: Request path.
    :type path: str
    :return: Advisory classification.
    :rtype: bool or None
    """
    rules = _ADVISORY_RULES.get(backend)
    if rules is None:
        return None
    matcher = rules.get(method.upper())
    return bool(matcher(path)) if matcher is not None else False


def selftest() -> bool:
    """Smoke-test the advisory classifier.

    Confirms representative read and non-read classifications without
    asserting that any request would be blocked.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert classify_read_only("anilist", "POST", "/") is True
    assert classify_read_only("jikan", "DELETE", "/anime") is False
    assert classify_read_only("not-a-backend", "GET", "/") is None
    return True
