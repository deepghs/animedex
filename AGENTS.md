# Repository Guidelines

This file is the binding policy document for any contributor to this
repository, human or agent. The project is in active scaffolding; the
rules below are the small set of decisions we have already locked in.

A symlink at `CLAUDE.md` points here, so Claude Code, Codex, and any
other agent that auto-loads either filename will see the same content.
Do not maintain two copies.

## Core Repository Rules

This repository is **English-only**. All tracked content must be written
in English, including source code, comments, docstrings, Markdown files,
generated documentation, examples, configuration text, commit messages,
and any new human-readable strings added to the codebase. Do not
introduce any other language into repository files.

This rule also applies when using Codex, Claude Code, or any other agent.
The conversation language with the user may be anything, but every
repository-facing action must remain in English. That includes file
edits, code comments, log messages, generated README content, commit
messages, and any other text written into the repository or its git
history.

## Commit Identity Policy

Every commit created for this repository must use the git identity:

```bash
git config user.name "narugo1992"
git config user.email "narugo1992@deepghs.org"
```

Verify the active identity before creating a commit:

```bash
git config user.name
git config user.email
```

If your local identity differs, override it before committing. Do not
create commits under any other name or email. Do **not** modify the
global git config to do this; configure the identity at the repository
level only.

## GitHub CLI Identity Policy

When using the GitHub CLI for repository operations (issue listing,
release creation, repo administration, etc.), use the `narugo1992`
account. Do **not** call `gh auth switch` mid-session; instead set the
`GH_TOKEN` environment variable explicitly when an isolated identity is
required:

```bash
GH_TOKEN="$(gh auth token --user narugo1992)" gh <command>
```

Do not commit or otherwise persist the token value.

## Commit Message Style

Recent history follows a `dev(<author>): <summary>` style. New commits
should keep that structure with an English summary:

```text
dev(narugo1992): scaffold animedex package and CI workflows
dev(narugo1992): add anilist passthrough to animedex api
```

Keep the subject under 72 columns. Wrap the body if there is one;
explain the *why* in the body, not the *what* (the diff already shows
the what).

## Project Overview

**animedex** is a read-only, multi-source, gh-flavored command-line
interface for anime and manga metadata. It targets two parallel
audiences: humans interactively at a terminal, and LLM agents (Codex,
Claude, and similar) invoking the CLI as a tool.

The project is currently a scaffold. The implementation order, scope,
and design rationale live in `plans/` and are binding. In particular:

- `plans/01-public-apis-anime-survey.md` enumerates which upstream
  services we use, and which we do not.
- `plans/02-design-policy-as-docstring.md` specifies that policy
  guidance (NSFW handling, opt-in legal greys, etc.) lives in
  docstrings, **not** in command-line flags. Do not introduce
  `--nsfw`, `--unsafe`, `--allow-...`, `--write`, or similar flags.
- `plans/03-cli-architecture-gh-flavored.md` defines the canonical
  command tree and the `animedex api` raw passthrough.
- `plans/04-roadmap-and-mvp.md` orders the work.

## Scope Constraints (binding)

- **Read-only**: animedex never writes to a user account on any
  upstream service. No `list add`, no `set score`, no `favorite`,
  no upload. The `animedex api` passthrough rejects mutating HTTP
  methods before the request leaves the host.
- **Source attribution mandatory**: every datum surfaced by an
  aggregate command must carry its source. The TTY renderer prints
  `[src: anilist]`, the JSON renderer carries `_source`. Do not
  produce un-attributed merged data.
- **English in code, in docs, in commits**. (Restated for emphasis.)
- **No paternalistic flags**. See `plans/02-design-policy-as-docstring.md`
  for the full reasoning. If you find yourself reaching for `--nsfw`
  or `--allow-...`, stop and put the guidance in the docstring instead.

## Style and Tooling

- Python source targets Python 3.7+.
- Code comments and docstrings are reST (Sphinx-style).
- Keep dependencies minimal; new runtime dependencies require a brief
  justification in the commit body.
- Run `make test` before sending a change. If tests are added or
  updated, run them locally on the version you support.
- Run `flake8 animedex` for a quick lint pass. CI runs the full matrix.

## Adding a Backend

When you wire up a new backend (or a new endpoint on an existing one):

1. Add the per-command function under
   `animedex/backends/<name>/...` (the directory will be created when
   the first backend is implemented).
2. Each public function must have a docstring with three blocks:
   `Backend: ...`, `Rate limit: ...`, and
   `--- LLM Agent Guidance --- ... --- End ---`. The lint check
   (when present) enforces this.
3. Register the command on the `animedex` Click group, and also via
   the MCP registration helper.
4. Source attribution: every record returned must include
   `_source = "<backend-name>"`.
5. Cache: choose a sensible default TTL and document it in the
   docstring.
6. Rate limit: configure the backend's token bucket from a single
   place; do not duplicate caps across files.

## When in Doubt

Re-read `plans/` in order. If the answer is not there, propose an
update to the relevant plan document in the same change that introduces
the new behaviour. The plans are versioned alongside the code; they
must not drift.
