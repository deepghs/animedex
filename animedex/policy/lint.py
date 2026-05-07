"""
Docstring lint for backend commands and MCP tools.

The lint enforces ``plans/02`` §4 on a Click command tree: every
``@cli.command(...)`` / ``@mcp.tool(...)`` callable must have a
docstring containing:

* a ``Backend:`` line that names the upstream;
* a ``Rate limit:`` line stating the documented cap;
* a block delimited by ``--- LLM Agent Guidance ---`` and
  ``--- End ---`` for the agent's policy text.

The helpers below operate on Click command objects so the lint can
also drive the auto-extracted Agents Reference page in the docs
build (``plans/02 §4`` and the ``animedex --agent-guide`` aggregator).
"""

from __future__ import annotations

import inspect
import re
import sys
from typing import Any, Dict, List, Optional

import click


_AGENT_GUIDANCE_BEGIN = "--- LLM Agent Guidance ---"
_AGENT_GUIDANCE_END = "--- End ---"


def _resolve_callable(command: click.Command) -> Any:
    callback = command.callback
    if callback is None:
        return command
    return callback


def _docstring(command: click.Command) -> str:
    return inspect.getdoc(_resolve_callable(command)) or ""


def check_command_docstring(command: click.Command) -> List[str]:
    """Validate one Click command's docstring against the policy template.

    :param command: A Click :class:`click.Command` (the decorated
                     callable, not a group).
    :type command: click.Command
    :return: List of human-readable problem descriptions; empty when
             the docstring is well-formed.
    :rtype: list of str
    """
    text = _docstring(command)
    problems: List[str] = []
    if not re.search(r"^\s*Backend:", text, re.MULTILINE):
        problems.append("missing 'Backend:' line")
    if not re.search(r"^\s*Rate limit:", text, re.MULTILINE):
        problems.append("missing 'Rate limit:' line")
    if _AGENT_GUIDANCE_BEGIN not in text:
        problems.append(f"missing '{_AGENT_GUIDANCE_BEGIN}' block opener")
    elif _AGENT_GUIDANCE_END not in text:
        problems.append(f"missing '{_AGENT_GUIDANCE_END}' block closer")
    return problems


def lint_group(group: click.Group) -> List[Dict[str, Any]]:
    """Walk a Click group recursively and collect every problem.

    :param group: A Click :class:`click.Group` (e.g. the top-level
                   ``animedex`` group).
    :type group: click.Group
    :return: List of ``{"command": "<name path>", "problems":
             [...]}`` dicts. Empty when every nested command is
             well-formed.
    :rtype: list of dict
    """
    out: List[Dict[str, Any]] = []
    for name, sub in group.commands.items():
        if isinstance(sub, click.Group):
            for entry in lint_group(sub):
                out.append({"command": f"{name} {entry['command']}", "problems": entry["problems"]})
            continue
        problems = check_command_docstring(sub)
        if problems:
            out.append({"command": name, "problems": problems})
    return out


def extract_agent_guidance(command: click.Command) -> Optional[str]:
    """Extract the ``--- LLM Agent Guidance ---`` block, if present.

    :param command: A Click :class:`click.Command`.
    :type command: click.Command
    :return: Text between the begin and end delimiters, stripped.
             ``None`` when the block is absent or malformed.
    :rtype: str or None
    """
    text = _docstring(command)
    begin = text.find(_AGENT_GUIDANCE_BEGIN)
    if begin < 0:
        return None
    end = text.find(_AGENT_GUIDANCE_END, begin)
    if (
        end < 0
    ):  # pragma: no cover - guarded by the lint itself; a docstring with the begin marker but no end marker would already fail check_command_docstring before reaching this helper.
        return None
    block = text[begin + len(_AGENT_GUIDANCE_BEGIN) : end]
    return block.strip()


def collect_agent_guidance(group: click.Group) -> List[Dict[str, str]]:
    """Walk a Click group and return every command's guidance block.

    :param group: A Click :class:`click.Group`.
    :type group: click.Group
    :return: List of ``{"command": "<name path>", "guidance": "..."}``
             dicts, in tree-walk order, for every command that has a
             guidance block.
    :rtype: list of dict
    """
    out: List[Dict[str, str]] = []
    for name, sub in group.commands.items():
        if isinstance(sub, click.Group):
            for entry in collect_agent_guidance(sub):
                out.append({"command": f"{name} {entry['command']}", "guidance": entry["guidance"]})
            continue
        guidance = extract_agent_guidance(sub)
        if guidance is not None:
            out.append({"command": name, "guidance": guidance})
    return out


def selftest() -> bool:
    """Smoke-test the lint helpers.

    Builds a synthetic Click command with the well-formed shape and
    confirms ``check_command_docstring`` returns no problems and
    ``extract_agent_guidance`` returns the block.

    :return: ``True`` on success.
    :rtype: bool
    """

    @click.command()
    def cmd() -> None:
        """Smoke command.

        Backend: _selftest.

        Rate limit: 1 req/s.

        --- LLM Agent Guidance ---
        none.
        --- End ---
        """

    assert check_command_docstring(cmd) == []
    assert extract_agent_guidance(cmd) is not None
    return True


def main(argv: Optional[List[str]] = None) -> int:
    """Console-script entry point for ``python -m animedex.policy.lint``.

    Iterates over the registered ``animedex`` Click group and exits
    non-zero when any command violates the policy template.

    :param argv: Argument list; currently unused (lint scope is
                  always the entire registered group).
    :type argv: list of str or None
    :return: Process exit code (``0`` on success, ``1`` on policy
             violation).
    :rtype: int
    """
    from animedex.entry import animedex_cli

    issues = lint_group(animedex_cli)
    if not issues:
        print("animedex docstring lint: OK")
        return 0
    print("animedex docstring lint: FAIL", file=sys.stderr)
    for entry in issues:
        for prob in entry["problems"]:
            print(f"  - {entry['command']}: {prob}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
