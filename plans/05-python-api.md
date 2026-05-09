# Plan 05 - Python API surface

> Status: design, frozen pre-implementation.
> Depends on: plan 03 (CLI architecture), plan 02 (policy-as-docstring).
> Drives: how every backend module is named, typed, and exported.

## 0. Why a Python API alongside the CLI

`animedex` ships as both a CLI binary and a normal Python package. A user installing `pip install animedex` (eventually) gets:

* The `animedex` console script. Same surface as `gh`, same multi-source contract, same `gh api` style passthrough.
* `import animedex` in their own Python code, same fields, same source-attribution shape, no subprocess overhead.

The two surfaces are **not parallel implementations**. The CLI is a thin renderer that calls into the same Python API a downstream user calls. There is exactly one place where the AniList GraphQL endpoint is invoked, where the source attribution is attached, where the rate limiter is consulted: the library. The CLI imports it.

Reasons we treat the library as a first-class deliverable:

1. **Secondary development.** Many users will want to script around animedex - "fetch every series in this user's MAL list, then resolve cover art via Danbooru, then drop the results into a markdown table." Forcing them through `subprocess.run(["animedex", ...], capture_output=True)` plus JSON parsing is a tax we can avoid by exposing a real Python API.
2. **Agent ergonomics.** An LLM-driven workflow that already runs in Python (e.g. an MCP server or a notebook) gets typed dataclasses for free and skips one layer of serialisation.
3. **Testability.** Unit tests can call the API directly with mocked HTTP and skip CLI runner gymnastics. CI stays fast.
4. **Composability.** A consumer can build their own CLI, GUI, web service, or Discord bot on top without re-implementing rate limiting, caching, or source attribution.

The cost of treating the API as first-class is discipline: names, return types, and stability boundaries have to be designed, not accidentally fall out of CLI implementation choices. The rest of this plan is that design.

## 1. Module layout

The Python API mirrors the CLI command tree from plan 03 one-for-one, with a few additional infrastructure modules for things the CLI exposes only as flags or implicit defaults.

```
animedex/
  __init__.py              re-exports the high-level convenience functions
                           (search, show, season, schedule, crossref, trace),
                           the source-attributed result dataclasses, and
                           __VERSION__/__TITLE__ etc.
  config/
    meta.py                committed identity (title, version, author).
    buildmeta.py           optional per-build metadata (commit, tag, dirty).
    profile.py             user-facing Config object (cache TTLs, rate-rate
                           overrides, source-attribution toggle, token store
                           backend) - the programmatic equivalent of CLI flags.
  backends/
    __init__.py            re-exports each backend submodule.
    anilist/__init__.py    public surface for the AniList backend.
    anilist/_client.py     internal HTTP/GraphQL client; underscore-prefixed.
    jikan/__init__.py      ditto for Jikan.
    kitsu/__init__.py      ...
    mangadex/__init__.py
    trace/__init__.py
    danbooru/__init__.py
    shikimori/__init__.py
    ann/__init__.py
    anidb/__init__.py
    ghibli/__init__.py
    nekos/__init__.py
    waifu/__init__.py
    quote/__init__.py
  api/
    __init__.py            programmatic equivalent of `animedex api ...`
                           (the raw passthrough escape hatch).
  diag/
    selftest.py            in-process diagnostic (already exists).
  entry/
    cli.py                 Click group; importer of the API. Not part of the
                           public Python API contract; internal use only.
  models/
    __init__.py            re-exports dataclasses used as return types.
    anime.py               Anime, AnimeTitle, AnimeRating, ...
    manga.py               Manga, Chapter, ...
    character.py           Character, Staff, Studio.
    common.py              SourceTag, Pagination, RateLimit, ApiError.
  utils/
    __init__.py            internal helpers; treat as private.
```

Two naming rules, applied consistently:

* **Public** modules and members have no leading underscore. They are part of the documented API and subject to the stability rules in section 7.
* **Private** modules and members start with an underscore (e.g. `animedex.backends.anilist._client`). They may move, rename, or vanish across minor releases without notice.

## 2. Public API surface (mirror of the CLI)

The public Python API maps to the CLI command tree from plan 03 verbatim. Every CLI subcommand has one corresponding Python function, in the same place, with the same arguments (modulo Pythonic naming for flags).

### 2.1 Top-level convenience

The functions in `animedex.__init__` cover the cross-source aggregate commands. They are the most-used entry points.

```python
from animedex import search, show, crossref, season, schedule, trace

results = search("Frieren")
detail  = show("anilist:154587")
mapping = crossref("mal:52991")
season_listing = season(2026, "spring")
this_week      = schedule(day="mon")
hit            = trace("path/to/screenshot.jpg")
```

Each returns a typed dataclass (or an iterable thereof) defined in `animedex.models`. Source attribution is preserved on every record: every dataclass has a `source: str` field set to the upstream that supplied it (or a list of `source` values when fields are merged).

### 2.2 Per-backend modules (mirror of `animedex <backend> <verb>`)

Each backend exposes a stable, narrow API in `animedex.backends.<name>`:

```python
from animedex.backends import anilist, jikan, kitsu, mangadex, trace, danbooru
from animedex.backends import shikimori, ann, anidb, ghibli, nekos, waifu, quote

a   = anilist.show(154587)                  # Anime dataclass
hit = jikan.show(52991, full=True)
opts = kitsu.streaming(47390)
chap = mangadex.feed("manga-id", lang="en", order="chapter:asc")
img  = danbooru.search("touhou marisa rating:g order:score", limit=20)
```

High-level backend modules do not ship account-mutation helpers. There are no `add_to_list` or `set_score` functions in any backend module; callers who intentionally need an upstream operation outside the high-level read surface use the raw passthrough and own the upstream result.

### 2.3 `animedex.api.call(backend, path_or_query, ...)` (raw passthrough)

The Python equivalent of `animedex api <backend> ...`. Returns the upstream's raw JSON, with rate limiting, caching, User-Agent injection, and MangaDex `Via` stripping applied; bypasses the schema-shaped result dataclasses. Method/path choices are forwarded verbatim, and callers own the upstream response.

```python
from animedex.api import call

data = call("anilist", "query { Media(id: 154587) { title { romaji } } }")
data = call("jikan", "/anime/52991")
data = call("kitsu", "/anime?filter[text]=Frieren&include=streamingLinks")
data = call("danbooru", "/posts.json?tags=touhou+rating:g")
```

## 3. Result dataclasses with source attribution

Every shape returned by the API is a dataclass (or a typed dict in places where structural variance defeats dataclasses). The shapes are documented in `animedex.models`.

The carrier of source attribution is `SourceTag`. Every dataclass that holds upstream-provided data has either:

* `source: SourceTag` for records that came from a single upstream, or
* `sources: list[SourceTag]` plus per-field `Annotated[..., SourceTag(...)]` markers for merged records produced by the cross-source aggregate functions.

```python
from animedex.models import Anime, AnimeTitle, SourceTag

@dataclass
class Anime:
    id: str                                   # canonical "<source>:<id>"
    title: AnimeTitle
    score: float | None
    episodes: int | None
    studios: list[str]
    streaming: list[StreamingLink]
    ids: dict[str, str]                       # cross-service ID map
    source: SourceTag                         # who told us about this anime

@dataclass
class SourceTag:
    backend: str        # "anilist" | "jikan" | "kitsu" | ...
    fetched_at: datetime
    cached: bool        # was the value served from local cache?
    rate_limited: bool  # did this call get throttled?
```

The same data is what the CLI's TTY renderer prints with `[src: ...]` annotations and what the JSON renderer emits as `_source` fields. There is exactly one source of truth.

## 4. Configuration

The `animedex.config.profile.Config` object is the programmatic equivalent of the CLI's flag stack. It is optional - every public function accepts a `config: Config | None = None` keyword argument and falls back to module-level defaults when not given.

```python
from animedex import search
from animedex.config import Config

cfg = Config(
    cache_ttl_seconds=3600,
    no_cache=False,
    rate=Rate.normal,                 # or Rate.slow; never faster than upstream
    source_attribution=True,
    user_agent="my-bot/1.0 (+contact)",
    timeout_seconds=30,
)

results = search("Frieren", config=cfg)
```

Token storage is decoupled: `Config.token_store` defaults to the OS keyring, but a programmatic user can plug in `InMemoryTokenStore()` for tests or `EncryptedFileTokenStore(path)` for headless CI.

The default `Config()` (no arguments) produces exactly the behaviour of an unflagged CLI invocation. The CLI flags themselves are translated into a `Config` instance one-to-one.

## 5. Sync vs async

**Default: synchronous.** This matches the CLI (which is sync) and the typical shape of one-off scripts and notebooks.

A future `animedex.aio` namespace will mirror the public API with async equivalents (`await search(...)`, etc.), implemented on top of `httpx.AsyncClient`. The async surface is **not** part of the v0.1.0 milestone; it lands when there is a real consumer that needs it.

## 6. Type hints and tooling

The library is fully type-annotated and ships `py.typed` (PEP 561) so `mypy --strict` works for downstream users without further configuration.

* All public functions have argument and return-type annotations.
* All dataclasses use either `dataclasses.dataclass` or `pydantic.BaseModel` (the choice is deferred until we know which one the cache and serialisation layers prefer; see plan 04 phase 0).
* All `Optional[T]` arguments default to `None`, never to a sentinel.
* Backend modules' types are `from __future__ import annotations`-compatible (no PEP 604 syntax in 3.7-3.9 contexts).

## 7. Stability guarantees

`animedex` follows semantic versioning. The public API surface for stability purposes is:

* All names exported from `animedex.__init__`.
* All names exported from `animedex.backends.<name>` (per backend).
* All names exported from `animedex.api`.
* All dataclasses in `animedex.models`.
* All names in `animedex.config.meta`, `animedex.config.buildmeta`, `animedex.config.profile`.

Anything else (anything starting with `_`, anything inside `animedex.entry`, `animedex.diag`, `animedex.utils`) is internal and can change without bumping a major version.

* **Patch releases (0.x.y -> 0.x.y+1):** bug fixes only. No public-API changes.
* **Minor releases (0.x.y -> 0.(x+1).0):** additive only. New backends, new optional arguments, new dataclasses. Existing names keep their semantics.
* **Major releases (0.x -> 1.0, 1.x -> 2.0):** breaking allowed. Each requires a migration note in the changelog.

Until v1.0 the project is in active design and minor releases may rename or restructure with a one-version deprecation cycle. After v1.0 the rules above are strict.

## 8. Examples

### 8.1 Round-trip an AniList title to its MAL counterpart

```python
from animedex.backends import anilist
from animedex.backends import jikan

a = anilist.show(154587)
print(a.title.romaji)            # "Sousou no Frieren"
print(a.ids["mal"])               # "52991"

m = jikan.show(int(a.ids["mal"]))
print(m.score)                    # 9.32 from the MAL view
```

### 8.2 Build a markdown table of this season's airing

```python
from animedex import season

rows = season(2026, "spring")
print("| Title | Studio | Score |")
print("|---|---|---|")
for r in rows:
    print(f"| {r.title.romaji} | {', '.join(r.studios)} | {r.score or '-'} |")
```

### 8.3 Use the raw passthrough for a query the high-level API does not cover

```python
from animedex.api import call

q = """
query ($search: String) {
  Page(perPage: 5) { media(search: $search, type: ANIME) { idMal title { romaji } } }
}
"""
data = call("anilist", q, variables={"search": "Frieren"})
for entry in data["data"]["Page"]["media"]:
    print(entry["idMal"], entry["title"]["romaji"])
```

### 8.4 Plug an in-memory token store for a test

```python
from animedex.config import Config, InMemoryTokenStore
from animedex.backends import anilist

cfg = Config(token_store=InMemoryTokenStore({"anilist": "fake-token-for-test"}))
result = anilist.viewer_list(config=cfg)   # uses the in-memory token, never the keyring
```

## 9. Relationship to the CLI

The CLI under `animedex/entry/` is a presentation-only layer. It:

1. Parses argv with Click.
2. Translates flags into a `Config` instance.
3. Calls into the API exactly as a downstream Python user would.
4. Renders the resulting dataclasses into TTY tables, JSON, or jq pipelines.
5. Exits with the appropriate code.

It does **not** contain backend logic, retry policy, source attribution, or rate limiting. Those live in the library. A bug in a CLI command is therefore either a flag-translation bug (in `animedex/entry/`) or a library bug (in `animedex/backends/<name>` or `animedex/api`); never both.

The reverse holds too: when you fix a behaviour in the library, every CLI command that uses it picks up the fix without further plumbing. When you write a new backend function, the corresponding CLI subcommand is a half-page wrapper around it.

## 10. Open questions (to revisit during phase 0)

* **dataclasses vs pydantic.** Pydantic gives us free JSON serialisation but adds a runtime dependency. Dataclasses are stdlib but require manual JSON adapters. Decision deferred until the cache layer (which serialises to disk) is concrete.
* **MCP server registration.** Plan 03 mentions registering each function as an MCP tool. The natural place to do that is the function decorator in each backend module. Whether decoration runs at import time (eager) or on-demand (lazy) affects startup cost.
* **Async surface.** Likely `animedex.aio.*`. Whether to literally re-implement or to wrap sync calls with `asyncio.to_thread` is a perf decision.
* **Public re-exports.** The exact set in `animedex/__init__.py` is final once phase 2 lands; for now it grows incrementally.
