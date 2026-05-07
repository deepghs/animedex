"""
Lightweight ``@mcp_tool`` decorator.

The decorator marks a callable as MCP-eligible without altering the
callable's runtime behaviour. Backends will eventually layer the
real MCP-package wiring on top of this marker; until then the
decorator gives backend authors a single, stable annotation site.

The module avoids importing the upstream ``mcp`` package so it can
be safely imported in environments where the optional ``[mcp]``
extra is not installed.
"""

from __future__ import annotations

from typing import Any, Callable


_MCP_TOOL_FLAG = "_animedex_mcp_tool"
_MCP_TOOL_NAME = "_animedex_mcp_tool_name"


def mcp_tool(*, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as an MCP-eligible tool.

    The decorator stores ``name`` on the function object so
    :func:`register_animedex_tools` (in :mod:`animedex.mcp.register`)
    can pick it up. The returned callable is the original callable,
    unchanged; no wrapping, no behaviour shift.

    :param name: MCP tool identifier
                  (e.g. ``"animedex.anilist.search"``).
    :type name: str
    :return: A decorator that marks and returns the callable.
    :rtype: Callable
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, _MCP_TOOL_FLAG, True)
        setattr(fn, _MCP_TOOL_NAME, name)
        return fn

    return _decorator


def is_mcp_tool(fn: Callable[..., Any]) -> bool:
    """Return ``True`` when ``fn`` was decorated by :func:`mcp_tool`.

    :param fn: A callable.
    :type fn: Callable
    :return: Whether the marker is present.
    :rtype: bool
    """
    return bool(getattr(fn, _MCP_TOOL_FLAG, False))


def mcp_tool_name(fn: Callable[..., Any]) -> str:
    """Return the registered MCP tool name for ``fn``.

    :param fn: A callable previously decorated by :func:`mcp_tool`.
    :type fn: Callable
    :return: The stored MCP tool identifier.
    :rtype: str
    :raises AttributeError: When ``fn`` was not decorated.
    """
    return getattr(fn, _MCP_TOOL_NAME)


def selftest() -> bool:
    """Smoke-test the decorator.

    :return: ``True`` on success.
    :rtype: bool
    """

    @mcp_tool(name="_selftest.tool")
    def _fn() -> int:
        return 1

    assert is_mcp_tool(_fn) is True
    assert mcp_tool_name(_fn) == "_selftest.tool"
    assert _fn() == 1
    return True
