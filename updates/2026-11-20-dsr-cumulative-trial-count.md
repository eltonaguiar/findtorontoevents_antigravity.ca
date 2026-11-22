# DSR counted only this ledger's trials (2026-11-20)

## What was broken

`audit3_tribunal.py` publishes `dsr_n_trials` per cell and `n_trials_dsr` in
provenance, which looks like a real multiple-testing correction. It is derived
from `n_trials = len(strat_groups)` — the number of cells **in the current
ledger**.

A live ledger is a survivor list. Every hypothesis that was tried and refuted
is also a trial, and those are exactly the rows a live ledger no longer shows.
So the deflated Sharpe was deflated by the trials that survived, which is the
optimistic direction: a cell can clear the DSR threshold partly because the
configurations that failed were forgotten.

## What changed

- `registry_trial_count(path="reports/hypothesis_registry.json")` — counts
  pre-registered hypotheses via `iter_hypotheses` from `hypothesis_status`.
  Returns `{"available", "count", "reason"}` and reports a missing or
  unreadable registry explicitly in `reason` rather than returning zero
  silently (zero would restore exactly the optimism this removes).
- Per cell: `dsr_cumulative`, `dsr_cumulative_n_trials`,
  `dsr_survives_cumulative` — the same deflated Sharpe recomputed with
  `n_trials_cumulative = n_trials + registry_count`.
- Provenance: `n_trials_registry`, `n_trials_cumulative`,
  `registry_trials_available`, `registry_trials_reason`,
  `n_cells_dsr_fails_cumulative`.

The existing verdict path is untouched. Re-gating on the registry count would
change verdicts on the strength of a count whose semantics (what counts as one
trial: one hypothesis, one parameter sweep, one feature family?) are still being
settled. Recording both numbers makes the difference visible without pretending
it is decided.

## Verification

`python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_edge_hunt.py -q`
→ 49 passed.

## Limitation

The cumulative count is a lower bound on the true search space. It counts
filed hypotheses, not unfiled ones, and not per-hypothesis parameter grids. It
is strictly better than counting survivors, and still not the real trial count.
