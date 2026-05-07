# animedex Design Plans

This directory holds the staged design documents for **animedex**. The plans are ordered: each one builds on the previous, and together they form the single source of truth for "why animedex is shaped the way it is".

When in doubt about scope, behaviour, or naming, check these files in order. Disagreements between code and plan should be resolved by either updating the plan first (if the design changed) or fixing the code (if the code diverged unintentionally).

## Index

| # | File | Topic |
|---|------|-------|
| 01 | [`01-public-apis-anime-survey.md`](./01-public-apis-anime-survey.md) | Survey of every entry under the Anime section of `public-apis/public-apis`. Per-site capabilities, rate limits, schema discoverability, LLM-agent friendliness, effort estimates. Identifies dead, redundant, and load-bearing sources. |
| 02 | [`02-design-policy-as-docstring.md`](./02-design-policy-as-docstring.md) | The "policy lives in docstrings, not in code gates" principle. Defines the P1 / P2 / P3 layering (protocol contract, content preference, policy text) and how that drives a flag-light, agent-friendly surface. |
| 03 | [`03-cli-architecture-gh-flavored.md`](./03-cli-architecture-gh-flavored.md) | The final command tree: read-only, multi-source-explicit, gh-flavored. Includes the `anime api` raw passthrough escape hatch, source attribution rules, and the auth model. |
| 04 | [`04-roadmap-and-mvp.md`](./04-roadmap-and-mvp.md) | Phased work plan. MVP scope (5 days), full v1 scope (~3 weeks), AniDB UDP as a separate heavy track. |

## Reading Order

If you are **new to the project**, read `01` → `02` → `03` → `04` in order.

If you are **implementing a feature**, the binding documents are `03` (what the CLI must look like) and `04` (when each piece is scheduled). `01` and `02` are context.

If you are **adding a backend not in the survey**, write a new plan file (`05-...md`, etc.) with the same structure as `01`'s per-entry template, then update `03`'s command tree.
