# Plan 01 - Survey of the Anime Section of public-apis/public-apis

> Status: research, complete. Snapshot taken 2026-05. Scope: every entry listed under the **Anime** category in `github.com/public-apis/public-apis`. Lens: how each one would slot into a read-only, JSON-first, agent-friendly CLI ("animedex").

## 0. TL;DR

1. Six sources actually carry the product: **AniList** (backbone search), **Jikan** (anonymous MAL view), **Kitsu** (legal streaming-link aggregator and cross-service ID mappings), **MangaDex** (manga + chapter data), **Trace.moe** (screenshot reverse-search), and **Trace.moe + Danbooru** for image-based use cases.
2. Three are dead or terminally degraded: **AniAPI** (domain re-pointed to a survey/ad page; GitHub repo archived 2022-12), **AnimeFacts** (Heroku free tier shut down, host returns 404), **Studio Ghibli API** (original repo archived; only a community Vercel mirror remains, content frozen).
3. **MyAnimeList Official API v2** becomes redundant under a read-only constraint: Jikan covers the same read paths better, and the only thing v2 adds is "write back to the user's MAL list", which we do not do.
4. The remaining sources (Catboy, Waifu.pics, Mangapi3) are duplicates of better options or paywalled aggregators with no public schema.

## 1. Tier Matrix

| Tier | Source | Role | LLM-friendliness | Effort | Verdict |
|------|--------|------|------------------|--------|---------|
| S | AniList | Backbone search and metadata (GraphQL with introspection) | 5/5 | S | must |
| S | Jikan v4 | Anonymous read of MAL view (REST + OpenAPI) | 4/5 | S | must |
| S | Trace.moe | Screenshot to anime + episode + timecode | 5/5 | S | must |
| A | Kitsu | Legal streaming-links, JSON:API mappings | 4/5 | S | recommended |
| A | MangaDex | Manga + chapters + At-Home image flow | 4/5 | M | recommended (with legal note) |
| A | Shikimori | `/api/calendar` season schedule, second opinion | 4/5 | M | recommended |
| B | Danbooru | Artist / tag DSL, art lookup | 5/5 read | M | recommended |
| B | AniDB (HTTP+UDP) | Cross-service ID map; ed2k file fingerprinting | 2/5 | L | optional heavy module |
| B | NekosBest | SFW images, role-play GIFs, attribution fields | 5/5 | S | recommended |
| B | Waifu.im | Tagged illustrations, explicit `is_nsfw` toggle | 5/5 | S | recommended |
| C | AnimeChan | Anime quotes (mandatory local cache; 5 req/h free tier) | 3/5 | S | secondary |
| C | ANN Encyclopedia | XML metadata fallback (no news feed!) | 2/5 | M | secondary |
| dead | AniAPI | domain has been resold, repo archived | 1/5 | n/a | drop |
| dead | AnimeFacts | host returns 404 | 1/5 | n/a | drop |
| zombie | Studio Ghibli API | only community mirror; frozen data | 4/5 | S | bundle as static snapshot, not online dependency |
| redundant | MyAnimeList Official API v2 | Jikan covers the read paths | 3/5 | M | drop under read-only |
| redundant | Catboy | duplicates NekosBest | 3/5 | S | drop |
| redundant | Waifu.pics | duplicates Waifu.im, has had SFW leakage history | 4/5 | S | drop |
| redundant/paid | Mangapi3 (RapidAPI) | duplicates MangaDex; RapidAPI paywall | 2/5 | S | drop |

## 2. Per-Source Notes

The sections below capture the operationally relevant facts for each source that survives the cut. Entries marked dropped get a short paragraph of reasoning; we keep them in the document so future contributors do not re-litigate the decision.

### 2.1 AniList - backbone

- Single GraphQL endpoint: `POST https://graphql.anilist.co`.
- OAuth2 with a Pin Redirect flow (`/api/v2/oauth/pin`) - ideal for a CLI because it does not need a local redirect listener.
- Stated rate limit: 90 req/min, currently degraded to 30 req/min. Standard `Retry-After`, `X-RateLimit-Reset`, `X-RateLimit-Remaining` headers on 429.
- Coverage: anime, manga, character, staff, studio, mediaList, airingSchedule, recommendation, review, activity, forum, streamingEpisodes, trending. `Media.idMal` exposes the cross-link to MAL; no AniDB id.
- The agent sweet spot: GraphQL introspection lets a model self-discover the schema and write queries with no out-of-band documentation.
- Effort: small. One endpoint, one auth pattern, fragments are reusable.

### 2.2 Jikan v4 - anonymous MAL view

- REST at `https://api.jikan.moe/v4/`. No authentication, no API key.
- Documented rate limit: 3 req/s and 60 req/min.
- Stable response envelope (`{ data, pagination }`); a published OpenAPI spec lives at `github.com/jikan-me/jikan-api-docs`.
- Read-only by design: the project explicitly states "Jikan REST API does not support authenticated requests. You can not update your lists."
- Data is scraped and cached from MAL: expect minutes-to-day staleness.
- Effort: small. OpenAPI lets us generate a typed client.

### 2.3 Trace.moe - screenshot reverse search

- REST at `https://api.trace.moe`.
- Anonymous tier: concurrency 1, quota 1000/month. Higher quotas via Patreon-issued API keys (header `x-trace-key`).
- Two ingest forms: `GET /search?url=<image_url>` and `POST /search` with raw image bytes (Content-Type: image/*, max 25 MiB).
- Result includes the AniList id, episode, start/end seconds, similarity (0-1), preview MP4, and JPEG thumbnail. Optional `anilistInfo` expands the AniList metadata in-line.
- The AniList id is the hand-off anchor: chain straight into AniList for full metadata.
- Index biases toward TV/film with BD/TV releases; obscure or hentai content is not covered. Similarity below ~0.87 is community-considered unreliable.
- Effort: small. Two endpoints plus `/me` for quota.

### 2.4 Kitsu - legal streaming and cross-service id map

- JSON:API 1.0 at `https://kitsu.app/api/edge` (legacy `kitsu.io` still serves but is being phased out).
- OAuth2 *Resource Owner Password Credentials* (username + password, exchanged directly for a token). Anonymous reads work for everything we need under read-only.
- Rate limit not stated in docs; community observation is around 10 rps.
- The two reasons to keep it: `streaming-links` resource (Crunchyroll, Hidive, Netflix, etc.) and the `mappings` resource that ties Kitsu IDs to MAL, AniList, AniDB, and Trakt.
- Effort: small.

### 2.5 MangaDex - manga and chapters

- REST at `https://api.mangadex.org`. Full OpenAPI spec served from `/docs/swagger.html`.
- Authentication migrated to Keycloak in 2023. Anonymous reads cover all searching/listing/feed paths. Personal Client (for write or for higher quotas) takes 1-4 weeks of manual approval.
- Documented rate limits include a global ~5 rps/IP and per-endpoint caps (e.g. `GET /at-home/server/{id}` 40/min; `POST /auth/login` 30/h). `User-Agent` header is mandatory; the `Via` header is forbidden.
- Image fetching is a two-step "At-Home" flow: `GET /at-home/server/{chapterId}` returns a *temporary* base URL plus page hashes, and the actual page bytes come from `<base>/data/<hash>/<file>`. Hot-linking the public CDN is against ToS.
- Legal status: MangaDex distributes user-uploaded scanlations; in May 2025 a coordinated DMCA wave from Kodansha, Square Enix, and Naver removed 7000+ titles. The reader path needs an explicit user opt-in (see plan 02 for how we handle that).
- Effort: medium. The At-Home flow plus paginated feeds are the only non-trivial parts.

### 2.6 Shikimori - season calendar and second opinion

- REST and GraphQL at `https://shikimori.io`. Note the recent migration from `.one` to `.io`.
- OAuth2 Authorization Code (web flow). All requests must carry a `User-Agent: <APPLICATION_NAME>` header; missing UA is rejected.
- Documented rate limit: 5 rps and 90 rpm.
- The headline endpoint is `/api/calendar`, which is the cleanest "what is airing this week" surface across all the sources we surveyed.
- Effort: medium under read-only - the OAuth flow can be skipped entirely if we restrict ourselves to public reads.

### 2.7 Danbooru - artist and tag DSL

- REST at `https://danbooru.donmai.us`. Adds `.json` / `.xml` extension to switch response format.
- Anonymous reads work. Login + API key only required for Gold-tier NSFW filters and writes (which we do not perform).
- Rate limit: 10 rps for reads, 1 rps for writes (4 rps for Gold members). Header `x-rate-limit-remaining` exposes the budget.
- Tag query is a small DSL: positional tags, `-tag` exclusion, `rating:g|s|q|e`, `score:>N`, `order:score|date`, `user:`. Worth teaching the agent in docstrings rather than re-implementing as flags.
- Each post carries a `rating` field; downstream NSFW handling is the consumer's responsibility (this is the core of plan 02's reasoning).
- Effort: medium. The DSL plus wiki/artist endpoints plus pagination cursor handling.

### 2.8 AniDB - cross-id map and file fingerprinting

- HTTP API at `http://api.anidb.net:9001/httpapi` returning gzipped XML.
- UDP API at `api.anidb.net:9000` for the things HTTP cannot do, including `FILE size=&ed2k=` for local-file fingerprinting.
- Both paths require a registered Project / Client identity. UDP additionally requires a user account password.
- Rate limits are aggressive: HTTP starts at 5 packets, then drops to one packet every 2 s, with a long-run cap around one packet every 4 s and a daily cap near 200. UDP is similar. Triggering a ban locks the IP for 15 minutes to 24 hours, with HTTP and UDP bans counted separately.
- The two unique capabilities that justify keeping it: (1) ed2k-hash file identification (a must for "what is this anime file in my library" scenarios), and (2) the `<resources>` element in anime responses, which cross-references MAL, ANN, Wikipedia, AllCinema, etc. - the broadest cross-service ID map of any source we surveyed.
- Effort: large. SQLite-backed cache, anime-titles dump for offline resolution, strict scheduler, XML-to-JSON adaptor, UDP socket client (with optional encryption, session, PING, sequence window). Skipping any of these is what triggers the bans.

### 2.9 ANN Encyclopedia - XML metadata fallback

- HTTP at `https://cdn.animenewsnetwork.com/encyclopedia/api.xml`.
- No authentication. Default rate limit 1 req/s/IP; the documented "no delay" alternative is 5 req per 5 s.
- Returns XML, not JSON. There is no OpenAPI or XSD; field discovery is by example.
- Critically, the encyclopedia API does not expose ANN's news feed - that has to be scraped from RSS or HTML.
- We treat ANN as a last-resort metadata fallback because of (a) XML ergonomics and (b) the lack of cross-service IDs, and demote it accordingly in the command tree.

### 2.10 Image / GIF / quote sources

We keep two of the four overlapping image services:

- **NekosBest** (`https://nekos.best/api/v2/`): no auth, 48 SFW categories, `?amount=N` batch, response includes `artist_name` / `source_url` for attribution. Best general-purpose pick.
- **Waifu.im** (`https://api.waifu.im/`): no auth for read; rate limit 200 req/min documented; explicit `is_nsfw=true|false` query parameter and a published list of NSFW tags. Best for tag-driven illustration searches.

We drop **Catboy** (no rate-limit docs, no attribution, fully duplicated by NekosBest) and **Waifu.pics** (duplicated by Waifu.im, no attribution, plus a historical SFW-endpoint NSFW-leakage issue: `Waifu-pics/waifu-api issue #54`).

**AnimeChan** (`https://api.animechan.io/v1/`): keep, but the free tier is 5 req/h with 1-hour ban on overshoot. Mandatory local SQLite cache; without it the experience is unusable.

**AnimeFacts**: drop. The original `*.herokuapp.com` host returns HTTP 404 since Heroku retired free dynos in 2022-11. The only sensible substitute is to vendor a static JSON snapshot of trivia.

### 2.11 Studio Ghibli - bundle as static data

- The original `ghibliapi.herokuapp.com` is gone; the GitHub repository `janaipakos/ghibliapi` was archived 2022-12-01.
- A community Vercel mirror at `https://ghibliapi.vercel.app/` serves the same JSON, but operations are not transparent and the data set is frozen at 22 films (does not include "How Do You Live?", 2023).
- Recommendation: ship the JSON as a static snapshot inside the package rather than depending on an unowned mirror. Total payload is small (kilobytes).

## 3. Operational Constraints to Inherit

The following are **technical contracts** (plan 02 calls them P1) that any implementation must respect:

- AniDB rate limits: hard. Bypassing them gets the user banned, not just warned.
- MangaDex User-Agent: required. Forbidden `Via` header on requests.
- Shikimori User-Agent: required. Missing UA returns 4xx.
- Danbooru User-Agent: must not pretend to be a browser; honest UA only.
- MangaDex At-Home base URLs are short-lived; do not cache them across chapters.
- Trace.moe: requests must be serialized when concurrency=1 (free tier).

These are non-negotiable across humans and agents alike.

## 4. What This CLI Does Not Implement

These are scope and technical-contract decisions, not value judgements about how a user should behave. A user who wants any of the following can build it on top of `animedex api` or in a separate tool; this project simply does not ship them.

- **Writes**. animedex is read-only. We do not implement `PATCH/POST/DELETE` against any user-account endpoint, and the `animedex api` passthrough rejects mutating HTTP methods. Why: it keeps the auth surface small, eliminates a whole class of bugs, and lets us promise that the CLI cannot disturb the user's existing account state. See plan 03.
- **Hot-linking the MangaDex public CDN**. The MangaDex ToS requires the At-Home flow (`GET /at-home/server/{id}` followed by `<base>/data/<hash>/<file>`); going around it has produced IP rate limits and is a technical contract, not a preference.
- **Reviving a dead upstream**. AniAPI's domain has been re-pointed away from the project and its repository is archived; we do not attempt to scrape, mirror, or otherwise reconstruct the service. When and if a maintained successor appears, this decision can be revisited.

What animedex *does* do, in keeping with the human-agency principle (see plan 02 and `AGENTS.md`), is inform the user about each upstream's legal status, rate-limit posture, and content classification, and let the user choose. We do not editorialise; we do not refuse on the user's behalf.

## 5. Sources

- public-apis/public-apis README, "Anime" section.
- AniList docs (`docs.anilist.co`), Jikan docs (`docs.api.jikan.moe`), Kitsu Apiary docs, Shikimori `/api/doc`, MangaDex Swagger, Trace.moe README, Danbooru `help:api`, AniDB Wiki HTTP / UDP API Definition pages.
- AniAPI archive evidence: GitHub repo "Archived on Dec 2, 2022"; `aniapi.com/docs/` 302 redirect to a survey landing page.
- MangaDex 2025-05 DMCA coverage (industry press).
