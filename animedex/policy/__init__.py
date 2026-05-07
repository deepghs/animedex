"""
Docstring-as-policy enforcement for animedex.

Per ``plans/02`` the project's content / NSFW / agent-guidance
policy lives in docstrings, not in command-line flags. This package
ships the lint that asserts every backend command and every MCP
tool carries the three required structural blocks (``Backend:``,
``Rate limit:``, the ``--- LLM Agent Guidance ---`` /
``--- End ---`` delimited block), and the helper that extracts the
guidance text for the ``animedex --agent-guide`` command.

The package is import-safe: it does not pull in any backend module.
"""
