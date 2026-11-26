# Weekly scorecard

_generated 2026-11-26 02:41 UTC by `tools/weekly_scorecard.py`_

T-bill hurdle used throughout: **3.50%/yr**

## Verdicts

| item | verdict | evidence | class |
|---|---|---|---|
| Harness certification | **NOT RUN** | artifact absent | - |
| Integrity lint | **NOT RUN** | run tools/integrity_lint.py | - |
| Live ledger net expectancy | **NOT RUN** | run tools/ledger_mine.py | - |
| Funding carry, net of fees | **NOT RUN** | run tools/funding_venue_dispersion.py | - |
| Vol risk premium | **NOT RUN** | run tools/vol_premium_pairs.py | - |
| Prediction market calibration | **NOT RUN** | run tools/prediction_market_calibration.py | - |
| Provenance ledger | **EMPTY** | 0 records; chain intact; forward-creditable 0 | deterministic |
| Provenance resolution | **NO DATA** | 0 resolved picks yet - no statistic can be formed | - |
| Source falsification | **NOT RUN** | run tools/mega_mutation_falsification.py | - |

## State notes

- Provenance ledger is EMPTY - no pick has yet been recorded at emit time, so no result can be forward-credited.
- provenance gate could not run: module 'provenance_resolver' has no attribute 'gate_problems'
- provenance gate: gate could not run: module 'provenance_resolver' has no attribute 'gate_problems'
- NOT RUN: harness certification (drift detector) (`reports/harness_certification/latest.json`)
- NOT RUN: live ledger mine (leakage + per-class + attribution) (`reports/ledger_mine/ledger_mine.json`)
- NOT RUN: pick survival + regime conditioning (`reports/survival_regime/survival_regime.json`)
- NOT RUN: cross-venue funding dispersion + fee tiers (`reports/funding_venues/funding_venues.json`)
- NOT RUN: vol risk premium + GDX/SLV pairs (`reports/vol_premium_pairs/vol_premium_pairs.json`)
- NOT RUN: prediction market calibration (`reports/prediction_market_calibration/calibration.json`)
- NOT RUN: execution sensitivity (capacity / maker-taker / turnover / fill) (`reports/execution_sensitivity/execution_sensitivity.json`)
- NOT RUN: carry execution cost (`reports/carry_execution/carry_execution_cost.json`)
- NOT RUN: pre-registered outside tests (`reports/prereg_outside/prereg_outside_tests.json`)
- NOT RUN: source falsification battery (max-stat null, median, duplicates) (`reports/mega_mutation/falsification.json`)
- NOT RUN: integrity lint (selection-on-DV, provenance, n_trials) (`reports/integrity_lint/latest.json`)

## What this scorecard deliberately does not do

- It does not rank strategies. Ranking is how an unmeasured candidate
  gets promoted; labels are set by evidence class, not by return.
- It does not print a number it could not measure. Absent artifacts
  read NOT RUN, and unmeasured cost blocks promotion
  (`docs/PROMOTION_GATE_2026-11-22.md` gate 1).
- It does not report gross without net.

---
No capital deployed. Not investment advice. UNMEASURED means unmeasured, not zero.