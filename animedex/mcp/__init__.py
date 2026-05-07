"""
MCP (Model Context Protocol) scaffold for animedex.

The package is lazy by design: it does not import the ``mcp``
package at import time, so installing animedex without the optional
``[mcp]`` extra still works. The two submodules expose a small,
duck-typed surface so tests can verify the wiring without pulling in
a real MCP runtime:

* :mod:`animedex.mcp.tool_decorator` - the ``@mcp_tool(name=...)``
  marker that flags a callable as an MCP-eligible tool. The
  decorator is intentionally minimal; it stores metadata on the
  function object and returns it unchanged so unit tests can call
  the wrapped callable directly.
* :mod:`animedex.mcp.register` - the ``register_animedex_tools``
  entry point that walks a Click group, extracts each command's
  Agent Guidance block, and registers a tool with a duck-typed MCP
  server (anything that exposes ``add_tool(name, description,
  handler)``).

The actual ``animedex mcp serve`` CLI subcommand and the binding to
the upstream MCP server library land in Phase 8; this scaffold
exists so backend code in Phases 1-7 can use the decorator and so
the registry mechanism is testable in isolation.
"""
