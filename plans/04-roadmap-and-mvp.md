# Plan 04 - Roadmap and MVP Scope

> Status: scheduling, current as of project bootstrap.
> Depends on: plan 03 (the command tree to actually build).
> Updates: bump this plan whenever a phase completes or scope changes.

## 0. Time Budget

Single-engineer estimates, intermediate experience, including tests and
documentation. Each phase ends in a tagged release of a usable artifact.

| Phase | Goal | Duration | Cumulative |
|------:|------|---------:|----------:|
| 0 | Core scaffolding | 4-5 d | 1 wk |
| 1 | `animedex api` for the eight ready backends | 2 d | 1.5 wk |
| 2 | High-level commands for AniList + Jikan + Trace.moe + NekosBest | 2-3 d | 2 wk |
| 3 | Kitsu + MangaDex (no reader) + Danbooru + Waifu.im | 3 d | 2.5 wk |
| 4 | Shikimori (calendar) + ANN (XML adapter) + Ghibli (bundled) + AnimeChan (cached) | 2 d | 3 wk |
| 5 | Aggregate commands (`search`, `show`, `crossref`, `season`, `schedule`) + static cross-id map | 2 d | 3.5 wk |
| 6 | MangaDex At-Home reader path | 1.5 d | 3.7 wk |
| 7 | AniDB HTTP read + ed2k UDP fingerprint module (heavy, optional) | 5-8 d | ~5 wk |
| 8 | Polish: completion scripts, alias, `--web`, MCP server, docs build | 2 d | ~5.3 wk |

The non-AniDB scope lands at roughly 3.5-4 weeks. AniDB is a separate
heavy track because of its UDP protocol, persistent rate-limit scheduler,
and ban risk; it should not block any earlier phase.

## 1. MVP (Phase 0 + 1 + 2): about 1 week

**Goal**: a single binary `animedex` that does enough to be useful for
both human exploration and agent invocation, without authenticated
operations of any kind.

Concrete deliverables:

```
animedex anilist search/show/schedule/trending
animedex jikan show/season/top
animedex trace <image|url>
animedex nekos <category>
animedex api anilist|jikan|trace
animedex auth status
animedex config get/set
animedex status
animedex --version
animedex --agent-guide

--json field projection
--jq filter
source attribution (the `_source` annotation pattern)
TTY <-> pipe automatic switching
```

The non-goals at MVP:

- No authenticated-mode features.
- No writes (this is permanent, not just MVP).
- No NSFW-aware paths beyond passthrough (no inserted defaults; that is
  a plan-02 decision, not an MVP-scope cut).
- No MangaDex chapter reader (that is phase 6).
- No AniDB anything.
- No alias / extension / completion (those land in phase 8).

## 2. Phase 0 - Core Scaffolding (4-5 days)

The substrate every later phase depends on. Done once, paid back forever.

```
- typer- or click-based CLI skeleton with sub-grouping conventions
- Source-attributed renderer (TTY summary, JSON full, --json projection,
  --jq pipeline)
- Per-backend HTTP client wrapper (UA, timeout, gzip, redirect rules)
- Token-bucket rate limiter, per-backend caps from plan 02 P1
- SQLite cache with default TTL table; --cache and --no-cache overrides
- OS keyring token store (Secret Service / Keychain / Credential Locker)
- docstring-as-policy template + lint check (enforce Backend / Rate limit
  / `--- LLM Agent Guidance ---` blocks)
- MCP server scaffolding so each CLI command can also register as a tool
- `animedex --agent-guide` aggregator for non-MCP shell consumers
```

This is the most important phase. Cutting corners here costs us in every
later phase.

## 3. Phase 1 - `animedex api` (2 days)

Implement the raw passthrough first, before any high-level commands. This
forces us to validate auth, caching, rate limiting, and source attribution
end-to-end on every backend.

```
animedex api anilist '<graphql>'      # POST GraphQL with optional --variables
animedex api jikan <path>             # GET, paginate-aware
animedex api kitsu <path>
animedex api mangadex <path>
animedex api trace <path>             # both /search and /me
animedex api danbooru <path>
animedex api shikimori <path>         # auto-inject UA
animedex api ann <path>               # XML auto-convert
```

Universal flags from plan 03 section 7 are wired in here.

Read-only enforcement: a small middleware rejects PUT/PATCH/DELETE and
known-mutation POST paths before the request leaves the host. The
rejection is informative (it names the policy, not "Method Not Allowed").

## 4. Phase 2 - High-level Commands for the MVP backends (2-3 days)

Build the ergonomic surface for the four most useful backends:

```
animedex anilist search/show/character/staff/studio/schedule/trending/user
animedex jikan show/search/season/top/schedule/random/watch
animedex trace <image|url>
animedex nekos categories|<category>
```

Every command's docstring carries the plan-02 template. The lint check
prevents any from shipping without it.

Source attribution is now exercised end-to-end: the renderer prints
`[src: anilist]` etc. on TTY, and the JSON shape contains `_source`.

## 5. Phase 3 - Mid-tier read backends (3 days)

```
animedex kitsu search/show/streaming/mappings/trending
animedex mangadex search/show/feed/chapter/cover           (no `pages` yet)
animedex danbooru search/post/artist/tag/pool/count
animedex waifu tags/search
```

Danbooru's tag DSL is documented in the docstring per plan 02. We do not
inject `rating:g`. The `pages` (image fetching) command is deliberately
deferred to phase 6.

## 6. Phase 4 - Calendar, news, trivia (2 days)

```
animedex shikimori calendar/search/show/screenshots/videos
animedex ann show/search/reports                            (XML adapter)
animedex ghibli films/people/locations/vehicles/species     (bundled snapshot)
animedex quote                                               (5 req/h, local cache)
```

The ANN XML adapter is small but tedious. We use ElementTree, not a
heavyweight schema framework, because there is no schema to drive.

The Ghibli static snapshot ships in `animedex/data/ghibli.json`. No
network calls.

The AnimeChan local cache is a small SQLite table populated lazily; the
intent is that human users almost never hit the upstream after the first
few invocations.

## 7. Phase 5 - Aggregate commands (2 days)

```
animedex search <q>
animedex show <id-or-name>
animedex crossref <id> [--from anilist|mal|anidb|kitsu] [--deep]
animedex season [year] [season]
animedex schedule [--day]
```

These commands sit on top of the per-backend commands they call. They
never hide which upstream answered: every emitted record carries the
`_source` (or `[src: ...]` in TTY mode).

The `crossref` command consults the static ID map (we vendor a snapshot
of the `nattadasu/animeApi` JSON) first, and only escalates to a live
AniDB call when `--deep` is given.

## 8. Phase 6 - MangaDex At-Home reader (1.5 days)

```
animedex mangadex pages <chapter-id> [--save-to <dir>]
```

Implementation notes:

- Step 1: `GET /at-home/server/{chapter-id}` returns a temporary base
  URL plus per-page hashes.
- Step 2: fetch each page from `<base>/data/<hash>/<file>`, with a
  shared-host concurrency limit (page fetches are bound by HTTP/2 to
  the same MangaDex At-Home node).
- The base URL is short-lived; re-resolve per chapter, do not cache it.
- The docstring states the legal-status reality (DMCA-flagged scanlations
  exist on the platform); per plan 02 we do not gate this behind a
  user-prompt confirmation, but the agent guidance block instructs the
  agent to invoke this command only when the user explicitly asks to
  read manga.

## 9. Phase 7 - AniDB (5-8 days, separate track)

The heavy module. Justified only because nothing else covers ed2k file
fingerprinting and the `<resources>` cross-id map.

```
animedex anidb show <aid>
animedex anidb crossref <aid>
animedex anidb dump-titles            # offline dump
animedex anidb fingerprint <file>     # UDP, requires login
```

Sub-tasks:

- Persistent rate-limit scheduler (file-backed; the rate window survives
  process exit). This is the single most important piece; without it the
  ban risk is real.
- HTTP API client (gzip + XML), with anime-titles dump for offline
  resolution.
- XML to JSON adaptor.
- UDP socket client: AUTH / ENCRYPT / sequence numbers / PING-keepalive
  for NAT environments.
- ed2k computation utility (one of the few non-trivial pieces of pure
  computation in animedex).
- AniDB user/password storage in keyring, distinct from any HTTP-only
  client name.

This phase can ship later than v1 without blocking anyone.

## 10. Phase 8 - Polish (2 days)

```
animedex completion bash | zsh | fish
animedex alias set / unset / list           # like gh alias
animedex extension ...                      # may be deferred again
--web for the commands listed in plan 03 section 9
MCP server registration for every CLI command
Sphinx (or alternative) documentation build, including the auto-extracted
  Agents Reference page that concatenates Agent Guidance blocks
```

## 11. Versioning Heuristics

- `0.1.x` covers MVP (phases 0-2). API may break across patch versions.
- `0.2.x` covers phases 3-5. Aggregate commands and source-attribution
  shape stabilize.
- `0.3.x` adds phase 6 (manga reader path).
- `1.0.0` requires the docstring lint to be green for every command,
  the smoke-test CI matrix to be green on at least Linux + macOS, and a
  documented stable schema for the source-attributed JSON shape.
- AniDB ships under a `0.x.x+anidb` build metadata tag whenever it
  lands, because it is operationally heavier than the rest of the surface.

## 12. Risk Register

| Risk | Likelihood | Mitigation |
|------|---|---|
| AniList rate-limit "degraded mode" stays at 30 req/min | high | hard-coded conservative limiter, per-call cache TTL |
| MangaDex DMCA churn changes the manga search surface | medium | OpenAPI is regenerated on each release; tests assert key endpoints |
| Trace.moe quota tightens | medium | `--source-attribution` and quota indicator in `auth status` |
| AniDB bans IP during development | low if scheduler is honest | persistent scheduler shipped before any AniDB code |
| Free-tier hosts (AnimeChan, Ghibli mirror) disappear | medium | local cache + bundled snapshot make us resilient |
| Docstring lint becomes load-bearing and brittle | medium | doctest-able examples, simple regex checks, opt-in pre-commit |
