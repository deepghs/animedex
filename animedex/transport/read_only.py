"""
Read-only firewall for the ``animedex api`` passthrough layer.

The CLI promises read-only behaviour against every supported
upstream (``plans/03 §7``). Naive method-level filtering does not
work because two of our backends use ``POST`` for legitimate reads:

* AniList GraphQL: every read goes ``POST /``.
* Trace.moe: image search is ``POST /search`` with the image bytes
  as the body.

This module owns the per-backend rules that decide which combinations
of ``(method, path)`` are reads, and rejects everything else with a
typed :class:`~animedex.models.common.ApiError` whose ``reason`` is
``"read-only"`` so callers do not have to grep error strings.

The rules are deliberately enumerated per backend, not derived from
heuristics, so a future backend addition is a code change reviewers
can trace.
"""

from __future__ import annotations

from typing import Callable, Dict

from animedex.models.common import ApiError


def _allow(_path: str) -> bool:
    return True


def _deny(_path: str) -> bool:
    return False


def _path_equals(target: str) -> Callable[[str], bool]:
    def matcher(path: str) -> bool:
        return path == target

    return matcher


def _allowed_methods_for_path(rules: Dict[str, Callable[[str], bool]], path: str) -> tuple:
    return tuple(method for method, matcher in sorted(rules.items()) if matcher(path))


# Per-backend `(method, path) -> allowed?` matrix.
#
# `GET` is universally allowed. The mapping below covers `POST` and
# every mutating method the read-only firewall must reason about.
# Methods not listed for a backend are rejected.
_RULES: Dict[str, Dict[str, Callable[[str], bool]]] = {
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
        # Shikimori exposes both REST (GET only) and GraphQL on
        # ``POST /api/graphql``; whitelist that one path.
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
    """Return the tuple of backends the firewall reasons about.

    :return: Ordered tuple of backend identifiers.
    :rtype: tuple
    """
    return tuple(_RULES.keys())


def enforce_read_only(backend: str, method: str, path: str) -> None:
    """Reject the request when it violates the read-only contract.

    The function returns silently when the request is a permitted
    read; otherwise it raises :class:`ApiError` with ``reason`` set
    to ``"read-only"`` for known-mutation rejections, or
    ``"unknown-backend"`` for typos in the backend identifier.

    :param backend: Backend identifier (e.g. ``"anilist"``).
    :type backend: str
    :param method: HTTP method, upper-cased
                    (e.g. ``"GET"``, ``"POST"``).
    :type method: str
    :param path: Request path. For GraphQL backends it is the path
                  on which the GraphQL document is posted (typically
                  ``"/"``).
    :type path: str
    :raises ApiError: When the request is not a permitted read.
    """
    rules = _RULES.get(backend)
    if rules is None:
        raise ApiError(
            f"unknown backend: {backend!r}",
            backend=backend,
            reason="unknown-backend",
        )
    matcher = rules.get(method.upper())
    if matcher is None or not matcher(path):
        method_up = method.upper()
        allowed = ", ".join(_allowed_methods_for_path(rules, path)) or "none"
        raise ApiError(
            f"{method_up} rejected by animedex's read-only policy for {backend}: "
            f"{method_up} {path} is not a permitted read; allowed read methods for this path are {allowed}",
            backend=backend,
            reason="read-only",
        )


def selftest() -> bool:
    """Smoke-test the firewall against representative inputs.

    Exercises one positive and one negative case per known backend
    so a future rule regression surfaces in the diagnostic before
    any backend issues a real request.

    :return: ``True`` on success.
    :rtype: bool
    """
    enforce_read_only("anilist", "GET", "/")
    enforce_read_only("anilist", "POST", "/")
    enforce_read_only("trace", "POST", "/search")
    enforce_read_only("ghibli", "GET", "/films")
    enforce_read_only("quote", "GET", "/quotes/random")
    for backend in known_backends():
        enforce_read_only(backend, "GET", "/anything")
    for method in ("PUT", "PATCH", "DELETE"):
        try:
            enforce_read_only("anilist", method, "/")
        except ApiError as exc:
            assert exc.reason == "read-only"
        else:  # pragma: no cover - defensive selftest assertion
            raise AssertionError(f"{method} should have been rejected")
    return True
