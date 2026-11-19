# Name the strategies that never reach a forward condition (2026-11-19)

**Scope:** `alpha_engine/forward_observations_ingest.py`,
`tests/test_forward_observations_ingest.py`. Preserved from peer worktree
`vh-mainport` before deletion.

## Why

`build_rows` counted every cohort row that matched no condition into one opaque
`not_in_any_condition` number. When a pod is registered but its strategy never
appears in the honest cohort, the forward clock silently never accrues and the
only symptom is a large anonymous count.

## Change

- `build_rows(..., unmatched_out: Counter | None = None)` records
  `{(asset_class, strategy): n}` for unmatched rows.
- `collect()` returns `meta["unmatched_top"]`: the 20 most frequent
  `{asset_class, strategy, n}` entries.

Additive and optional: callers that do not pass `unmatched_out` behave exactly
as before.

## Verification

`pytest tests/test_forward_observations_ingest.py tests/test_forward_observations.py tests/test_audit3_forward_gate.py -q`
→ **53 passed**, plus a new test asserting the counter is populated for an
unmatched row.
