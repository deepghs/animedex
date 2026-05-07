"""
Tests for :mod:`animedex.mcp.register` and :mod:`animedex.mcp.tool_decorator`.

The MCP layer is lazy by design: ``import animedex`` does not import
the ``mcp`` package, and merely importing this submodule does not
register anything. The registration entry point
:func:`register_animedex_tools` accepts a duck-typed server object
(anything with an ``add_tool`` method) so unit tests can verify the
wiring without pulling in a real MCP runtime.
"""

from __future__ import annotations

import click
import pytest


pytestmark = pytest.mark.unittest


class _FakeServer:
    def __init__(self):
        self.tools = []

    def add_tool(self, *, name, description, handler):
        self.tools.append({"name": name, "description": description, "handler": handler})


class TestRegisterAnimedexTools:
    def test_no_side_effects_on_import(self):
        """Importing the module must not touch the server."""
        import animedex.mcp.register  # noqa: F401  - import is the test

        # Reaching this line means the module imported cleanly.

    def test_registers_one_tool_per_command_with_guidance(self):
        from animedex.mcp.register import register_animedex_tools

        @click.group()
        def root():
            pass

        @root.command()
        def echo() -> None:
            """Synthetic command.

            Backend: _selftest.

            Rate limit: 1 req/s.

            --- LLM Agent Guidance ---
            Synthetic guidance.
            --- End ---
            """

        server = _FakeServer()
        register_animedex_tools(server, group=root)

        assert len(server.tools) == 1
        assert server.tools[0]["name"] == "echo"
        assert "Synthetic guidance" in server.tools[0]["description"]

    def test_skips_command_without_agent_guidance(self):
        from animedex.mcp.register import register_animedex_tools

        @click.group()
        def root():
            pass

        @root.command()
        def naked() -> None:
            """Just a command, no guidance block."""

        server = _FakeServer()
        register_animedex_tools(server, group=root)

        assert server.tools == []

    def test_uses_animedex_cli_when_no_group_given(self):
        from animedex.entry import animedex_cli
        from animedex.mcp.register import register_animedex_tools

        server = _FakeServer()
        register_animedex_tools(server)
        # Phase 0 wires Agent Guidance blocks for the built-in
        # `status` / `selftest` utilities; backend commands arrive in
        # later phases. The contract here is "registration succeeds
        # against the real animedex_cli without raising".
        registered_names = [tool["name"] for tool in server.tools]
        assert "status" in registered_names
        assert "selftest" in registered_names
        assert animedex_cli is not None  # smoke


class TestSelftest:
    def test_register_selftest_runs(self):
        from animedex.mcp import register

        assert register.selftest() is True

    def test_tool_decorator_selftest_runs(self):
        from animedex.mcp import tool_decorator

        assert tool_decorator.selftest() is True


class TestToolDecorator:
    def test_decorator_marks_callable(self):
        from animedex.mcp.tool_decorator import is_mcp_tool, mcp_tool

        @mcp_tool(name="example.tool")
        def fn():
            """doc"""

        assert is_mcp_tool(fn)

    def test_decorator_remembers_name(self):
        from animedex.mcp.tool_decorator import mcp_tool, mcp_tool_name

        @mcp_tool(name="example.tool")
        def fn():
            """doc"""

        assert mcp_tool_name(fn) == "example.tool"

    def test_decorator_does_not_change_callable_behaviour(self):
        from animedex.mcp.tool_decorator import mcp_tool

        @mcp_tool(name="x")
        def fn(value):
            return value * 2

        assert fn(3) == 6
