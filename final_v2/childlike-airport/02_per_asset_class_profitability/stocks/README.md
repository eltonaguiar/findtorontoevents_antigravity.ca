# Stocks — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** No proven production edge in current system; pilot signal exists

## Current State (evidence)
- `data/live_picks.db`: STOCKS 5 rows; overall pick universe heavily degraded (stale ~172d, PnL/sign/calc issues, zombies). Equity-labeled exposure small in DB snapshot.
- deepAI: aggregate/system PF ~0.80, widespread fake 0% P/L and understated losses — stock picks not exempt.
- No Kilo OOS-validated stock strategy in this pass.

## Evidence of Edge
| Approach | Evidence | Verdict |
|---|---|---|
| Walk-Forward Variant C (deepAI) | PF 1.26, n=237, p<0.0013 (equity/ETF pilot) | **PILOT** — statistically suggestive, below PF≥1.5; needs replication, broader universe, cost/slippage stress |
| Faber TAA (SMA trend, monthly) | Cited/tested in research (e.g. Kilo harness noted ~PF 3.35/Sharpe 3.78 but only ~8 train trades, no OOS significance in that run) | **RESEARCH CANDIDATE** — conceptually sound for equities; requires rigorous OOS with sufficient trades |

## Recommendation
- **Primary:** **Walk-Forward Variant C** as monitored pilot (paper/shadow) after independent reproduction and T2-gate evaluation.
- **Secondary/build:** **Faber-style trend (TAA/SMA)** on liquid equities/indices with daily data (ample history) to achieve trade/sample sufficiency.
- **Gate before live:** PF≥1.5 (target), Sharpe≥1.0, MDD<20%, PBO<0.3, DSR>0.95, n sufficient, net-of-costs; clean PnL pipeline.

## Implementation Notes
- Reproduce Variant C out-of-sample; publish parameter stability and drawdown profile.
- Add benchmark-relative and regime-aware sizing; avoid mining from the existing broken multi-signal zoo.
