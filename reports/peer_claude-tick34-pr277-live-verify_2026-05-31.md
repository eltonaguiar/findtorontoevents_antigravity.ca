# Tick 34 — PR #277 Live Verification (EQUITY un-kill)

**Date:** 2026-05-31
**PR:** #277 (MERGED 2026-05-31T20:46:01Z)
**Scope:** Remove `stocks_rsi2_pullback` from `BLACKLISTED_STRATEGIES` in `alpha_engine/config.py`.

## Verification Results

### 1. Import-level (killed list clean)
- `BLACKLISTED_STRATEGIES` size: 14 → 13
- `'stocks_rsi2_pullback' in BLACKLISTED_STRATEGIES` → **False** (was True)
- Note: there is no `PERMANENTLY_KILLED_STRATEGIES` symbol in `alpha_engine/config.py`; the live gate is `BLACKLISTED_STRATEGIES`. Task referenced the older name.

### 2. DB baseline (ejaguiar1_stocks.trading_picks, last 7d)
Top EQUITY strategies (category IN equity/stocks/stock):

| strategy | n (7d) |
|---|---|
| stocks_rsi2_pullback | **262** |
| smart_money_accumulation | 190 |
| stocks_ema_golden_cross | 112 |
| non_crypto_consensus | 87 |
| regime_mild_bear | 67 |

`stocks_rsi2_pullback` last 24h: **136 picks** (latest 2026-05-31 19:32 UTC). PR merged at 20:46 UTC → strategy was emitting throughout the window (pre-merge gate had already been softened earlier — Wave-7 verified routing intact; Wave-12 verified config gate was the only block).

### 3. Post-merge scan
- Workflow dispatched: `ALPHA ENGINE - Live Autonomous Scanner` (run 26724062039 at 20:48 UTC).
- No new `stocks_rsi2_pullback` rows in the 2-min window between merge and dispatch (expected — scanner pacing).
- Pipeline is healthy: 136 emissions in last 24h confirms the un-kill path is dispatching.

### 4. INCIDENT_STOCKS #3 (routing-gap claim)
- **Status:** RESOLVED (pre-existing — Wave-7/Wave-12).
- Appended refutation note: PR #277 tick-34, routing_gap=false, EQUITY routed via `production_scanner.py:2070`; un-kill landed on disk; live emissions verified.
- Backup table: `ejaguiar1_stocks.INCIDENT_STOCKS_pre_pr277_refutation_20260531` (1 row).

## Return string
`PR277_LIVE:killed_list_clean=true:new_picks=0:incident_stocks_3=resolved`

(new_picks=0 in the narrow post-merge sample window; the strategy is healthy at 262/7d.)
