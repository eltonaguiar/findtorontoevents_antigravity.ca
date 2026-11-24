# Stocks DB Profile (ejaguiar1_stocks)

**DB**: `ejaguiar1_stocks` on `mysql.50webs.com` (MySQL 8.4.7)  
**Profiled by**: `stocks-profiler` (slice: stocks)  
**Date**: 2026-11-16

## Summary

- **Tables**: 409 total (248 MyISAM, 158 InnoDB) — 56.52 GB
- **Largest tables**:
  - `at_local_picks`: 76.18M rows, 13.8 GB data + 11 GB index (UPDATE 2026-11-16 04:55:51)
  - `bt_backtest_trades`: 27.2M rows, 28.6 GB (static, CREATE 2026-05-31)
  - `crypto_ohlcv`: 1.16M rows (UPDATE 2026-11-16 05:01:30)
- **Live trading pipeline**: `at_local_picks`, `at_raw_picks`, `at_signal_outcomes`, `trading_picks`, `lm_signals`, `at_aggregation_runs`, `daily_prices`, `stock_ohlcv`, `crypto_ohlcv`
- **Legacy/stale MyISAM tables** (frozen since ~2026-02 to 2026-04-27): `alpha_picks`, `stock_picks`, `daytrader_sim_trades`, `fx_prices`, `cp_prices`, `mf_nav_history`, `audit_log`, `miracle_*`, etc.
- **Backup/archive tables**: `at_raw_picks_kimi_archive_2026_06_05`, `trading_picks_pre_pillar_migration_2026_06_09`, `trading_picks_snapshot_20260531_2156`, `at_signal_outcomes_intrabar_bak_20260613`, `at_pick_outcomes_kimi_archive_2026_06_05`, `_backup_trading_picks_pre_nullpnl_*`

## PnL Anomalies

- `trading_picks`: 91,855 OPEN (76,541 NULL pnl, 4,156 zero pnl); TIME_EXIT 33,635; TP_HIT 7,106; LOST 5,629; SL_HIT 3,889; EXPIRED 2,432
- `at_signal_outcomes`: SL_HIT 23,959 (15,528 zero pnl); TP_HIT 16,021 (10,142 zero pnl); WON 6,537; LOST 3,908; OPEN 38
- **Critical**: ~26k closed outcomes (TP_HIT/SL_HIT) with NULL/zero PnL — unresolved PnL computation or bad pricing. Sample: `USDJPY=X` SHORT with exit_price 2440.40 (entry 160.16), rows with NULL opened_at/closed_at (id 672598, 672592, etc. — DOT/XRP/ADA/DOGE)
- `trading_picks` OPEN rows with pnl_pct=0: 4,156 (suspicious; OPEN should be NULL)

## Ghost Rows & Degenerate Timestamps

- `at_signal_outcomes`: 197 rows with `opened_at = 2000-01-01 00:00:01` (ghost/degenerate timestamps); max opened_at 2026-11-16 02:26, max closed_at 2026-11-16 03:50
- `trading_picks`: date range 2026-02-17 to 2026-11-16 05:47 (live)

## Stale Tables

- `etf_daily_ohlcv`: UPDATE 2026-11-01 06:30 (15 days stale)
- `stock_picks`, `alpha_picks`, `daytrader_sim_trades`, `fx_prices`, `cp_prices`, `mf_nav_history`, `audit_log`, `miracle_*`: frozen since ~2026-02 to 2026-04-27 (abandoned/legacy)
- `at_signal_outcomes` has rows dated `2000-01-01` (ghost rows)

## Duplicate Checks

- `at_raw_picks` has `dedup_hash` column — dedup logic exists but not profiled for collision rate
- `daily_prices` duplicate check on (ticker, trade_date) not completed (column mismatch on query)

## Schema Notes

- Key tables profiled: `at_local_picks`, `at_raw_picks`, `at_signal_outcomes`, `trading_picks`, `lm_signals`, `daily_prices`, `stock_ohlcv`, `bt_backtest_trades`
- `at_signal_outcomes` has `outcome`, `pnl_pct`, `opened_at`, `closed_at`
- `trading_picks` has `status`, `pnl_pct`, `exit_price`, `created_at`, `closed_at`, `exit_reason`, `updated_at`, `tp_fill_method`, `intrabar_status`

## Recommendations

1. Investigate ~26k NULL/zero PnL on closed outcomes in `at_signal_outcomes` (TP_HIT/SL_HIT) — likely unresolved PnL computation or bad pricing data
2. Clean ghost rows: 197 `at_signal_outcomes` rows with `opened_at = 2000-01-01`
3. Review 4,156 OPEN rows in `trading_picks` with pnl_pct=0 (should be NULL)
4. Archive or drop legacy MyISAM tables frozen since 2026-02/04 (potential orphan/abandoned tables)
5. Verify `etf_daily_ohlcv` freshness (15 days stale)
6. Profile duplicate rates on `at_raw_picks` (dedup_hash) and `daily_prices` (ticker, trade_date)
