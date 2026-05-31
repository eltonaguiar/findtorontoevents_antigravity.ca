# Plan — /money-maker-readyv2 FUTURES (2026-05-31)

## Goal
Produce a concrete per-class action plan for FUTURES toward T2 graduation (PF>1.5 / WR>50 / MDD<20 / n>=100 clean closures).

## Steps
1. Pull `trading_picks` rows where `category='futures'` (only `futures` exists in DB; no `futs`/`future`).
2. Compute terminal aggregates using statuses `('CLOSED','WON','LOST','TP_HIT','SL_HIT','TIME_EXIT','EXPIRED')` — the verdict pipeline's `status='CLOSED'`-only filter under-counts FUTURES by ~100%.
3. Bucket by strategy and identify mark-to-market gaps (TIME_EXIT rows with `pnl_pct=0` and `closed_at IS NULL`).
4. Check vs Phase 3 MC watchlist (FUTURES has no MC candidate; closest cousin is FOREX `fx_smart_carry_trade_momentum` and EQUITY `stocks_rsi2_pullback`).
5. Verify symbol concentration (e-mini index basket concentration).
6. Produce ranked actions and ship reports + docs PR.

## Sources
- `ejaguiar1_stocks.trading_picks` (live).
- `alpha_engine/outcome_resolver.py` (FUTURES policy at lines 127, 144, 251; TIME_EXIT path at 1507-1512).
- `reports/peer_blackbox_incidents-enhancements-pr_2026-05-31.md` (Phase 4 resolver findings).
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
