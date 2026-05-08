"""CLI helpers: shared option decorators, output rendering,
``--jq <expr>`` filter, and the ``register_subcommand`` factory used
to bind a Python API function to a Click subcommand without
hand-written wrappers per endpoint.
"""

from __future__ import annotations

import inspect
import json
import sys
from typing import Callable, List, Optional

import click

from animedex.config import Config
from animedex.models.common import AnimedexModel, ApiError
from animedex.render.jq import apply_jq as _native_apply_jq
from animedex.render.json_renderer import render_json
from animedex.render.tty import is_terminal as _is_terminal
from animedex.render.tty import render_tty


# ---------- shared options ----------


def common_options(func: Callable) -> Callable:
    """Decorator: attach ``--json``, ``--jq``, ``--no-cache``,
    ``--cache``, ``--rate``, ``--no-source`` flags to a CLI subcommand.

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
    """Render a model (or list) as TTY text. Calls
    :func:`animedex.render.tty.render_tty` directly so the ``emit``
    caller's ``use_json`` decision is honoured — going through
    ``render_for_stream`` would re-check isatty(stdout) and bounce
    list[Anime] into the JSON branch when stdout isn't a real TTY."""
    if isinstance(model_or_list, list):
        return "\n".join(_to_tty_text(item) for item in model_or_list)
    if isinstance(model_or_list, AnimedexModel):
        return render_tty(model_or_list)
    return str(model_or_list)


def _apply_jq(json_text: str, jq_expr: str) -> str:
    """Filter ``json_text`` through ``jq <expr>`` using the bundled
    :pypi:`jq` wheel. Typed :class:`ApiError`s from
    :func:`animedex.render.jq.apply_jq` are surfaced as
    :class:`click.ClickException` so the CLI exits non-zero with a
    clean one-line error rather than a Python traceback."""
    try:
        return _native_apply_jq(json_text, jq_expr)
    except ApiError as exc:
        raise click.ClickException(str(exc)) from exc


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
        "guidance": "Read-only AniList query. Anonymous reads cover the public schema; auth-required endpoints raise auth-required at runtime until token storage lands.",
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


def _build_policy_docstring(
    name: str,
    summary: str,
    backend: str,
    guidance_override: Optional[str] = None,
) -> str:
    """Compose a policy-lint-compliant docstring with the three
    structural blocks (Backend / Rate limit / Agent Guidance).

    The Click ``\\f`` formfeed cuts the policy blocks off the human
    --help so the output stays readable; ``inspect.getdoc`` (used by
    the policy lint) keeps them.

    :param name: Subcommand name (kept for diagnostic purposes).
    :type name: str
    :param summary: One-line human summary of the command.
    :type summary: str
    :param backend: Backend group name. Looked up in
                     :data:`_BACKEND_POLICY` for the Backend /
                     Rate-limit lines and the default guidance.
    :type backend: str
    :param guidance_override: Operation-specific Agent-Guidance text.
                               When set, replaces the backend-wide
                               default for this one docstring; the
                               Backend / Rate-limit lines stay
                               backend-wide. Use this for operations
                               where the right behaviour depends on
                               the call (NSFW filter handling, privacy
                               carve-outs, etc.) rather than on the
                               backend.
    :type guidance_override: str or None
    :raises ApiError: ``reason='unknown-backend'`` when ``backend`` is
                       not in :data:`_BACKEND_POLICY`. Falling back
                       silently would hide typos at the call site.
    """
    if backend not in _BACKEND_POLICY:
        raise ApiError(
            f"unknown backend {backend!r}; expected one of {sorted(_BACKEND_POLICY)}",
            backend=backend,
            reason="unknown-backend",
        )
    pol = _BACKEND_POLICY[backend]
    guidance = guidance_override if guidance_override is not None else pol["guidance"]
    return (
        f"{summary}\n"
        "\n\f\n"
        f"Backend: {pol['backend_line']}\n"
        "\n"
        f"Rate limit: {pol['rate_line']}\n"
        "\n"
        "--- LLM Agent Guidance ---\n"
        f"{guidance}\n"
        "--- End ---\n"
    )


def register_subcommand(
    group: click.Group,
    name: str,
    fn: Callable,
    *,
    help: Optional[str] = None,
    command_aliases: List[str] = None,
    guidance_override: Optional[str] = None,
):
    """Bind a Python API ``fn`` as a Click subcommand on ``group``.

    Argument inference:
    * Positional parameters with no default → ``click.argument``.
    * Keyword parameters with default → ``click.option``.
    * ``config`` / ``no_cache`` / ``cache_ttl`` / ``rate`` are
      injected via :func:`common_options` (suppressed from
      auto-binding).

    The wrapped command builds the ``Config`` from the common flags
    and passes it as ``config=...``. The function's return value is
    rendered via :func:`emit`.
    """
    sig = inspect.signature(fn)
    skip = {"config", "no_cache", "cache_ttl", "rate", "session", "cache", "rate_limit_registry"}
    # Conventional optional-positional kwarg names. ``jikan search
    # Frieren`` must work even though ``jikan.search(q=None)`` is
    # technically a kwarg with a default. We promote these by name to
    # positional-optional Click arguments so the CLI feels natural.
    positional_optional_names = {"q", "query", "search"}

    # Resolve forward-reference annotations (the backends use
    # ``from __future__ import annotations`` so e.g. ``per_page: int``
    # arrives as the *string* ``'int'`` in inspect.signature). Without
    # ``get_type_hints`` we'd fall through to ``click_type=str`` for
    # every typed kwarg, and the int-comparison code paths inside the
    # mapper would crash with TypeError("'<' not supported between
    # instances of 'int' and 'str'") at runtime.
    try:
        resolved_hints = inspect.get_annotations(fn, eval_str=True)  # py3.10+
    except (NameError, AttributeError):
        from typing import get_type_hints as _th

        try:
            resolved_hints = _th(fn)
        except Exception:
            resolved_hints = {}

    def _click_type(annotation, default):
        """Map a (possibly resolved) annotation + default to a Click
        scalar type. Falls back to str for unknown types."""
        # Direct int/float/str/bool
        if annotation in (int, float, str, bool):
            return annotation
        # Optional[X] / Union[X, None]
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            type_args = [a for a in getattr(annotation, "__args__", ()) if a is not type(None)]
            if len(type_args) == 1 and type_args[0] in (int, float, str, bool):
                return type_args[0]
        # Fall back to default's runtime type, but only if it is a
        # primitive scalar. Otherwise plain str so Click can still
        # accept user input.
        if default is not None and type(default) in (int, float, str, bool):
            return type(default)
        return str

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
            # The typed ``ApiError`` keeps its ``[backend=... reason=...]``
            # prefix. ``str(exc)`` produces a single-line message that
            # ``ClickException`` prints to stderr.
            raise click.ClickException(str(exc))
        except click.ClickException:
            # Already a Click error (e.g. from inside emit/_apply_jq);
            # let Click handle it without re-wrapping.
            raise
        except Exception as exc:
            # Anything else — pydantic ValidationError from upstream
            # schema drift, TypeError from a partial response,
            # ConnectionError from the wire — surfaces as a clean
            # one-line Click error rather than a raw Python traceback.
            raise click.ClickException(f"{type(exc).__name__}: {exc}")
        emit(result, json_flag=json_flag, jq_expr=jq_expr, no_source=no_source)

    # Apply decorators bottom-up (closest to function = innermost).
    # Click reads decorators outer-to-inner for positional argument
    # order, so the LAST decorator applied is the FIRST argument
    # consumed from argv. Therefore we apply common_options
    # first (innermost), then keyword options, then positional
    # arguments in REVERSE source order (so argument(year) ends up
    # outermost and gets argv[0]).
    cmd_fn = common_options(_cmd)
    arg_decs = []
    opt_decs = []
    for pname, param in sig.parameters.items():
        if pname in skip:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        annotation = resolved_hints.get(pname, param.annotation)
        if param.default is inspect.Parameter.empty:
            arg_type = _click_type(annotation, None) if annotation is not inspect.Parameter.empty else str
            arg_decs.append(click.argument(pname, type=arg_type))
        elif pname in positional_optional_names and param.default is None:
            # Promote q / query / search to positional-optional. Lets
            # ``jikan search Frieren`` parse Frieren as q while
            # ``jikan top-anime`` (no positional) still works.
            arg_type = _click_type(annotation, None)
            arg_decs.append(click.argument(pname, type=arg_type, required=False))
        elif isinstance(param.default, bool):
            opt_decs.append(click.option(f"--{pname.replace('_', '-')}", pname, is_flag=True, default=param.default))
        else:
            click_type = _click_type(annotation, param.default)
            opt_decs.append(
                click.option(
                    f"--{pname.replace('_', '-')}",
                    pname,
                    default=param.default,
                    type=click_type,
                    show_default=True,
                )
            )

    # Inner-to-outer: options first (in any order), then arguments in
    # REVERSE so the first source-order argument ends up outermost.
    for opt in opt_decs:
        cmd_fn = opt(cmd_fn)
    for arg in reversed(arg_decs):
        cmd_fn = arg(cmd_fn)

    # Now register with the group. group.command(name) returns a
    # decorator that converts the function into a click.Command.
    cmd = group.command(name=name, help=summary)(cmd_fn)

    # Inject policy-compliant docstring (Backend / Rate limit /
    # Agent Guidance) so the policy lint stays green. ``\f`` cuts
    # the policy blocks off Click's --help; ``inspect.getdoc`` (used
    # by the lint) keeps them.
    full_doc = _build_policy_docstring(name, summary, backend, guidance_override=guidance_override)
    cmd.__doc__ = full_doc
    if cmd.callback is not None:
        cmd.callback.__doc__ = full_doc
    cmd.help = full_doc

    return cmd
