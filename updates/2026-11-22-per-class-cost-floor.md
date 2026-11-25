# Added, 2026-11-22: per-class cost floor and detection limit

## What was added

`tools/per_class_cost_floor.py` (+ `reports/per_class_cost_floor_2026-11-22.json`,
`reports/2026-11-22-cost-floor-and-power.md`). Three questions, one artifact:

1. **Cost floor** — the cost multiple at which each cell's CI lower bound hits zero, from the
   measured 1× and 2× cost CI-LB. `k* = 1 + CI_LB(1x)/(CI_LB(1x) − CI_LB(2x))`.
2. **MDE** — minimum detectable effect on the daily mean at 95% confidence / 80% power.
3. **Required n** — days of daily data needed to detect a tradable effect (2× the cash hurdle).

## What it found

- **6 classes bounded, 4 already below floor, 0 unbounded.** FUTURES dies at **1.8×** the assumed
  cost (18 bp round trip); EQUITY would need **30.7×** (614 bp) before cost decided anything.
- **18 of 40 cells have a CI-LB below their own MDE.** For EQUITY the two are nearly equal
  (7.246 vs 7.17 bp/day): the programme's best cell sits exactly at the detection limit.
- **Detecting a 1.92 bp/day effect needs 15–1,572 years of daily data** depending on class. No
  daily-return backtest on 14 years can resolve an effect that size in any class here.

## A bug caught in my own first draft

The first version elected the class representative as the highest CI-LB **regardless of status**,
which made `H-200:NVDA` (n=13, `INSUFFICIENT_N`) EQUITY's best cell and pushed its cost floor to
162×. That is the same selection trap (choosing on the outcome) that this programme exists to
catch, committed by me, in a tool written to detect it.

Fixed: the representative must be **admissible** (`INSUFFICIENT_N` and `DATA_INTEGRITY_FAIL`
excluded), and a class with no admissible cell reports `NO_ADMISSIBLE_CELL` rather than promoting
one on a technicality. EQUITY's representative became `H-201` at 30.7×.

## Consistency fixes

- `reports/2026-11-22-cost-is-the-constraint.md`: "cost would have to rise ~13×" → the measured
  **30.7×**.
- Claim C-016 in `reports/claim_register.json`: same correction.

## Verified

- `python3 tools/per_class_cost_floor.py` → exit 0, 40 cells, 10 class rows, wrote JSON.
- Representative-rule change re-run and diffed: EQUITY moved `H-200:NVDA` → `H-201`,
  MUTUAL_FUND `H-216` → `H-220`.
- Register still 16 claims, C-001 intact (append-only preserved).

## Not claimed

The cost floor assumes CI-LB is locally linear in cost between 1× and 2×; beyond that it is an
extrapolation. The MDE assumes independent daily observations, which is conservative for
autocorrelated series and optimistic for event-driven ones. No forward observations, no capital.
