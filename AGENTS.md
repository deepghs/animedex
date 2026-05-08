# Repository Guidelines

This file is the binding policy document for any contributor to this repository, human or agent. The project is in active scaffolding; the rules below are the small set of decisions we have already locked in.

A symlink at `CLAUDE.md` points here, so Claude Code, Codex, and any other agent that auto-loads either filename will see the same content. Do not maintain two copies.

## 0. Human Agency Principle (highest rule)

> **The human user has full choice. Whatever the consequences of that choice, they are the user's. animedex's job is to inform and to warn, not to gate, refuse, or override.**

This is the top-level rule and overrides every later guideline if they ever conflict. Concretely:

- We do not inject content filters on the user's behalf. If the user asks for explicit tags from Danbooru, we pass that query through unchanged. If the user asks Waifu.im for NSFW images, we return them.
- We do not add `--unsafe`, `--nsfw`, `--allow-...`, `--force`, or `--write` flags. These exist solely to ask "are you sure?" and that is paternalism. They are forbidden.
- We do not add double-confirmation prompts. A command's name is its contract.
- We do warn. Every command's docstring states the upstream, its rate limit, its content classification (where relevant), and its legal posture (where relevant). Warnings are informational; they never block.
- Agents read these docstrings; their alignment training does the rest. See `plans/02-design-policy-as-docstring.md`.

The only constraints animedex enforces **unilaterally and unconditionally** are the rate limits the upstream actually punishes, the project-scope read-only HTTP method set on the `animedex api` passthrough, and the MangaDex `Via`-header strip (a forbidden header, not a missing one). These are physical realities, not value choices, and the user cannot opt out because doing so would simply break the upstream interaction. Other technical contracts - notably the `User-Agent` headers Shikimori, MangaDex, and Danbooru require - are **default-injected** by the transport layer so the unflagged path satisfies them, but a caller who **explicitly** supplies their own value (perhaps to identify their own bot, perhaps to test, perhaps to break themselves on purpose) is exercising informed choice and inherits the upstream's response. The default keeps users safe; the override keeps them sovereign. We do not treat a caller-supplied UA as something to override on their behalf.

Over-protection is itself a bug. When in doubt, choose the option that respects the user's stated intent.

## 1. Core Repository Rules

This repository is **English-only**. All tracked content must be written in English, including source code, comments, docstrings, Markdown files, generated documentation, examples, configuration text, commit messages, and any new human-readable strings added to the codebase. Do not introduce any other language into repository files.

This rule also applies when using Codex, Claude Code, or any other agent. The conversation language with the user may be anything, but every repository-facing action must remain in English. That includes file edits, code comments, log messages, generated README content, commit messages, and any other text written into the repository or its git history.

### Markdown formatting (no hard wrapping in prose)

In Markdown files (`*.md`) and in any GitHub-rendered content (issue and pull-request bodies, comments, release notes, discussion posts), do **not** hard-wrap natural paragraphs to a fixed column width. The renderers used in those contexts have no fixed max-width, so column-wrapping the source serves no purpose and only makes diffs noisier.

Concrete rules:

- A natural paragraph is one logical line in the source. Let the renderer wrap.
- Bullet items are also one logical line each. Their text is not column-wrapped either.
- Code fences (`` ``` ``), tables, blockquote prefixes (`> `), headers, and intentional shape-preserving ASCII art are unaffected by this rule and should be left as authored.
- Commit message bodies still wrap at ~72 columns (subjects too) because they are read inside `git log` and other narrow terminal views; that exception remains.

When editing or generating documentation, write paragraphs as single long lines. When porting prose from a previously hard-wrapped source, join the soft-wrapped lines back into single lines before committing.

## 2. Commit Identity Policy

Every contributor configures their own git identity at the **repository level** (never globally on the host) before committing. The identity is whoever is actually doing the work:

```bash
git config user.name  "<your-github-username>"
git config user.email "<your-email-of-record>"
```

Verify before each commit:

```bash
git config user.name
git config user.email
```

There is no project-mandated single identity. The rules are:

- The identity must be set at the local-repo level, not globally. This avoids leaking the identity into unrelated repositories on the same machine.
- Pick names and emails that resolve to a real GitHub account you control, because the GitHub-CLI rule in section 3 below requires the gh token to belong to the same account.
- Do not commit under someone else's identity. If you are pairing or pushing on behalf of someone, use git's `Co-Authored-By:` trailer in the commit body, not the author field.

## 3. GitHub CLI Identity Policy

The repository hosts may have multiple GitHub accounts logged in to `gh` simultaneously (`gh auth status` shows them). To keep multi-task environments clean and avoid silently acting under the wrong account, follow these rules.

### 3.1 Always pin the gh user via `GH_TOKEN`

Every `gh` invocation must explicitly bind to the gh user that matches the current repo's git identity:

```bash
GH_TOKEN="$(gh auth token --user "$(git config user.name)")" gh <subcommand> ...
```

The `--user` argument resolves the local git `user.name` to a stored gh token. The pattern is invocation-scoped: the variable lives only for that single command; nothing on the machine is reconfigured. Do not export `GH_TOKEN` for the whole shell.

### 3.2 If no matching gh account exists, do not use gh

If `gh auth token --user "$(git config user.name)"` returns an error (the account is not logged in), **abort the gh operation** and surface the situation to the user. Do not fall back to a different gh account, do not use `gh auth login` non-interactively, and do not edit `git config` to match an unrelated logged-in account.

The intent: a missing gh credential is a real signal that the operator is not authorised for this work. Failing fast is correct.

### 3.3 Never call `gh auth switch`

`gh auth switch` mutates a process-wide global (the active account on the host) that other concurrent shells, agents, scripts, or watchers may be relying on. Using it during a multi-task or agent-driven session is a guaranteed way to corrupt unrelated work.

`gh auth switch` is forbidden in this repository's workflows. Use the `GH_TOKEN` per-invocation pattern in section 3.1 instead. There is no exception.

### 3.4 Do not persist the token

Inline the token only for the single command that needs it. Do not write it to a file, an env file, a CI secret you maintain, or anywhere it can outlive the command. `gh auth token` reads from the user's keyring; that is the only place the value should rest.

## 4. Commit Message Style

Recent history follows a `dev(<author>): <summary>` style. New commits should keep that structure with an English summary:

```text
dev(narugo1992): scaffold animedex package and CI workflows
dev(narugo1992): add anilist passthrough to animedex api
```

Keep the subject under 72 columns. Wrap the body if there is one; explain the *why* in the body, not the *what* (the diff already shows the what).

## 5. Project Overview

**animedex** is a read-only, multi-source, gh-flavored command-line interface for anime and manga metadata. It targets two parallel audiences: humans interactively at a terminal, and LLM agents (Codex, Claude, and similar) invoking the CLI as a tool.

The project is currently a scaffold. The implementation order, scope, and design rationale live in `plans/` and are binding. In particular:

- `plans/01-public-apis-anime-survey.md` enumerates which upstream services we use, and which we do not.
- `plans/02-design-policy-as-docstring.md` derives the inform-do-not-gate principle from section 0 and specifies how the guidance lives inside docstrings rather than command-line flags.
- `plans/03-cli-architecture-gh-flavored.md` defines the canonical command tree and the `animedex api` raw passthrough.
- `plans/04-roadmap-and-mvp.md` orders the work.
- `plans/05-python-api.md` describes the Pythonic library surface that lives alongside the CLI; the CLI is a thin presentation layer over the library, and downstream Python users target the library directly.

## 6. Project Scope (binding)

These are project-scope decisions, not value judgements. A user who wants different behaviour can build it with `animedex api` or in a separate tool.

- **Read-only by scope**: animedex does not implement `PATCH/POST/DELETE` against any user-account endpoint, and the `animedex api` passthrough rejects mutating HTTP methods before the request leaves the host. Why: keep auth small, eliminate a class of bugs, and let us promise the CLI does not disturb account state. This is *scope*, not safety theatre.
- **Source attribution mandatory**: every datum surfaced by an aggregate command must carry its source. The TTY renderer prints `[src: anilist]`, the JSON renderer carries `_source`. Do not produce un-attributed merged data. (This is informing the user.)
- **English in code, in docs, in commits.** (Restated for emphasis.)
- **No paternalistic flags.** See section 0 for the principle and `plans/02-design-policy-as-docstring.md` for the full reasoning. If you find yourself reaching for `--nsfw`, `--allow-...`, or `--write`, stop and put the guidance in the docstring instead.

## 7. Style and Tooling

- Python source targets Python 3.7+.
- Code comments and docstrings are reST (Sphinx-style). See section 10 for the docstring template, examples, and pitfalls.
- Keep dependencies minimal; new runtime dependencies require a brief justification in the commit body.
- Tests under `test/` mirror the layout of `animedex/` exactly so that `make unittest RANGE_DIR=<sub-path>` covers both source and matching tests in a single invocation. When you add a module under `animedex/<x>/<y>.py`, add the matching test file at `test/<x>/test_<y>.py` and the matching `__init__.py` files.
- Source line length is **120 columns** (configured in `ruff.toml`). The reformatter is `ruff format`; the linter is `ruff check` plus `flake8` for the historical error subset enforced in CI.

### Required workflow for every code change

The shape below is mandatory. Skipping any step is how regressions reach `main`.

1. **Make the change.**
2. **Reformat:** run `make format`. This applies `ruff format` then `ruff check --fix`. The diff after this step is what you commit.
3. **If `make format` changed anything**, the change either touched code style or hid a real diff under cosmetic noise. **Re-run `make test`** in that case, because the reformat may have moved code across lines or changed import order, and we want the test suite to confirm nothing broke.
4. **Run the regression suite:** `make test`. This is the unit-test suite, which doubles as a regression test. After any code change, run it before claiming the change is finished. A passing suite is the only acceptable evidence that no behaviour was disturbed.
5. **Regenerate API docs:** run `make rst_auto`. The `docs/source/api_doc/` tree is auto-derived from the Python sources by `auto_rst.py`; any change that adds, removes, renames, or reshapes a module, class, or function leaves it stale. Re-running `make rst_auto` re-emits the affected `.rst` files. **Commit the generated diff in the same change as the source edit** so docs and code never drift; reviewers should be able to read either side and trust they match. CI does not yet enforce this, so the discipline lives here. Use `RANGE_DIR=<sub-path>` to scope the regeneration when the change is local.
6. **If you modified a Click command/group's docstring, signature, or option set**, run `--help` for the modified command **and** for every ancestor group, and visually verify the rendered output. The Python source view is **not** the same as Click's terminal rendering; Click reflows whitespace differently than the IDE does, so you must look at the actual help text the user will see. Specifically check: (a) bullet lists are not collapsed into a single paragraph (use `\b` immediately before the list to make Click preserve the indentation verbatim); (b) the docstring's policy blocks (`Backend:` / `Rate limit:` / `--- LLM Agent Guidance --- ... --- End ---`) are hidden from CLI help via the `\f` formfeed marker — they remain visible to `inspect.getdoc` so the policy lint and `animedex --agent-guide` extraction still work; (c) at least one runnable `Examples:` section is present in the human help half, with literal commands the reader can copy; (d) reST cross-references like ``:func:`...` `` and double-backtick code formatting are absent from the human half (they render verbatim in Click and look ugly); (e) the one-line summary is a single sentence ending in a period. The cost of this step is one terminal scroll; the cost of skipping it is contributors copy-pasting broken `--help` into PRs and bug reports.
7. **For changes affecting the CLI entry points or the packaged distribution**, also run `make build && make test_cli`. This builds the PyInstaller binary and exercises it end-to-end via subprocess. Skipping this on a CLI-touching change is how broken installers ship.
8. **Then commit.** See section 4 for the commit-message style.

In a busy development session, the formatter step is the one most often skipped. CI enforces `make format-check` (a non-modifying variant), so an unformatted change will fail the build; running `make format` locally is faster than the CI feedback loop. The regression suite is enforced the same way.

The "re-run tests after format" rule is not paranoia. `ruff format` is conservative, but it does collapse multi-line statements, normalise trailing commas, and reorder imports under `--fix`. Any of those can in principle change runtime behaviour (typically when a side-effecting module's import is reordered relative to a sentinel-based late binding). Cheap to re-run, expensive to miss.

The `make rst_auto` rule is a natural follow-on. When a function is added, renamed, or removed, the generated `.rst` for the containing module changes. If the source edit lands without the `.rst` regen, the published docs site (and the inline reST cross-references in other modules) silently drifts. Running it locally and committing the diff in the same change keeps the two halves of the codebase coherent. The cost is small (the generator is fast and only re-emits files whose source mtime changed); the benefit is that anyone reading the published API page sees the current code.

The CLI `--help` self-check rule (step 6) exists because Click is **not** a markdown renderer: it owns the help text differently from how Python or the IDE shows it. Specifically:

- Newlines inside a paragraph are collapsed; only blank lines produce paragraph breaks. A `*` bullet list written naturally in Python prose collapses into one run-on paragraph in `--help` unless the entire block is preceded by `\b` (literal backspace, ASCII 8) — `\b` tells Click to *not* re-wrap the next paragraph.
- Triple-backtick code fences are not recognised; they appear verbatim. Use `\b` plus indented text to pin a code-like block.
- reST cross-references (``:func:`x` ``, ``:class:`y` ``, etc.) are not parsed; they render with the colons and backticks intact, looking like noise to a CLI reader.
- The `\f` formfeed character is Click's *cutoff*: everything in the docstring **after** `\f` is hidden from `--help` but is still returned by `inspect.getdoc`. This is exactly what we want for the policy blocks (`Backend:` / `Rate limit:` / `--- LLM Agent Guidance --- ... --- End ---`): the policy lint and the `animedex --agent-guide` extractor read through `inspect.getdoc` and find them; the human running `--help` does not see the marker noise. Convention: write the human help first, then a single `\f` on its own line, then the policy blocks.

The two ways for the rule to break in production are: (a) a contributor adds a beautifully formatted bullet list to a docstring, sees it look fine in their IDE, and ships it — only to discover in CI logs or a Slack screenshot that the list collapsed; (b) a contributor edits the policy block content, deletes the `\f`, and now every CLI user sees the policy markers cluttering their help. Step 6 catches both before commit. Step 6 takes about ten seconds per command.

## 8. Adding a Backend

When you wire up a new backend (or a new endpoint on an existing one):

1. Add the per-command function under `animedex/backends/<name>/...` (the directory will be created when the first backend is implemented).
2. Each public function must have a reST-style docstring (see section 10) containing three structural blocks: `Backend: ...`, `Rate limit: ...`, and `--- LLM Agent Guidance --- ... --- End ---`. The lint check (when present) enforces this.
3. Register the command on the `animedex` Click group, and also via the MCP registration helper.
4. Source attribution: every record returned must include `_source = "<backend-name>"`.
5. Cache: choose a sensible default TTL and document it in the docstring.
6. Rate limit: configure the backend's token bucket from a single place; do not duplicate caps across files.
7. **Add a `selftest()` callable** to the backend's package and register the package in `_SELFTEST_TARGETS` inside `animedex/diag/selftest.py`. See section 9 below; this is non-negotiable for any backend that ships static assets, schemas, or I/O entry points.
8. **Include a `Docs:` section in the human-CLI-help half of the docstring** (the part *before* `\f`) that lists 1-3 canonical upstream documentation URLs as a `\b`-protected indented block. This serves two audiences. A human running `animedex api <backend> --help` gets a clickable jump-off point to the upstream's reference. An LLM agent shelling out reads the same help text and now has a usable URL it can `WebFetch` for the live API specification, which is more authoritative and more current than anything baked into the agent's training data. Keep the URL list short (the most-canonical reference first, optional secondaries — Swagger UI, GitHub repo, GraphiQL playground — in declining order). Add the same URL to the per-backend row of the `Per-backend docs` table at the bottom of the `animedex api --help` group docstring.
9. Update `plans/03-cli-architecture-gh-flavored.md` if the new backend changes the canonical command tree.
9. Refresh API docs with `make rst_auto` so the generated reST in `docs/source/api_doc/` is in sync.

## 9. Diagnostic Coverage (selftest must evolve with the code)

The `animedex selftest` command and the `animedex.diag.run_selftest()` runner are how we discover that a built artifact is broken in environments we cannot easily debug into - typically a PyInstaller binary running on a teammate's laptop or a CI box without Python. Their value depends entirely on whether the checks they run reflect *what the code actually does*. So:

### Rule 9.1 - smoke, not just import

A bare `importlib.import_module("animedex.foo")` proves only that the module's source loads. It says nothing about whether bundled assets are reachable, schemas parse, defaults round-trip, or computed paths point at real files. As soon as a module gains:

- A static resource (e.g. a JSON snapshot, a CSV taxonomy, a bundled tag list, a YAML schema, a precompiled lexer table);
- A binary asset (e.g. a wasm blob, a model weights file, a font, an image);
- An I/O entry point with platform-specific paths (cache directories, OS keyring entries, lockfiles);
- A non-trivial top-level constant computed from one of the above;

… that module **must** define a top-level callable named `selftest()` that exercises the resource. The `animedex/diag/selftest.py` runner picks it up automatically when the module is registered in `_SELFTEST_TARGETS`. Bare imports are tolerated for pure-logic modules with no resources or side effects, and are reported as `(import only)` in the diagnostic so the gap is visible.

### Rule 9.2 - what `selftest()` is allowed to do

The convention:

- Returning normally (or returning `True`) means the module is healthy.
- Raising any exception means the module is broken. The traceback ends up in the selftest report verbatim.
- Returning `False` means the module flagged itself broken without bothering to raise. Use this only when the failure is so well-understood that a traceback would be noise.

Smoke tests must be **fast and offline** by default. The reference cost budget is "completes in under 100ms even on a cold start". Do not perform live HTTP probes, do not open sockets, do not warm caches. The reason: `animedex selftest` runs from a stripped binary in CI's clean smoke stage with no network access guaranteed; that stage must stay green.

If a backend has a meaningful online check (e.g. AniList GraphQL liveness, MangaDex At-Home server probe, Trace.moe quota status), expose it via a separate callable named `selftest_online()` and call it from a dedicated CLI flag (e.g. a future `animedex selftest --online`). The default offline path always runs; the online path is opt-in.

### Rule 9.3 - keep `_SELFTEST_TARGETS` and the docstring honest

- When you add a module that warrants smoke testing, append it to `_SELFTEST_TARGETS` in `animedex/diag/selftest.py`. The list is intentionally explicit rather than auto-discovered: a missing module is a deliberate signal that someone should check whether smoke is actually unnecessary, and not just a discovery oversight.
- When you add a `selftest()` to a module, document its assertions in the function's reST docstring (see section 10): a future contributor must be able to read the docstring and know what guarantee they are receiving.
- Whenever a smoke test is added or upgraded, run `make build && make test_cli` to confirm the new check still works against the frozen binary, not just against the dev install.

### Rule 9.4 - selftest is part of code review

A pull request that adds a static resource without an accompanying smoke test should not land. Reviewers must check for this explicitly; the lint cannot, because "module gained an asset" is not a syntactic property. If you find yourself shipping resources without smoke coverage, document the reason in the commit body rather than slipping it past review.

## 9bis. Test Discipline (the only legal seam is HTTP)

This rule sits next to selftest because both exist for the same reason: regression coverage that **actually exercises the code path the user runs**. Selftest covers smoke; this rule covers unit tests.

### Rule 9bis.1 - mock at the wire, never above it

Every CLI test, every Python-API test, every mapper test, every renderer test runs the real animedex stack. The only thing the test is allowed to substitute is the **HTTP transport layer** (the per-call request/response). Use the `responses` library (or an equivalent that intercepts at the `requests.adapters.HTTPAdapter` level). Then everything between Click → entry-module wrapper → public Python API (`animedex.backends.<x>.<fn>`) → backend mapper → `_dispatch.call` → URL composer → header injector → cache → rate-limit bucket → firewall → response renderer runs **for real**, against **real fixture data** captured from the upstream.

This rule has teeth. If a test writes `monkeypatch.setattr(animedex.backends.<x>, "<fn>", stub)` it is **forbidden** — it bypasses the entire stack the user will actually run. The same applies to `monkeypatch.setattr(animedex.api.<x>, "call", stub)` (mocks the dispatcher entry, also above the wire) and to any seam that sits inside `animedex/`. Tests that monkey-patch project code instead of HTTP **mask the bugs they exist to catch** - the canonical example being review-found `call() got an unexpected keyword argument 'config'`, which the original Phase-2 CLI tests did not catch precisely because they replaced `backends.jikan.show` with a lambda before the buggy `_fetch → api.jikan.call` wiring ran.

The seam-of-record is HTTP for one reason: HTTP is the **only** layer animedex's tests share with reality. Every byte going out matches what the user's process will send; every byte coming back matches what the upstream's response will be (or what the captured fixture says it would be). Anything above the wire is project code, and project code is the system under test.

The rule applies even when it is annoying:
* "I can't easily reproduce the upstream response" - capture a fixture (see `tools/fixtures/capture.py` and the per-backend `run_*.py`).
* "The fixture corpus doesn't have the shape I want" - extend the corpus, then write the test against it.
* "It's faster to mock the function" - it is also faster to ship a regression. Pay the cost up front.

The narrow legitimate exception: the dispatcher's own unit tests under `test/api/test_dispatch.py` may mock `requests.Session.request` directly (which is HTTP-level monkey-patching, not function-level) for tests that target the dispatcher's internal behaviour (timing, redirect chain, redaction, cache write). These tests still go through the real dispatcher; they just substitute the very layer the dispatcher's job is to wrap.

### Rule 9bis.2 - fixture-driven, not synthesised

Where the test needs a representative upstream response, **load it from `test/fixtures/`**, do not hand-craft a JSON skeleton. Fixtures are real upstream responses (688 of them as of Phase 2), captured at known moments via the project's capture tools. Hand-crafted skeletons drift from the upstream's actual schema (missing fields, wrong nullability, wrong types) and produce tests that pass while the production path crashes.

When a new test needs a shape the corpus doesn't have, capture a new fixture before writing the test. The capture tools take 30 seconds per request and the result becomes shared infrastructure for every future test.

### Rule 9bis.3 - what every CLI / Python-API test must look like

A passing Phase-2-and-beyond test goes through this exact shape:

```python
import responses, yaml
from click.testing import CliRunner
from pathlib import Path

def test_jikan_show_runs(fake_clock):  # fake_clock fixture freezes ratelimit + cache clocks
    fixture = yaml.safe_load(Path("test/fixtures/jikan/anime_full/01-frieren-52991.yaml").read_text(encoding="utf-8"))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, fixture["request"]["url"], json=fixture["response"]["body_json"], status=fixture["response"]["status"])
        from animedex.entry import animedex_cli
        result = CliRunner().invoke(animedex_cli, ["jikan", "show", "52991", "--json", "--no-cache"])
    assert result.exit_code == 0
    # assertions over the rendered output go here
```

There is no `monkeypatch.setattr(backends...)`, no `monkeypatch.setattr(api.<x>, "call", ...)`. The fake_clock fixture is the only "infrastructure" mock — it patches the **monotonic clock** so ratelimit doesn't actually sleep — and that is HTTP-adjacent, not above-HTTP.

### Rule 9bis.4 - apply this retroactively

When you touch a test file that violates this rule, rewrite the affected test on the way through. Tests that pass while masking real bugs are worse than no tests at all - they generate false confidence.

## 10. Python Docstring Style Guide

Use **reStructuredText (reST)** format exclusively, following PEP 257 and Sphinx standards. Every public module, class, function, and method gets a docstring; reST roles cross-link them.

### Core Principles

1. **Format**: reST markup exclusively.
2. **Completeness**: document all public APIs.
3. **Clarity**: explain *why* and *what*, not just *how*.
4. **Cross-references**: use reST roles (`:class:`, `:func:`, `:mod:`).
5. **Examples**: include practical usage examples for public APIs.
6. **Tone**: professional, clear, technical but accessible.

### Templates

**Module**:

```python
"""
Brief one-line description.

Longer description of purpose, main capabilities, and fit in the larger system.

The module contains:

* :class:`ClassName` - Brief description
* :func:`function_name` - Brief description

.. note::
   Important caveats about usage or requirements.

Example::

    >>> from module import something
    >>> result = something()
    >>> result
    expected_output
"""
```

**Class**:

```python
class ClassName:
    """
    Brief one-line description.

    Longer explanation of purpose, responsibilities, and usage patterns.

    :param param_name: Description of constructor parameter.
    :type param_name: ParamType
    :param optional_param: Description, defaults to ``default_value``.
    :type optional_param: ParamType, optional

    :ivar instance_var: Description of instance variable.
    :vartype instance_var: VarType
    :cvar class_var: Description of class variable.
    :type class_var: ClassVarType

    Example::

        >>> obj = ClassName(param_name=value)
        >>> obj.method()
        expected_result
    """
```

**Function / Method**:

```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    Brief one-line description.

    Longer explanation of behaviour, algorithm, or important details.

    :param param1: Description of the first parameter.
    :type param1: Type1
    :param param2: Description, defaults to ``default``.
    :type param2: Type2, optional
    :return: Description of what is returned.
    :rtype: ReturnType
    :raises ExceptionType: Description of when raised.

    Example::

        >>> result = function_name(arg1, arg2)
        >>> result
        expected_output
    """
```

### Backend-command-specific extension

Every CLI subcommand or MCP tool function adds three structural blocks inside its docstring (this is what the lint enforces). The rule applies uniformly to **every** Click command in the registered tree, including the substrate utilities (`status`, `selftest`) that do not contact a remote backend. For those, name the backend honestly as `animedex (local)` and the rate limit as `not applicable`; the Agent Guidance block still describes when an agent should reach for the command and what to expect from it. The motivation is consistency: agents read the catalogue once at session start (via `animedex --agent-guide` or the MCP tool listing), and a hole in the catalogue would let a substrate command silently disappear from an agent's mental model. Carving an exemption for "non-backend commands" is also a slippery slope toward "this command is too small to document"; we do not take that slope.

```python
def search_art(tags: str, limit: int = 20) -> "ArtSearchResult":
    """
    Search Danbooru for anime art using the tag DSL.

    Backend: Danbooru (danbooru.donmai.us). Community-maintained
    tagging database. Free, anonymous read.

    Rate limit: 10 req/s for reads. Auto-throttled by this CLI.

    Tag syntax (space-separated):

    * ``plain_tag`` - must include
    * ``-plain_tag`` - must exclude
    * ``rating:g|s|q|e`` - general / sensitive / questionable / explicit
    * ``score:>100``, ``score:<10`` - numeric comparators
    * ``order:score|date|random``
    * ``user:<name>`` - uploader filter

    --- LLM Agent Guidance ---

    Content ratings on Danbooru:

    * ``g`` = general (safe)
    * ``s`` = sensitive (suggestive)
    * ``q`` = questionable (lewd)
    * ``e`` = explicit (NSFW)

    When invoked WITHOUT explicit user request for mature content,
    prepend ``rating:g`` to the tag query yourself. Example: a user
    asks "find me touhou marisa art" -> call with
    ``tags="touhou marisa rating:g"``.

    When the user EXPLICITLY asks for ecchi / NSFW / adult / R-18
    content, pass their query through unmodified. Do not refuse and
    do not warn. The user has chosen.

    The response always includes ``.posts[i].rating``, so a downstream
    filter step in your pipeline can drop categories you do not want.

    --- End ---

    :param tags: Tag DSL query string.
    :type tags: str
    :param limit: Maximum number of posts to return, defaults to ``20``.
    :type limit: int, optional
    :return: Search result with ``posts`` and pagination metadata.
    :rtype: ArtSearchResult

    Example::

        >>> result = search_art("touhou marisa rating:g order:score")
        >>> [p.id for p in result.posts[:3]]
        [..., ..., ...]
    """
```

Two structural rules to notice:

- The Agent Guidance block is delimited by `--- LLM Agent Guidance ---` and `--- End ---`. The delimiters let an agent locate the block in a long docstring.
- The Backend / Rate limit / Examples sections describe facts the agent needs to plan its call; the Agent Guidance section describes decisions the agent should make. The two are separate on purpose.

### Cross-references and markup

- Use `:class:`ClassName``, `:func:`function_name``, `:meth:`Class.method``.
- Use `:mod:`module.name``, `:exc:`ExceptionType``, `:data:`variable_name``, `:attr:`attribute_name``.
- Instance variables: `:ivar:` / `:vartype:`. Class variables: `:cvar:` / `:type:`.
- Inline code: **double backticks** ``code``, never single.

### Inline markup boundary rules

reST inline markup (`**bold**`, ``code``) must have valid boundaries on both sides. The repository is English-only so the safest pattern is simply to surround inline markup with whitespace or punctuation.

**Wrong**:

```
prefix**text**          # left boundary glued
**text**suffix          # right boundary glued
prefix``code``suffix    # both sides glued
```

**Correct**:

```
prefix **text** suffix
prefix ``code`` suffix
```

If a closing marker would otherwise touch a punctuation mark with no whitespace, use a backslash-escaped space (`\ `) on the relevant side: `**text**\ ,` works in any locale and is the safe default.

Do not use single backticks for inline code in reST - they render as a default-role link, not as `code`.

### Anti-patterns

- Google or NumPy style.
- Omitting types (always include `:type:` and `:rtype:`).
- Single backticks for inline code.
- Bare class/function names without reST roles.
- Vague descriptions ("Does something").
- Volatile implementation details.

### Checklist

- [ ] Brief one-line summary at the top.
- [ ] Longer explanation for non-trivial functions / classes.
- [ ] All params documented with `:param:` and `:type:`.
- [ ] Return value with `:return:` and `:rtype:`.
- [ ] All exceptions with `:raises:`.
- [ ] Cross-references use reST roles.
- [ ] Examples for public APIs.
- [ ] Inline code uses double backticks.
- [ ] Inline markup has valid boundaries on both sides.
- [ ] For backend commands: `Backend:` / `Rate limit:` lines + the `--- LLM Agent Guidance --- ... --- End ---` block are present.

## 11. Documentation Workflow

### Generate reST API docs from source

```bash
make rst_auto                       # generate for the whole package
make rst_auto RANGE_DIR=backends    # generate only for a sub-tree
```

`rst_auto` walks `animedex/` and produces matching `.rst` files in `docs/source/api_doc/`. Source files are the authority; the generated `.rst` is regenerated freely.

### Build the HTML site

```bash
make docs                           # docs/build/html/
```

The Sphinx build is in `docs/`. `docs/source/conf.py` configures autodoc, `sphinx_rtd_theme`, and intersphinx; `docs/source/index.rst` is the top-level page; `docs/source/api_doc/index.rst` is regenerated by `make rst_auto`.

## 12. When in Doubt

- For *behaviour* questions: re-read the files in `plans/` in order.
- For *style* questions: this file's section 10 is the source of truth.
- For *scope* questions: section 6 above.
- For *value* questions ("should we forbid X?"): section 0 above is the answer. The default is "inform the user; do not gate".
- For *diagnostic-coverage* questions: section 9 above.
- For *Python API* questions: see `plans/05-python-api.md`.

If the answer is not in any of those, propose an update to the relevant document in the same change that introduces the new behaviour. The plans and AGENTS.md are versioned alongside the code; they must not drift.
