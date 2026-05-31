# Phase-4 Suspect-PF Audit — Plan (2026-05-31)

## Targets
1. `cta_golden_cross_200` COMMODITY: n=25, WR 96%, PF 44, mean 4.55%, std 1.98%
2. `prediction_market_consensus`: n=89, WR 90%, PF 24.5

## Method
- Query `trading_picks` from `ejaguiar1_stocks` for both strategies.
- Recompute `pnl_pct` from entry/exit/direction.
- Compare `pnl_pct` vs `(TP - entry)/entry` exact matches → TP_HIT artifact ratio.
- Check exit_reason distribution, symbol concentration (HHI), SL/TP sanity, direction-PnL coherence.
- Diagnose: RETIRE / MUTATE / VERIFY.
- Ship docs-only PR with findings.
