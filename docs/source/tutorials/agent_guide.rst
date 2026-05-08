``animedex --agent-guide`` (for LLM agents)
===========================================

animedex is designed for two audiences. The first is a human at a
terminal. The second is an LLM agent (Codex, Claude, and friends)
shelling out to ``animedex`` as a tool. This page is for the second.

Why a single CLI flag for the catalogue
---------------------------------------

When an agent shells out to a CLI it has not seen before, the
typical reflex is to spam ``--help`` on every subcommand and try to
stitch the pieces back together. animedex short-circuits that: every
command's docstring carries an ``--- LLM Agent Guidance --- ...
--- End ---`` block, and a single top-level invocation prints all of
them at once.

.. code-block:: bash

   animedex --agent-guide

The output is structured plain text — one ``=== <command> ===``
header per command, followed by the guidance block, separated by
blank lines. Total output is in the low thousands of characters
across the entire CLI tree, comfortably below any reasonable agent
context budget.

What the guidance blocks contain
--------------------------------

The blocks describe **decisions the agent should make**, not
**facts about the call**. A typical block names:

* The command's content classification (NSFW / SFW posture, age-of-
  consent considerations).
* The reflex when the user has not explicitly asked for mature
  content (e.g. "prepend ``rating:g``" for Danbooru, "no filter
  needed" for nekos.best).
* Privacy considerations when the command surfaces user-attributable
  data (e.g. Trace.moe ``/me`` echoes the caller's egress IP — the
  rich shape carries it; the common shape does not).
* Pagination shapes that are non-obvious (e.g. Jikan's long-tail
  endpoints all return ``JikanGenericResponse``; use ``--jq`` to
  filter).
* Empty-result semantics that differ from the obvious reading (e.g.
  nekos.best ``/search`` is fuzzy and never returns empty).

Backend / Rate-limit / Examples sections live in a separate part of
the docstring — they describe **facts the agent needs to plan its
call**, and they are visible on ordinary ``--help`` too.

Example: a real ``--agent-guide`` excerpt
-----------------------------------------

.. code-block:: text

   === anilist search ===
   Read-only AniList query. Anonymous reads cover the public schema;
   auth-required endpoints raise auth-required at runtime until token
   storage lands.

   === jikan search ===
   Search returns anime regardless of content rating by default. Pass
   --sfw true if the user did not explicitly ask for adult/ecchi
   material. When the user did explicitly request such content, pass
   it through unmodified — the project's posture is to inform, not to
   gate. The 'rating' field on each row tags general/PG-13/R+/Rx so a
   downstream pipeline can re-filter.

   === nekos search ===
   Searches anime_name / artist_name / source_url for the query phrase.
   type=1 for images (default), type=2 for GIFs. The upstream is
   fuzzy: it always returns up to 'amount' results, falling through
   to a near-random ranking when nothing closely matches — callers
   cannot rely on an empty-results signal. nekos.best v2 has no NSFW
   tier, so result rating is always 'g' and agents do not need to add
   a content filter.

   === trace search ===
   Identify anime scenes from screenshots; --anilist-info inlines
   AnimeTitle so callers can chain into anilist commands without an
   extra round-trip.

The above is real output — every block was extracted from a live
CLI subcommand by the policy lint and the ``animedex --agent-guide``
flag. Regenerate it any time with the same command.

Per-command overrides
---------------------

Most commands share a backend-wide default guidance string. A
handful of commands have an **operation-specific** override —
``register_subcommand`` accepts a ``guidance_override`` keyword that
the policy lint preserves verbatim. This is how ``jikan search``
gets its NSFW-default-filter advice while ``jikan top-anime`` keeps
the Jikan-wide default.

If you write tooling that consumes the agent guide, parse on the
``=== ... ===`` headers and treat each block as an independent
record.

The MCP forward path
--------------------

A future revision will expose the same surface as a Model Context
Protocol server (``animedex mcp serve``). The MCP scaffolding in
``animedex.mcp`` is a lazy-import entry point today: it has no
import-time side effects and the MCP runtime dependencies live in
the ``requirements-mcp.txt`` extras (not the runtime baseline).
Until ``mcp serve`` lands, the ``--agent-guide`` flag is the
project's single best-effort tool catalogue.

Pairing pattern: ``--jq`` for structured extraction
---------------------------------------------------

When you have parsed the catalogue and chosen the right command,
the next reflex is to project just the field your downstream step
needs. Use ``--jq``:

.. code-block:: bash

   # Pull just the romaji title — short, deterministic, easy to
   # parse without grep.
   animedex anilist show 154587 --jq '.title.romaji'
   # => "Sousou no Frieren"

   # Pull just the URLs from a multi-result image fetch.
   animedex nekos image husbando --amount 5 --jq '.[].url'

The bundled jq wheel ships with the package; it always works without
a host ``jq`` binary on PATH. A bad expression surfaces as a clean
``ApiError`` with ``reason="jq-failed"``, which the CLI re-raises
as a ``click.ClickException`` (typed prefix, non-zero exit, no
Python traceback in the output).

Reading the rate-limit posture
------------------------------

Every command's docstring has a ``Rate limit:`` line. Treat it as a
hard ceiling: the project's transport will block until the bucket
refills, and burning through the budget on a degraded backend (e.g.
AniList's anonymous 30 / min) will visibly slow down your loop. A
pragmatic agent reads the rate-limit line, paces its calls
accordingly, and uses the local SQLite cache (default for every
2xx response) to absorb duplicates without triggering the bucket.

If you absolutely need to bust the cache for a fresh fetch, pass
``--no-cache``. Use it deliberately — it skips the cache **read AND
the cache write**, so a hot path that always passes ``--no-cache``
will silently disable caching for itself.

Verifying a fresh install
-------------------------

Two cheap probes confirm the CLI is functional in your sandbox:

.. code-block:: bash

   animedex --version
   animedex selftest

``selftest`` is local-only: it imports every project module, runs
each module's offline ``selftest()`` callable, and probes every
registered subcommand's ``--help``. It does not touch the network,
so it is safe to run in a sandboxed environment. Exit ``0`` means
healthy; ``1`` means at least one check failed; ``2`` means the
runner itself crashed (should be unreachable).

Checklist for a well-behaved agent
----------------------------------

* On first contact with a fresh install: run ``animedex --version``
  and ``animedex selftest``.
* To populate the tool catalogue: run ``animedex --agent-guide``
  once, parse the ``=== ... ===`` headers.
* For every command call: prefer ``--jq`` to extract only the field
  the next pipeline step needs; do not paste full payloads into
  context.
* Respect ``rating`` posture. Read each command's
  ``--- LLM Agent Guidance ---`` block; honour the SFW/NSFW
  reflexes it describes when the user has not explicitly asked
  otherwise. **Do not add a redundant content filter** on top of
  one already documented in the guidance (e.g., nekos.best v2 is
  SFW-only — no further filter needed).
* Use the local cache. Avoid ``--no-cache`` unless freshness is
  load-bearing for the current step.
* Catch ``ApiError`` (or its CLI-mapped ``ClickException``) and
  branch on the typed ``reason``, not on the message text.

The :doc:`raw_passthrough` page covers the
``animedex api <backend> <path>`` escape hatch for endpoints not
yet wired into a high-level command.
