# COT paper-pilot TIER-1 claim FALSIFIED — over-emission artifact

**Date:** 2026-05-13
**Tool:** `tools/verify_cot_post_patch.py`
**Headline before:** TIER_1_RENAISSANCE, DSR 1.0, WR 90.1%, PF 2.73, n=101
**Headline after consolidation:** **NO_EDGE**, WR 40%, PF 0.17, n=5, -$52 PnL

## Forensic discovery

Original `audit_dashboard/data/cot_paper_pilot_status.json` shows 101 paper trades on `cot_positioning::CT=F` strategy. Retrospective audit grouped trades by the COT report-date they would have used.

**5 unique CFTC weekly releases produced 101 picks** — over-emission ratio ~20×:

| CFTC release date | Picks emitted | Win rate within group |
|---|---:|---|
| 2026-05-05 | 19 | 19 WON / 0 LOST |
| 2026-04-28 | 50 | 50 WON / 0 LOST |
| 2026-04-21 | 26 | 20 WON / 6 LOST |
| 2026-04-14 | 3 | 0 WON / 3 LOST |
| 2026-04-07 | 3 | 0 WON / 3 LOST |

Plus assorted single-pick reports.

## What this means

The strategy was **re-firing the same weekly signal hourly across multiple days**. When the signal was a winner (April 28 / May 5 reports), 50× over-emission inflated the headline WR. When the signal was a loser (April 7 / 14 reports), only 3× over-emission contributed to the loss count.

**The 90% WR is asymmetric over-emission, NOT real edge.**

## Consolidated 1-pick-per-cycle re-aggregation

Taking the FIRST chronological pick from each weekly cycle as the canonical signal:

| Metric | Original headline | Consolidated | Delta |
|---|---:|---:|---:|
| n_trades | 101 | **5** | -96 |
| Win rate | 90.1% | **40.0%** | **-50.1pp** |
| Profit factor | 2.73 | **0.17** | **-2.56** |
| Total PnL USD | +$360 | **-$52** | **-$412** |
| Verdict | TIER_1_RENAISSANCE | **NO_EDGE / sub-floor** | — |

## Connection to prior session findings

This is the same fabrication-risk pattern as:
- `kimi_signal_tracking` PF 0.28 → 8.38 (resolver-denominator artifact, this session)
- `multi_asset_cot` PF 21.86 / WR 94.1% (dashboard claim, NS-A DB verify pending)

**Pattern: aggregate stats that look implausibly high are usually an emission/resolver artifact, not real edge.**

## Why PR #941 lag patch doesn't fix this

PR #941 enforces 3-day lag between CFTC report date and pick emission. That fixes the **look-ahead bias** failure mode. It does NOT address the **over-emission** failure mode (same weekly signal triggering 50 picks within the 3-day-public window).

Both bugs needed fixing. The lag patch alone is insufficient.

## Required follow-up (CRITICAL)

1. **Add emission de-duplication** to `cot_positioning_strategy()`: once a signal is emitted for a given (symbol, report_date, direction) tuple, do NOT emit again until next CFTC report. Code change in `alpha_engine/cot_positioning.py`.

2. **Re-classify `cot_positioning::CT=F` from TIER_1 to NO_EDGE** in `audit_dashboard/data/cot_paper_pilot_status.json` and downstream dashboards. The strategy's true n is 5 weekly signals over ~5 weeks (Apr 7 – May 5), and on that real sample size the edge is negative.

3. **Block real-money sizing** on cot_positioning::CT=F until:
   - De-duplication patch ships
   - Fresh paper pilot runs for 4+ weeks producing 4+ unique weekly cycles
   - Re-aggregated PF ≥ 1.5 on 1-pick-per-cycle basis (acceptance gate from `reports/cot_paper_pilot_testing_plan_2026-05-12.md`)

4. **Re-audit other strategies for over-emission**: any strategy whose dashboard n is >5× its expected signal-cycle count is suspect. Candidates from this session's earlier work: `multi_asset_cot` (102 closed picks but signal source unclear), `kimi_signal_tracking` (similar emission pattern unconfirmed).

## Implications for COMMODITY class promotion

Plan synthesis (`reports/real_money_plan_review_synthesis_20260513.md`) noted COMMODITY Tier-1 status depends on COT timing-leakage fix not crashing it. This finding goes further: **the COMMODITY TIER-1 claim was already crashed by over-emission, independently of the lag bug.**

Real-money-ready gate analysis must now update:
- COMMODITY: not Tier-1 — n inflated by over-emission; need 4-week post-dedup pilot
- EQUITY: still Tier-2 (n=447 is real)
- VIX+YC overlay (PR #960): still the highest-conviction path to 2nd Tier-2+ class

## Cross-references

- `tools/verify_cot_post_patch.py` — this verifier
- `reports/cot_paper_pilot_retro_lag_audit.json` — raw output (5 multi-trade groups visible)
- `reports/cot_timing_leakage_audit_2026-05-13.md` — original lag bug audit (PR #941)
- `reports/cot_paper_pilot_testing_plan_2026-05-12.md` — acceptance gate
- `audit_dashboard/data/cot_paper_pilot_status.json` — original headline payload
- `alpha_engine/cot_positioning.py` — strategy code (lag patch applied; dedup patch needed)

NFA. No production change. Strategy reclassification + dedup patch are follow-up work.
