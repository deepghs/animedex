# Plan 03 - CLI Architecture: read-only, gh-flavored, multi-source-explicit

> Status: design, frozen. Depends on: plan 01 (sources), plan 02 (policy principle). Drives: plan 04 (roadmap and MVP scope).

## 0. Positioning

animedex is a "gh for anime": a single read-only CLI that aggregates several public anime metadata services, exposes both high-level convenience commands and a raw API passthrough, and tells you at every turn which upstream answered a given question. It is built so that a human pasting commands and an LLM agent invoking tools can use the same surface.

## 1. What we copy from `gh`

| `gh` design point | how we use it |
|---|---|
| `gh api ...` raw passthrough | `animedex api <backend> ...` - one escape hatch per backend |
| `--json field1,field2` field projection | identical |
| `--jq <expr>` post-filter | identical |
| `--template <tmpl>` custom rendering | optional |
| Resource-then-verb structure | each backend is a top-level group: `animedex anilist search`, `animedex jikan top`, etc. |
| `auth login / status / logout` | identical, but only the backends that need auth offer login |
| Default to human-readable on TTY, JSON when piped | identical |
| `--web` to open a browser | per-backend mapping where it makes sense |
| `gh extension` plug-in mechanism | deferred; revisit when scope justifies it |
| `gh completion <shell>` | same |

## 2. What we do NOT copy

- `gh` happily mutates GitHub. animedex never mutates anything. There is no parallel to `gh issue create` or `gh repo delete`.
- `gh` has implicit current-directory context (current PR). animedex has no equivalent "current anime"; commands are stateless.
- `gh` shows a single source (GitHub). animedex deals with many, so we surface the source explicitly in every output (see section 5).

## 3. Top-Level Layout

```
                 animedex
                    |
   .----------------+----------------.----------.----------.
   |                |                |          |          |
 backend         aggregate          api       auth      utility
 commands        commands         passthrough commands   commands
   |                |                |          |          |
 anilist          search           api anilist auth status config
 jikan            show             api jikan   auth login  cache
 kitsu            season           api kitsu   auth logout completion
 mangadex         schedule         api mangadex auth token alias
 trace            crossref         api trace             status
 danbooru         trace            api danbooru          version
 shikimori                         api shikimori
 ann                               api ann
 anidb                             api anidb
 ghibli
 nekos
 waifu
 quote
```

## 4. Backend Commands

Per-backend command groups. Each group prints the upstream service in its help banner and in every default-rendered output. The first column lists the command, the second its data source, the third whether anonymous use suffices.

```
# AniList (graphql.anilist.co) - search backbone
animedex anilist search <q>                            anonymous
animedex anilist show <id>                             anonymous
animedex anilist character <id>                        anonymous
animedex anilist staff <id>                            anonymous
animedex anilist studio <id>                           anonymous
animedex anilist schedule [--day mon|tue|...]          anonymous
animedex anilist trending [--type anime|manga]         anonymous
animedex anilist user <name>                           anonymous (public profile)
animedex anilist user <name> list [--status ...]       anonymous (public list)
animedex anilist viewer                                requires token (own private data)
animedex anilist viewer list                           requires token

# Jikan v4 (api.jikan.moe) - MAL view, read-only
animedex jikan show <mal-id>                           anonymous
animedex jikan search <q>                              anonymous
animedex jikan top --type anime|manga                  anonymous
animedex jikan season [year] [season] | now | upcoming anonymous
animedex jikan schedule [--day mon|...]                anonymous
animedex jikan random                                  anonymous
animedex jikan watch episodes | promos                 anonymous
animedex jikan user <mal-name>                         anonymous (public)
animedex jikan producer <id>                           anonymous

# Kitsu (kitsu.app) - streaming-links and cross-id mappings
animedex kitsu search <q>                              anonymous
animedex kitsu show <id>                               anonymous
animedex kitsu streaming <id>                          anonymous
animedex kitsu mappings <id> [--from anilist|mal|...]  anonymous
animedex kitsu trending                                anonymous

# MangaDex (api.mangadex.org) - manga
animedex mangadex search <q> [--lang en]               anonymous
animedex mangadex show <manga-id>                      anonymous
animedex mangadex feed <manga-id> [--lang en]          anonymous
animedex mangadex chapter <chapter-id>                 anonymous
animedex mangadex pages <chapter-id> [--save-to <dir>] anonymous (At-Home flow)
animedex mangadex cover <manga-id>                     anonymous

# Trace.moe (api.trace.moe) - screenshot reverse search
animedex trace <image|url> [--anilist-info] [--cut-borders]  anonymous (1000/mo)
animedex trace quota                                   anonymous

# Danbooru (danbooru.donmai.us) - artist and tag DSL
animedex danbooru search "<tag-dsl>" [--limit N --page N]    anonymous
animedex danbooru post <id>                            anonymous
animedex danbooru artist <name>                        anonymous
animedex danbooru tag <name>                           anonymous (wiki + aliases)
animedex danbooru pool <id>                            anonymous
animedex danbooru count "<tag-dsl>"                    anonymous (cheap count)

# Shikimori (shikimori.io) - season calendar, second opinion
animedex shikimori calendar                            anonymous (UA required)
animedex shikimori search <q>                          anonymous
animedex shikimori show <id>                           anonymous
animedex shikimori screenshots <id>                    anonymous
animedex shikimori videos <id>                         anonymous (PV/OP/ED)

# Anime News Network Encyclopedia (cdn.animenewsnetwork.com) - XML fallback
animedex ann show <id>                                 anonymous (XML auto-converted)
animedex ann search <name>                             anonymous
animedex ann reports                                   anonymous (paginated enumerate)

# AniDB (api.anidb.net) - cross-id map and ed2k file fingerprint
animedex anidb show <aid>                              client name only
animedex anidb crossref <aid>                          client name only
animedex anidb fingerprint <file>                      requires UDP login
animedex anidb dump-titles                             anonymous (offline dump)

# Studio Ghibli - bundled static snapshot
animedex ghibli films [--id N]                         offline, no network
animedex ghibli people | locations | vehicles | species offline

# NekosBest (nekos.best) - SFW image / GIF
animedex nekos categories                              anonymous
animedex nekos <category> [--amount 1..20]             anonymous

# Waifu.im (api.waifu.im) - tagged illustration search
animedex waifu tags                                    anonymous
animedex waifu search [--include-tag ...] [--exclude-tag ...] [--is-nsfw] anonymous

# AnimeChan (api.animechan.io) - quote
animedex quote                                         anonymous, 5 req/h, local cache
animedex quote --anime <name>                          premium-only at present
animedex quote --character <name>                      premium-only at present
```

## 5. Source Attribution

Every aggregate or backend command must make its data origin obvious to the caller. Two complementary mechanisms:

### TTY rendering

```
$ animedex show "Frieren"
Sousou no Frieren                                  [2023, TV, finished]
---------------------------------------------------------------------
Title (en)        Frieren: Beyond Journey's End          [src: anilist]
Title (ja)        Sousou no Frieren                      [src: anilist]
Score             9.34 (anilist) / 9.32 (jikan)          [src: anilist + jikan]
Episodes          28                                      [src: anilist]
Studios           Madhouse                                [src: anilist]
Streaming (legal) Crunchyroll, Hidive                     [src: kitsu]
IDs               anilist:154587 / mal:52991 / anidb:17795 / kitsu:47390
                                                          [src: kitsu mappings]
External          ANN/26834 / Wikipedia/zh                [src: anidb]
---------------------------------------------------------------------
```

Every fact is annotated. There is no anonymous data.

### JSON rendering

```json
{
  "id": "anilist:154587",
  "title": {
    "en": {"value": "Frieren: Beyond Journey's End", "_source": "anilist"},
    "ja": {"value": "Sousou no Frieren", "_source": "anilist"}
  },
  "score": [
    {"value": 9.34, "_source": "anilist"},
    {"value": 9.32, "_source": "jikan"}
  ],
  "streaming": {"value": [], "_source": "kitsu"},
  "_meta": {
    "fetched_at": "...",
    "sources_consulted": ["anilist", "jikan", "kitsu", "anidb"],
    "sources_failed": []
  }
}
```

A `--source-attribution=off` option exists for the rare consumer that wants the raw data without the metadata noise. There is no equivalent for TTY mode; the human will always see the source column.

## 6. Aggregate Commands (cross-source)

Few. Each must prove it does something the per-backend commands cannot.

```
animedex search <q>           AniList primary, Jikan and Kitsu as supplements
animedex show <id-or-name>    accepts anilist:154587 / mal:52991 / etc.,
                              fetches and merges from multiple sources
animedex crossref <id>        static map (nattadasu/animeApi) first;
                              `--deep` falls back to AniDB <resources>
animedex season [year] [s]    default Jikan; `--source shikimori` for calendar
animedex schedule [--day]     default AniList airingSchedule
animedex trace <image|url>    top-level alias of `animedex trace`
```

These commands always emit the source-attributed JSON shape from section 5. They never hide which upstream answered.

## 7. The `animedex api` Passthrough

A faithful adaptation of `gh api`. The first positional is the backend, the second the path or GraphQL document. Authentication, rate limiting, caching, and User-Agent injection still apply (those are P1 concerns from plan 02). Schema parsing does not.

```
animedex api anilist '<graphql-document>' [-f var=value]
animedex api anilist --variables '{"id":154587}' '<graphql>'

animedex api jikan <path>
animedex api jikan /anime/52991
animedex api jikan '/anime?q=naruto&type=tv'

animedex api kitsu <path>
animedex api kitsu '/anime?filter[text]=Frieren&include=streamingLinks'

animedex api mangadex <path> [--paginate]
animedex api mangadex '/manga/{id}/feed?translatedLanguage[]=en'

animedex api trace <path>
animedex api trace '/search?url=...'

animedex api danbooru <path>
animedex api danbooru '/posts.json?tags=touhou+rating:g+order:score'

animedex api shikimori <path>          # auto-injects User-Agent
animedex api shikimori /api/calendar

animedex api ann <path>                 # XML auto-converted by default
animedex api ann --xml '/encyclopedia/api.xml?anime=14679'

animedex api anidb httpapi --request anime --aid 17795
animedex api anidb udp 'ANIME aid=17795'   # requires login
```

Universal flags:

```
--paginate         auto-paginate (Jikan, MangaDex, Danbooru)
--jq <expr>        jq post-filter
--method/-X        HTTP method override; forwarded verbatim
--header/-H K:V    add header
--field/-f K=V     form/url-encoded field
--raw-field/-F K=V no type coercion
--input <file>|-   request body from file or stdin
--cache <ttl>      override default cache TTL
--no-cache         bypass cache for this call
--rate slow        voluntarily go slower (cannot go faster than P1 cap)
```

Two contracts on this command:

1. The output is the upstream's raw JSON, not our annotated shape. No `_source` is added; this is a passthrough.
2. Method/path choices are forwarded verbatim. The raw passthrough is an escape hatch; callers own the upstream response.

## 8. Auth Model

Default: **anonymous**. Almost every backend works without a token.

```
animedex auth status
    # Reports per-backend state. Example output:
    #   anilist     anonymous   (login unlocks private user data)
    #   jikan       always anonymous
    #   kitsu       anonymous
    #   mangadex    anonymous   (read paths only)
    #   trace.moe   anonymous   (quota 312/1000 used this month)
    #   danbooru    anonymous   (login unlocks Gold-tier filters)
    #   shikimori   anonymous   (User-Agent header injected automatically)
    #   ann         anonymous
    #   anidb-http  client name registered as "<your project>"
    #   anidb-udp   not authenticated (`fingerprint` subcommand unavailable)
    #   ghibli      offline
    #   nekos       always anonymous
    #   waifu       always anonymous
    #   animechan   anonymous   (premium key gives 1000 req/hour)

animedex auth login <backend>
    # Only meaningful for:
    #   anilist     Pin Redirect (browser flow, paste-back token)
    #   trace.moe   record a Patreon-issued API key
    #   danbooru    record username + api_key
    #   anidb-udp   record AniDB account + UDP API password
    #   animechan   record premium API key
    # All other backends respond with "this backend does not need login".

animedex auth logout <backend>
animedex auth token <backend>            # print token (with confirmation)
```

Token storage uses the OS keyring (Secret Service / Keychain / Credential Locker). No plain-text dotfile fallback.

## 9. Output Modes

The output system is consistent across every command:

```
default (TTY)            human-friendly table or summary, with [src: ...]
default (pipe)           full source-attributed JSON
--json field1,field2     JSON with selected fields only
--jq <expr>              jq post-filter
--template <tmpl>        custom render (jinja initially)
--web / -w               open the upstream's webpage for this resource
--source-attribution off remove `_source` annotations from JSON
```

`--web` mappings include:

```
animedex anilist show 154587 -w   -> https://anilist.co/anime/154587
animedex jikan show 52991 -w      -> https://myanimelist.net/anime/52991
animedex mangadex show <id> -w    -> https://mangadex.org/title/{id}
animedex danbooru post <id> -w    -> https://danbooru.donmai.us/posts/{id}
animedex trace <img> -w           -> https://trace.moe/?url=<...>
```

## 10. Cross-Cutting Infrastructure

These exist before any backend; they are written once and used by all.

- **HTTP client wrapper**: User-Agent injection, base URL, timeout, redirect policy, gzip handling.
- **Per-backend rate limiter**: token bucket honouring P1 caps from plan 02. AniDB gets its own scheduler (file-based, persistent across invocations, because rate-limit windows survive process exit).
- **SQLite cache**: keyed by (backend, request signature). Default TTLs: 72 h for metadata, 24 h for lists, 1 h for schedules and trending, 30 d for offline dumps. `--no-cache` and `--cache <ttl>` overrides.
- **Token store**: OS keyring frontend; per-backend namespacing.
- **Source-attributed renderer**: pluggable per output mode; same underlying source-aware data structure feeds TTY, JSON, jq, jinja, and `--web`.
- **Docstring lint**: enforces the plan-02 docstring contract on every CLI command and MCP tool function.
- **MCP tool registration**: each CLI command registers with an MCP decorator so the same code drives an MCP server (the Agent Guidance block becomes the tool description).
