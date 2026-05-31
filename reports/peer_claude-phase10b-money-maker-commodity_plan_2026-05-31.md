# Plan — /money-maker-readyv2 for COMMODITY (2026-05-31)

## Scope
Goal #1 (audit). COMMODITY class. Categories unioned: `commodity` (lowercase only — no plural variants present in DB).

## Inputs
- Live `ejaguiar1_stocks.trading_picks` snapshot at 2026-05-31T06:30Z
- Phase 3 MC watchlist (Phase 10b session brief) — COMMODITY has **no** active MC candidate (no commodity strategy was on the EQUITY/FOREX watchlist; the only commodity-flagged strategy was `cta_golden_cross_200`, retired by PR #182 as a resolver artifact)
- Phase 5 retirements relevant to this class: `cta_golden_cross_200`, `prediction_market_consensus`
- Phase 4 resolver bug (writes past-TP without intrabar verification) — directly affects COMMODITY because >72% of class rows are TIME_EXIT with pnl=0

## Method
1. Pull `n / wins / losses / closed / gross_win / gross_loss / avg_pnl` overall AND per `(source_system, strategy)` filtered to `LOWER(category)='commodity'`
2. Define **CLEAN closure** = `status IN ('WON','TP_HIT','LOST')` (exclude TIME_EXIT — all 4,727 rows have pnl=0, they're unresolved-as-flat, not true losses)
3. Recompute PF, WR, avg on clean basis only
4. 14d / 90d windows for recency
5. Symbol concentration on clean closures
6. Cross-check vs `alpha_engine/strategy_blocklist.py` and `alpha_engine/commodity_kill_switch.py`

## Acceptance for "/money-maker-readyv2 PASS"
T2: PF≥1.5, WR≥50%, MDD<20%, n≥100 on clean basis with ≥3 symbols and HHI<0.30.
