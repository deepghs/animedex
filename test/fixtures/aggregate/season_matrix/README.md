# Season Matrix Calibration Fixtures

This directory is the adjudicated calibration corpus for aggregate season merging. It covers every anime season from 2010 through 2025 against captured AniList and Jikan season fixtures, then records which cross-source rows are the same anime in `expected_matches.json`.

## Contents

- `candidates/*.json` are compact per-season candidate files generated from the captured upstream fixtures.
- `adjudication_inputs/*.json` are sharded, compact inputs for parallel human or model-assisted adjudication.
- `expected_matches.json` is the reviewed ground truth consumed by `tools/merge_eval/evaluate_rule.py`.

## Regenerating

Regenerate the upstream season fixtures first under `test/fixtures/anilist/season_matrix/` and `test/fixtures/jikan/season_matrix/`. Use the existing fixture capture tooling with conservative pacing, because this matrix makes 64 season requests per backend. If a proxy is needed to avoid upstream throttling, keep proxy credentials in the shell environment only and never commit them.

After the upstream fixtures are present, rebuild candidates:

```bash
PATH="$PWD/venv/bin:$PATH" python tools/merge_eval/build_candidates.py --start-year 2010 --end-year 2025
```

Build adjudication shards:

```bash
PATH="$PWD/venv/bin:$PATH" python tools/merge_eval/build_adjudication_inputs.py --shards 8
```

Review each shard and write shard outputs with `seasons[].matches[]` entries containing `anilist_index` and `jikan_index` pairs. Combine the reviewed shard outputs:

```bash
PATH="$PWD/venv/bin:$PATH" python tools/merge_eval/combine_adjudication.py path/to/shard-*.json --output test/fixtures/aggregate/season_matrix/expected_matches.json
```

Validate the deterministic merge rule against the corpus:

```bash
PATH="$PWD/venv/bin:$PATH" python tools/merge_eval/evaluate_rule.py --limit-details 40
```

The current rule expects zero false positives and zero false negatives against this checked-in corpus. If regenerated upstream data changes enough that perfect parity is no longer realistic, document the exact misses in the PR and bias threshold changes toward precision: a missed merge leaves two attributed rows visible, while a wrong merge can mislead callers about which upstream said what.
