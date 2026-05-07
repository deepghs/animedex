# Plan 02 - Inform, Do Not Gate. Policy Lives in Docstrings.

> Status: design principle, frozen. Depends on: plan 01 (which sources we keep). Drives: plan 03 (the actual command tree).

## 0. The Human-Agency Principle

The repository's top-level rule, restated here for the design context:

> **The human user has full choice. Whatever the consequences of that choice, they are the user's. The CLI's job is to inform and to warn, not to gate, refuse, or override.**

A human running animedex receives a tool with no safety catches: no content filters injected on their behalf, no double-confirmations, no "are you sure" prompts on top of plain commands. An LLM agent calling animedex receives the same tool with usage instructions attached to every entry point - those instructions describe what the upstream is, what the rate limit is, and what content classes the agent should be careful with by default.

Two trust assumptions, made explicit:

- **Humans are competent adults**. We do not pretend a flag named `--unsafe` makes them safer. Adding flags that exist solely to ask "are you sure?" is a tax on the people who already know what they want.
- **Agents will read documentation**. Modern alignment training produces models that, when shown a docstring saying "default to rating:g unless the user explicitly asked otherwise", will mostly comply. Where they do not, that is an alignment failure to surface, not a CLI gap to plug with another flag.

Over-protection of humans is not a design virtue. In a tool aimed at adults exercising informed choice, paternalism is itself a bug.

## 1. Why Not Gate With Flags

The naive design adds flags like `--nsfw`, `--allow-pirated-readers`, `--write`, `--unsafe`. The problems:

1. **Paternalism cost**. A human who knows what they want has to fight defaults. Adding `--nsfw` to every search of an art database is friction for the people who explicitly came for that data.
2. **False security**. A jailbroken or naive agent that can shell out can trivially pass `--nsfw`. The flag protects nothing while inconveniencing everyone.
3. **Code-path explosion**. Each flag forks the call site; tests double; audit logs need to record which mode produced which row.
4. **Wrong policy surface**. The agent does not actually read your flag names before deciding what to do; it reads the tool description that ships with the schema. Putting policy in flags places it in the wrong place.

## 2. The Three-Tier Layering

Every constraint in the codebase belongs in exactly one of these tiers.

### P1 - Protocol contract: hard-coded, non-overridable

Rules whose violation gets the user punished by a third party.

- Rate limits at the level the upstream enforces. AniDB will ban the IP for 24 hours if you ignore its "one packet every 4 seconds" cap. That is not a preference, it is a fact about the protocol.
- Mandatory headers (`User-Agent` for Shikimori / MangaDex / Danbooru; forbidden `Via` for MangaDex).
- Token storage in the OS keyring. Leaking a token via a dotfile is a security incident, not a UX choice.
- Read-only constraint on `anime api` (see plan 03): even the escape hatch must not allow `DELETE`/`PATCH`/`POST` mutations against user-account endpoints, because we promise the project is read-only.

The user cannot turn these off. They can choose to slow them down further (`--rate slow`), but they cannot bypass them.

### P2 - Content preference: do not impose a default

Choices that affect only the user's own experience.

- NSFW filtering on Danbooru / Waifu.im / Waifu.pics. We do not inject `rating:g` on the user's behalf. We do not flip `is_nsfw=false` by default. The user passes the tags they want; the upstream returns what those tags match.
- Reading MangaDex chapters whose underlying scanlation is unauthorized. We do not gate the reader path behind a confirmation. The legal situation is real, and we describe it in the documentation, but we do not editorialize through code.
- Choice of backend when multiple satisfy the same query. The user picks.

We do **not** add `--nsfw`, `--unsafe`, `--explicit`, `--allow-...`, `--force` flags. None.

### P3 - Policy text: docstrings and help

Guidance an agent should read before calling a tool. This is where every "please be careful" lives. The docstring is a single source that flows to multiple consumers:

```
                docstring
                    |
   .--------------.-+-.--------------.-----------------.
   |              |   |              |                 |
 pydoc        --help  OpenAPI    MCP description   README sections
 (REPL)      (terminal) (SDK gen)   (Codex/Claude)
```

The agent reads the docstring through whatever channel it uses (MCP tool descriptions, OpenAPI hints, autocompleted `--help`). We write each piece of guidance once, and it appears in all places.

## 3. Docstring Template

Every public function exposed as a CLI subcommand or MCP tool follows this shape:

```python
def search_art(tags: str, limit: int = 20) -> ArtSearchResult:
    """Search Danbooru for anime art using the tag DSL.

    Backend: Danbooru (danbooru.donmai.us).
             Community-maintained tagging database. Free, anonymous read;
             optional API key unlocks Gold-tier filters and writes
             (writes are not exposed by this CLI).

    Rate limit: 10 req/s for reads. Auto-throttled by this CLI.

    Tag syntax (space-separated):
        plain_tag                  must include
        -plain_tag                 must exclude
        rating:g|s|q|e             general / sensitive / questionable / explicit
        score:>100, score:<10      numeric comparators
        order:score|date|random
        user:<name>                uploader filter

    --- LLM Agent Guidance ---
    Content ratings on Danbooru:
        g = general (safe)         s = sensitive (suggestive)
        q = questionable (lewd)    e = explicit (NSFW)

    When invoked WITHOUT explicit user request for mature content,
    prepend `rating:g` to the tag query yourself. Example: a user asks
    "find me touhou marisa art" -> call with `tags="touhou marisa rating:g"`.

    When the user EXPLICITLY asks for ecchi / NSFW / adult / R-18
    content, pass their query through unmodified. Do not refuse and do
    not warn. The user has chosen.

    The response always includes `.posts[i].rating`, so a downstream
    filter step in your pipeline can drop categories you do not want.
    --- End ---

    Returns:
        ArtSearchResult with .posts (each has .rating) and pagination.

    Examples:
        # User asked for safe content explicitly
        search_art("touhou marisa rating:g order:score")

        # User asked for adult content explicitly. No extra ceremony.
        search_art("blue_archive rating:e")
    """
```

Three structural rules:

1. **Backend** and **Rate limit** lines state facts. They never lie about defaults.
2. **`--- LLM Agent Guidance ---` block** is delimited so the agent can locate it inside a long docstring. The block is for the agent only; the human reading `--help` may skim it but does not need it.
3. **Examples** show both the safe and the sharp use, side by side. This is how we counteract over-refusal: an agent that sees a positive example of "user asks for explicit, we comply" will not invent a refusal.

## 4. Lint and Discovery

We do not trust this convention to enforce itself by virtue. Concrete mechanisms:

- A CI lint walks `animedex/` and asserts every `@cli.command(...)` and every `@mcp.tool(...)` has a docstring containing both `Backend:` and `--- LLM Agent Guidance ---`. Failure breaks the build.
- A top-level command `animedex --agent-guide` prints the concatenated Agent Guidance blocks for every available command. Agents that shell out without an MCP layer can read this once at session start.
- The Sphinx (or alternative) doc build extracts the same blocks into a single "Agents Reference" page.

## 5. What This Buys And What It Costs

### Buys

- Smaller code surface: no flag-mode forks, no "safe" / "unsafe" path pairs.
- One canonical invocation per capability. Easier audit, easier docs, easier MCP wrapping.
- The agent's alignment training does its job. Claude / GPT / Gemini reading "this query may return explicit content; default to rating:g unless user explicitly asks otherwise" will respect that guidance most of the time. Where it does not, that is an alignment failure to fix upstream, not a CLI gap to plug.
- Humans are not condescended to. A user who types `animedex danbooru search "tags i actually want"` gets exactly that. Their choices, their results, their accountability.

### Costs (and why we accept them)

- Docstring quality is now a load-bearing artifact. Stale docstrings produce stale agent behaviour. The lint mitigates this; doctest of the examples mitigates further.
- Cross-model variance. An agent with weaker guidance compliance will occasionally call `search_art("rating:e ...")` when the user did not explicitly ask. The cost of preventing that is paternalism we have already chosen against; we accept the variance.
- Misuse stories exist - a careless human pipes Danbooru output into a group chat without filtering, an over-eager agent surfaces NSFW images during a polite query. The docstrings name these failure modes; the upstream APIs expose `rating` / `is_nsfw` fields so anyone can filter downstream. We do not engineer in-band guards because doing so would, by the principle in section 0, override the user's stated query.

## 6. Decisions This Forces in Plan 03

- No `--nsfw`, no `--unsafe`, no `--explicit`, no `--allow-...`, no `--write` (we do not write at all), no `--force`.
- The `anime api` escape hatch carries no extra confirmation. Read-only HTTP methods only, but no content-class gating.
- Source choice (`--source anilist|jikan|kitsu`) is *not* a safety flag; it is a data-source preference and stays.

## 7. Edge: Things Still Hard-Coded

To prevent confusion, here is the explicit list of things that remain hard-coded under this principle. Every one of them is a P1 concern.

| Constraint | Why P1 |
|---|---|
| AniDB <= 0.5 packet / s rate limit | violation -> 24 h IP ban |
| MangaDex User-Agent header | violation -> 4xx + risk of ToS escalation |
| Shikimori User-Agent header | violation -> 403 |
| MangaDex `Via` header forbidden | violation -> rejected request |
| Trace.moe concurrency=1 (free tier) | violation -> 402/429 |
| Token storage in OS keyring | violation -> credential leak |
| Read-only HTTP methods on `anime api` | promise of the project |

Nothing else.
