# P1-5 blocker: H-119 benchmark coverage 0.798 (credential-free verifier added)

**Date:** 2026-11-23
**Worktree:** vanilla-handsaw
**Author:** Kilo (orchestrator)

## Blocker
The plan requires benchmark_coverage ≥ 0.90 for H-119 (and other forward hypotheses) before the forward gate can promote any pod. Live measurement on `audit2_forward.json` (generated 2026-11-19T08:41Z):

```
H-119: benchmark_leg 343 / n 430 = 0.798 < 0.90
```

Root cause (per plan): `forward_observations_ingest.py:302` `benchmark_leg(...)` misses ~87 rows because the right-edge query window does not reach the latest exit for every symbol. The fix is a DB-backed price join (`BENCHMARK_LOOKAHEAD_MS` padding + backfill).

## What was shipped (credential-free)
- `tools/verify_forward_benchmark.py` — reads `audit2_forward.json` (or `forward_clock.json`), computes coverage from `by_hypothesis` shape, fails CI if any hypothesis < 0.90.
- Can run in any CI job that has the published JSON (no DB creds required).
- Current run on the live file correctly exits 1 (0.798 < 0.90), proving the gate is wired.

## Test plan executed
```bash
python3 tools/verify_forward_benchmark.py          # EXIT=1 (expected)
python3 -m pytest tests/test_pod_emission_audit.py tests/test_assert_surface_parity.py tests/test_audit3_tribunal.py -q
# 43 passed
```

## Numbers
- 87 rows missing (plan estimate)
- 0.798 measured coverage (H-119)
- 1 writer site for verdict history (already verified in item 2)
- 4 drawdown tests green (item 3)
- 4 pod-emission tests green (item 4)

## Remaining
The actual price-join backfill still requires `ejaguiar1_stocks` creds (dbpasses.txt). Operator/DBA action only. This tool gives CI a permanent, non-silent signal until the data is fixed.

*Nothing here is investment advice. 0 PROVEN / 0 CANDIDATE.*
