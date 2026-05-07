"""
``register_animedex_tools`` - lazy MCP registration entry point.

The function walks a Click group (defaulting to the registered
top-level :data:`animedex.entry.animedex_cli`), extracts each leaf
command's :func:`animedex.policy.lint.extract_agent_guidance` block,
and calls the duck-typed server object's ``add_tool`` method with
the command name, the guidance block as the tool description, and
the underlying callable as the handler.

Tool name convention: ``animedex.<dotted-command-path>``. A top-level
command ``status`` registers as ``"animedex.status"``; a nested
``backends jikan search`` registers as ``"animedex.backends.jikan.search"``.
This matches the example in :func:`animedex.mcp.tool_decorator.mcp_tool`'s
docstring so the two MCP-side surfaces use the same ID space.

The registration is explicit (the caller passes the server in)
because ``import animedex`` should never spin up an MCP server as a
side effect. The signature is duck-typed so unit tests can pass a
small fake server, and so the eventual wiring to the upstream
``mcp`` package can use whatever object that package exposes.
"""

from __future__ import annotations

from typing import Any, Optional

import click


def register_animedex_tools(server: Any, *, group: Optional[click.Group] = None) -> int:
    """Register every animedex command with an Agent Guidance block.

    :param server: A duck-typed object with an ``add_tool(name=...,
                    description=..., handler=...)`` method. The
                    Phase 8 implementation will pass the real MCP
                    server; tests pass a small fake.
    :type server: Any
    :param group: A Click group to walk. Defaults to
                   :data:`animedex.entry.animedex_cli` when ``None``.
    :type group: click.Group or None
    :return: Number of commands registered.
    :rtype: int
    """
    from animedex.policy.lint import collect_agent_guidance

    if group is None:
        from animedex.entry import animedex_cli

        group = animedex_cli

    blocks = collect_agent_guidance(group)
    count = 0
    for entry in blocks:
        # Resolve the actual command object so the handler we pass
        # back is the bare callback, not the Click wrapper. This is
        # what the upstream MCP server will eventually invoke.
        command = group
        for token in entry["command"].split():
            command = command.commands[token] if isinstance(command, click.Group) else None
            if command is None:  # pragma: no cover - defensive; collect_agent_guidance only emits paths it just walked.
                break
        handler = command.callback if isinstance(command, click.Command) else None
        # Convert the space-joined Click path ("backends jikan search")
        # into the dotted form documented by `mcp_tool` ("animedex.backends.jikan.search").
        tool_name = "animedex." + ".".join(entry["command"].split())
        server.add_tool(
            name=tool_name,
            description=entry["guidance"],
            handler=handler,
        )
        count += 1
    return count


def selftest() -> bool:
    """Smoke-test the registration entry point.

    Builds a synthetic Click group with one well-formed command,
    registers it against a tiny fake server, and asserts the
    metadata round-trips. Stays import-only against the real
    ``mcp`` package; the actual MCP runtime ships in Phase 8.

    :return: ``True`` on success.
    :rtype: bool
    """

    class _FakeServer:
        def __init__(self):
            self.tools: list = []

        def add_tool(self, *, name, description, handler):
            self.tools.append((name, description, handler))

    @click.group()
    def root():
        pass  # pragma: no cover - click never invokes the group body

    @root.command()
    def hello() -> None:
        """Smoke command.

        Backend: _selftest.

        Rate limit: 1 req/s.

        --- LLM Agent Guidance ---
        smoke guidance.
        --- End ---
        """

    server = _FakeServer()
    count = register_animedex_tools(server, group=root)
    assert count == 1
    assert server.tools[0][0] == "animedex.hello"
    assert "smoke guidance" in server.tools[0][1]
    return True
