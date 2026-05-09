# animedex

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/animedex)](https://pypi.org/project/animedex/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/animedex)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/animedex)
![PyPI - Downloads](https://img.shields.io/pypi/dm/animedex)

![Loc](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/narugo1992/84fb1b7646cd29b1305e90e3cad6f392/raw/loc.json)
![Comments](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/narugo1992/84fb1b7646cd29b1305e90e3cad6f392/raw/comments.json)
[![codecov](https://codecov.io/gh/deepghs/animedex/graph/badge.svg)](https://codecov.io/gh/deepghs/animedex)
[![Documentation Status](https://readthedocs.org/projects/animedex/badge/?version=latest)](https://animedex.readthedocs.io/en/latest/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/deepghs/animedex)

[![Code Test](https://github.com/deepghs/animedex/workflows/Code%20Test/badge.svg)](https://github.com/deepghs/animedex/actions?query=workflow%3A%22Code+Test%22)
[![Release Test](https://github.com/deepghs/animedex/workflows/Release%20Test/badge.svg)](https://github.com/deepghs/animedex/actions?query=workflow%3A%22Release+Test%22)
[![Badge Creation](https://github.com/deepghs/animedex/workflows/Badge%20Creation/badge.svg)](https://github.com/deepghs/animedex/actions?query=workflow%3A%22Badge+Creation%22)
[![Package Release](https://github.com/deepghs/animedex/workflows/Package%20Release/badge.svg)](https://github.com/deepghs/animedex/actions?query=workflow%3A%22Package+Release%22)

[![GitHub stars](https://img.shields.io/github/stars/deepghs/animedex)](https://github.com/deepghs/animedex/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/deepghs/animedex)](https://github.com/deepghs/animedex/network)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/deepghs/animedex)
[![GitHub issues](https://img.shields.io/github/issues/deepghs/animedex)](https://github.com/deepghs/animedex/issues)
[![GitHub pulls](https://img.shields.io/github/issues-pr/deepghs/animedex)](https://github.com/deepghs/animedex/pulls)
[![Contributors](https://img.shields.io/github/contributors/deepghs/animedex)](https://github.com/deepghs/animedex/graphs/contributors)
[![GitHub license](https://img.shields.io/github/license/deepghs/animedex)](https://github.com/deepghs/animedex/blob/main/LICENSE)

</div>

---

> A read-only, multi-source, [`gh`](https://cli.github.com/)-flavored command-line interface for anime and manga metadata, designed to be used both by humans and by LLM agents (Codex, Claude, and friends).

<div align="center">

![animedex demo](https://raw.githubusercontent.com/deepghs/animedex/main/docs/source/_static/gifs/hero.gif)

</div>

Documentation: <https://animedex.readthedocs.io/en/latest/>

## Why animedex?

There are a dozen public anime APIs. AniList has the cleanest GraphQL surface but degraded rate limits. Jikan scrapes MyAnimeList and is the deepest catalogue. Trace.moe identifies a scene from a screenshot. nekos.best curates SFW art. Each is great at one thing — and each speaks a different protocol, has its own rate limit, and shapes responses differently.

`animedex` is one CLI (and one Python library) over all of them, with three guarantees:

- **Source-attributed**: every datum on screen carries `[src: anilist]` / `[src: jikan]` / etc. There is no "merged answer"; you always know who told you what.
- **Read-only by project scope**: no `add to list`, no `set score`, no upload. Auth is small, account state stays untouched.
- **Inform, do not gate**: rate limits, content classifications, and legal greys are documented in `--help` and agent-guidance blocks; the CLI does not refuse, second-guess, or impose content filters on the user's behalf.

The CLI is a thin presentation layer over an installable Python package — anything you can run at the prompt is one `from animedex.backends.X import show` away.

## What works today

| Backend | High-level commands | Raw passthrough | Status |
|---|---|---|---|
| **AniList** (graphql.anilist.co) | `animedex anilist` — search / show / character / staff / studio / schedule / trending / user / + 20 long-tail endpoints (28 anonymous, plus 4 auth-required stubs) | `animedex api anilist '<graphql-query>'` | live |
| **Jikan v4** (api.jikan.moe; MyAnimeList view) | `animedex jikan` — 87 anonymous endpoints across anime / manga / character / person / producer / season / top / random / users / clubs / magazines / genres / watch | `animedex api jikan /anime/52991` | live |
| **Kitsu** (kitsu.io/api/edge; JSON:API library aggregator) | `animedex kitsu` — 38 anonymous endpoints across anime / manga / characters / people / producers / mappings / streaming / categories / users | `animedex api kitsu /anime/7442` | live |
| **MangaDex** (api.mangadex.org; scanlation aggregator) | `animedex mangadex` — 26 anonymous endpoints (search / show / feed / chapter / cover / aggregate / statistics / authors / groups / lists) plus 13 authenticated reads (`me` / `my-follows-*` / `my-history` / `my-manga-status` / `my-manga-read-markers`) | `animedex api mangadex /manga/...` | live |
| **Danbooru** (danbooru.donmai.us; tag-DSL art catalogue) | `animedex danbooru` — 57 anonymous endpoints (search / post / artist / tag / pool / count / autocomplete / iqdb-query / wiki / forum / commentary / votes / versions / moderation / operational) plus 2 authenticated reads (`profile` / `saved-searches`) | `animedex api danbooru /posts.json` | live |
| **Waifu.im** (api.waifu.im; SFW + NSFW art) | `animedex waifu` — 9 anonymous endpoints (`tags` / `images` / `artists` / per-id + per-slug lookups / `stats-public`) plus 1 authenticated read (`me`) | `animedex api waifu /images?...` | live |
| **Trace.moe** (api.trace.moe) | `animedex trace` — search by image (`--url` or `--input <bytes>`), `quota` | `animedex api trace /me` | live |
| **nekos.best v2** (nekos.best/api/v2; SFW art / GIF) | `animedex nekos` — `categories`, `categories-full`, `image <category>`, `search` | `animedex api nekos /husbando` | live |
| **Shikimori** (shikimori.io; REST + GraphQL catalogue) | `animedex shikimori` — calendar / search / show / screenshots / videos / characters / staff / similar / related / external-links / topics / studios / genres | `animedex api shikimori <path>` | live |
| **ANN Encyclopedia** (cdn.animenewsnetwork.com; XML) | `animedex ann` — show / search / reports with typed XML warning handling | `animedex api ann <path>` | live |
| Ghibli, AnimeChan, MAL v2 | — | — | not yet implemented |

The `animedex api <backend>` passthrough is wired for ten backends. Every passthrough call honours the project's read-only firewall (`PUT/PATCH/DELETE` and unwhitelisted `POST` paths are rejected before hitting the wire) and the per-upstream `User-Agent` requirements.

## Try it in 30 seconds

```bash
pip install -e .

# AniList: GraphQL fetch + jq projection on the result
animedex anilist show 154587 --jq '.title.romaji'
# => "Sousou no Frieren"

# Jikan: MyAnimeList full record
animedex jikan show 52991 --jq '.data.title'
# => "Sousou no Frieren"

# Trace.moe: identify a scene
animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info --jq '.[0].anilist_title.romaji'

# nekos.best: SFW image grab
animedex nekos image husbando --jq '.[0].url'
```

Each command auto-switches between TTY (human-readable, source-marked) and JSON (when piped, when `--json` is set, or when `--jq` is set), respects the per-upstream rate limit (visibly: e.g., AniList's degraded 30 req/min, nekos.best's 200 req/min), and caches successful responses in a local SQLite at `~/.cache/animedex/`. Pass `--no-cache` to bypass.

## Documentation

The full documentation lives at <https://animedex.readthedocs.io/en/latest/>. Notable pages:

- **Quickstart** — five progressive examples that cover TTY rendering, `--json`, `--jq`, `--no-cache`, and the Python library.
- **Tutorials** — systematic per-backend deep-dives (anilist / ann / jikan / kitsu / mangadex / danbooru / waifu / trace / nekos / shikimori), the raw passthrough (`animedex api`), output modes, the `Config` Python entry point, and the `--agent-guide` flag for LLM agents.
- **API reference** — auto-generated from the source docstrings.

## Human Agency Principle (the top rule)

> **The human user has full choice. Whatever the consequences of that choice, they are the user's. animedex's job is to inform and to warn, not to gate, refuse, or override.**

This rule supersedes every other design guideline. Concretely:

- No content filters injected on the user's behalf. If you ask Danbooru for explicit tags, you get explicit results.
- No `--unsafe`, `--nsfw`, `--allow-...`, `--force` flags. Those exist purely to ask "are you sure?" and that is paternalism.
- No double-confirmation prompts. If a command name says it does something, running the command does that thing.
- We do warn — in `--help` text and per-command agent-guidance blocks — about every upstream whose legal posture, content class, or rate ceiling the user might want to be aware of. The warning is informational; it never blocks.

LLM agents read the same docstrings; their alignment training does the rest.

The only constraints `animedex` enforces unilaterally are **technical contracts**: the rate limits the upstream actually punishes, the mandatory headers (Shikimori / MangaDex / Danbooru `User-Agent`), the read-only HTTP method set on the passthrough. Those are physics, not preferences.

## Repository map

```
animedex/                Installable package (the runtime)
  api/                     Raw passthrough dispatcher + per-backend modules
  backends/                High-level Python API per backend (anilist, ann, jikan, shikimori, ...)
  cache/                   SQLite TTL cache
  config/                  Build metadata + Config entry point
  diag/                    selftest runner + per-module smokes
  entry/                   Click command tree (anilist, ann, shikimori, trace + api)
  models/                  Cross-source common types (Anime, Character, ArtPost, ...)
  policy/                  Docstring lint + agent-guide extractor
  render/                  TTY / JSON / raw / jq / field-projection renderers
  transport/               HTTP client + ratelimit + read-only firewall + UA
test/                    Unit tests + 700+ fixture YAMLs (test/fixtures/)
plans/                   Staged design documents (binding for contributors)
docs/                    Sphinx source -> https://animedex.readthedocs.io
tools/                   Fixture capture, build helpers
AGENTS.md                Repository policy (English-only, commit identity, naming discipline)
CLAUDE.md                Symlink to AGENTS.md
```

## Install

```bash
pip install -e .
```

PyPI publication will follow once the project clears the v0.1.0 milestone (see the [master tracking issue](https://github.com/deepghs/animedex/issues/1) for the full roadmap).

## How to navigate

**As a contributor:** read [`AGENTS.md`](./AGENTS.md) first (it states the binding policies — English-only repository content, commit-identity rules, naming discipline, test discipline, the lossless rich-model contract); then [`plans/README.md`](./plans/README.md) for the design rationale.

**As an LLM agent shelling out:** the per-command Agent Guidance blocks are extracted by `animedex --agent-guide`; that single invocation is enough to populate your tool catalogue. The blocks describe each command's content classification (NSFW posture, age-of-consent considerations), rate ceilings, and the right reflexes when the user has not explicitly asked for mature content. Read [`plans/02-design-policy-as-docstring.md`](./plans/02-design-policy-as-docstring.md) for the full rationale.

## License

Apache License 2.0. See [`LICENSE`](./LICENSE).
