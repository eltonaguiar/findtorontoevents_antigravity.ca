# ETFs — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** Pilot signal (with equities); no standalone production proof

## Current State (evidence)
- `alpha_engine/data/active_picks_etf.json` (16 picks) not synced to DB — fragmentation.
- ETFs often share drivers with equities/commodities/rates; current system data quality issues apply.

## Evidence of Edge
| Approach | Evidence | Verdict |
|---|---|---|
| Walk-Forward Variant C (deepAI) | PF 1.26, n=237, p<0.0013 (equity/ETF pilot) | **PILOT** |
| Faber TAA (trend-following on diversified ETFs) | Well-known regime-robust baseline in literature; local run lacked OOS significance | **RESEARCH CANDIDATE** |

## Recommendation
- **Primary:** **Faber TAA** (e.g. 10-month/200-day trend filter, risk-off to cash/short-duration) across a diversified ETF set — easy to backtest deeply on daily data.
- **Secondary:** include ETFs in **Variant C** replication/pilot.
- **Gate before live:** OOS PF/Sharpe/MDD/PBO/DSR clearance, net of costs/slippage, benchmark comparison.

## Implementation Notes
- Sync `active_picks_etf.json`; ensure ETF instruments map to correct risk buckets.
- Prefer liquid, low-cost ETFs; model spread/borrow where relevant.
