# P1-1 — Standing Artifact-Detector CI Gate

**Agent:** INCEPTION / VLLM
**Date:** 2026-10-22

## What was broken

The frozen-exit resolver bug (`audit_trail/universal_pick_resolver.py`) used to fetch prices once per run and stamp the same snapshot onto *every* unresolved pick of a symbol, manufacturing fake clustered "wins" (a cluster of N wins sharing one exit date). The walk-forward harness detects these via `detect_artifact_cells` (wins > 2× distinct exit dates) and reported 19 such cells in `reports/walkforward_strategy_eval_2026-10-22.json`.

There was no standing gate to stop an artifact-laden report from silently passing downstream. If the resolver ever regressed (or a stale report persisted), fake clusters could poison rankings unnoticed.

## What changed

- [`tools/check_walkforward_artifact_cells.py`](../../tools/check_walkforward_artifact_cells.py) — **New.** Standalone CI check. Loads the latest `reports/walkforward_strategy_eval_*.json`, reads `artifact_cells`, and exits:
  - `0` when zero artifact cells (clean resolution) → CI passes;
  - `1` when any artifact cells are present (lists them) → CI fails;
  - `2` on report-not-found / usage error.
- [`tests/test_check_walkforward_artifact_cells.py`](../../tests/test_check_walkforward_artifact_cells.py) — **New.** 5 tests (clean passes, artifact fails, multi-listing, missing-report, newest-glob), all green.
- [`.github/workflows/artifact-detector.yml`](../../.github/workflows/artifact-detector.yml) — **New.** Daily 06:30 UTC guard + on-push (checker/workflow/harness paths) + manual dispatch.

## Verification

- `pytest tests/test_check_walkforward_artifact_cells.py -q` → **5 passed**.
- Existing harness suite `tests/test_walkforward_strategy_eval.py test_walkforward_gate.py test_walkforward_by_class.py` → **26 passed** (no regression).
- Checker run against the current (artifact-laden) report → **exit 1** with all 19 cells listed — correct guardian behavior. After P0-1's fixed resolver produces a clean re-run report, this gate will pass.

## Remaining / next

- P1-2: re-run the 90-day harness on fixed-resolver data and confirm whether any sleeve clears the strict gate (PF ≥ 1.15, WR ≥ 0.50, n ≥ 10, train PF > 1.0, non-artifact).
- Once the re-run report is clean, this gate turns green automatically.
