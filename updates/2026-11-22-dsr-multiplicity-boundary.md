# DSR multiplicity: H-201 fails by one trial, so the label changes

**Date:** 2026-11-22 · **Type:** new measurement + one self-caught bug
**Files:** `tools/dsr_multiplicity_sensitivity.py` (new),
`tests/test_dsr_multiplicity_sensitivity.py` (new, 6 passing),
`reports/dsr_multiplicity_2026-11-22.{json,md}` (new),
`plans/2026-11-22-50-action-items.md` (status log)

## What was broken

The 40-cell per-class sweep returned **0 cells clearing every gate**, and the closest one —
H-201 `xsmom_top3_6m` — was marked `FAILS_MULTIPLICITY` because its DSR is **0.9469**
against 0.95. That label states the outcome and withholds everything that matters: the
size of the miss, whether the trial count that produced it is right, and whether the
verdict is a property of the data or a property of bookkeeping. A reader cannot tell
"narrowly failed" from "failed decisively", and the difference determines whether an
independent replication is worth commissioning.

## What changed

1. **`tools/dsr_multiplicity_sensitivity.py`** rebuilds the artifact's DSR column from first
   principles. `var_sr` is not stored, so the scale is recovered exactly from the
   artifact's own `expected_max_sharpe_daily` via
   `sqrt(var_sr) = sr0 / K(N)` with `K(N) = (1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne))`. The
   skew/kurtosis denominator term is not recovered (it is not stored), so its size is
   **reported as the residual** rather than assumed away.
2. **Trial-count reconciliation.** 29 declared, 26 with cells, H-202/H-203/H-204 absent
   because they produced no admissible cell. Counted at 29 — the conservative direction.
3. **Multiplicity break-even.** H-201 holds 0.95 up to **N=28**; at 26 trials the identical
   data scores **0.9547** and would pass.
4. **Data break-even.** It needed a daily Sharpe of **0.073872** and observed **0.073600**,
   a shortfall equal to **76.7 more trading days** (0.30 years) at the same effect size.
5. **Label corrected to `NOT_PROVEN`** in the programme status log: not refuted (the return
   series is unchanged, CI-LB still +7.246 bp/day), not proven (significance that flips on
   one trial is not sizeable).

## Verification

- `python3 tools/dsr_multiplicity_sensitivity.py --cells reports/per_class_edge_2026-11-22.json`
  → `RC=0`; focus-cell residual **0.001364** (0.948264 vs 0.9469 stored).
- 39 of 40 cells reproduce within 0.05; the single outlier is H-228 at 0.1374, where the
  non-normality term is largest. Reported, not suppressed, and the tool's gate applies to
  the extrapolated cell rather than the family.
- `python3 -m pytest tests/test_dsr_multiplicity_sensitivity.py -q` → **6 passed**.

## Bug caught during the build

The first bisection hunted the **first failing** trial count in a true-then-false predicate,
so it walked away from the crossing and returned the search cap, reporting a margin of
−99,971 trials. Caught on first execution, inverted to hunt the **last passing** count, and
pinned by a regression test. The lesson is the one already in the programme: a tool that
prints an absurd number and gets believed is worse than one that raises.
