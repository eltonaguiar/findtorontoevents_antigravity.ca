# Tactical Pick Emission — Wiring & Status (finpredict-v4)

**Date:** 2026-11-15 (AM)
**Status:** LIVE — model picks fed into the audit dashboard pipeline.

---

## What was emitted

4 tactical allocation picks from the validated Faber 200-day MA + dual-momentum model:

| Symbol | Class | Direction | Score | Signal |
|--------|-------|-----------|-------|--------|
| VTI | ETF | STRONG_BUY | 73.0 | Above 200dMA; 6m mom +3.0% |
| TLT | BOND | STRONG_BUY | 70.0 | Flight-to-safety (below 200dMA) |
| SGOV | BOND | STRONG_BUY | 71.8 | T-bill floor, above 200dMA |
| BND | BOND | STRONG_BUY | 70.0 | Bond core (below 200dMA) |

Justification: these match the *only* grounded, backtest-proven path (Faber 200-day MA trend, Sharpe 1.01 vs 0.79 B&H, maxDD -18.8% vs -46.3%). We emit the defensive sleeve (TLT/SGOV/BND) when risk assets fall below their trend, so the system stays positioned in the safest liquid assets rather than chasing falling prices.

---

## The wiring (how it reaches the audit dashboard)

1. **Emitter:** `2026-11-15_AM_plan/finpredict-v4/05_simulation/emit_tactical_picks.py`
   - Pulls live prices (yfinance), computes 200-day MA + 6-m momentum.
   - Writes `audit_dashboard/data/picks_now_model_finpredict_v4.json`.
2. **Merge:** model picks are added to `audit_dashboard/data/picks_now.json` (schema-compatible; existing 25 preserved).
3. **DB save:** `tools/save_picks_to_db.py` inserts into MySQL `picks_now_tracker` (29 picks inserted).
4. **Live PnL:** `tools/live_pnl_tracker.py --apply` fetches current prices and writes `audit_dashboard/data/picks_now_live_pnl.json` — the file the `/audit` dashboard reads.

Verified: VTI / TLT / SGOV / BND all appear in `picks_now_live_pnl.json` with live `current_price` and `pnl_pct` (e.g., BND +0.8%, SGOV +0.04–0.13%).

---

## How to refresh

```bash
# regenerate model picks (daily)
python3 2026-11-15_AM_plan/finpredict-v4/05_simulation/emit_tactical_picks.py
# merge + save to DB
python3 tools/save_picks_to_db.py
# refresh live PnL for dashboard
python3 tools/live_pnl_tracker.py --apply --summary
```

---

## Notes & caveats

- These are **allocation/tactical** picks (beta + risk-off rotation), not high-frequency alpha. They are intended for the "Active Picks" monitoring alongside the existing pipeline.
- Backtest proof is risk-adjusted (lower drawdown), not absolute beat-the-market; total return is near B&H.
- No real capital is deployed — these feed the **monitoring** dashboard. Forward-test protocol applies before any live sizing.
- The four picks are deliberately low-frequency (monthly rebalance) to avoid turnover drag.
