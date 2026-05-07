"""Phase-2 CLI helpers: shared option decorators, output rendering,
``--jq <expr>`` filter, and the ``register_subcommand`` factory used
to bind a Python API function to a Click subcommand without 100+
hand-written wrappers.
"""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import sys
from typing import Callable, List, Optional

import click

from animedex.config import Config
from animedex.models.common import AnimedexModel, ApiError
from animedex.render.json_renderer import render_json
from animedex.render.tty import render_for_stream


# ---------- shared options ----------


def common_phase2_options(func: Callable) -> Callable:
    """Decorator: attach ``--json``, ``--jq``, ``--no-cache``,
    ``--cache``, ``--rate``, ``--no-source`` flags to a Phase-2 CLI
    subcommand.

    ``--jq`` runs the rendered JSON through the system ``jq`` binary;
    when ``jq`` isn't on PATH the command falls through to printing
    un-filtered JSON and warns once on stderr.
    """
    func = click.option("--no-source", is_flag=True, default=False, help="Drop _source attribution from JSON output.")(
        func
    )
    func = click.option("--rate", type=click.Choice(["normal", "slow"]), default="normal", help="Voluntary slowdown.")(
        func
    )
    func = click.option("--cache", "cache_ttl", type=int, default=None, help="Override cache TTL in seconds.")(func)
    func = click.option("--no-cache", is_flag=True, default=False, help="Skip cache lookup and write.")(func)
    func = click.option("--jq", "jq_expr", default=None, help="Filter JSON output through jq. Forces JSON mode.")(func)
    func = click.option(
        "--json", "json_flag", is_flag=True, default=False, help="Always emit JSON (default auto-switches by TTY)."
    )(func)
    return func


# ---------- rendering ----------


def _is_terminal(stream) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)())


def _to_json_text(model_or_list, *, include_source: bool) -> str:
    """Render a model (or list of models) as a single JSON string."""
    if isinstance(model_or_list, list):
        items = [
            json.loads(render_json(m, include_source=include_source)) if isinstance(m, AnimedexModel) else m
            for m in model_or_list
        ]
        return json.dumps(items, indent=2, ensure_ascii=False)
    if isinstance(model_or_list, AnimedexModel):
        return render_json(model_or_list, include_source=include_source)
    return json.dumps(model_or_list, indent=2, ensure_ascii=False, default=str)


def _to_tty_text(model_or_list) -> str:
    """Render a model (or list) as TTY text."""
    if isinstance(model_or_list, list):
        return "\n".join(_to_tty_text(item) for item in model_or_list)
    if isinstance(model_or_list, AnimedexModel):
        return render_for_stream(model_or_list, sys.stdout)
    return str(model_or_list)


def _apply_jq(json_text: str, jq_expr: str) -> str:
    """Filter ``json_text`` through ``jq <expr>``. Falls back to
    un-filtered output with a stderr warning when ``jq`` is not on
    PATH."""
    if shutil.which("jq") is None:
        click.echo("warning: jq not on PATH; printing un-filtered JSON.", err=True)
        return json_text
    proc = subprocess.run(
        ["jq", jq_expr],
        input=json_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        click.echo(f"jq error: {proc.stderr.strip()}", err=True)
        # Re-raise so the CLI exit code reflects the failure.
        raise click.ClickException(proc.stderr.strip() or "jq filter failed")
    return proc.stdout


def emit(
    result,
    *,
    json_flag: bool,
    jq_expr: Optional[str],
    no_source: bool,
):
    """Render ``result`` (single model or list) and ``echo`` it to
    stdout. Picks JSON or TTY based on flags + isatty.
    """
    include_source = not no_source
    force_json = json_flag or jq_expr is not None
    use_json = force_json or not _is_terminal(sys.stdout)

    if use_json:
        text = _to_json_text(result, include_source=include_source)
        if jq_expr is not None:
            text = _apply_jq(text, jq_expr)
    else:
        text = _to_tty_text(result)

    click.echo(text.rstrip("\n"))


# ---------- python-api → click ----------


_BACKEND_POLICY = {
    "anilist": {
        "backend_line": "AniList (graphql.anilist.co); GraphQL.",
        "rate_line": "30 req/min anonymous (degraded from baseline 90/min).",
        "guidance": "Read-only AniList query. Anonymous reads cover the public schema; auth-required endpoints raise auth-required at runtime (Phase 8).",
    },
    "jikan": {
        "backend_line": "Jikan v4 (api.jikan.moe); REST scraper of MyAnimeList.",
        "rate_line": "60 req/min, 3 req/sec.",
        "guidance": "Read-only Jikan endpoint; fully anonymous. Long-tail sub-endpoints return JikanGenericResponse — use --jq to filter structurally.",
    },
    "trace": {
        "backend_line": "Trace.moe (api.trace.moe).",
        "rate_line": "Anonymous concurrency 1, quota 100/month.",
        "guidance": "Identify anime scenes from screenshots; --anilist-info inlines AnimeTitle so callers can chain into anilist commands without an extra round-trip.",
    },
}


def _build_policy_docstring(name: str, summary: str, backend: str) -> str:
    """Compose a policy-lint-compliant docstring with the three
    structural blocks (Backend / Rate limit / Agent Guidance).

    The Click ``\\f`` formfeed cuts the policy blocks off the human
    --help so the output stays readable; ``inspect.getdoc`` (used by
    the policy lint) keeps them.
    """
    pol = _BACKEND_POLICY.get(backend, _BACKEND_POLICY["anilist"])
    return (
        f"{summary}\n"
        "\n\f\n"
        f"Backend: {pol['backend_line']}\n"
        "\n"
        f"Rate limit: {pol['rate_line']}\n"
        "\n"
        "--- LLM Agent Guidance ---\n"
        f"{pol['guidance']}\n"
        "--- End ---\n"
    )


def register_subcommand(
    group: click.Group, name: str, fn: Callable, *, help: Optional[str] = None, command_aliases: List[str] = None
):
    """Bind a Python API ``fn`` as a Click subcommand on ``group``.

    Argument inference:
    * Positional parameters with no default → ``click.argument``.
    * Keyword parameters with default → ``click.option``.
    * ``config`` / ``no_cache`` / ``cache_ttl`` / ``rate`` are
      injected via :func:`common_phase2_options` (suppressed from
      auto-binding).

    The wrapped command builds the ``Config`` from the common flags
    and passes it as ``config=...``. The function's return value is
    rendered via :func:`emit`.
    """
    sig = inspect.signature(fn)
    skip = {"config", "no_cache", "cache_ttl", "rate", "session", "cache", "rate_limit_registry"}

    decorators = []
    for pname, param in sig.parameters.items():
        if pname in skip:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.default is inspect.Parameter.empty:
            decorators.append(click.argument(pname))
        else:
            ptype = type(param.default) if param.default is not None else str
            if ptype is bool:
                decorators.append(
                    click.option(f"--{pname.replace('_', '-')}", pname, is_flag=True, default=param.default)
                )
            else:
                py_type = param.annotation if param.annotation is not inspect.Parameter.empty else type(param.default)
                # narrow to click-supported types
                if py_type in (int, float, str, bool):
                    click_type = py_type
                else:
                    click_type = str
                decorators.append(
                    click.option(
                        f"--{pname.replace('_', '-')}",
                        pname,
                        default=param.default,
                        type=click_type,
                        show_default=True,
                    )
                )

    summary = (help or (fn.__doc__ or fn.__name__).strip().split("\n", 1)[0]).rstrip(".") + "."
    backend = group.name  # group is named "anilist" / "jikan" / "trace"
    fn_module = getattr(fn, "__module__", None)
    fn_qualname = getattr(fn, "__name__", None)

    def _resolve_fn():
        """Look up ``fn`` from its module at call time so test
        ``monkeypatch.setattr(module, name, ...)`` reaches the
        wrapped command. Falls back to the original closure when
        the lookup is impossible (e.g. lambdas)."""
        if fn_module and fn_qualname:
            import importlib

            try:
                mod = importlib.import_module(fn_module)
                return getattr(mod, fn_qualname, fn)
            except ImportError:
                return fn
        return fn

    @group.command(name=name, help=summary)
    @common_phase2_options
    def _cmd(json_flag, jq_expr, no_cache, cache_ttl, rate, no_source, **kwargs):
        cfg = Config(
            no_cache=no_cache,
            cache_ttl_seconds=cache_ttl,
            rate=rate,
            source_attribution=not no_source,
        )
        try:
            result = _resolve_fn()(config=cfg, **kwargs)
        except ApiError as exc:
            raise click.ClickException(str(exc))
        emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)

    # Inject the policy-compliant docstring AFTER click.command() so
    # that inspect.getdoc() (which the policy lint uses) sees the
    # full three-block structure but Click's --help (which stops at
    # ``\f``) shows only the summary.
    _cmd.__doc__ = _build_policy_docstring(name, summary, backend)
    if hasattr(_cmd, "callback") and _cmd.callback is not None:
        _cmd.callback.__doc__ = _cmd.__doc__
    if hasattr(_cmd, "help"):
        _cmd.help = _cmd.__doc__

    # Apply argument decorators in reverse so the resulting Click
    # command's positional argument order matches the function's.
    for dec in reversed(decorators):
        _cmd = dec(_cmd)

    return _cmd
