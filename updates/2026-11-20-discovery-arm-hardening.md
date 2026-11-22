# Discovery arm: four ways it could have reported a false positive (2026-11-20)

## What was broken

`tools/skyrocket_reverse_eng.py` is the reverse-engineering entry point, and it
had four gaps that all bias toward finding something:

1. **The objective was gross.** The event label came from `pnl_pct` — return
   before costs. A feature that predicts high-turnover winners looks excellent on
   gross and can be net-negative, which is precisely the failure mode that has
   produced most of this repo's inflated numbers.
2. **No direction check.** Rank correlation, the decile spread and the matched
   difference are three views of one feature with different failure modes. They
   were reported side by side but never compared, so a feature could show
   `rho > 0` with a *negative* decile spread and nothing flagged it.
3. **Silent skips.** A feature with too few rows or too few distinct values was
   dropped with `continue`. `features_tested: 0` then reads identically whether
   nothing is predictive or nothing was measurable — the same ambiguity as an
   empty search result.
4. **No trial memory.** Each run counted its own tests and forgot them. Running
   the same search twice on overlapping data resets the multiple-testing debt to
   zero and makes a repeat "discovery" look independent.

## What changed

- `resolve_objective()` prefers `pnl_net_pct` / `net_pnl_pct` when present and
  records why in `event.objective_note`; it keeps the requested field when no net
  field exists but says the survivors must be cost-checked downstream. An explicit
  net request is never rewritten.
- `direction_check()` returns `consistent` / `inconsistent` / `unknown`, and
  `analyze()` collects the inconsistent features into `direction_inconsistent`.
- Every skipped feature is now recorded in `skipped` with its `coverage`, `n`,
  `distinct` count and a human reason. `inconclusive` is true when nothing was
  testable but candidates existed.
- `load_trial_counter` / `bump_trial_counter` persist a cumulative count to JSON,
  wired via `--trial-counter` and reported as `trials: {path, this_run, cumulative}`.
- Each tested feature also carries its own `coverage`.

## Verification

`python3 -m pytest tests/test_skyrocket_reverse_eng.py tests/test_rsi2_replication.py tests/test_audit3_tribunal.py -q`
→ 62 passed (18 in the discovery suite, 8 of them new).

One test failure was mine, not the code's: I asserted that `rho > 0` with both the
decile spread and the matched diff negative should be "consistent". It is not —
that is a real three-way disagreement. The test now asserts the correct behavior
and an all-negative agreement case.

## Limitation

The trial counter counts features tested, not parameter combinations explored.
It is a floor on the true search space, the same caveat as the cumulative DSR
count in the tribunal.
