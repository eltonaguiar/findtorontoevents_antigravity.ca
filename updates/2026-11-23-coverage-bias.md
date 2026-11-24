# 2026-11-23 — Coverage bias (Block 56)

## What was asked

Is the "measured fifth" behind `audit3_ledger.json`'s verdicts a representative
subsample of all closed picks, or a biased one? The brief quoted
`covered = 3,133 of total_closed_picks = 14,941` (20.97%) as coming from
`coverage.denominator`.

## What was measured

- Reproduced the ledger at `origin/main` (`85c0c9c3`). The brief's provenance is
  wrong: `3,133` is `selection_alpha.covered` and `14,941` is a mid-day
  `coverage.total_closed_picks` (commit `602ad22a`, 2026-11-23T12:35Z). At HEAD the
  values are `selection_alpha.covered = 3,190`, `n_universe = 3,500`,
  `coverage.total_closed_picks = 14,997`, `coverage.scored_rows = 8,886`.
  `coverage.denominator` contains neither number.
- Located both producers: `alpha_engine/audit3_selection_alpha.py` (price coverage,
  numerator `len(per)` at line 383) and `audit_trail/dashboard_generator.py`
  (the 3,500-row cap at line 285 and the class-reserved, most-recent-first
  selection at lines 286-287, 7031, 7135).
- Decomposed the gap: of 11,807 not price-covered, **6,111 are unscoreable**
  (excluded from the canonical view) and **5,696 are scoreable but outside the
  3,500 display cap**.
- Class mix of the 3,500-row universe vs the 8,827-row canonical population, and
  per-class price coverage (`classes[].n` vs `classes[].alpha_n`).

## What was found

**BIASED.** Two different selections stack:

1. Which picks are scoreable at all is **outcome-selected**: `auto_expired` (9,356)
   and `integrity_excluded` (6,013) are dropped because of how they resolved.
2. Which scoreable picks get a price benchmark is **class-skewed**: CRYPTO is 78.5%
   of the population but 52.7% of the priced set (0.67×); EQUITY 2.15×, ETF 2.56×.
   Per-class price coverage runs from CRYPTO 24.2% to BOND 100%; the gate itself
   marks CRYPTO, FOREX and FUTURES `alpha_coverage_ok = false`.

The 20.97% ratio is a cross-section of two unrelated quantities. The defined rates
are 91.14% of the display universe, 35.90% of the scoreable record, 21.27% of all
closed picks. Affected verdicts needing a coverage caveat: every `classes[]`
alpha field, `selection_alpha.by_class/by_slice/by_strategy/overall/gate`, and the
`segments`/`cells` built on them. `coverage.*` itself needs a different caveat
(unscored by outcome).

## What was NOT measured, and why

- Per-row covered/uncovered join, and therefore the strategy and date distribution
  of the uncovered set, and the alpha of the 310 price-missing rows.
- The class composition of the 6,111 unscoreable rows.

Reason: the canonical rows file (`resolved_closed_picks_net.json`) and the full
current `dashboard_data.json` are not shipped in the repo, and the price tables are
live MySQL. The join cannot be re-run offline from `origin/main`. Only the shipped
aggregates (ledger JSON, the 2026-11-22 payload snapshot) were usable.

## Premises in the brief that measurement falsified

- `covered` and `total_closed_picks` do **not** live under `coverage.denominator`.
- The counts are **not** 3,133 / 14,941 at HEAD (they are 3,190 / 14,997).
- The two numbers are **not** a part and a whole, so 20.97% is not a coverage rate.
