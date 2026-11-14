# COMMODITY — quick wins

## 1. Backfill `current_price` at emit time (M / M)
- **Problem:** 27 OPEN commodity picks, 67% frozen (`current==entry`). Emitters set `entry_price` only; no live-price enrichment runs → `current_price` never set.
- **Fix:** Wire `fetch_commodity_prices_batch()` into `collect_commodity_signals()` so every emitted commodity pick gets `current_price` + `unrealized_pnl_pct` at emit; drop the pick when fetch fails instead of leaving `current==entry`.
- **Targets:** `alpha_engine/commodity_price_failover.py:387/:413`; `alpha_engine/commodities_strategies.py:1026` (`collect_commodity_signals`, emitters set entry only e.g. `:87`); `tools/research/commodity_carry_momo.py:178` (`build_picks`).
- **Verify:** after scan, non-frozen commodity fraction >33%; frozen-without-price rows dropped.
- **Note:** peer target path `copy_trader_intel/commodity_carry_momo.py` does **not** exist — actual is `tools/research/commodity_carry_momo.py`.
