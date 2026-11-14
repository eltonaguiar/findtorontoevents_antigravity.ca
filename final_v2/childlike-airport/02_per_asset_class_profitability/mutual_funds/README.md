# Mutual Funds — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** No coverage, no validated edge (build required)

## Current State (evidence)
- `data/live_picks.db`: **no mutual fund picks**; `MUTUAL_FUND` not represented as a first-class class in the audited flow.
- No peer/Kilo OOS results for mutual funds.

## Evidence of Edge
- **None.**

## Recommendation
- **Primary (to build): Mutual Fund Faber TAA / trend allocation** using end-of-day NAV series (lower frequency, execution/latency constraints).
- Treat as a **new capability**, not a tuning of existing crypto/equity logic.

## Implementation Notes (proposed)
- Add `MUTUAL_FUND` to `alpha_engine/asset_class.py` and `ml_gatekeeper/gatekeeper.py` (`ASSET_CLASS_MAP` / classification paths).
- Wire/build `mutual_fund_ranker.py` (or equivalent) for universe selection and trend/risk filters.
- Account for trading restrictions, fees, minimums, and next-NAV execution; validate with realistic fill assumptions.
- Only promote after OOS validation meeting strict gates (ample daily history should make sample size feasible).
