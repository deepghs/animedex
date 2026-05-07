# animedex

> A read-only, multi-source, `gh`-flavored command-line interface for anime and manga metadata, designed to be used both by humans and by LLM agents (Codex, Claude, and friends).

[![Build status](https://github.com/deepghs/animedex/actions/workflows/test.yml/badge.svg)](https://github.com/deepghs/animedex/actions/workflows/test.yml) [![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](./LICENSE) [![Status: WIP](https://img.shields.io/badge/status-WIP%20%28scaffold%20only%29-orange.svg)](./plans)

## Status: work in progress

**This repository currently contains only the project scaffolding.** None of the per-backend commands described in the plans are implemented yet. The CLI installs and runs, but every command is a stub.

What you can do today:

```bash
pip install -e .
animedex --version
animedex status
```

That is the entire functional surface at the moment. The point of this early commit is to lock in:

- the project name (`animedex`, available on both PyPI and GitHub);
- the staged design (see `plans/`);
- the layered policy model that separates protocol contracts from content preferences (see `plans/02-design-policy-as-docstring.md`);
- the build, test, and release scaffolding so contributors can wire up one backend at a time without re-litigating infrastructure choices.

If you found this repository looking for a working anime CLI, come back in a few weeks. If you are here to read or contribute to the design, keep reading.

## Human Agency Principle (the top rule)

> **The human user has full choice. Whatever the consequences of that choice, they are the user's. animedex's job is to inform and to warn, not to gate, refuse, or override.**

This rule supersedes every other design guideline in the repository. Concretely it means:

- No content filters are injected on the user's behalf. If you ask Danbooru for explicit tags, you get explicit results. If you ask Waifu.im for NSFW images, you get NSFW images. The CLI does not decide for you.
- No `--unsafe`, `--nsfw`, `--allow-...`, `--force` flags. Those exist purely to ask "are you sure?" and they are paternalism. We do not ship them.
- No double-confirmation prompts. If a command name says it does something, running the command does that thing.
- We do warn, in `--help` text and in docstrings, about every upstream whose data class or legal posture the user might want to be aware of: legal greys (MangaDex scanlations), content classifications (Danbooru `rating:e`), bandwidth costs, rate-limit ceilings. The warning is informational; it never blocks.

For LLM agents, the same surface comes with explicit usage guidance in each docstring (see [`plans/02-design-policy-as-docstring.md`](./plans/02-design-policy-as-docstring.md)). Agents read docstrings; their alignment training does the rest.

The only constraints animedex enforces unilaterally are **technical contracts** (rate limits the upstream actually punishes, mandatory headers, read-only HTTP methods). Those are physics, not preferences.

## What animedex aims to be

A single command, modelled on [`gh`](https://cli.github.com/), that:

1. Aggregates the public anime / manga APIs surveyed in [`plans/01-public-apis-anime-survey.md`](./plans/01-public-apis-anime-survey.md).
2. Is **read-only by project scope**. animedex does not implement `add to list`, `set score`, `favourite`, or upload commands. The read-only choice keeps auth small and lets us promise the CLI does not disturb your existing account state. (See plan 03.)
3. Names the source of every piece of data it returns. There is no "magic merged answer"; every field carries `[src: anilist]` / `[src: jikan]` / etc. so you always know who told you what.
4. Treats safety policy as **documentation, not flags**. See [`plans/02-design-policy-as-docstring.md`](./plans/02-design-policy-as-docstring.md).
5. Provides a `gh api`-style raw passthrough (`animedex api <backend>`) so anything not covered by a high-level command is still one HTTP call away.

## Repository map

```
animedex/                Source package (currently scaffold only)
animedex_cli.py          Top-level CLI shim
test/                    Unit tests (currently smoke tests)
plans/                   Staged design documents - read these in order
  README.md              Index and reading order
  01-public-apis-anime-survey.md
  02-design-policy-as-docstring.md
  03-cli-architecture-gh-flavored.md
  04-roadmap-and-mvp.md
docs/                    Documentation source (not yet wired up)
.github/workflows/       CI: test, release, release-test
AGENTS.md                Repository policy for human + agent contributors
CLAUDE.md                Symlink to AGENTS.md
LICENSE                  Apache-2.0
```

## How to navigate as a contributor

1. Read [`plans/README.md`](./plans/README.md) and follow its recommended reading order.
2. Read [`AGENTS.md`](./AGENTS.md). It states the English-only and commit-identity policies that every change must respect.
3. Pick a phase from [`plans/04-roadmap-and-mvp.md`](./plans/04-roadmap-and-mvp.md). The MVP block (phases 0-2) is the next thing to ship; everything else builds on top.

## How to navigate as an LLM agent

If you are an LLM agent (e.g. Codex or Claude) working in this repo:

- Read `AGENTS.md` first; it is the binding policy for any change you make.
- Read the four plan documents in order before proposing implementations. The plans tell you not just *what* to build but *why* certain things are out of scope (e.g. writes, NSFW gating flags, content moderation in code rather than docs).
- When implementing a CLI command, follow the docstring template in `plans/02-design-policy-as-docstring.md` section 3. The lint check enforces it.

## Install

```bash
pip install -e .
```

PyPI publication will follow once the project clears the v0.1.0 milestone described in `plans/04-roadmap-and-mvp.md`.

## License

Apache License 2.0. See [`LICENSE`](./LICENSE).
