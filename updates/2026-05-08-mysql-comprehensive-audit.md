# Comprehensive Database Audit: `ejaguiar1_stocks` @ `mysql.50webs.com`

**Generated:** 2026-05-08 14:29:24 UTC
**Total Tables:** 322
**Approx. Total Rows:** 2,258,424
**Data Size:** 1,789MB
**Index Size:** 318MB
**Engine:** MariaDB (50webs.com shared hosting)

---

## 📊 Tables by Purpose Category

| Category | Tables | Rows | Size (MB) |
|----------|--------|------|-----------|
| Backtesting | 7 | 1,315,117 | 1,419 |
| Audit | 13 | 674,342 | 289 |
| Live Market | 70 | 60,984 | 17 |
| Misc/Unknown | 97 | 57,417 | 21 |
| Daily | 5 | 49,344 | 2 |
| Trading | 3 | 24,644 | 7 |
| Mutual Funds | 33 | 13,761 | 0 |
| Alpha Engine | 8 | 12,074 | 9 |
| Signals | 4 | 11,883 | 1 |
| Stocks | 1 | 7,239 | 2 |
| Crypto | 12 | 5,913 | 0 |
| Goldmine | 6 | 5,470 | 0 |
| Forex | 16 | 4,594 | 0 |
| Picks | 6 | 4,510 | 0 |
| Forex Pro | 12 | 4,259 | 0 |
| Algo | 2 | 3,559 | 0 |
| Strategy | 3 | 1,241 | 0 |
| Penny Stocks | 3 | 1,083 | 0 |
| Consensus | 4 | 728 | 0 |
| Memecoins | 5 | 150 | 0 |
| Challenge | 1 | 62 | 0 |
| Portfolio | 1 | 26 | 0 |
| Kimi System | 6 | 14 | 0 |
| Validation | 2 | 10 | 0 |
| Performance | 2 | 0 | 0 |

---

## 📋 Complete Table Inventory (by approx. row count)

| # | Table | Rows | Data (MB) | Idx (MB) | Updated | Purpose |
|---|-------|------|-----------|----------|---------|---------|
| 1 | `bt_backtest_trades` | 1,312,509 | 1,419 | 124 | 2026-05-08 14:13 | Backtesting: Imported SQLite trade-level data |
| 2 | `at_filter_log` | 505,080 | 66 | 64 | 2026-05-08 13:49 | Audit: Filter/rejection log |
| 3 | `at_raw_picks` | 121,857 | 215 | 96 | 2026-05-08 14:27 | Audit: Raw signals from all source systems |
| 4 | `daily_prices` | 49,340 | 2 | 2 | 2026-04-29 13:53 | Daily: Aggregated data |
| 5 | `lm_signals` | 33,557 | 13 | 1 | 2026-05-08 14:20 | Live Market: Signals |
| 6 | `at_audit_events` | 27,602 | 4 | 5 | 2026-05-08 14:27 | Audit: Event log |
| 7 | `trading_picks` | 24,644 | 7 | 0 | 2026-05-08 14:17 | Trading: Unified pick tracking |
| 8 | `now_history` | 23,859 | 11 | 3 | 2026-05-08 14:02 | Misc/Unknown |
| 9 | `lm_sports_clv` | 20,607 | 3 | 1 | 2026-04-02 03:53 | Live Market: Signals |
| 10 | `rapid_signals` | 11,709 | 1 | 2 | 2026-05-08 13:43 | Signals: Tracking |
| 11 | `at_discord_gate_log` | 10,640 | 2 | 1 | 2026-05-08 13:59 | Audit: Discord gate state |
| 12 | `stock_picks` | 7,239 | 2 | 0 | 2026-04-27 23:49 | Stocks: Pick data |
| 13 | `mf2_nav_history` | 6,860 | 0 | 0 | 2026-03-29 04:38 | Mutual Funds: Backtests |
| 14 | `simulation_grid` | 6,000 | 0 | 0 | 2026-04-26 06:54 | Misc/Unknown |
| 15 | `audit_log` | 5,937 | 0 | 0 | 2026-05-06 17:06 | Misc/Unknown |
| 16 | `at_consensus_picks` | 5,176 | 2 | 4 | 2026-05-08 13:50 | Audit: Multi-system consensus picks |
| 17 | `alpha_picks` | 5,043 | 1 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 18 | `mf_nav_history` | 5,000 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 19 | `cp_prices` | 4,857 | 0 | 0 | 2026-02-09 06:18 | Misc/Unknown |
| 20 | `at_discord_notifications` | 4,637 | 4 | 0 | 2026-05-08 14:18 | Misc/Unknown |
| 21 | `cr_price_history` | 4,529 | 0 | 0 | 2026-05-07 23:53 | Crypto: Backtests/signals |
| 22 | `fx_prices` | 3,855 | 0 | 0 | 2026-02-09 06:18 | Forex: Signals/backtests |
| 23 | `algorithm_rolling_perf` | 3,536 | 0 | 0 | 2026-04-27 23:54 | Algo: Performance tracking |
| 24 | `alpha_fundamentals` | 2,964 | 7 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 25 | `alpha_factor_scores` | 2,860 | 1 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 26 | `fxp_price_history` | 2,658 | 0 | 0 | 2026-05-07 23:52 | Forex Pro: Backtests |
| 27 | `at_local_picks` | 2,103 | 0 | 0 | 2026-05-08 12:40 | Picks: Storage |
| 28 | `lm_snapshots` | 2,096 | 0 | 0 | 2026-05-08 14:19 | Live Market: Signals |
| 29 | `gm_sec_13f_holdings` | 2,084 | 0 | 0 | 2026-03-22 06:17 | Goldmine: Unified picks |
| 30 | `at_aggregation_runs` | 1,847 | 0 | 0 | 2026-05-08 14:27 | Audit: Aggregation run metadata |
| 31 | `gm_unified_picks` | 1,846 | 0 | 0 | 2026-03-16 18:25 | Goldmine: Unified picks |
| 32 | `kelly_sizing_log` | 1,702 | 0 | 0 | 2026-04-27 23:54 | Misc/Unknown |
| 33 | `at_permutation_picks` | 1,514 | 0 | 0 | 2026-03-08 23:41 | Picks: Storage |
| 34 | `lm_position_sizing` | 1,409 | 0 | 0 | 2026-05-07 21:12 | Live Market: Signals |
| 35 | `at_discord_sent` | 1,305 | 0 | 0 | 2026-05-08 12:03 | Audit: Discord sent notifications |
| 36 | `at_incubator_backtest_results` | 1,210 | 0 | 0 | 2026-05-08 06:44 | Backtesting |
| 37 | `strategy_registry` | 1,187 | 0 | 0 | 2026-04-04 19:51 | Strategy: Genome registry |
| 38 | `fxp_pair_picks` | 1,184 | 0 | 0 | 2026-05-07 23:51 | Forex Pro: Backtests |
| 39 | `at_large_backtest_results` | 1,061 | 0 | 0 | 2026-05-08 06:44 | Backtesting |
| 40 | `penny_picks` | 1,029 | 0 | 0 | 2026-04-27 12:44 | Penny Stocks: Pick data |
| 41 | `cr_pair_picks` | 952 | 0 | 0 | 2026-05-07 23:53 | Crypto: Backtests/signals |
| 42 | `daytrader_sim_trades` | 838 | 0 | 0 | 2026-04-27 23:57 | Misc/Unknown |
| 43 | `stock_dividends` | 831 | 0 | 0 | 2026-04-27 23:51 | Misc/Unknown |
| 44 | `alpha_refresh_log` | 731 | 0 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 45 | `gm_sec_insider_trades` | 714 | 0 | 0 | 2026-05-08 13:42 | Goldmine: Unified picks |
| 46 | `audit_trails` | 684 | 0 | 0 | 2026-02-17 21:58 | Misc/Unknown |
| 47 | `ps_history` | 684 | 0 | 0 | 2026-02-16 19:09 | Misc/Unknown |
| 48 | `cw_scan_log` | 666 | 4 | 0 | 2026-05-08 12:35 | Misc/Unknown |
| 49 | `miracle_audit2` | 659 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 50 | `miracle_picks3` | 644 | 0 | 0 | 2026-05-07 23:54 | Picks: Storage |
| 51 | `challenge_200_trades` | 620 | 0 | 0 | 2026-04-27 23:57 | Misc/Unknown |
| 52 | `mf2_fund_picks` | 600 | 0 | 0 | 2026-03-29 01:00 | Mutual Funds: Backtests |
| 53 | `fx_signals` | 585 | 0 | 0 | 2026-02-11 00:47 | Forex: Signals/backtests |
| 54 | `market_regimes` | 560 | 0 | 0 | 2026-05-06 17:06 | Misc/Unknown |
| 55 | `lm_smart_consensus` | 552 | 0 | 0 | 2026-05-08 11:27 | Live Market: Signals |
| 56 | `lm_sports_odds` | 502 | 1 | 0 | 2026-04-02 03:53 | Live Market: Signals |
| 57 | `goldmine_cursor_predictions` | 478 | 0 | 0 | 2026-02-11 00:03 | Misc/Unknown |
| 58 | `mf2_backtest_trades` | 450 | 0 | 0 | 2026-02-12 23:45 | Mutual Funds: Backtests |
| 59 | `gm_failure_alerts` | 414 | 0 | 0 | 2026-04-30 00:23 | Goldmine: Unified picks |
| 60 | `miracle_audit3` | 412 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 61 | `at_strategy_symbol_performance` | 410 | 0 | 0 | 2026-03-06 21:53 | Audit: Strategy performance stats |
| 62 | `miracle_learning3` | 410 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 63 | `ml_feature_store` | 396 | 0 | 0 | 2026-02-16 19:09 | Misc/Unknown |
| 64 | `cr_audit_log` | 393 | 0 | 0 | 2026-05-07 23:53 | Crypto: Backtests/signals |
| 65 | `stock_earnings` | 381 | 0 | 0 | 2026-04-27 23:51 | Misc/Unknown |
| 66 | `fxp_audit_log` | 380 | 0 | 0 | 2026-05-07 23:52 | Forex Pro: Backtests |
| 67 | `lm_sports_value_bets` | 375 | 0 | 0 | 2026-04-02 03:53 | Live Market: Signals |
| 68 | `ua_predictions` | 355 | 0 | 0 | 2026-02-16 19:10 | Misc/Unknown |
| 69 | `consensus_lessons` | 348 | 0 | 0 | 2026-04-27 23:57 | Consensus: Aggregation |
| 70 | `cw_winners` | 342 | 0 | 0 | 2026-05-08 00:48 | Misc/Unknown |
| 71 | `mf2_audit_log` | 328 | 0 | 0 | 2026-05-08 12:42 | Mutual Funds: Backtests |
| 72 | `consensus_tracked` | 318 | 0 | 0 | 2026-04-29 19:47 | Consensus: Aggregation |
| 73 | `at_raw_picks_anomaly_log` | 304 | 0 | 0 | 2026-04-02 01:13 | Audit: Raw signals from all source systems |
| 74 | `bt_backtest_runs` | 285 | 0 | 0 | 2026-03-26 15:13 | Backtesting: Run-level aggregates |
| 75 | `gm_system_health` | 272 | 0 | 0 | 2026-04-30 00:23 | Goldmine: Unified picks |
| 76 | `mf_audit_log` | 260 | 0 | 0 | 2026-03-28 21:56 | Mutual Funds: Backtests |
| 77 | `miracle_picks2` | 249 | 0 | 0 | 2026-05-07 23:17 | Picks: Storage |
| 78 | `alpha_earnings` | 242 | 0 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 79 | `lm_sports_daily_picks` | 222 | 0 | 0 | 2026-04-02 03:53 | Live Market: Signals |
| 80 | `lm_market_regime` | 213 | 0 | 0 | 2026-05-08 12:00 | Live Market: Signals |
| 81 | `lm_trades` | 200 | 0 | 0 | 2026-05-08 14:19 | Live Market: Signals |
| 82 | `lm_hour_learning` | 195 | 0 | 0 | 2026-05-03 03:04 | Live Market: Signals |
| 83 | `alpha_macro` | 181 | 0 | 0 | 2026-04-27 21:54 | Alpha Engine: Picks/performance |
| 84 | `daytrader_sim_days` | 176 | 0 | 0 | 2026-04-27 23:57 | Misc/Unknown |
| 85 | `at_incubator_strategies` | 174 | 1 | 0 | 2026-05-08 06:44 | Misc/Unknown |
| 86 | `cp_signals` | 174 | 0 | 0 | 2026-02-09 06:18 | Signals: Tracking |
| 87 | `lm_intelligence` | 169 | 0 | 0 | 2026-05-08 12:00 | Live Market: Signals |
| 88 | `eh_grade_history` | 168 | 0 | 0 | 2026-02-16 19:10 | Misc/Unknown |
| 89 | `stocks` | 153 | 0 | 0 | 2026-04-29 13:50 | Misc/Unknown |
| 90 | `algorithms` | 142 | 0 | 0 | 2026-04-27 23:49 | Misc/Unknown |
| 91 | `gm_news_sentiment` | 140 | 0 | 0 | 2026-02-16 18:38 | Goldmine: Unified picks |
| 92 | `miracle_results2` | 140 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 93 | `lm_breaker_log` | 133 | 0 | 0 | 2026-04-29 14:27 | Live Market: Signals |
| 94 | `lm_sports_credit_usage` | 132 | 0 | 0 | 2026-04-02 03:53 | Live Market: Signals |
| 95 | `challenge_200_days` | 124 | 0 | 0 | 2026-04-27 23:57 | Misc/Unknown |
| 96 | `at_signal_outcomes` | 121 | 0 | 0 | 2026-03-10 09:13 | Audit: Signal outcome tracking |
| 97 | `stock_fundamentals` | 119 | 0 | 0 | 2026-04-27 23:51 | Misc/Unknown |
| 98 | `whatif_scenarios` | 114 | 0 | 0 | 2026-05-06 12:03 | Misc/Unknown |
| 99 | `fx_audit_log` | 89 | 0 | 0 | 2026-02-17 22:34 | Forex: Signals/backtests |
| 100 | `lm_analyst_ratings` | 84 | 0 | 0 | 2026-05-08 11:26 | Live Market: Signals |
| 101 | `ss_baselines` | 82 | 0 | 0 | 2026-03-16 14:02 | Misc/Unknown |
| 102 | `lm_sports_ml_predictions` | 79 | 0 | 0 | 2026-02-12 21:05 | Live Market: Signals |
| 103 | `miracle_results3` | 78 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 104 | `mf2_tracked_picks` | 75 | 0 | 0 | 2026-02-15 01:15 | Mutual Funds: Backtests |
| 105 | `lm_sports_bets` | 74 | 0 | 0 | 2026-03-28 15:05 | Live Market: Signals |
| 106 | `miracle_watchlist2` | 68 | 0 | 0 | 2026-02-09 18:51 | Misc/Unknown |
| 107 | `lm_price_cache` | 66 | 0 | 0 | 2026-05-08 14:19 | Live Market: Signals |
| 108 | `consensus_performance_daily` | 62 | 0 | 0 | 2026-04-27 23:57 | Consensus: Aggregation |
| 109 | `pf_challenge_positions` | 62 | 0 | 0 | 2026-03-10 19:02 | Challenge: PF positions |
| 110 | `miracle_watchlist3` | 56 | 0 | 0 | 2026-02-09 18:52 | Misc/Unknown |
| 111 | `penny_picks_daily` | 54 | 0 | 0 | 2026-04-27 12:40 | Penny Stocks: Pick data |
| 112 | `strategy_health` | 54 | 0 | 0 | 2026-05-08 12:24 | Strategy: Health monitoring |
| 113 | `alpha_universe` | 52 | 0 | 0 | 2026-02-09 18:22 | Alpha Engine: Picks/performance |
| 114 | `pf_pair_patterns` | 51 | 0 | 0 | 2026-04-30 03:01 | Misc/Unknown |
| 115 | `strategy_test_runs` | 51 | 0 | 0 | 2026-04-03 00:25 | Misc/Unknown |
| 116 | `backtest_trades` | 50 | 0 | 0 | 2026-02-09 05:04 | Backtesting |
| 117 | `meme_ml_signals` | 50 | 0 | 0 | 2026-02-12 22:27 | Memecoins: Signal data |
| 118 | `meme_signal_results` | 50 | 0 | 0 | 2026-02-12 22:31 | Memecoins: Signal data |
| 119 | `meme_signals` | 50 | 0 | 0 | 2026-02-12 22:29 | Memecoins: Signal data |
| 120 | `pf_fingerprints` | 47 | 0 | 0 | 2026-04-30 03:01 | Misc/Unknown |
| 121 | `lm_challenger_showdown` | 46 | 0 | 0 | 2026-05-08 11:27 | Live Market: Signals |
| 122 | `portfolios` | 39 | 0 | 0 | 2026-02-09 18:22 | Misc/Unknown |
| 123 | `ps_scores` | 36 | 0 | 0 | 2026-02-16 19:09 | Misc/Unknown |
| 124 | `mf_selections` | 34 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 125 | `strategy_symbol_coverage` | 34 | 0 | 0 | 2026-04-03 00:25 | Misc/Unknown |
| 126 | `lm_nba_team_stats` | 30 | 0 | 0 | 2026-02-12 05:25 | Live Market: Signals |
| 127 | `at_permutation_snapshots` | 28 | 0 | 0 | 2026-03-08 23:41 | Misc/Unknown |
| 128 | `lm_algo_health` | 28 | 0 | 0 | 2026-05-08 12:00 | Live Market: Signals |
| 129 | `portfolio_snapshots` | 26 | 0 | 0 | 2026-03-10 19:00 | Portfolio: Snapshots |
| 130 | `super_strategy_candidates` | 26 | 0 | 0 | 2026-04-03 00:25 | Misc/Unknown |
| 131 | `algorithm_performance` | 23 | 0 | 0 | 2026-05-03 16:20 | Algo: Performance tracking |
| 132 | `crypto_exchange_netflow` | 20 | 0 | 0 | 2026-02-16 06:56 | Misc/Unknown |
| 133 | `mf_funds` | 20 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 134 | `cp_audit_log` | 19 | 0 | 0 | 2026-02-16 23:20 | Misc/Unknown |
| 135 | `now_strategy_stats` | 17 | 0 | 0 | 2026-05-08 13:58 | Misc/Unknown |
| 136 | `fx_pair_picks` | 16 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 137 | `cp_pairs` | 15 | 0 | 0 | 2026-02-09 06:18 | Misc/Unknown |
| 138 | `fx_pairs` | 15 | 0 | 0 | 2026-02-09 06:18 | Forex: Signals/backtests |
| 139 | `lm_discovered_movers` | 15 | 0 | 0 | 2026-02-10 04:02 | Live Market: Signals |
| 140 | `lm_ml_status` | 15 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 141 | `lm_sports_bankroll` | 15 | 0 | 0 | 2026-03-28 15:05 | Live Market: Signals |
| 142 | `mf2_funds` | 15 | 0 | 0 | 2026-02-09 17:57 | Mutual Funds: Backtests |
| 143 | `mf_fund_picks` | 15 | 0 | 0 | 2026-02-09 08:41 | Mutual Funds: Backtests |
| 144 | `KIMI_GOLDMINE_SOURCES` | 14 | 0 | 0 | 2026-03-17 08:15 | Kimi System: Data |
| 145 | `crypto_assets` | 14 | 0 | 0 | 2026-02-14 20:48 | Misc/Unknown |
| 146 | `lm_nba_games_today` | 14 | 0 | 0 | 2026-02-12 05:25 | Live Market: Signals |
| 147 | `ml_learning_curve` | 14 | 0 | 0 | 2026-02-16 19:09 | Misc/Unknown |
| 148 | `eh_alerts` | 13 | 0 | 0 | 2026-02-16 13:45 | Misc/Unknown |
| 149 | `eh_engine_grades` | 12 | 0 | 0 | 2026-02-16 19:10 | Misc/Unknown |
| 150 | `lm_bridge_options` | 12 | 0 | 0 | 2026-02-16 12:02 | Live Market: Signals |
| 151 | `lm_conviction_history` | 12 | 0 | 0 | 2026-02-11 03:55 | Live Market: Signals |
| 152 | `lm_conviction_performance` | 12 | 0 | 0 | 2026-02-11 03:55 | Live Market: Signals |
| 153 | `lm_multi_dimensional` | 12 | 0 | 0 | 2026-02-11 03:55 | Live Market: Signals |
| 154 | `lm_price_targets` | 12 | 0 | 0 | 2026-02-11 02:56 | Live Market: Signals |
| 155 | `lm_wsb_sentiment` | 12 | 0 | 0 | 2026-02-11 02:50 | Live Market: Signals |
| 156 | `mf2_portfolios` | 12 | 0 | 0 | 2026-02-09 17:57 | Mutual Funds: Backtests |
| 157 | `cp_strategies` | 10 | 0 | 0 | 2026-02-09 06:18 | Misc/Unknown |
| 158 | `cr_pairs` | 10 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 159 | `cr_portfolios` | 10 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 160 | `fx_portfolios` | 10 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 161 | `fxp_portfolios` | 10 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 162 | `lm_bridge_onchain` | 10 | 0 | 0 | 2026-02-15 16:20 | Live Market: Signals |
| 163 | `lm_insider_sentiment` | 10 | 0 | 0 | 2026-05-08 11:26 | Live Market: Signals |
| 164 | `mf2_algo_performance` | 10 | 0 | 0 | 2026-05-08 12:42 | Mutual Funds: Backtests |
| 165 | `mf2_algorithms` | 10 | 0 | 0 | 2026-02-09 17:57 | Mutual Funds: Backtests |
| 166 | `mf2_backtest_results` | 10 | 0 | 0 | 2026-02-12 23:45 | Mutual Funds: Backtests |
| 167 | `mf_algo_performance` | 10 | 0 | 0 | 2026-02-09 17:17 | Mutual Funds: Backtests |
| 168 | `mf_algorithms` | 10 | 0 | 0 | 2026-02-09 08:41 | Mutual Funds: Backtests |
| 169 | `mf_strategies` | 10 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 170 | `walk_forward_summary` | 10 | 0 | 0 | 2026-02-09 21:11 | Validation: Walk-forward |
| 171 | `goldmine_cursor_data_health` | 9 | 0 | 0 | 2026-02-11 00:27 | Misc/Unknown |
| 172 | `lm_conviction_stats` | 9 | 0 | 0 | 2026-02-11 03:55 | Live Market: Signals |
| 173 | `lm_kelly_fractions` | 9 | 0 | 0 | 2026-05-08 14:20 | Live Market: Signals |
| 174 | `mf2_tracking_lessons` | 9 | 0 | 0 | 2026-02-15 01:15 | Mutual Funds: Backtests |
| 175 | `cr_algo_performance` | 8 | 0 | 0 | 2026-05-08 06:23 | Crypto: Backtests/signals |
| 176 | `cr_algorithms` | 8 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 177 | `fx_algo_performance` | 8 | 0 | 0 | 2026-02-09 17:29 | Forex: Signals/backtests |
| 178 | `fx_algorithms` | 8 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 179 | `fx_strategies` | 8 | 0 | 0 | 2026-02-09 06:18 | Forex: Signals/backtests |
| 180 | `fxp_algo_performance` | 8 | 0 | 0 | 2026-05-08 06:23 | Forex Pro: Backtests |
| 181 | `fxp_algorithms` | 8 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 182 | `fxp_pairs` | 8 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 183 | `lm_alert_configs` | 8 | 0 | 0 | 2026-02-11 03:54 | Live Market: Signals |
| 184 | `mf_portfolios` | 8 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 185 | `mf_whatif_scenarios` | 8 | 0 | 0 | 2026-02-09 08:41 | Mutual Funds: Backtests |
| 186 | `miracle_portfolios2` | 8 | 0 | 0 | 2026-02-09 18:51 | Misc/Unknown |
| 187 | `miracle_strategies2` | 8 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 188 | `miracle_strategies3` | 8 | 0 | 0 | 2026-05-07 23:54 | Misc/Unknown |
| 189 | `goldmine_cursor_algo_scorecard` | 7 | 0 | 0 | 2026-02-11 00:27 | Misc/Unknown |
| 190 | `lm_quant_bridge` | 6 | 0 | 0 | 2026-02-16 12:02 | Live Market: Signals |
| 191 | `mc_scan_log` | 6 | 0 | 0 | 2026-02-10 21:38 | Misc/Unknown |
| 192 | `miracle_portfolios3` | 6 | 0 | 0 | 2026-02-09 18:52 | Misc/Unknown |
| 193 | `at_futures_symbol_edge` | 4 | 0 | 0 | 2026-04-09 20:56 | Misc/Unknown |
| 194 | `lm_injury_intel_cache` | 4 | 0 | 0 | 2026-04-04 18:03 | Live Market: Signals |
| 195 | `lm_meta_labeler` | 4 | 0 | 0 | 2026-04-26 15:28 | Live Market: Signals |
| 196 | `lm_opportunities` | 4 | 0 | 0 | 2026-02-10 12:15 | Live Market: Signals |
| 197 | `stock_analyst_recs` | 4 | 0 | 0 | 2026-02-09 22:10 | Misc/Unknown |
| 198 | `cr_whatif_scenarios` | 3 | 0 | 0 | 2026-03-28 18:33 | Crypto: Backtests/signals |
| 199 | `fxp_whatif_scenarios` | 3 | 0 | 0 | 2026-02-16 11:25 | Forex Pro: Backtests |
| 200 | `lm_conviction_alerts` | 3 | 0 | 0 | 2026-04-07 20:55 | Live Market: Signals |
| 201 | `lm_fear_greed` | 3 | 0 | 0 | 2026-02-11 02:51 | Live Market: Signals |
| 202 | `lm_schedule_intel_cache` | 3 | 0 | 0 | 2026-04-28 18:39 | Live Market: Signals |
| 203 | `lm_scraped_data` | 3 | 0 | 0 | 2026-02-11 03:40 | Live Market: Signals |
| 204 | `mf2_tracking_daily` | 3 | 0 | 0 | 2026-02-15 01:15 | Mutual Funds: Backtests |
| 205 | `ml_platform_daily` | 3 | 0 | 0 | 2026-02-16 19:09 | Daily: Aggregated data |
| 206 | `ml_regime_snapshots` | 3 | 0 | 0 | 2026-02-16 19:09 | Misc/Unknown |
| 207 | `report_cache` | 3 | 1 | 0 | 2026-05-08 12:31 | Misc/Unknown |
| 208 | `simulation_meta` | 3 | 0 | 0 | 2026-04-26 06:54 | Misc/Unknown |
| 209 | `backtest_results` | 2 | 0 | 0 | 2026-02-09 05:04 | Backtesting |
| 210 | `lm_algo_performance` | 2 | 0 | 0 | 2026-02-10 21:39 | Live Market: Signals |
| 211 | `mf2_whatif_scenarios` | 2 | 0 | 0 | 2026-03-29 03:28 | Mutual Funds: Backtests |
| 212 | `mf_report_cache` | 2 | 0 | 0 | 2026-03-28 21:56 | Mutual Funds: Backtests |
| 213 | `alpha_status` | 1 | 0 | 0 | 2026-04-27 21:55 | Alpha Engine: Picks/performance |
| 214 | `lm_bridge_cusum` | 1 | 0 | 0 | 2026-02-15 15:19 | Live Market: Signals |
| 215 | `lm_mlb_stats_cache` | 1 | 0 | 0 | 2026-04-04 18:03 | Live Market: Signals |
| 216 | `lm_nba_stats_cache` | 1 | 0 | 0 | 2026-04-04 18:03 | Live Market: Signals |
| 217 | `lm_nfl_stats_cache` | 1 | 0 | 0 | 2026-04-04 18:03 | Live Market: Signals |
| 218 | `lm_nhl_stats_cache` | 1 | 0 | 0 | 2026-04-04 18:03 | Live Market: Signals |
| 219 | `lm_webhook_config` | 1 | 0 | 0 | 2026-02-11 03:54 | Live Market: Signals |
| 220 | `mc_daily_snapshots` | 1 | 0 | 0 | 2026-02-10 21:38 | Daily: Aggregated data |
| 221 | `KIMI_GOLDMINE_ALERTS` | 0 | 0 | 0 | 2026-02-11 00:39 | Kimi System: Data |
| 222 | `KIMI_GOLDMINE_DAILY_SNAPSHOT` | 0 | 0 | 0 | 2026-02-11 00:39 | Kimi System: Data |
| 223 | `KIMI_GOLDMINE_PERFORMANCE` | 0 | 0 | 0 | 2026-02-11 00:39 | Kimi System: Data |
| 224 | `KIMI_GOLDMINE_PICKS` | 0 | 0 | 0 | 2026-02-11 00:39 | Kimi System: Data |
| 225 | `KIMI_GOLDMINE_WINNERS` | 0 | 0 | 0 | 2026-02-11 00:39 | Kimi System: Data |
| 226 | `at_discord_gate_state` | 0 | 0 | 0 | 2026-03-06 20:54 | Audit: Discord gate state |
| 227 | `at_sqlite_imports` | 0 | 0 | 0 | 2026-03-26 15:13 | Audit: Import tracking |
| 228 | `at_strategy_stats` | 0 | 0 | 0 | 2026-03-26 15:13 | Audit: Strategy performance stats |
| 229 | `circuit_breaker_log` | 0 | 0 | 0 | 2026-02-09 21:05 | Misc/Unknown |
| 230 | `consensus_history` | 0 | 0 | 0 | 2026-02-09 20:39 | Consensus: Aggregation |
| 231 | `consolidated_cache` | 0 | 0 | 0 | 2026-02-09 20:39 | Misc/Unknown |
| 232 | `cp_backtest_results` | 0 | 0 | 0 | 2026-02-09 06:18 | Backtesting |
| 233 | `cp_report_cache` | 0 | 0 | 0 | 2026-02-09 06:18 | Misc/Unknown |
| 234 | `cr_backtest_results` | 0 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 235 | `cr_backtest_trades` | 0 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 236 | `cr_category_perf` | 0 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 237 | `cr_comparisons` | 0 | 0 | 0 | 2026-02-09 09:03 | Crypto: Backtests/signals |
| 238 | `crypto_indicators` | 0 | 0 | 0 | 2026-02-14 20:48 | Misc/Unknown |
| 239 | `crypto_ohlcv` | 0 | 0 | 0 | 2026-02-14 20:41 | Misc/Unknown |
| 240 | `crypto_patterns` | 0 | 0 | 0 | 2026-02-14 20:48 | Misc/Unknown |
| 241 | `crypto_signals` | 0 | 0 | 0 | 2026-02-14 20:41 | Signals: Tracking |
| 242 | `crypto_whale_movements` | 0 | 0 | 0 | 2026-02-12 22:10 | Misc/Unknown |
| 243 | `crypto_whale_wallets` | 0 | 0 | 0 | 2026-02-12 22:10 | Misc/Unknown |
| 244 | `fx_backtest_results` | 0 | 0 | 0 | 2026-02-09 06:18 | Forex: Signals/backtests |
| 245 | `fx_backtest_trades` | 0 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 246 | `fx_category_perf` | 0 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 247 | `fx_comparisons` | 0 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 248 | `fx_price_history` | 0 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 249 | `fx_report_cache` | 0 | 0 | 0 | 2026-02-09 06:18 | Forex: Signals/backtests |
| 250 | `fx_whatif_scenarios` | 0 | 0 | 0 | 2026-02-09 09:03 | Forex: Signals/backtests |
| 251 | `fxp_backtest_results` | 0 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 252 | `fxp_backtest_trades` | 0 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 253 | `fxp_category_perf` | 0 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 254 | `fxp_comparisons` | 0 | 0 | 0 | 2026-02-09 17:57 | Forex Pro: Backtests |
| 255 | `goldmine_cursor_benchmarks` | 0 | 0 | 0 | 2026-02-10 23:59 | Misc/Unknown |
| 256 | `goldmine_cursor_circuit_breaker` | 0 | 0 | 0 | 2026-02-10 23:59 | Misc/Unknown |
| 257 | `goldmine_cursor_correlation_matrix` | 0 | 0 | 0 | 2026-02-10 23:59 | Misc/Unknown |
| 258 | `goldmine_cursor_regime_log` | 0 | 0 | 0 | 2026-02-10 23:59 | Misc/Unknown |
| 259 | `lm_bridge_congress` | 0 | 0 | 0 | 2026-02-15 14:19 | Live Market: Signals |
| 260 | `lm_bridge_entropy` | 0 | 0 | 0 | 2026-02-15 14:19 | Live Market: Signals |
| 261 | `lm_bridge_portfolio` | 0 | 0 | 0 | 2026-02-15 14:19 | Live Market: Signals |
| 262 | `lm_bridge_sentiment` | 0 | 0 | 0 | 2026-02-15 14:19 | Live Market: Signals |
| 263 | `lm_cross_correlation` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 264 | `lm_daily_price_history` | 0 | 0 | 0 | 2026-02-11 03:54 | Live Market: Signals |
| 265 | `lm_ensemble_weights` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 266 | `lm_feature_importance` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 267 | `lm_guru_picks` | 0 | 0 | 0 | 2026-02-11 01:48 | Live Market: Signals |
| 268 | `lm_guru_tracker` | 0 | 0 | 0 | 2026-02-11 01:48 | Live Market: Signals |
| 269 | `lm_meta_labels` | 0 | 0 | 0 | 2026-02-11 05:16 | Live Market: Signals |
| 270 | `lm_model_versions` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 271 | `lm_picks_bridge` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 272 | `lm_prediction_calibration` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 273 | `lm_signal_performance` | 0 | 0 | 0 | 2026-02-11 01:48 | Live Market: Signals |
| 274 | `lm_sports_ml_metrics` | 0 | 0 | 0 | 2026-02-12 21:05 | Live Market: Signals |
| 275 | `lm_supplemental_dimensions` | 0 | 0 | 0 | 2026-02-11 03:40 | Live Market: Signals |
| 276 | `lm_virtual_comparison` | 0 | 0 | 0 | 2026-02-10 21:38 | Live Market: Signals |
| 277 | `lm_walk_forward` | 0 | 0 | 0 | 2026-02-12 21:15 | Live Market: Signals |
| 278 | `mc_winners` | 0 | 0 | 0 | 2026-02-10 21:38 | Misc/Unknown |
| 279 | `meme_ml_models` | 0 | 0 | 0 | 2026-02-12 22:27 | Memecoins: Signal data |
| 280 | `meme_ml_predictions` | 0 | 0 | 0 | 2026-02-12 22:27 | Memecoins: Signal data |
| 281 | `mf2_category_perf` | 0 | 0 | 0 | 2026-02-09 17:57 | Mutual Funds: Backtests |
| 282 | `mf2_comparisons` | 0 | 0 | 0 | 2026-02-09 17:57 | Mutual Funds: Backtests |
| 283 | `mf_backtest_results` | 0 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 284 | `mf_backtest_trades` | 0 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 285 | `mf_benchmarks` | 0 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 286 | `mf_category_perf` | 0 | 0 | 0 | 2026-02-09 08:41 | Mutual Funds: Backtests |
| 287 | `mf_comparisons` | 0 | 0 | 0 | 2026-02-09 08:41 | Mutual Funds: Backtests |
| 288 | `mf_simulation_grid` | 0 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 289 | `mf_simulation_meta` | 0 | 0 | 0 | 2026-02-09 05:39 | Mutual Funds: Backtests |
| 290 | `ml_ab_tests` | 0 | 0 | 0 | 2026-02-14 20:34 | Misc/Unknown |
| 291 | `ml_calibration_log` | 0 | 0 | 0 | 2026-02-14 20:34 | Misc/Unknown |
| 292 | `ml_ensemble_weights` | 0 | 0 | 0 | 2026-02-14 20:34 | Misc/Unknown |
| 293 | `ml_model_performance` | 0 | 0 | 0 | 2026-02-14 20:48 | Performance: Metrics |
| 294 | `ml_model_registry` | 0 | 0 | 0 | 2026-02-14 20:34 | Misc/Unknown |
| 295 | `ml_models` | 0 | 0 | 0 | 2026-02-14 20:48 | Misc/Unknown |
| 296 | `paper_portfolio_daily` | 0 | 0 | 0 | 2026-02-09 21:05 | Daily: Aggregated data |
| 297 | `paper_trades` | 0 | 0 | 0 | 2026-02-09 21:05 | Misc/Unknown |
| 298 | `penny_stocks` | 0 | 0 | 0 | 2026-02-14 20:41 | Penny Stocks: Pick data |
| 299 | `pf_alerts` | 0 | 0 | 0 | 2026-02-15 22:44 | Misc/Unknown |
| 300 | `portfolio_comparisons` | 0 | 0 | 0 | 2026-02-09 05:54 | Misc/Unknown |
| 301 | `portfolio_daily_equity` | 0 | 0 | 0 | 2026-02-09 19:18 | Daily: Aggregated data |
| 302 | `portfolio_positions` | 0 | 0 | 0 | 2026-02-09 19:18 | Trading: Positions |
| 303 | `portfolio_resets` | 0 | 0 | 0 | 2026-03-10 18:59 | Misc/Unknown |
| 304 | `portfolio_strategy_stats` | 0 | 0 | 0 | 2026-03-10 18:59 | Misc/Unknown |
| 305 | `saved_portfolios` | 0 | 0 | 0 | 2026-02-09 19:18 | Misc/Unknown |
| 306 | `social_influencers` | 0 | 0 | 0 | 2026-02-13 06:53 | Misc/Unknown |
| 307 | `social_sentiment` | 0 | 0 | 0 | 2026-02-13 06:53 | Misc/Unknown |
| 308 | `sp_batches` | 0 | 0 | 0 | 2026-04-15 06:08 | Misc/Unknown |
| 309 | `sp_daily_performance` | 0 | 0 | 0 | 2026-04-15 06:08 | Performance: Metrics |
| 310 | `sp_picks` | 0 | 0 | 0 | 2026-04-15 06:08 | Picks: Storage |
| 311 | `ss_spikes` | 0 | 0 | 0 | 2026-02-15 22:44 | Misc/Unknown |
| 312 | `stock_assets` | 0 | 0 | 0 | 2026-02-14 20:41 | Misc/Unknown |
| 313 | `stock_ohlcv` | 0 | 0 | 0 | 2026-02-14 20:41 | Misc/Unknown |
| 314 | `stock_signals` | 0 | 0 | 0 | 2026-02-14 20:41 | Signals: Tracking |
| 315 | `strategy_health_audit` | 0 | 0 | 0 | 2026-03-04 22:18 | Strategy: Health monitoring |
| 316 | `strategy_status_history` | 0 | 0 | 0 | 2026-04-03 00:23 | Misc/Unknown |
| 317 | `strategy_whatif_results` | 0 | 0 | 0 | 2026-04-03 00:23 | Misc/Unknown |
| 318 | `test_portfolio_positions` | 0 | 0 | 0 | 2026-04-03 00:23 | Trading: Positions |
| 319 | `tracked_portfolio_picks` | 0 | 0 | 0 | 2026-02-09 19:08 | Picks: Storage |
| 320 | `tracked_portfolios` | 0 | 0 | 0 | 2026-02-09 19:08 | Misc/Unknown |
| 321 | `ua_engine_stats` | 0 | 0 | 0 | 2026-02-14 20:34 | Misc/Unknown |
| 322 | `walk_forward_results` | 0 | 0 | 0 | 2026-02-09 21:05 | Validation: Walk-forward |

---

## 🔬 Deep Dive: Tables With Data


### 1. `bt_backtest_trades` — ~1,312,509 rows (1,419MB + 124MB idx)
**Purpose:** Backtesting: Imported SQLite trade-level data

**Columns (19):** `id` (int), `backtest_run_id` (char(36)), `source_db` (varchar(200)), `source_table` (varchar(100)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `direction` (enum('LONG','SHORT')), `strategy` (varchar(200)), `entry_price` (decimal(18,8)), `exit_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)) … +7 more

**Primary Key:** `id`
**Indexed:** `backtest_run_id`, `symbol`, `asset_class`, `strategy`, `status`

### 2. `at_filter_log` — ~505,080 rows (66MB + 64MB idx)
**Purpose:** Audit: Filter/rejection log

**Columns (10):** `id` (int), `aggregation_run_id` (char(36)), `raw_pick_id` (char(36)), `symbol` (varchar(50)), `direction` (varchar(10)), `source_system` (varchar(100)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `filter_reason` (varchar(100)), `details` (text), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `aggregation_run_id`, `symbol`, `filter_reason`

### 3. `at_raw_picks` — ~121,857 rows (215MB + 96MB idx)
**Purpose:** Audit: Raw signals from all source systems

**Columns (26):** `id` (char(36)), `aggregation_run_id` (char(36)), `source_system` (varchar(100)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `direction` (enum('LONG','SHORT')), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `risk_reward` (decimal(10,4)), `confidence` (decimal(5,4)), `strategy` (varchar(200)) … +14 more

**Primary Key:** `id`
**Indexed:** `aggregation_run_id`, `source_system`, `symbol`, `asset_class`, `signal_timestamp`, `dedup_hash`, `status`

**`source_system` distribution:**
- `incubator_gainer`: 21,336
- `AlphaEngine`: 13,498
- `quan_engine`: 13,255
- `alpha_engine`: 12,641
- `Predictions`: 12,539
- `ml_crypto_pred`: 11,156
- `smart_money`: 9,129
- `battleground`: 7,191
- `audit_trail_local`: 7,065
- `KIMI_RiseOfTheClaw`: 2,909
- `CoinglassDNA`: 2,648
- `CryptoMLEdge`: 2,500

**`asset_class` distribution:**
- `CRYPTO`: 101,706
- `EQUITY`: 13,544
- `FOREX`: 7,469
- `UNKNOWN`: 4,325
- `MEMECOIN`: 3,155
- `FUTURES`: 2,508
- ``: 2,490
- `PENNY_STOCK`: 707
- `ETF`: 152

**`direction` distribution:**
- `LONG`: 98,575
- `SHORT`: 37,481

**`strategy` distribution:**
- `incubator_gainer`: 21,356
- `enhanced_ml_A_xgboost`: 9,894
- `smart_money_consensus`: 9,131
- `quan_engine`: 8,398
- ``: 7,658
- `prediction_market_consensus`: 2,573
- `coinglass_leverage_squeeze`: 2,495
- `connors_rsi2`: 2,439
- `stocks_rsi2_pullback`: 2,381
- `ig_contrarian_sentiment`: 2,212
- `SCALP`: 2,167
- `quan_engine_scalp`: 2,059

**Sample Rows:**
```json
{
  "id": "00005e31-373d-4b14-9161-98eaf62cd449",
  "aggregation_run_id": "e5332222-bb0a-444b-9b6b-37348091ea54",
  "source_system": "alpha_engine",
  "symbol": "FETUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 0.2506,
  "take_profit": 0.258118,
  "stop_loss": 0.245588,
  "risk_reward": 1.5,
  "confidence": 0.5,
  "strategy": "ml_enhanced_FETUSDT",
  "raw_payload": "{\"id\": \"ml_enhanced_FETUSDT::FETUSDT::2026-03-28\", \"status\": \"ACTIVE\", \"symbol\": \"FETUSDT\", \"category\": \"crypto\", \"strategy\": \"ml_enhanced_FETUSDT\", \"...",
  "signal_timestamp": "2026-03-28 14:15:44",
  "recorded_at": "2026-03-28 14:54:20",
  "dedup_hash": "221cb7c67218e9185a4300b91433f3803790f2dd0b7ccfc43ac0aae6eb556273",
  "was_stale": 0,
  "was_banned": 0,
  "was_demoted": 0,
  "was_wr_suppressed": 0,
  "created_by": "aggregator",
  "status": "EXPIRED",
  "exit_price": null,
  "exit_reason": null,
  "pnl_pct": null,
  "closed_at": null
}
{
  "id": "00011612-93ad-42ce-8b89-776ce1f775d1",
  "aggregation_run_id": "44c92f20-1c8a-465f-84ce-a15e92951276",
  "source_system": "audit_trail_local",
  "symbol": "BTCUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 67989.0,
  "take_profit": 68941.88,
  "stop_loss": 67353.75,
  "risk_reward": 1.5,
  "confidence": 0.7,
  "strategy": "coinglass_leverage_squeeze",
  "raw_payload": "{\"id\": \"22e393df-3002-48ba-9750-6d8390eda1ae\", \"symbol\": \"BTCUSDT\", \"strategy\": \"coinglass_leverage_squeeze\", \"direction\": \"LONG\", \"stop_loss\": 67353....",
  "signal_timestamp": null,
  "recorded_at": "2026-03-10 19:09:56",
  "dedup_hash": "63b36fc0ab5afb79f5fe86c8f117494026304693170874bb2738ae0214bc8ce0",
  "was_stale": 0,
  "was_banned": 0,
  "was_demoted": 0,
  "was_wr_suppressed": 0,
  "created_by": "full_sync",
  "status": "EXPIRED",
  "exit_price": null,
  "exit_reason": "",
  "pnl_pct": null,
  "closed_at": null
}
```

### 4. `daily_prices` — ~49,340 rows (2MB + 2MB idx)
**Purpose:** Daily: Aggregated data

**Columns (9):** `id` (int), `ticker` (varchar(10)), `trade_date` (date), `open_price` (decimal(12,4)), `high_price` (decimal(12,4)), `low_price` (decimal(12,4)), `close_price` (decimal(12,4)), `adj_close` (decimal(12,4)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `ticker`, `trade_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "ABBV",
  "trade_date": "2025-02-07",
  "open_price": 193.16,
  "high_price": 193.86,
  "low_price": 190.44,
  "close_price": 190.6,
  "adj_close": 184.4136,
  "volume": 3805900
}
{
  "id": 2,
  "ticker": "ABBV",
  "trade_date": "2025-02-10",
  "open_price": 191.46,
  "high_price": 191.46,
  "low_price": 189.09,
  "close_price": 190.34,
  "adj_close": 184.1621,
  "volume": 3685700
}
```

**`trade_date` range:** 2024-02-07 → 2026-04-29

### 5. `lm_signals` — ~33,557 rows (13MB + 1MB idx)
**Purpose:** Live Market: Signals

**Columns (24):** `id` (int), `asset_class` (varchar(10)), `symbol` (varchar(20)), `algorithm_name` (varchar(100)), `signal_type` (varchar(20)), `signal_strength` (int), `entry_price` (decimal(18,8)), `target_tp_pct` (decimal(6,2)), `target_sl_pct` (decimal(6,2)), `max_hold_hours` (int), `timeframe` (varchar(20)), `rationale` (text) … +12 more

**Primary Key:** `id`
**Indexed:** `asset_class`, `symbol`, `signal_time`, `status`

**`asset_class` distribution:**
- `CRYPTO`: 30,421
- `FOREX`: 1,914
- `STOCK`: 1,222

**`status` distribution:**
- `expired`: 33,289
- `executed`: 199
- `active`: 59
- `resolved`: 10

**Sample Rows:**
```json
{
  "id": 1,
  "asset_class": "FOREX",
  "symbol": "EURUSD",
  "algorithm_name": "RSI Reversal",
  "signal_type": "SHORT",
  "signal_strength": 45,
  "entry_price": 1.19131,
  "target_tp_pct": 2.0,
  "target_sl_pct": 1.0,
  "max_hold_hours": 6,
  "timeframe": "1h",
  "rationale": "{\"reason\":\"RSI at 72.6 (overbought)\",\"rsi\":72.6}",
  "param_source": "learned",
  "tp_original": 2.0,
  "sl_original": 1.0,
  "hold_original": 12,
  "signal_time": "2026-02-09 22:16:18",
  "expires_at": "2026-02-09 22:46:18",
  "status": "executed",
  "exit_price": 0.0,
  "pnl_pct": 0.0,
  "exit_reason": "",
  "resolved_at": null,
  "current_price": 0.0
}
{
  "id": 2,
  "asset_class": "FOREX",
  "symbol": "EURUSD",
  "algorithm_name": "Consensus",
  "signal_type": "BUY",
  "signal_strength": 70,
  "entry_price": 1.19131,
  "target_tp_pct": 3.0,
  "target_sl_pct": 2.0,
  "max_hold_hours": 12,
  "timeframe": "1h",
  "rationale": "{\"reason\":\"2 algorithms picked EURUSD in the last 24h\",\"algo_count\":2,\"algorithms\":[\"FX Momentum\",\"FX Trend Following\"]}",
  "param_source": "learned",
  "tp_original": 3.0,
  "sl_original": 2.0,
  "hold_original": 24,
  "signal_time": "2026-02-09 22:16:18",
  "expires_at": "2026-02-09 22:46:18",
  "status": "expired",
  "exit_price": 0.0,
  "pnl_pct": 0.0,
  "exit_reason": "",
  "resolved_at": null,
  "current_price": 0.0
}
```

**`timeframe` range:** 1h → 7d

**`signal_time` range:** 2026-02-09 22:16:18 → 2026-05-08 14:20:00

### 6. `at_audit_events` — ~27,602 rows (4MB + 5MB idx)
**Purpose:** Audit: Event log

**Columns (9):** `id` (int), `event_type` (varchar(100)), `pick_id` (char(36)), `aggregation_run_id` (char(36)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `payload` (json), `origin` (varchar(50)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `event_type`, `pick_id`, `aggregation_run_id`, `symbol`

**`event_type` distribution:**
- `AGGREGATION_START`: 22,878
- `DISCORD_POSTED`: 18,221
- `EDGE_AUDIT_PUSH`: 4,526
- `KIMI_AUDIT_PUSH`: 2,631
- `SIGNAL_AGGREGATOR_AUDIT_PUSH`: 2,456
- `ALPHA_AUDIT_PUSH`: 1,661
- `MERCURY2_AUDIT_PUSH`: 1,540
- `ARENA_SCAN_COMPLETE`: 1,486
- `QUAN_ENGINE_SCAN_COMPLETE`: 860
- `COINGLASS_DNA_AUDIT_PUSH`: 791
- `BATTLEGROUND_AUDIT_PUSH`: 761
- `PREDICTIONS_AUDIT_PUSH`: 715

**`asset_class` distribution:**
- `UNKNOWN`: 40,590
- `CRYPTO`: 14,294
- `EQUITY`: 2,904
- `MEMECOIN`: 896
- ``: 489
- `FOREX`: 1

**Sample Rows:**
```json
{
  "id": 2,
  "event_type": "AGGREGATION_START",
  "pick_id": null,
  "aggregation_run_id": "c14bfe0a-93fe-40d4-89b9-3433c174158a",
  "symbol": null,
  "asset_class": "UNKNOWN",
  "payload": "{\"regime\": null, \"portfolio_dd\": 9.0168}",
  "origin": "aggregator",
  "created_at": "2026-03-06 21:01:21"
}
{
  "id": 3,
  "event_type": "DISCORD_POSTED",
  "pick_id": null,
  "aggregation_run_id": null,
  "symbol": "BTCUSDT",
  "asset_class": "CRYPTO",
  "payload": "{\"agreement\": 3, \"direction\": \"LONG\", \"confidence\": 0.99}",
  "origin": "discord_notify",
  "created_at": "2026-03-06 21:01:32"
}
```

**`created_at` range:** 2026-03-06 21:01:21 → 2026-05-08 14:27:13

### 7. `trading_picks` — ~24,644 rows (7MB + 0MB idx)
**Purpose:** Trading: Unified pick tracking

**Columns (19):** `id` (varchar(100)), `symbol` (varchar(20)), `direction` (varchar(10)), `strategy` (varchar(100)), `entry_price` (decimal(20,8)), `take_profit` (decimal(20,8)), `stop_loss` (decimal(20,8)), `confidence` (decimal(5,4)), `elite_score` (int), `trust_score` (int), `category` (varchar(20)), `source_system` (varchar(50)) … +7 more

**Primary Key:** `id`

**`direction` distribution:**
- `SHORT`: 30,592
- `LONG`: 28,239
- `BUY`: 3,290
- `SELL`: 1,364
- ``: 449

**`strategy` distribution:**
- `ig_contrarian_sentiment`: 6,625
- `myfxbook_retail_contrarian`: 4,876
- `non_crypto_consensus`: 4,769
- `stocks_rsi2_pullback`: 3,704
- `cot_positioning`: 3,667
- `cta_cross_asset_tsmom`: 3,511
- `forex_rsi2_mean_reversion`: 3,488
- `cta_commodity_momentum_term`: 3,380
- ``: 2,668
- `futures_momentum`: 2,649
- `prediction_market_consensus`: 2,249
- `cftc_cot_commercial_signal`: 2,117

**`category` distribution:**
- `forex`: 22,393
- `commodity`: 16,754
- `crypto`: 13,745
- `equity`: 5,980
- ``: 3,434
- `futures`: 513
- `bond`: 460
- `index`: 379
- `meme`: 146
- `etf`: 57
- `stocks`: 38
- `stock`: 27

**`source_system` distribution:**
- `multi_asset_copytrader`: 28,885
- `cta_replicator`: 7,858
- `non_crypto_consensus`: 4,769
- `multi_asset_cot`: 3,657
- `prediction_market_agents`: 1,915
- `polymarket_whale_tracker`: 1,856
- `luxalgo_filters`: 1,532
- `ml_crypto_pred`: 1,478
- `copy_trader_polymarket`: 1,456
- `short_dominant_engine`: 1,285
- `ml_crypto_predictor`: 1,256
- `copy_trader_intel`: 1,077

**Sample Rows:**
```json
{
  "id": "0006cfc20f04",
  "symbol": "ENAUSDT",
  "direction": "",
  "strategy": "",
  "entry_price": 0.092,
  "take_profit": null,
  "stop_loss": null,
  "confidence": null,
  "elite_score": null,
  "trust_score": null,
  "category": "",
  "source_system": "mega_mutation",
  "status": "WON",
  "pnl_pct": 8.661,
  "exit_price": 0.100152,
  "created_at": null,
  "closed_at": "2026-04-24 23:03:08",
  "exit_reason": "TP_HIT",
  "updated_at": "2026-04-24 23:47:50"
}
{
  "id": "000b6a5bbfe8",
  "symbol": "STXUSDT",
  "direction": "SELL",
  "strategy": "luxalgo_confluence",
  "entry_price": 0.2566,
  "take_profit": 0.252216,
  "stop_loss": 0.259191,
  "confidence": 0.7025,
  "elite_score": null,
  "trust_score": null,
  "category": "",
  "source_system": "luxalgo_filters",
  "status": "SL_HIT",
  "pnl_pct": -2.49,
  "exit_price": null,
  "created_at": "2026-03-15 21:37:28",
  "closed_at": "2026-03-16 03:33:51",
  "exit_reason": null,
  "updated_at": "2026-04-11 03:30:20"
}
```

**`created_at` range:** 2026-02-17 20:22:40 → 2026-05-08 13:52:37

**`closed_at` range:** 2026-02-22 00:00:00 → 2026-05-08 12:56:50

### 8. `now_history` — ~23,859 rows (11MB + 3MB idx)
**Purpose:** Misc/Unknown

**Columns (19):** `id` (int), `run_id` (varchar(36)), `scan_time` (datetime), `symbol` (varchar(20)), `direction` (enum('LONG','SHORT')), `strategy` (varchar(50)), `entry_price` (decimal(20,8)), `sl_price` (decimal(20,8)), `tp_price_1_5` (decimal(20,8)), `tp_price_2_0` (decimal(20,8)), `sl_pct` (decimal(8,4)), `confidence` (decimal(5,2)) … +7 more

**Primary Key:** `id`
**Indexed:** `scan_time`, `symbol`, `strategy`, `outcome_1_5`

**`direction` distribution:**
- `LONG`: 36,452
- `SHORT`: 3,603

**`strategy` distribution:**
- `ema_stack`: 8,337
- `st_fear_greed_contrarian`: 7,740
- `macd_crossover`: 6,363
- `bollinger_squeeze`: 4,199
- `stochrsi_macd_combo`: 4,021
- `st_obv_support_divergence`: 2,880
- `st_rsi_momentum_confluence`: 1,478
- `volume_spike_breakout`: 1,376
- `st_multi_day_momentum`: 1,075
- `macd_rsi_confluence`: 1,071
- `st_bb_squeeze_expansion`: 567
- `rsi_bounce`: 364

**Sample Rows:**
```json
{
  "id": 1,
  "run_id": "9b7546e5",
  "scan_time": "2026-03-07 03:48:14",
  "symbol": "XRPUSDT",
  "direction": "LONG",
  "strategy": "ema_stack",
  "entry_price": 1.3682,
  "sl_price": 1.3435724,
  "tp_price_1_5": 1.4051414,
  "tp_price_2_0": 1.4174552,
  "sl_pct": 1.8,
  "confidence": 60.6,
  "reason": "EMA stack aligned (9>1.37 > 21>1.37 > 50>1.37). Price bounced off 9 EMA.",
  "outcome_1_5": "EXPIRED",
  "outcome_2_0": "EXPIRED",
  "peak_price": 1.3686,
  "trough_price": 1.3606,
  "resolved_at": "2026-03-07 05:00:25",
  "actual_pnl_pct": -0.3654
}
{
  "id": 2,
  "run_id": "9b7546e5",
  "scan_time": "2026-03-07 03:48:14",
  "symbol": "ETHUSDT",
  "direction": "LONG",
  "strategy": "ema_stack",
  "entry_price": 1982.86,
  "sl_price": 1947.16852,
  "tp_price_1_5": 2036.39722,
  "tp_price_2_0": 2054.24296,
  "sl_pct": 1.8,
  "confidence": 60.5,
  "reason": "EMA stack aligned (9>1983.61 > 21>1982.58 > 50>1981.62). Price bounced off 9 EMA.",
  "outcome_1_5": "EXPIRED",
  "outcome_2_0": "EXPIRED",
  "peak_price": 1983.94,
  "trough_price": 1964.34,
  "resolved_at": "2026-03-07 05:00:27",
  "actual_pnl_pct": -0.3409
}
```

**`scan_time` range:** 2026-03-07 03:48:14 → 2026-05-08 14:01:43

**`resolved_at` range:** 2026-03-07 05:00:25 → 2026-05-08 13:58:30

### 9. `lm_sports_clv` — ~20,607 rows (3MB + 1MB idx)
**Purpose:** Live Market: Signals

**Columns (16):** `id` (int), `event_id` (varchar(100)), `sport` (varchar(50)), `home_team` (varchar(100)), `away_team` (varchar(100)), `commence_time` (datetime), `bookmaker_key` (varchar(50)), `market` (varchar(20)), `outcome_name` (varchar(100)), `opening_price` (decimal(10,4)), `closing_price` (decimal(10,4)), `opening_implied_prob` (decimal(8,6)) … +4 more

**Primary Key:** `id`
**Indexed:** `event_id`, `sport`, `commence_time`

**Sample Rows:**
```json
{
  "id": 1,
  "event_id": "123a238486098cc9e8f71fea0cf4e7b0",
  "sport": "americanfootball_ncaaf",
  "home_team": "Virginia Cavaliers",
  "away_team": "NC State Wolfpack",
  "commence_time": "2026-08-29 16:00:00",
  "bookmaker_key": "fanduel",
  "market": "h2h",
  "outcome_name": "NC State Wolfpack",
  "opening_price": 2.34,
  "closing_price": 2.34,
  "opening_implied_prob": 0.42735,
  "closing_implied_prob": 0.42735,
  "clv_pct": 0.0,
  "first_seen": "2026-02-11 02:36:17",
  "last_updated": "2026-02-12 02:54:55"
}
{
  "id": 2,
  "event_id": "123a238486098cc9e8f71fea0cf4e7b0",
  "sport": "americanfootball_ncaaf",
  "home_team": "Virginia Cavaliers",
  "away_team": "NC State Wolfpack",
  "commence_time": "2026-08-29 16:00:00",
  "bookmaker_key": "fanduel",
  "market": "h2h",
  "outcome_name": "Virginia Cavaliers",
  "opening_price": 1.62,
  "closing_price": 1.62,
  "opening_implied_prob": 0.617284,
  "closing_implied_prob": 0.617284,
  "clv_pct": 0.0,
  "first_seen": "2026-02-11 02:36:17",
  "last_updated": "2026-02-12 02:54:55"
}
```

**`commence_time` range:** 2026-02-11 00:32:30 → 2026-09-12 16:00:00

**`last_updated` range:** 2026-02-11 02:36:17 → 2026-04-02 03:53:22

### 10. `rapid_signals` — ~11,709 rows (1MB + 2MB idx)
**Purpose:** Signals: Tracking

**Columns (13):** `signal_id` (int), `strategy_name` (varchar(100)), `pair` (varchar(20)), `signal_type` (varchar(10)), `strength` (decimal(5,2)), `entry_price` (decimal(20,8)), `take_profit` (decimal(20,8)), `stop_loss` (decimal(20,8)), `created_at` (timestamp), `status` (varchar(20)), `outcome` (varchar(20)), `closed_at` (timestamp) … +1 more

**Primary Key:** `signal_id`
**Indexed:** `strategy_name`, `created_at`, `status`

**`status` distribution:**
- `closed`: 35,324

**`outcome` distribution:**
- `win`: 17,706
- `loss`: 17,618

**Sample Rows:**
```json
{
  "signal_id": 1,
  "strategy_name": "quality-minus-junk",
  "pair": "XOM",
  "signal_type": "long",
  "strength": 33.39,
  "entry_price": 152.360001,
  "take_profit": 147.300003,
  "stop_loss": null,
  "created_at": "2026-02-19 14:49:46",
  "status": "closed",
  "outcome": "loss",
  "closed_at": "2026-02-21 07:08:52",
  "pnl": -0.03
}
{
  "signal_id": 2,
  "strategy_name": "quality-momentum-scout",
  "pair": "XOM",
  "signal_type": "long",
  "strength": 34.09,
  "entry_price": 152.139999,
  "take_profit": 147.300003,
  "stop_loss": null,
  "created_at": "2026-02-19 14:49:46",
  "status": "closed",
  "outcome": "loss",
  "closed_at": "2026-02-21 07:08:52",
  "pnl": -0.03
}
```

**`created_at` range:** 2026-02-19 14:49:46 → 2026-05-06 22:20:54

**`closed_at` range:** 2026-02-21 07:08:50 → 2026-05-08 13:42:42

### 11. `at_discord_gate_log` — ~10,640 rows (2MB + 1MB idx)
**Purpose:** Audit: Discord gate state

**Columns (11):** `id` (int), `symbol` (varchar(50)), `direction` (varchar(10)), `system_name` (varchar(100)), `strategy` (varchar(100)), `gate_name` (varchar(30)), `gate_result` (varchar(10)), `reason` (varchar(255)), `confidence` (decimal(5,4)), `entry_price` (decimal(18,8)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `symbol`, `gate_name`, `created_at`

**`direction` distribution:**
- `LONG`: 15,803
- `BUY`: 15,570
- `SELL`: 4,317
- `SHORT`: 2,381
- `WATCH`: 3

**`strategy` distribution:**
- `Gainer ML (VERY HIGH)`: 3,844
- `prediction_market_consensus`: 2,410
- `stocks_rsi2_pullback`: 2,282
- `Consensus (2/2 systems)`: 1,910
- `myfxbook_retail_contrarian`: 1,798
- `Consensus (2/3 systems)`: 848
- `luxalgo_confluence`: 801
- `forex_rsi2_mean_reversion`: 745
- `Bollinger Squeeze Breakout`: 708
- `Crypto RSI Scout`: 669
- `volume_spike_breakout`: 657
- `winner_pattern_precursor`: 617

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "BCHUSDT",
  "direction": "BUY",
  "system_name": "KIMI Rise of the Claw",
  "strategy": "Funding Rate Arbitrage",
  "gate_name": "G2_CONFIDENCE",
  "gate_result": "REJECT",
  "reason": "G2: confidence 0.40 < 0.65",
  "confidence": 0.4,
  "entry_price": 448.975281,
  "created_at": "2026-03-04 17:47:03"
}
{
  "id": 2,
  "symbol": "MANAUSDT",
  "direction": "BUY",
  "system_name": "KIMI Rise of the Claw",
  "strategy": "Meme Coin Scout",
  "gate_name": "G2_CONFIDENCE",
  "gate_result": "REJECT",
  "reason": "G2: confidence 0.40 < 0.65",
  "confidence": 0.4,
  "entry_price": 0.09953,
  "created_at": "2026-03-04 17:47:04"
}
```

**`created_at` range:** 2026-03-04 17:47:03 → 2026-05-08 13:59:11

### 12. `stock_picks` — ~7,239 rows (2MB + 0MB idx)
**Purpose:** Stocks: Pick data

**Columns (16):** `id` (int), `ticker` (varchar(10)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_price` (decimal(12,4)), `simulated_entry_price` (decimal(12,4)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)) … +4 more

**Primary Key:** `id`
**Indexed:** `ticker`, `algorithm_name`, `pick_date`, `pick_hash`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "GM",
  "algorithm_id": 5,
  "algorithm_name": "Technical Momentum",
  "pick_date": "2026-01-28",
  "pick_time": "2026-01-28 02:50:07",
  "entry_price": 86.38,
  "simulated_entry_price": 86.38,
  "score": 100,
  "rating": "STRONG BUY",
  "risk_level": "High",
  "timeframe": "3d",
  "stop_loss_price": 82.42,
  "pick_hash": "",
  "indicators_json": "{\"rsi\":59,\"rsiZScore\":0.51,\"volumeSurge\":2.33,\"volumeZScore\":3.01,\"breakout\":true,\"bollingerSqueeze\":true,\"atr\":2.64}",
  "verified": 0
}
{
  "id": 2,
  "ticker": "PFE",
  "algorithm_id": 5,
  "algorithm_name": "Technical Momentum",
  "pick_date": "2026-01-28",
  "pick_time": "2026-01-28 02:50:07",
  "entry_price": 26.5,
  "simulated_entry_price": 26.5,
  "score": 85,
  "rating": "STRONG BUY",
  "risk_level": "High",
  "timeframe": "3d",
  "stop_loss_price": 25.69,
  "pick_hash": "",
  "indicators_json": "{\"rsi\":65,\"rsiZScore\":0.91,\"volumeSurge\":1.42,\"volumeZScore\":2.48,\"breakout\":true,\"bollingerSqueeze\":true,\"atr\":0.54}",
  "verified": 0
}
```

**`pick_date` range:** 2024-02-07 → 2026-04-27

**`pick_time` range:** 2024-02-07 09:30:00 → 2026-04-27 21:55:28

### 13. `mf2_nav_history` — ~6,860 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (7):** `id` (int), `symbol` (varchar(20)), `nav_date` (date), `nav` (decimal(12,4)), `prev_nav` (decimal(12,4)), `daily_return_pct` (decimal(10,6)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `symbol`, `nav_date`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "RBF450",
  "nav_date": "2025-02-10",
  "nav": 5.6296,
  "prev_nav": 5.6293,
  "daily_return_pct": 0.005329,
  "volume": 0
}
{
  "id": 2,
  "symbol": "RBF450",
  "nav_date": "2025-02-11",
  "nav": 5.6181,
  "prev_nav": 5.6296,
  "daily_return_pct": -0.204277,
  "volume": 0
}
```

**`nav_date` range:** 2024-02-13 → 2026-03-27

### 14. `simulation_grid` — ~6,000 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (21):** `id` (int), `batch_id` (int), `direction` (varchar(5)), `algorithm` (varchar(80)), `algo_combo` (varchar(255)), `tp` (decimal(6,2)), `sl` (decimal(6,2)), `hold_days` (int), `commission` (decimal(6,2)), `regime` (varchar(20)), `total_trades` (int), `winning_trades` (int) … +9 more

**Primary Key:** `id`
**Indexed:** `batch_id`, `direction`, `algorithm`, `total_return_pct`

**`direction` distribution:**
- `LONG`: 6,000

**Sample Rows:**
```json
{
  "id": 1,
  "batch_id": 0,
  "direction": "LONG",
  "algorithm": "13F Hedge Fund Clone",
  "algo_combo": "",
  "tp": 3.0,
  "sl": 2.0,
  "hold_days": 1,
  "commission": 0.0,
  "regime": "all",
  "total_trades": 160,
  "winning_trades": 41,
  "win_rate": 25.63,
  "total_return_pct": -11.8356,
  "final_value": 8816.44,
  "max_drawdown_pct": 12.2631,
  "sharpe_ratio": -0.6528,
  "profit_factor": 0.0,
  "total_pnl": -1183.56,
  "total_commissions": 0.0,
  "created_at": "2026-04-26 06:38:10"
}
{
  "id": 2,
  "batch_id": 0,
  "direction": "LONG",
  "algorithm": "13F Hedge Fund Clone",
  "algo_combo": "",
  "tp": 3.0,
  "sl": 2.0,
  "hold_days": 2,
  "commission": 0.0,
  "regime": "all",
  "total_trades": 161,
  "winning_trades": 53,
  "win_rate": 32.92,
  "total_return_pct": -9.9001,
  "final_value": 9009.99,
  "max_drawdown_pct": 10.3002,
  "sharpe_ratio": -0.4368,
  "profit_factor": 0.0,
  "total_pnl": -990.01,
  "total_commissions": 0.0,
  "created_at": "2026-04-26 06:38:10"
}
```

**`created_at` range:** 2026-04-26 06:38:10 → 2026-04-26 06:54:07

### 15. `audit_log` — ~5,937 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "Schema created/verified",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 04:51:01"
}
{
  "id": 2,
  "action_type": "import_picks",
  "details": "Imported 18, skipped 0",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 04:51:06"
}
```

**`created_at` range:** 2026-02-09 04:51:01 → 2026-05-06 17:06:07

### 16. `at_consensus_picks` — ~5,176 rows (2MB + 4MB idx)
**Purpose:** Audit: Multi-system consensus picks

**Columns (26):** `id` (char(36)), `aggregation_run_id` (char(36)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `direction` (enum('LONG','SHORT')), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `risk_reward` (decimal(10,4)), `confidence` (decimal(5,4)), `agreement_count` (int), `source_systems` (json) … +14 more

**Primary Key:** `id`
**Indexed:** `aggregation_run_id`, `symbol`, `asset_class`, `status`

**`asset_class` distribution:**
- `CRYPTO`: 9,679
- `EQUITY`: 767
- `MEMECOIN`: 707
- ``: 279
- `UNKNOWN`: 3
- `FOREX`: 1

**`direction` distribution:**
- `LONG`: 10,997
- `SHORT`: 439

**`consensus_tier` distribution:**
- `MODERATE`: 6,201
- `STRONG`: 3,954
- `SUPER`: 1,112
- `high_conviction`: 116
- `medium_conviction`: 28
- `speculative`: 25

**`classification` distribution:**
- `None`: 11,267
- `technical`: 76
- `correlation`: 52
- `leap`: 21
- `verified`: 20

**Sample Rows:**
```json
{
  "id": "0010db92-4441-4154-856f-fcaeafcba85b",
  "aggregation_run_id": "1a91d633-0974-4a2c-a607-4d11cb6ac9d2",
  "symbol": "BTCUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 71090.7,
  "take_profit": 75799.89642857,
  "stop_loss": 67951.23571429,
  "risk_reward": 1.5,
  "confidence": 0.755,
  "agreement_count": 5,
  "source_systems": "[\"crypto_ml_edge\", \"genome\", \"kimi\", \"alpha_engine\", \"incubator_fwd\", \"quan_engine\"]",
  "source_strategies": "{\"kimi\": \"Extreme Fear Contrarian Buy\", \"genome\": \"AuditEnsemble_LONG\", \"alpha_engine\": \"winner_pattern_precursor\", \"incubator_fwd\": \"ConsecutiveBodyR...",
  "system_confidences": "{\"kimi\": null, \"genome\": null, \"quan_engine\": null, \"alpha_engine\": 50.0, \"incubator_fwd\": null, \"crypto_ml_edge\": null}",
  "consensus_tier": "STRONG",
  "classification": null,
  "regime_data": null,
  "discord_channel": null,
  "discord_message_id": null,
  "status": "LOST",
  "exit_price": 70284.74,
  "exit_reason": "SL_HIT",
  "pnl_pct": -0.5649,
  "slippage_estimate": null,
  "generated_at": "2026-03-20 02:21:48",
  "closed_at": "2026-03-20 02:22:06"
}
{
  "id": "00126486-2a94-4e76-ac0e-a8f7e9c559e0",
  "aggregation_run_id": "fc0a1088-f7e2-496f-ba29-9acb2bbfd8e0",
  "symbol": "XRPUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 1.4139,
  "take_profit": 1.456317,
  "stop_loss": 1.385622,
  "risk_reward": 1.5,
  "confidence": 0.665,
  "agreement_count": 2,
  "source_systems": "[\"kimi\", \"battleground\", \"ml_crypto_pred\"]",
  "source_strategies": "{\"kimi\": \"Skyrocket Breakout Scalper\", \"battleground\": \"drawdown_recovery_rsi_xrp\", \"ml_crypto_pred\": \"enhanced_ml_A_xgboost\"}",
  "system_confidences": "{\"kimi\": null, \"battleground\": null, \"ml_crypto_pred\": null}",
  "consensus_tier": "MODERATE",
  "classification": null,
  "regime_data": null,
  "discord_channel": null,
  "discord_message_id": null,
  "status": "WON",
  "exit_price": 1.4404,
  "exit_reason": "TP_HIT",
  "pnl_pct": 2.1277,
  "slippage_estimate": null,
  "generated_at": "2026-05-07 13:18:24",
  "closed_at": "2026-05-06 09:20:20"
}
```

**`generated_at` range:** 2026-03-06 21:01:27 → 2026-05-08 13:49:06

**`closed_at` range:** 2026-03-10 03:07:14 → 2026-05-08 11:44:42

### 17. `alpha_picks` — ~5,043 rows (1MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (17):** `id` (int), `ticker` (varchar(10)), `strategy` (varchar(100)), `pick_date` (date), `entry_price` (decimal(12,4)), `score` (decimal(12,4)), `conviction` (varchar(20)), `expected_horizon` (varchar(20)), `risk_level` (varchar(20)), `position_size_pct` (decimal(12,4)), `stop_loss_pct` (decimal(12,4)), `take_profit_pct` (decimal(12,4)) … +5 more

**Primary Key:** `id`
**Indexed:** `ticker`, `strategy`, `pick_date`, `pick_hash`

**`strategy` distribution:**
- `Alpha Factor Consensus`: 597
- `Alpha Factor Composite`: 563
- `Alpha Factor Growth`: 560
- `Alpha Factor Quality`: 560
- `Alpha Factor Safe Bets`: 557
- `Alpha Factor Earnings`: 553
- `Alpha Factor Low Vol`: 551
- `Alpha Factor Momentum`: 551
- `Alpha Factor Value`: 551

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "GOOGL",
  "strategy": "Alpha Factor Momentum",
  "pick_date": "2026-02-09",
  "entry_price": 325.11,
  "score": 91.08,
  "conviction": "high",
  "expected_horizon": "1m",
  "risk_level": "Medium",
  "position_size_pct": 8.0,
  "stop_loss_pct": 20.0,
  "take_profit_pct": 40.0,
  "rationale": "Rank #1 in Alpha Factor Momentum. Composite: 66.8. Regime: calm_bull. Strong momentum. Earnings strength",
  "top_factors": "Momentum: 91.1; Earnings: 86.5; Growth: 80.4",
  "avoid_reasons": "",
  "pick_hash": "36c0b126fa3c98122cd603ab8aa40fe48c97d115",
  "created_at": "2026-02-09 18:26:50"
}
{
  "id": 2,
  "ticker": "CAT",
  "strategy": "Alpha Factor Momentum",
  "pick_date": "2026-02-09",
  "entry_price": 735.0,
  "score": 89.8,
  "conviction": "high",
  "expected_horizon": "1m",
  "risk_level": "Medium",
  "position_size_pct": 8.0,
  "stop_loss_pct": 20.0,
  "take_profit_pct": 40.0,
  "rationale": "Rank #2 in Alpha Factor Momentum. Composite: 47.5. Regime: calm_bull. Strong momentum",
  "top_factors": "Momentum: 89.8; Growth: 52; Quality: 47.5",
  "avoid_reasons": "",
  "pick_hash": "8738fe877a3bf1abb611297921a0f9f69ce29e02",
  "created_at": "2026-02-09 18:26:50"
}
```

**`pick_date` range:** 2026-02-09 → 2026-04-27

**`created_at` range:** 2026-02-09 18:26:50 → 2026-04-27 21:55:28

### 18. `mf_nav_history` — ~5,000 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (7):** `id` (int), `ticker` (varchar(15)), `nav_date` (date), `nav_price` (decimal(12,4)), `adj_nav` (decimal(12,4)), `change_pct` (decimal(8,4)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `ticker`, `nav_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "DODFX",
  "nav_date": "2025-02-10",
  "nav_price": 13.3675,
  "adj_nav": 12.3768,
  "change_pct": 0.0,
  "volume": 0
}
{
  "id": 2,
  "ticker": "DODFX",
  "nav_date": "2025-02-11",
  "nav_price": 13.395,
  "adj_nav": 12.4023,
  "change_pct": 0.2061,
  "volume": 0
}
```

**`nav_date` range:** 2025-02-10 → 2026-02-06

### 19. `cp_prices` — ~4,857 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `pair` (varchar(15)), `trade_date` (date), `open_price` (decimal(18,8)), `high_price` (decimal(18,8)), `low_price` (decimal(18,8)), `close_price` (decimal(18,8)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `pair`, `trade_date`

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "AAVE-USD",
  "trade_date": "2025-02-09",
  "open_price": 239.33306885,
  "high_price": 252.38621521,
  "low_price": 230.51690674,
  "close_price": 241.62512207,
  "volume": 297811208
}
{
  "id": 2,
  "pair": "AAVE-USD",
  "trade_date": "2025-02-10",
  "open_price": 241.62512207,
  "high_price": 256.47213745,
  "low_price": 235.03410339,
  "close_price": 252.02619934,
  "volume": 340055198
}
```

**`trade_date` range:** 2025-02-09 → 2026-02-09

### 20. `at_discord_notifications` — ~4,637 rows (4MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (19):** `id` (int), `symbol` (varchar(50)), `direction` (varchar(10)), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `confidence` (decimal(5,4)), `agreement_count` (int), `source_systems` (json), `strategy` (varchar(100)), `signal_tier` (varchar(20)), `asset_class` (varchar(20)) … +7 more

**Primary Key:** `id`
**Indexed:** `symbol`, `discord_channel`, `event_type`, `created_at`

**`direction` distribution:**
- ``: 21,320
- `LONG`: 18,368
- `SHORT`: 481

**`strategy` distribution:**
- `None`: 21,356
- ``: 3,407
- `Extreme Fear Contrarian Buy`: 2,327
- `AuditEnsemble_LONG`: 958
- `Multi-Timeframe Trend Alignment`: 929
- `ema_stack`: 874
- `st_fear_greed_contrarian`: 803
- `CCI Reversal Scout`: 742
- `incubator_gainer`: 678
- `Crypto RSI Scout`: 629
- `st_obv_support_divergence`: 482
- `Volume Spike Scout`: 436

**`signal_tier` distribution:**
- `None`: 40,164
- `STRONG`: 3
- `MODERATE`: 2

**`asset_class` distribution:**
- `UNKNOWN`: 21,335
- `CRYPTO`: 14,451
- `EQUITY`: 3,026
- `MEMECOIN`: 865
- `MEME`: 489
- `FOREX`: 3

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "TLT",
  "direction": "LONG",
  "entry_price": 89.43,
  "take_profit": 90.3399,
  "stop_loss": 88.8234,
  "confidence": 0.66,
  "agreement_count": null,
  "source_systems": null,
  "strategy": null,
  "signal_tier": null,
  "asset_class": "EQUITY",
  "discord_channel": "freshpicks",
  "discord_webhook": null,
  "discord_message_id": null,
  "event_type": "PICK_POSTED",
  "pnl_pct": null,
  "payload": null,
  "created_at": "2026-03-04 03:19:15"
}
{
  "id": 2,
  "symbol": "NEARUSDT",
  "direction": "SHORT",
  "entry_price": 1.387,
  "take_profit": 0.9048,
  "stop_loss": 1.4594,
  "confidence": 0.865,
  "agreement_count": null,
  "source_systems": null,
  "strategy": null,
  "signal_tier": null,
  "asset_class": "CRYPTO",
  "discord_channel": "freshpicks",
  "discord_webhook": null,
  "discord_message_id": null,
  "event_type": "PICK_POSTED",
  "pnl_pct": null,
  "payload": null,
  "created_at": "2026-03-04 03:37:21"
}
```

**`created_at` range:** 2026-02-25 00:00:00 → 2026-05-08 14:18:12

### 21. `cr_price_history` — ~4,529 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (8):** `id` (int), `symbol` (varchar(20)), `price_date` (date), `open` (decimal(18,8)), `high` (decimal(18,8)), `low` (decimal(18,8)), `close` (decimal(18,8)), `volume` (decimal(24,2))

**Primary Key:** `id`
**Indexed:** `symbol`, `price_date`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "ADAUSD",
  "price_date": "2025-02-09",
  "open": 0.70177603,
  "high": 0.71263701,
  "low": 0.65405601,
  "close": 0.68270099,
  "volume": 679645670.0
}
{
  "id": 2,
  "symbol": "ADAUSD",
  "price_date": "2025-02-10",
  "open": 0.68277299,
  "high": 0.716281,
  "low": 0.66560298,
  "close": 0.710693,
  "volume": 751114200.0
}
```

**`price_date` range:** 2025-02-09 → 2026-05-07

### 22. `fx_prices` — ~3,855 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (8):** `id` (int), `pair` (varchar(10)), `trade_date` (date), `open_price` (decimal(12,6)), `high_price` (decimal(12,6)), `low_price` (decimal(12,6)), `close_price` (decimal(12,6)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `pair`, `trade_date`

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "AUDCAD",
  "trade_date": "2025-02-10",
  "open_price": 0.89693,
  "high_price": 0.90104,
  "low_price": 0.89685,
  "close_price": 0.89693,
  "volume": 0
}
{
  "id": 2,
  "pair": "AUDCAD",
  "trade_date": "2025-02-11",
  "open_price": 0.898788,
  "high_price": 0.900938,
  "low_price": 0.8975,
  "close_price": 0.898788,
  "volume": 0
}
```

**`trade_date` range:** 2025-02-10 → 2026-02-09

### 23. `algorithm_rolling_perf` — ~3,536 rows (0MB + 0MB idx)
**Purpose:** Algo: Performance tracking

**Columns (15):** `id` (int), `source_table` (varchar(30)), `algorithm_name` (varchar(100)), `period` (varchar(10)), `calc_date` (date), `total_picks` (int), `resolved_picks` (int), `wins` (int), `losses` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `avg_win_pct` (decimal(10,4)) … +3 more

**Primary Key:** `id`
**Indexed:** `source_table`, `algorithm_name`, `calc_date`

**Sample Rows:**
```json
{
  "id": 1,
  "source_table": "stock_picks",
  "algorithm_name": "Adversarial Trend (V2)",
  "period": "7d",
  "calc_date": "2026-02-09",
  "total_picks": 3,
  "resolved_picks": 0,
  "wins": 0,
  "losses": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 0.0,
  "profit_factor": 0.0,
  "created_at": "2026-02-09 21:07:40"
}
{
  "id": 2,
  "source_table": "stock_picks",
  "algorithm_name": "Adversarial Trend (V2)",
  "period": "30d",
  "calc_date": "2026-02-09",
  "total_picks": 3,
  "resolved_picks": 0,
  "wins": 0,
  "losses": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 0.0,
  "profit_factor": 0.0,
  "created_at": "2026-02-09 21:07:40"
}
```

**`calc_date` range:** 2026-02-09 → 2026-04-27

**`created_at` range:** 2026-02-09 21:07:40 → 2026-04-27 23:54:26

### 24. `alpha_fundamentals` — ~2,964 rows (7MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (34):** `id` (int), `ticker` (varchar(10)), `fetch_date` (date), `market_cap` (decimal(20,2)), `pe_trailing` (decimal(12,4)), `pe_forward` (decimal(12,4)), `peg_ratio` (decimal(12,4)), `price_to_book` (decimal(12,4)), `price_to_sales` (decimal(12,4)), `ev_to_ebitda` (decimal(12,4)), `return_on_equity` (decimal(12,4)), `return_on_assets` (decimal(12,4)) … +22 more

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "fetch_date": "2026-02-09",
  "market_cap": 4036344152064.0,
  "pe_trailing": 34.762,
  "pe_forward": 29.5975,
  "peg_ratio": 0.0,
  "price_to_book": 45.7853,
  "price_to_sales": 0.0,
  "ev_to_ebitda": 0.0,
  "return_on_equity": 1.5202,
  "return_on_assets": 0.2438,
  "gross_margins": 0.4733,
  "operating_margins": 0.3537,
  "profit_margins": 0.2704,
  "revenue_growth": 0.157,
  "earnings_growth": 0.183,
  "total_debt": 90509000704.0,
  "total_cash": 66907000832.0,
  "debt_to_equity": 102.63,
  "current_ratio": 0.974,
  "free_cashflow": 106312753152.0,
  "operating_cashflow": 135471996928.0,
  "dividend_yield": 0.003707,
  "payout_ratio": 0.0,
  "shares_outstanding": 14681140000,
  "beta": 0.0,
  "fifty_two_week_high": 288.62,
  "fifty_two_week_low": 169.21,
  "fifty_day_avg": 268.7022,
  "two_hundred_day_avg": 238.5706,
  "avg_volume": 48062168,
  "regular_market_price": 274.62,
  "raw_json": "{\"language\":\"en-US\",\"region\":\"US\",\"quoteType\":\"EQUITY\",\"typeDisp\":\"Equity\",\"quoteSourceName\":\"Nasdaq Real Time Price\",\"triggerable\":true,\"customPriceA..."
}
{
  "id": 2,
  "ticker": "ABBV",
  "fetch_date": "2026-02-09",
  "market_cap": 394586259456.0,
  "pe_trailing": 94.2025,
  "pe_forward": 13.964,
  "peg_ratio": 0.0,
  "price_to_book": -149.3378,
  "price_to_sales": 0.0,
  "ev_to_ebitda": 0.0,
  "return_on_equity": 11.0667,
  "return_on_assets": 0.0,
  "gross_margins": 0.7165,
  "operating_margins": 0.3496,
  "profit_margins": 0.0691,
  "revenue_growth": 0.1,
  "earnings_growth": 0.0,
  "total_debt": 68849000448.0,
  "total_cash": 5671000064.0,
  "debt_to_equity": 0.0,
  "current_ratio": 0.0,
  "free_cashflow": 0.0,
  "operating_cashflow": 0.0,
  "dividend_yield": 0.029763,
  "payout_ratio": 0.0,
  "shares_outstanding": 1767384632,
  "beta": 0.0,
  "fifty_two_week_high": 244.81,
  "fifty_two_week_low": 164.39,
  "fifty_day_avg": 224.0206,
  "two_hundred_day_avg": 209.6446,
  "avg_volume": 6430878,
  "regular_market_price": 223.26,
  "raw_json": "{\"language\":\"en-US\",\"region\":\"US\",\"quoteType\":\"EQUITY\",\"typeDisp\":\"Equity\",\"quoteSourceName\":\"Nasdaq Real Time Price\",\"triggerable\":true,\"customPriceA..."
}
```

**`fetch_date` range:** 2026-02-09 → 2026-04-27

### 25. `alpha_factor_scores` — ~2,860 rows (1MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (40):** `id` (int), `ticker` (varchar(10)), `score_date` (date), `momentum_12m` (decimal(12,4)), `momentum_6m` (decimal(12,4)), `momentum_3m` (decimal(12,4)), `momentum_1m` (decimal(12,4)), `momentum_score` (decimal(12,4)), `momentum_rank` (int), `quality_roe` (decimal(12,4)), `quality_margins` (decimal(12,4)), `quality_fcf_yield` (decimal(12,4)) … +28 more

**Primary Key:** `id`
**Indexed:** `ticker`, `score_date`, `composite_rank`, `regime_adj_rank`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "score_date": "2026-02-09",
  "momentum_12m": 0.2218,
  "momentum_6m": 0.2126,
  "momentum_3m": 0.0359,
  "momentum_1m": 0.0723,
  "momentum_score": 66.96,
  "momentum_rank": 82,
  "quality_roe": 1.5202,
  "quality_margins": 0.4255,
  "quality_fcf_yield": 0.0263,
  "quality_debt": 102.63,
  "quality_score": 67.74,
  "quality_rank": 88,
  "value_pe": 29.5975,
  "value_pb": 45.7853,
  "value_ps": 999.0,
  "value_div_yield": 0.003707,
  "value_score": 7.06,
  "value_rank": 0,
  "earnings_surprise_avg": 0.0567,
  "earnings_beat_rate": 1.0,
  "earnings_growth_rate": 0.183,
  "earnings_score": 73.33,
  "earnings_rank": 86,
  "vol_realized_60d": 0.1891,
  "vol_beta": 1.2488,
  "vol_max_dd_90d": 0.138,
  "vol_score": 46.67,
  "vol_rank": 43,
  "growth_revenue": 0.157,
  "growth_earnings": 0.183,
  "growth_score": 71.57,
  "growth_rank": 78,
  "composite_score": 54.52,
  "composite_rank": 65,
  "regime_adj_score": 58.88,
  "regime_adj_rank": 78,
  "factors_json": "{\"regime\":\"calm_bull\",\"regime_weights\":{\"m\":0.3,\"q\":0.18,\"v\":0.15,\"e\":0.17,\"vol\":0.05,\"g\":0.15},\"momentum_components\":{\"12m\":0.2218,\"6m\":0.2126,\"3m\":0..."
}
{
  "id": 2,
  "ticker": "ABBV",
  "score_date": "2026-02-09",
  "momentum_12m": 0.1722,
  "momentum_6m": 0.1281,
  "momentum_3m": 0.0195,
  "momentum_1m": 0.0152,
  "momentum_score": 59.21,
  "momentum_rank": 59,
  "quality_roe": 11.0667,
  "quality_margins": 0.5697,
  "quality_fcf_yield": 0.0,
  "quality_debt": 0.0,
  "quality_score": 74.02,
  "quality_rank": 96,
  "value_pe": 13.964,
  "value_pb": 999.0,
  "value_ps": 999.0,
  "value_div_yield": 0.029763,
  "value_score": 43.63,
  "value_rank": 39,
  "earnings_surprise_avg": 0.0279,
  "earnings_beat_rate": 1.0,
  "earnings_growth_rate": 0.0,
  "earnings_score": 38.92,
  "earnings_rank": 29,
  "vol_realized_60d": 0.2659,
  "vol_beta": 0.4398,
  "vol_max_dd_90d": 0.1327,
  "vol_score": 40.39,
  "vol_rank": 27,
  "growth_revenue": 0.1,
  "growth_earnings": 0.0,
  "growth_score": 44.12,
  "growth_rank": 39,
  "composite_score": 52.62,
  "composite_rank": 59,
  "regime_adj_score": 52.89,
  "regime_adj_rank": 57,
  "factors_json": "{\"regime\":\"calm_bull\",\"regime_weights\":{\"m\":0.3,\"q\":0.18,\"v\":0.15,\"e\":0.17,\"vol\":0.05,\"g\":0.15},\"momentum_components\":{\"12m\":0.1722,\"6m\":0.1281,\"3m\":0..."
}
```

**`score_date` range:** 2026-02-09 → 2026-04-27

### 26. `fxp_price_history` — ~2,658 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (8):** `id` (int), `symbol` (varchar(20)), `price_date` (date), `open_price` (decimal(12,6)), `high_price` (decimal(12,6)), `low_price` (decimal(12,6)), `close_price` (decimal(12,6)), `volume` (bigint)

**Primary Key:** `id`
**Indexed:** `symbol`, `price_date`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "AUDUSD",
  "price_date": "2025-02-10",
  "open_price": 0.625892,
  "high_price": 0.6289,
  "low_price": 0.625309,
  "close_price": 0.62589,
  "volume": 0
}
{
  "id": 2,
  "symbol": "AUDUSD",
  "price_date": "2025-02-11",
  "open_price": 0.627136,
  "high_price": 0.62968,
  "low_price": 0.62611,
  "close_price": 0.627128,
  "volume": 0
}
```

**`price_date` range:** 2025-02-10 → 2026-05-07

### 27. `at_local_picks` — ~2,103 rows (0MB + 0MB idx)
**Purpose:** Picks: Storage

**Columns (17):** `id` (int), `symbol` (varchar(50)), `direction` (varchar(10)), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `confidence` (decimal(5,4)), `strategy` (varchar(100)), `source_system` (varchar(100)), `source_file` (varchar(200)), `asset_class` (varchar(20)), `status` (varchar(20)) … +5 more

**Primary Key:** `id`
**Indexed:** `symbol`, `strategy`, `source_system`, `status`, `signal_timestamp`

**`direction` distribution:**
- `LONG`: 24,798
- `SHORT`: 2,713

**`strategy` distribution:**
- `super_signal_strong`: 9,941
- `super_signal_super`: 8,860
- `regime_accumulation`: 1,649
- `regime_mild_bear`: 1,451
- `regime_mild_bull`: 1,345
- `None`: 1,296
- `regime_strong_bear`: 891
- `regime_strong_bull`: 434
- `regime_crash`: 192
- ``: 141
- `claude_gainer_monero`: 119
- `ensemble`: 77

**`source_system` distribution:**
- `super_signals`: 18,801
- `regime_terminal`: 5,962
- `kimi_signal_tracker`: 1,038
- `claude_gainer_ml`: 540
- `battleground`: 180
- `kimi_feb17`: 141
- `kimi_riseoftheclaw`: 133
- `opposite_day`: 126
- `alpha_engine`: 125
- `signal_recorder`: 103
- `live_picks_tracker`: 97
- `predictions_engine`: 91

**`asset_class` distribution:**
- `CRYPTO`: 21,659
- `EQUITY`: 3,681
- `FOREX`: 1,796
- `MEMECOIN`: 252
- `UNKNOWN`: 123

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "SPY",
  "direction": "LONG",
  "entry_price": 683.789978,
  "take_profit": 0.0,
  "stop_loss": 0.0,
  "confidence": null,
  "strategy": "unknown",
  "source_system": "live_picks_tracker",
  "source_file": "data/live_picks.db:live_picks",
  "asset_class": "EQUITY",
  "status": "ACTIVE",
  "exit_price": null,
  "exit_reason": null,
  "pnl_pct": null,
  "signal_timestamp": null,
  "created_at": "2026-03-04 17:59:28"
}
{
  "id": 2,
  "symbol": "QQQ",
  "direction": "LONG",
  "entry_price": 605.340027,
  "take_profit": 0.0,
  "stop_loss": 0.0,
  "confidence": null,
  "strategy": "unknown",
  "source_system": "live_picks_tracker",
  "source_file": "data/live_picks.db:live_picks",
  "asset_class": "EQUITY",
  "status": "ACTIVE",
  "exit_price": null,
  "exit_reason": null,
  "pnl_pct": null,
  "signal_timestamp": null,
  "created_at": "2026-03-04 17:59:28"
}
```

**`signal_timestamp` range:** 2026-02-17 20:18:00 → 2026-05-08 12:24:23

**`created_at` range:** 2026-02-23 08:01:30 → 2026-05-08 12:24:23

### 28. `lm_snapshots` — ~2,096 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (14):** `id` (int), `snapshot_time` (datetime), `total_value_usd` (decimal(12,2)), `cash_usd` (decimal(12,2)), `invested_usd` (decimal(12,2)), `open_positions` (int), `unrealized_pnl_usd` (decimal(12,2)), `realized_pnl_today` (decimal(12,2)), `cumulative_pnl_usd` (decimal(12,2)), `total_trades` (int), `total_wins` (int), `win_rate` (decimal(5,2)) … +2 more

**Primary Key:** `id`
**Indexed:** `snapshot_time`

**Sample Rows:**
```json
{
  "id": 1,
  "snapshot_time": "2026-02-09 22:29:36",
  "total_value_usd": 9999.55,
  "cash_usd": 7999.5,
  "invested_usd": 2000.0,
  "open_positions": 4,
  "unrealized_pnl_usd": 0.05,
  "realized_pnl_today": 0.0,
  "cumulative_pnl_usd": 0.0,
  "total_trades": 0,
  "total_wins": 0,
  "win_rate": 0.0,
  "peak_value": 10000.0,
  "drawdown_pct": 0.0045
}
{
  "id": 2,
  "snapshot_time": "2026-02-09 22:49:13",
  "total_value_usd": 9999.93,
  "cash_usd": 7999.5,
  "invested_usd": 2000.0,
  "open_positions": 4,
  "unrealized_pnl_usd": 0.43,
  "realized_pnl_today": 0.0,
  "cumulative_pnl_usd": 0.0,
  "total_trades": 0,
  "total_wins": 0,
  "win_rate": 0.0,
  "peak_value": 10000.0,
  "drawdown_pct": 0.0007
}
```

**`snapshot_time` range:** 2026-02-09 22:29:36 → 2026-05-08 14:19:51

### 29. `gm_sec_13f_holdings` — ~2,084 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (14):** `id` (int), `cik` (varchar(20)), `fund_name` (varchar(200)), `ticker` (varchar(10)), `cusip` (varchar(9)), `name_of_issuer` (varchar(200)), `value_thousands` (bigint), `shares` (bigint), `filing_quarter` (varchar(10)), `filing_date` (date), `prev_shares` (bigint), `change_pct` (decimal(10,4)) … +2 more

**Primary Key:** `id`
**Indexed:** `cik`, `ticker`, `filing_quarter`, `change_type`

**Sample Rows:**
```json
{
  "id": 1,
  "cik": "0001336528",
  "fund_name": "Bridgewater Associates",
  "ticker": "GOOG",
  "cusip": "02079K107",
  "name_of_issuer": "ALPHABET INC",
  "value_thousands": 1540217750,
  "shares": 6324031,
  "filing_quarter": "Q3-2025",
  "filing_date": "2025-11-14",
  "prev_shares": 0,
  "change_pct": 0.0,
  "change_type": "new",
  "created_at": "2026-02-11 01:23:50"
}
{
  "id": 2,
  "cik": "0001336528",
  "fund_name": "Bridgewater Associates",
  "ticker": "GOOGL",
  "cusip": "02079K305",
  "name_of_issuer": "ALPHABET INC",
  "value_thousands": 1177569836,
  "shares": 4843973,
  "filing_quarter": "Q3-2025",
  "filing_date": "2025-11-14",
  "prev_shares": 0,
  "change_pct": 0.0,
  "change_type": "new",
  "created_at": "2026-02-11 01:23:50"
}
```

**`filing_date` range:** 2025-11-03 → 2026-02-17

**`created_at` range:** 2026-02-11 01:23:50 → 2026-03-22 06:17:11

### 30. `at_aggregation_runs` — ~1,847 rows (0MB + 0MB idx)
**Purpose:** Audit: Aggregation run metadata

**Columns (10):** `run_id` (char(36)), `started_at` (datetime), `finished_at` (datetime), `status` (enum('RUNNING','COMPLETED','FAILED')), `systems_loaded` (int), `raw_picks_count` (int), `consensus_count` (int), `regime_data` (json), `portfolio_drawdown` (decimal(10,4)), `source` (varchar(50))

**Primary Key:** `run_id`
**Indexed:** `started_at`, `status`

**`status` distribution:**
- `COMPLETED`: 24,269
- `RUNNING`: 558

**Sample Rows:**
```json
{
  "run_id": "000047cc-4c93-4c21-8993-af9a065dea5b",
  "started_at": "2026-04-03 01:54:13",
  "finished_at": "2026-04-03 01:54:14",
  "status": "COMPLETED",
  "systems_loaded": 1,
  "raw_picks_count": 5,
  "consensus_count": 5,
  "regime_data": "{\"source\": \"CryptoMLEdge\"}",
  "portfolio_drawdown": 0.0,
  "source": "aggregator"
}
{
  "run_id": "00033338-bb00-4755-b3cc-b01684ee3c61",
  "started_at": "2026-05-07 19:20:53",
  "finished_at": "2026-05-07 19:20:53",
  "status": "COMPLETED",
  "systems_loaded": 0,
  "raw_picks_count": 0,
  "consensus_count": 0,
  "regime_data": null,
  "portfolio_drawdown": 0.0,
  "source": "full_sync"
}
```

### 31. `gm_unified_picks` — ~1,846 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (36):** `id` (int), `source_system` (varchar(30)), `source_page` (varchar(100)), `source_id` (int), `source_table` (varchar(50)), `pick_date` (date), `pick_time` (datetime), `asset_type` (varchar(20)), `ticker` (varchar(30)), `asset_name` (varchar(200)), `direction` (varchar(10)), `algorithm_name` (varchar(100)) … +24 more

**Primary Key:** `id`
**Indexed:** `source_system`, `pick_date`, `asset_type`, `ticker`, `algorithm_name`, `confidence_score`, `status`

**`source_system` distribution:**
- `live_signal`: 1,656
- `consolidated`: 82
- `sports`: 69
- `meme`: 29
- `penny`: 6
- `edge`: 4

**`direction` distribution:**
- `SHORT`: 1,194
- `LONG`: 643
- `STRONG_BUY`: 9

**`status` distribution:**
- `sl_hit`: 664
- `max_hold`: 486
- `tp_hit`: 363
- `expired`: 272
- `open`: 61

**Sample Rows:**
```json
{
  "id": 1,
  "source_system": "consolidated",
  "source_page": "/findstocks/portfolio2/consolidated.html",
  "source_id": 1,
  "source_table": "consensus_tracked",
  "pick_date": "2026-02-10",
  "pick_time": "2026-02-10 13:00:42",
  "asset_type": "stock",
  "ticker": "AAPL",
  "asset_name": "Apple Inc",
  "direction": "LONG",
  "algorithm_name": "Cursor Genius, Blue Chip Growth, Alpha Factor Quality, Alpha Factor Earnings, Alpha Factor Momentum,",
  "algo_count": 7,
  "entry_price": 278.12,
  "target_price": 300.3696,
  "stop_loss_price": 266.9952,
  "target_pct": 8.0,
  "stop_loss_pct": 4.0,
  "confidence_score": 544,
  "hold_period_hours": 0,
  "metadata_json": null,
  "status": "sl_hit",
  "current_price": 261.73,
  "current_return_pct": -5.8931,
  "peak_price": 278.12,
  "trough_price": 261.73,
  "exit_price": 261.73,
  "exit_date": "2026-02-13 02:08:12",
  "exit_reason": "stop_loss_hit",
  "final_return_pct": -5.8931,
  "hold_hours": 61.13,
  "dividends_earned": 0.0,
  "earnings_events": 0,
  "total_return_pct": -5.8931,
  "created_at": "2026-02-10 23:52:57",
  "updated_at": "2026-02-13 02:08:12"
}
{
  "id": 2,
  "source_system": "consolidated",
  "source_page": "/findstocks/portfolio2/consolidated.html",
  "source_id": 2,
  "source_table": "consensus_tracked",
  "pick_date": "2026-02-10",
  "pick_time": "2026-02-10 13:00:42",
  "asset_type": "stock",
  "ticker": "GM",
  "asset_name": "General Motors Company",
  "direction": "LONG",
  "algorithm_name": "Technical Momentum, Composite Rating",
  "algo_count": 2,
  "entry_price": 84.24,
  "target_price": 90.9792,
  "stop_loss_price": 80.8704,
  "target_pct": 8.0,
  "stop_loss_pct": 4.0,
  "confidence_score": 175,
  "hold_period_hours": 0,
  "metadata_json": null,
  "status": "sl_hit",
  "current_price": 79.93,
  "current_return_pct": -5.1163,
  "peak_price": 84.24,
  "trough_price": 79.93,
  "exit_price": 79.93,
  "exit_date": "2026-02-13 02:08:12",
  "exit_reason": "stop_loss_hit",
  "final_return_pct": -5.1163,
  "hold_hours": 61.13,
  "dividends_earned": 0.0,
  "earnings_events": 0,
  "total_return_pct": -5.1163,
  "created_at": "2026-02-10 23:52:57",
  "updated_at": "2026-02-13 02:08:12"
}
```

**`pick_date` range:** 2026-02-10 → 2026-02-16

**`pick_time` range:** 2026-02-10 12:15:17 → 2026-02-16 18:39:50

### 32. `kelly_sizing_log` — ~1,702 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (13):** `id` (int), `source_table` (varchar(30)), `algorithm_name` (varchar(100)), `calc_date` (date), `win_rate` (decimal(5,2)), `avg_win_pct` (decimal(10,4)), `avg_loss_pct` (decimal(10,4)), `full_kelly` (decimal(8,4)), `half_kelly` (decimal(8,4)), `quarter_kelly` (decimal(8,4)), `recommended_pct` (decimal(8,4)), `trades_used` (int) … +1 more

**Primary Key:** `id`
**Indexed:** `source_table`, `algorithm_name`, `calc_date`

**Sample Rows:**
```json
{
  "id": 15,
  "source_table": "stock_picks",
  "algorithm_name": "Blue Chip Growth",
  "calc_date": "2026-02-10",
  "win_rate": 80.0,
  "avg_win_pct": 5.6037,
  "avg_loss_pct": 3.7951,
  "full_kelly": 0.25,
  "half_kelly": 0.125,
  "quarter_kelly": 0.0625,
  "recommended_pct": 0.0625,
  "trades_used": 25,
  "created_at": "2026-02-10 03:50:56"
}
{
  "id": 16,
  "source_table": "stock_picks",
  "algorithm_name": "Composite Rating",
  "calc_date": "2026-02-10",
  "win_rate": 50.0,
  "avg_win_pct": 5.981,
  "avg_loss_pct": 6.5212,
  "full_kelly": 0.0,
  "half_kelly": 0.0,
  "quarter_kelly": 0.0,
  "recommended_pct": 0.0,
  "trades_used": 12,
  "created_at": "2026-02-10 03:50:56"
}
```

**`calc_date` range:** 2026-02-10 → 2026-04-27

**`created_at` range:** 2026-02-10 03:50:56 → 2026-04-27 23:54:28

### 33. `at_permutation_picks` — ~1,514 rows (0MB + 0MB idx)
**Purpose:** Picks: Storage

**Columns (12):** `id` (int), `snapshot_id` (int), `permutation_id` (varchar(100)), `symbol` (varchar(50)), `direction` (enum('LONG','SHORT')), `agreement_count` (int), `source_systems` (json), `confidence` (decimal(5,4)), `pnl_pct` (decimal(10,4)), `exit_reason` (varchar(50)), `pick_status` (enum('ACTIVE','CLOSED')), `recorded_at` (datetime)

**Primary Key:** `id`
**Indexed:** `permutation_id`, `symbol`, `pick_status`

**`direction` distribution:**
- `LONG`: 1,340
- `SHORT`: 274

**Sample Rows:**
```json
{
  "id": 1,
  "snapshot_id": 1,
  "permutation_id": "solo_battleground",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "agreement_count": 1,
  "source_systems": "[\"battleground\"]",
  "confidence": 0.5882,
  "pnl_pct": 0.0,
  "exit_reason": null,
  "pick_status": "ACTIVE",
  "recorded_at": "2026-03-08 23:41:11"
}
{
  "id": 2,
  "snapshot_id": 1,
  "permutation_id": "solo_battleground",
  "symbol": "BTCUSDT",
  "direction": "SHORT",
  "agreement_count": 1,
  "source_systems": "[\"battleground\"]",
  "confidence": 0.5724,
  "pnl_pct": 0.0,
  "exit_reason": null,
  "pick_status": "ACTIVE",
  "recorded_at": "2026-03-08 23:41:11"
}
```

### 34. `lm_position_sizing` — ~1,409 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (13):** `id` (int), `date` (datetime), `algorithm_name` (varchar(100)), `kelly_base` (decimal(8,4)), `vol_scalar` (decimal(8,2)), `regime_modifier` (decimal(8,2)), `decay_weight` (decimal(8,2)), `final_size_pct` (decimal(8,2)), `dollar_amount` (decimal(12,2)), `algo_sharpe_30d` (decimal(8,3)), `is_decaying` (tinyint), `regime_composite` (decimal(6,2)) … +1 more

**Primary Key:** `id`
**Indexed:** `date`, `algorithm_name`

**Sample Rows:**
```json
{
  "id": 9,
  "date": "2026-02-13 21:40:25",
  "algorithm_name": "Consensus",
  "kelly_base": 0.05,
  "vol_scalar": 1.5,
  "regime_modifier": 0.89,
  "decay_weight": 0.25,
  "final_size_pct": 1.67,
  "dollar_amount": 164.9,
  "algo_sharpe_30d": -0.5,
  "is_decaying": 1,
  "regime_composite": 53.7,
  "created_at": "2026-02-13 21:40:25"
}
{
  "id": 3,
  "date": "2026-02-12 21:37:24",
  "algorithm_name": "Consensus",
  "kelly_base": 0.05,
  "vol_scalar": 1.5,
  "regime_modifier": 0.95,
  "decay_weight": 1.0,
  "final_size_pct": 7.13,
  "dollar_amount": 709.72,
  "algo_sharpe_30d": 0.5,
  "is_decaying": 0,
  "regime_composite": 53.7,
  "created_at": "2026-02-12 21:37:24"
}
```

**`date` range:** 2026-02-12 21:37:24 → 2026-05-07 21:12:26

**`created_at` range:** 2026-02-12 21:37:24 → 2026-05-07 21:12:26

### 35. `at_discord_sent` — ~1,305 rows (0MB + 0MB idx)
**Purpose:** Audit: Discord sent notifications

**Columns (17):** `id` (int), `channel` (varchar(100)), `webhook_name` (varchar(100)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `direction` (enum('LONG','SHORT')), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `confidence` (decimal(5,4)), `strategy` (varchar(200)), `source_system` (varchar(100)) … +5 more

**Primary Key:** `id`
**Indexed:** `channel`, `symbol`, `asset_class`, `dedup_key`, `sent_at`

**`channel` distribution:**
- `consensus`: 3,992
- `fresh-picks`: 325

**`asset_class` distribution:**
- `CRYPTO`: 3,824
- `EQUITY`: 235
- `MEMECOIN`: 181
- `FOREX`: 36
- `PENNY_STOCK`: 15
- `FUTURES`: 15
- `ETF`: 11

**`direction` distribution:**
- `LONG`: 4,155
- `SHORT`: 162

**`strategy` distribution:**
- `None`: 4,317

**Sample Rows:**
```json
{
  "id": 1,
  "channel": "consensus",
  "webhook_name": null,
  "symbol": "ADAUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 0.2646,
  "take_profit": null,
  "stop_loss": null,
  "confidence": null,
  "strategy": null,
  "source_system": "cross_aggregator",
  "dedup_key": "ADAUSDT__LONG__0.2646",
  "consensus_pick_id": null,
  "sent_at": "2026-03-27 18:59:37",
  "discord_message_id": null,
  "sent_payload": null
}
{
  "id": 2,
  "channel": "consensus",
  "webhook_name": null,
  "symbol": "BTCUSDT",
  "asset_class": "CRYPTO",
  "direction": "LONG",
  "entry_price": 70180.1,
  "take_profit": null,
  "stop_loss": null,
  "confidence": null,
  "strategy": null,
  "source_system": "cross_aggregator",
  "dedup_key": "BTCUSDT__LONG__70180.1",
  "consensus_pick_id": null,
  "sent_at": "2026-03-27 18:59:37",
  "discord_message_id": null,
  "sent_payload": null
}
```

**`sent_at` range:** 2026-03-27 03:54:40 → 2026-05-08 12:03:08

### 36. `at_incubator_backtest_results` — ~1,210 rows (0MB + 0MB idx)
**Purpose:** Backtesting

**Columns (20):** `id` (int), `perm_id` (varchar(20)), `archetype` (varchar(80)), `symbol` (varchar(30)), `params_json` (json), `total_trades` (int), `wins` (int), `losses` (int), `win_rate` (decimal(6,4)), `sharpe` (decimal(10,4)), `sortino` (decimal(10,4)), `max_drawdown` (decimal(10,6)) … +8 more

**Primary Key:** `id`
**Indexed:** `perm_id`, `symbol`, `sharpe`

**Sample Rows:**
```json
{
  "id": 1,
  "perm_id": "9ce31cab42ed",
  "archetype": "rsi_mean_reversion",
  "symbol": "BTC-USD",
  "params_json": "{\"atr_period\": 14, \"rsi_period\": 3, \"sl_atr_mult\": 2.189607, \"tp_atr_mult\": 2.920508, \"max_hold_days\": 3, \"use_sma_filter\": true, \"sma_filter_period\":...",
  "total_trades": 1,
  "wins": 1,
  "losses": 0,
  "win_rate": 1.0,
  "sharpe": 0.0,
  "sortino": 0.0,
  "max_drawdown": 0.0,
  "profit_factor": 99.0,
  "total_return": 0.019354,
  "avg_trade_pnl": 0.020854,
  "avg_hold_bars": 3.0,
  "slippage_pct": 0.0,
  "commission_pct": 0.0,
  "backtest_type": "fast",
  "created_at": "2026-03-10 06:18:23"
}
{
  "id": 2,
  "perm_id": "9ce31cab42ed",
  "archetype": "rsi_mean_reversion",
  "symbol": "ETH-USD",
  "params_json": "{\"atr_period\": 14, \"rsi_period\": 3, \"sl_atr_mult\": 2.189607, \"tp_atr_mult\": 2.920508, \"max_hold_days\": 3, \"use_sma_filter\": true, \"sma_filter_period\":...",
  "total_trades": 2,
  "wins": 2,
  "losses": 0,
  "win_rate": 1.0,
  "sharpe": 80.191,
  "sortino": 81.587,
  "max_drawdown": 0.0,
  "profit_factor": 99.0,
  "total_return": 0.172335,
  "avg_trade_pnl": 0.087667,
  "avg_hold_bars": 3.0,
  "slippage_pct": 0.0,
  "commission_pct": 0.0,
  "backtest_type": "fast",
  "created_at": "2026-03-10 06:18:23"
}
```

**`created_at` range:** 2026-03-10 06:18:23 → 2026-05-08 06:44:23

### 37. `strategy_registry` — ~1,187 rows (0MB + 0MB idx)
**Purpose:** Strategy: Genome registry

**Columns (16):** `id` (int), `strategy_id` (varchar(100)), `strategy_name` (varchar(200)), `system_name` (varchar(100)), `section_name` (varchar(200)), `module_file` (varchar(300)), `asset_class` (varchar(20)), `strategy_type` (varchar(50)), `win_rate` (varchar(30)), `sharpe` (varchar(30)), `source_ref` (varchar(200)), `is_banned` (tinyint(1)) … +4 more

**Primary Key:** `id`
**Indexed:** `strategy_id`, `system_name`, `asset_class`, `is_banned`

**`asset_class` distribution:**
- `MULTI`: 695
- `CRYPTO`: 471
- `EQUITY`: 17
- `FOREX`: 12

**Sample Rows:**
```json
{
  "id": 1,
  "strategy_id": "adaptive_momentum",
  "strategy_name": "Adaptive Momentum",
  "system_name": "baby_strategies",
  "section_name": "1. Baby Strategies — 77",
  "module_file": "baby_strategies/adaptive_momentum.py",
  "asset_class": "CRYPTO",
  "strategy_type": "Trend / Adaptive",
  "win_rate": null,
  "sharpe": null,
  "source_ref": null,
  "is_banned": 0,
  "is_active": 1,
  "notes": null,
  "created_at": "2026-03-04 18:00:46",
  "updated_at": "2026-03-05 04:14:14"
}
{
  "id": 2,
  "strategy_id": "adx_range_mean_reversion",
  "strategy_name": "Adx Range Mean Reversion",
  "system_name": "baby_strategies",
  "section_name": "1. Baby Strategies — 77",
  "module_file": "baby_strategies/adx_range_mean_reversion.py",
  "asset_class": "CRYPTO",
  "strategy_type": "Mean Reversion",
  "win_rate": null,
  "sharpe": null,
  "source_ref": null,
  "is_banned": 0,
  "is_active": 1,
  "notes": null,
  "created_at": "2026-03-04 18:00:46",
  "updated_at": "2026-03-05 04:14:14"
}
```

**`created_at` range:** 2026-03-04 18:00:46 → 2026-04-02 15:27:00

**`updated_at` range:** 2026-03-05 04:14:14 → 2026-04-04 19:51:07

### 38. `fxp_pair_picks` — ~1,184 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (13):** `id` (int), `symbol` (varchar(20)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_price` (decimal(12,6)), `direction` (varchar(10)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)) … +1 more

**Primary Key:** `id`
**Indexed:** `symbol`, `algorithm_name`, `pick_date`, `pick_hash`

**`direction` distribution:**
- `LONG`: 740
- `SHORT`: 444

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "EURUSD",
  "algorithm_id": 1,
  "algorithm_name": "FX Trend Following",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_price": 1.0845,
  "direction": "LONG",
  "score": 82,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "1d",
  "pick_hash": ""
}
{
  "id": 2,
  "symbol": "EURUSD",
  "algorithm_id": 2,
  "algorithm_name": "FX Momentum",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_price": 1.082,
  "direction": "LONG",
  "score": 75,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "4h",
  "pick_hash": ""
}
```

**`pick_date` range:** 2026-02-09 → 2026-05-07

**`pick_time` range:** 2026-02-09 16:00:00 → 2026-05-07 16:00:00

### 39. `at_large_backtest_results` — ~1,061 rows (0MB + 0MB idx)
**Purpose:** Backtesting

**Columns (21):** `id` (int), `perm_id` (varchar(20)), `archetype` (varchar(80)), `symbol` (varchar(30)), `params_json` (json), `total_trades` (int), `wins` (int), `losses` (int), `win_rate` (decimal(6,4)), `sharpe` (decimal(10,4)), `sortino` (decimal(10,4)), `max_drawdown` (decimal(10,6)) … +9 more

**Primary Key:** `id`
**Indexed:** `perm_id`, `sharpe`

**Sample Rows:**
```json
{
  "id": 1,
  "perm_id": "f1d11123299e",
  "archetype": "rsi_mean_reversion",
  "symbol": "BTC-USD",
  "params_json": "{\"atr_period\": 20, \"rsi_period\": 3, \"sl_atr_mult\": 1.892991, \"tp_atr_mult\": 2.645195, \"max_hold_days\": 3, \"use_sma_filter\": false, \"sma_filter_period\"...",
  "total_trades": 5,
  "wins": 3,
  "losses": 2,
  "win_rate": 0.6,
  "sharpe": 4.461,
  "sortino": 7.558,
  "max_drawdown": -0.072273,
  "profit_factor": 2.19,
  "total_return": 0.086022,
  "avg_trade_pnl": 0.017204,
  "avg_hold_bars": 3.0,
  "slippage_pct": 0.0,
  "commission_pct": 0.0,
  "equity_curve_json": null,
  "trade_log_json": null,
  "created_at": "2026-03-10 06:18:26"
}
{
  "id": 2,
  "perm_id": "f1d11123299e",
  "archetype": "rsi_mean_reversion",
  "symbol": "ETH-USD",
  "params_json": "{\"atr_period\": 20, \"rsi_period\": 3, \"sl_atr_mult\": 1.892991, \"tp_atr_mult\": 2.645195, \"max_hold_days\": 3, \"use_sma_filter\": false, \"sma_filter_period\"...",
  "total_trades": 7,
  "wins": 6,
  "losses": 1,
  "win_rate": 0.8571,
  "sharpe": 7.918,
  "sortino": 7.918,
  "max_drawdown": -0.116201,
  "profit_factor": 3.218,
  "total_return": 0.257733,
  "avg_trade_pnl": 0.036819,
  "avg_hold_bars": 2.9,
  "slippage_pct": 0.0,
  "commission_pct": 0.0,
  "equity_curve_json": null,
  "trade_log_json": null,
  "created_at": "2026-03-10 06:18:26"
}
```

**`created_at` range:** 2026-03-10 06:18:26 → 2026-05-08 06:44:42

### 40. `penny_picks` — ~1,029 rows (0MB + 0MB idx)
**Purpose:** Penny Stocks: Pick data

**Columns (41):** `id` (int), `pick_date` (date), `symbol` (varchar(20)), `name` (varchar(200)), `price` (decimal(10,4)), `composite_score` (decimal(5,2)), `rating` (varchar(20)), `market_cap` (bigint), `exchange_name` (varchar(30)), `country` (varchar(5)), `rrsp_eligible` (tinyint), `avg_volume` (int) … +29 more

**Primary Key:** `id`
**Indexed:** `pick_date`, `symbol`, `composite_score`, `rating`, `status`

**`status` distribution:**
- `active`: 698
- `closed`: 331

**Sample Rows:**
```json
{
  "id": 1,
  "pick_date": "2026-02-11",
  "symbol": "SAM.TO",
  "name": "STARCORE INTERNATIONAL MINES LT",
  "price": 1.18,
  "composite_score": 74.1,
  "rating": "BUY",
  "market_cap": 106038952,
  "exchange_name": "TSX",
  "country": "CA",
  "rrsp_eligible": 1,
  "avg_volume": 358033,
  "stop_loss_pct": 15.0,
  "take_profit_pct": 30.0,
  "max_hold_days": 90,
  "position_size_pct": 1.5,
  "health_score": 79.7,
  "momentum_score": 100.0,
  "volume_score": 43.1,
  "technical_score": 75.0,
  "earnings_score": 50.0,
  "smart_money_score": 60.0,
  "quality_score": 47.8,
  "z_score": 12.15,
  "f_score": 4,
  "current_ratio": 4.76,
  "rsi": 47.8,
  "ema_alignment": 3,
  "rvol": 1.53,
  "mom_3m": 68.3,
  "mom_6m": 221.2,
  "inst_pct": 0.0,
  "short_pct": 0.4,
  "ann_volatility": 117.9,
  "status": "active",
  "current_price": 1.03,
  "current_return_pct": -12.71,
  "exit_price": 0.0,
  "exit_date": null,
  "exit_reason": "",
  "created_at": "2026-02-11 19:12:36"
}
{
  "id": 2,
  "pick_date": "2026-02-11",
  "symbol": "TRX",
  "name": "TRX Gold Corporation",
  "price": 1.705,
  "composite_score": 73.76,
  "rating": "BUY",
  "market_cap": 497924160,
  "exchange_name": "NYSE American",
  "country": "US",
  "rrsp_eligible": 1,
  "avg_volume": 5377447,
  "stop_loss_pct": 15.0,
  "take_profit_pct": 30.0,
  "max_hold_days": 90,
  "position_size_pct": 1.5,
  "health_score": 82.2,
  "momentum_score": 66.2,
  "volume_score": 98.5,
  "technical_score": 75.0,
  "earnings_score": 75.0,
  "smart_money_score": 50.0,
  "quality_score": 54.3,
  "z_score": 6.39,
  "f_score": 5,
  "current_ratio": 4.96,
  "rsi": 63.7,
  "ema_alignment": 3,
  "rvol": 2.91,
  "mom_3m": 26.3,
  "mom_6m": 182.4,
  "inst_pct": 3.0,
  "short_pct": 3.5,
  "ann_volatility": 84.3,
  "status": "closed",
  "current_price": 1.38,
  "current_return_pct": -19.06,
  "exit_price": 1.38,
  "exit_date": "2026-03-20",
  "exit_reason": "stop_loss",
  "created_at": "2026-02-11 19:12:36"
}
```

**`pick_date` range:** 2026-02-11 → 2026-04-27

**`exit_date` range:** 2026-03-03 → 2026-04-27

### 41. `cr_pair_picks` — ~952 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (14):** `id` (int), `symbol` (varchar(20)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_price` (decimal(18,8)), `direction` (varchar(10)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)) … +2 more

**Primary Key:** `id`
**Indexed:** `symbol`, `algorithm_name`, `pick_date`, `direction`, `pick_hash`

**`direction` distribution:**
- `LONG`: 816
- `SHORT`: 136

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "BTCUSD",
  "algorithm_id": 7,
  "algorithm_name": "CR Halving Cycle",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 12:00:00",
  "entry_price": 97500.0,
  "direction": "LONG",
  "score": 88,
  "rating": "Strong Buy",
  "risk_level": "Medium",
  "timeframe": "6m",
  "pick_hash": "",
  "rationale_json": ""
}
{
  "id": 2,
  "symbol": "BTCUSD",
  "algorithm_id": 3,
  "algorithm_name": "CR Trend Following",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 12:00:00",
  "entry_price": 97500.0,
  "direction": "LONG",
  "score": 82,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "3m",
  "pick_hash": "",
  "rationale_json": ""
}
```

**`pick_date` range:** 2026-02-09 → 2026-05-07

**`pick_time` range:** 2026-02-09 12:00:00 → 2026-05-07 12:00:00

### 42. `daytrader_sim_trades` — ~838 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (14):** `id` (int), `sim_date` (date), `ticker` (varchar(10)), `strategy_name` (varchar(100)), `source_table` (varchar(30)), `entry_price` (decimal(12,4)), `exit_price` (decimal(12,4)), `shares` (int), `invested` (decimal(12,2)), `pnl` (decimal(12,2)), `return_pct` (decimal(10,4)), `exit_reason` (varchar(50)) … +2 more

**Primary Key:** `id`
**Indexed:** `sim_date`, `ticker`, `algo_version`

**Sample Rows:**
```json
{
  "id": 1,
  "sim_date": "2026-02-09",
  "ticker": "META",
  "strategy_name": "Momentum Continuation",
  "source_table": "miracle_picks3",
  "entry_price": 680.99,
  "exit_price": 680.99,
  "shares": 1,
  "invested": 680.99,
  "pnl": 0.0,
  "return_pct": 0.0,
  "exit_reason": "no_data",
  "algo_version": "original",
  "created_at": "2026-02-09 20:41:33"
}
{
  "id": 2,
  "sim_date": "2026-02-09",
  "ticker": "AMZN",
  "strategy_name": "Mean Reversion Sniper",
  "source_table": "miracle_picks2",
  "entry_price": 210.2,
  "exit_price": 210.2,
  "shares": 1,
  "invested": 210.2,
  "pnl": 0.0,
  "return_pct": 0.0,
  "exit_reason": "no_data",
  "algo_version": "original",
  "created_at": "2026-02-09 20:41:33"
}
```

**`sim_date` range:** 2026-02-09 → 2026-04-27

**`created_at` range:** 2026-02-09 20:41:33 → 2026-04-27 23:57:00

### 43. `stock_dividends` — ~831 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `ticker` (varchar(10)), `ex_date` (date), `payment_date` (date), `amount` (decimal(10,6)), `frequency` (varchar(20)), `source` (varchar(20)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `ticker`, `ex_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "ex_date": "2024-02-09",
  "payment_date": null,
  "amount": 0.24,
  "frequency": "quarterly",
  "source": "yahoo_v8",
  "updated_at": "2026-02-09 20:34:03"
}
{
  "id": 2,
  "ticker": "AAPL",
  "ex_date": "2024-05-10",
  "payment_date": null,
  "amount": 0.25,
  "frequency": "quarterly",
  "source": "yahoo_v8",
  "updated_at": "2026-04-27 23:50:09"
}
```

**`ex_date` range:** 2024-02-09 → 2026-04-22

### 44. `alpha_refresh_log` — ~731 rows (0MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (8):** `id` (int), `refresh_date` (datetime), `step` (varchar(100)), `status` (varchar(20)), `details` (text), `duration_seconds` (int), `tickers_processed` (int), `errors_count` (int)

**Primary Key:** `id`
**Indexed:** `refresh_date`, `step`

**`status` distribution:**
- `completed`: 665
- `started`: 66

**Sample Rows:**
```json
{
  "id": 1,
  "refresh_date": "2026-02-09 18:22:48",
  "step": "fetch_macro",
  "status": "completed",
  "details": "{\"macro\":{\"fetched\":5,\"days_inserted\":126}}",
  "duration_seconds": 0,
  "tickers_processed": 0,
  "errors_count": 0
}
{
  "id": 2,
  "refresh_date": "2026-02-09 18:23:03",
  "step": "fetch_fundamentals",
  "status": "completed",
  "details": "{\"fundamentals\":{\"fetched\":0,\"total\":52}}",
  "duration_seconds": 0,
  "tickers_processed": 0,
  "errors_count": 3
}
```

**`refresh_date` range:** 2026-02-09 18:22:48 → 2026-04-27 21:55:28

### 45. `gm_sec_insider_trades` — ~714 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (17):** `id` (int), `cik` (varchar(20)), `ticker` (varchar(10)), `filer_name` (varchar(200)), `filer_title` (varchar(100)), `transaction_date` (date), `transaction_type` (varchar(10)), `shares` (decimal(18,4)), `price_per_share` (decimal(12,4)), `total_value` (decimal(18,2)), `shares_owned_after` (decimal(18,4)), `filing_date` (date) … +5 more

**Primary Key:** `id`
**Indexed:** `ticker`, `transaction_date`, `transaction_type`, `filing_date`, `accession_number`

**Sample Rows:**
```json
{
  "id": 1,
  "cik": "0000320193",
  "ticker": "AAPL",
  "filer_name": "WAGNER SUSAN",
  "filer_title": "",
  "transaction_date": "2026-02-01",
  "transaction_type": "M",
  "shares": 1255.0,
  "price_per_share": 0.0,
  "total_value": 0.0,
  "shares_owned_after": 63746.0,
  "filing_date": "2026-02-03",
  "accession_number": "0001059235-26-000002",
  "is_director": 1,
  "is_officer": 0,
  "is_ten_pct_owner": 0,
  "created_at": "2026-02-11 01:18:29"
}
{
  "id": 2,
  "cik": "0000320193",
  "ticker": "AAPL",
  "filer_name": "SUGAR RONALD D",
  "filer_title": "",
  "transaction_date": "2026-02-01",
  "transaction_type": "M",
  "shares": 1255.0,
  "price_per_share": 0.0,
  "total_value": 0.0,
  "shares_owned_after": 110566.0,
  "filing_date": "2026-02-03",
  "accession_number": "0001216519-26-000002",
  "is_director": 1,
  "is_officer": 0,
  "is_ten_pct_owner": 0,
  "created_at": "2026-02-11 01:18:29"
}
```

**`transaction_date` range:** 2025-03-04 → 2027-01-25

**`filing_date` range:** 2026-01-12 → 2026-05-07

### 46. `audit_trails` — ~684 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `asset_class` (varchar(50)), `symbol` (varchar(50)), `pick_timestamp` (datetime), `generation_source` (varchar(100)), `reasons` (text), `supporting_data` (text), `pick_details` (text), `formatted_for_ai` (text)

**Primary Key:** `id`
**Indexed:** `asset_class`

**`asset_class` distribution:**
- `STOCKS`: 684

**Sample Rows:**
```json
{
  "id": 1,
  "asset_class": "STOCKS",
  "symbol": "KO",
  "pick_timestamp": "2026-02-13 21:21:47",
  "generation_source": "stock_picks - Alpha Factor Safe Bets",
  "reasons": "Algorithm: Alpha Factor Safe Bets. Score: 59. Rating: Speculative Buy. Risk: Low",
  "supporting_data": "{\"strategy\":\"Alpha Factor Safe Bets\",\"factor_scores\":{\"Low Vol\":82.1,\"Momentum\":53.1,\"Earnings\":47.6,\"Quality\":47.2,\"Value\":44.5,\"Growth\":30.4},\"compo...",
  "pick_details": "{\"entry_price\":79,\"score\":59,\"rating\":\"Speculative Buy\",\"risk_level\":\"Low\",\"timeframe\":\"6m\"}",
  "formatted_for_ai": "Analyze this stock pick:\nSymbol: KO\nAlgorithm: Alpha Factor Safe Bets\nScore: 59/100\nRating: Speculative Buy\nEntry: $79.0000\nRisk: Low\nTimeframe: 6m\nIn..."
}
{
  "id": 2,
  "asset_class": "STOCKS",
  "symbol": "ABBV",
  "pick_timestamp": "2026-02-13 21:21:47",
  "generation_source": "stock_picks - Alpha Factor Safe Bets",
  "reasons": "Algorithm: Alpha Factor Safe Bets. Score: 59. Rating: Speculative Buy. Risk: Low",
  "supporting_data": "{\"strategy\":\"Alpha Factor Safe Bets\",\"factor_scores\":{\"Quality\":74,\"Low Vol\":60.1,\"Momentum\":54.8,\"Growth\":44.1,\"Value\":40.3,\"Earnings\":38.9},\"composi...",
  "pick_details": "{\"entry_price\":227.5,\"score\":59,\"rating\":\"Speculative Buy\",\"risk_level\":\"Low\",\"timeframe\":\"6m\"}",
  "formatted_for_ai": "Analyze this stock pick:\nSymbol: ABBV\nAlgorithm: Alpha Factor Safe Bets\nScore: 59/100\nRating: Speculative Buy\nEntry: $227.5000\nRisk: Low\nTimeframe: 6m..."
}
```

**`pick_timestamp` range:** 2026-02-02 09:30:00 → 2026-02-17 21:58:35

### 47. `ps_history` — ~684 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `pair` (varchar(30)), `predictability_score` (float), `hurst_exponent` (float), `computed_at` (datetime)

**Primary Key:** `id`
**Indexed:** `pair`

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "XXBTZUSD",
  "predictability_score": 53.0,
  "hurst_exponent": 0.5776,
  "computed_at": "2026-02-14 20:32:42"
}
{
  "id": 2,
  "pair": "XETHZUSD",
  "predictability_score": 44.1,
  "hurst_exponent": 0.5658,
  "computed_at": "2026-02-14 20:32:42"
}
```

### 48. `cw_scan_log` — ~666 rows (4MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `scan_id` (varchar(20)), `pair` (varchar(30)), `price` (double), `score` (int), `factors_json` (text), `verdict` (varchar(20)), `chg_24h` (double), `vol_usd_24h` (double), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `scan_id`, `created_at`

**Sample Rows:**
```json
{
  "id": 24458,
  "scan_id": "20260507070657",
  "pair": "DOT_USDT",
  "price": 1.3291,
  "score": 62,
  "factors_json": "{\"multi_timeframe_momentum\":{\"score\":20,\"max\":20,\"mom_4h\":1.69,\"mom_1h\":1.34},\"volume_surge\":{\"score\":0,\"max\":20,\"ratio\":0.1},\"rsi_sweet_spot\":{\"score...",
  "verdict": "SKIP",
  "chg_24h": 1.61,
  "vol_usd_24h": 144055.4,
  "created_at": "2026-05-07 07:06:57"
}
{
  "id": 24459,
  "scan_id": "20260507070657",
  "pair": "ARB_USDT",
  "price": 0.1283,
  "score": 61,
  "factors_json": "{\"multi_timeframe_momentum\":{\"score\":20,\"max\":20,\"mom_4h\":2.15,\"mom_1h\":1.02},\"volume_surge\":{\"score\":0,\"max\":20,\"ratio\":0.13},\"rsi_sweet_spot\":{\"scor...",
  "verdict": "SKIP",
  "chg_24h": 5.86,
  "vol_usd_24h": 95981.03,
  "created_at": "2026-05-07 07:06:57"
}
```

**`created_at` range:** 2026-05-01 18:28:20 → 2026-05-08 12:35:39

### 49. `miracle_audit2` — ~659 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema2",
  "details": "DayTrades Miracle Claude schema created",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 18:51:10"
}
{
  "id": 2,
  "action_type": "scan",
  "details": "Scanned 67 tickers, found 23 signals, saved 20 picks",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 18:51:50"
}
```

**`created_at` range:** 2026-02-09 18:51:10 → 2026-05-07 23:54:20

### 50. `miracle_picks3` — ~644 rows (0MB + 0MB idx)
**Purpose:** Picks: Storage

**Columns (27):** `id` (int), `ticker` (varchar(10)), `company_name` (varchar(200)), `strategy_name` (varchar(100)), `scan_date` (date), `scan_time` (datetime), `entry_price` (decimal(12,4)), `stop_loss_price` (decimal(12,4)), `take_profit_price` (decimal(12,4)), `stop_loss_pct` (decimal(5,2)), `take_profit_pct` (decimal(5,2)), `score` (int) … +15 more

**Primary Key:** `id`
**Indexed:** `ticker`, `strategy_name`, `scan_date`, `score`, `outcome`, `pick_hash`

**`direction` distribution:**
- `LONG`: 644

**`outcome` distribution:**
- `lost`: 344
- `won`: 258
- `pending`: 42

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "META",
  "company_name": "Meta Platforms",
  "strategy_name": "Momentum Continuation",
  "scan_date": "2026-02-09",
  "scan_time": "2026-02-09 18:52:46",
  "entry_price": 680.99,
  "stop_loss_price": 659.5388,
  "take_profit_price": 743.9816,
  "stop_loss_pct": 3.15,
  "take_profit_pct": 9.25,
  "score": 78,
  "confidence": "Very Strong",
  "direction": "LONG",
  "signals_json": "{\"sma20\":660.09,\"sma50\":659.56,\"pullback_dist\":0.2}",
  "is_cdr": 1,
  "is_canadian": 0,
  "questrade_buy_fee": 0.0,
  "questrade_sell_fee": 0.0,
  "net_profit_if_tp": 62.99,
  "risk_reward_ratio": 2.94,
  "outcome": "lost",
  "outcome_price": 659.5388,
  "outcome_pct": -3.15,
  "outcome_date": "2026-02-11",
  "outcome_reason": "stop_loss",
  "pick_hash": "c6c77a6e46dd9ab7d8c28340f316fe9e"
}
{
  "id": 2,
  "ticker": "INTC",
  "company_name": "Intel Corp",
  "strategy_name": "CDR Zero-Fee Priority",
  "scan_date": "2026-02-09",
  "scan_time": "2026-02-09 18:52:46",
  "entry_price": 51.16,
  "stop_loss_price": 49.881,
  "take_profit_price": 53.718,
  "stop_loss_pct": 2.5,
  "take_profit_pct": 5.0,
  "score": 75,
  "confidence": "Very Strong",
  "direction": "LONG",
  "signals_json": "{\"rsi\":53.95,\"sma20\":48.23,\"vol_ratio\":0.46}",
  "is_cdr": 1,
  "is_canadian": 0,
  "questrade_buy_fee": 0.0,
  "questrade_sell_fee": 0.0,
  "net_profit_if_tp": 51.16,
  "risk_reward_ratio": 2.0,
  "outcome": "lost",
  "outcome_price": 49.881,
  "outcome_pct": -2.5,
  "outcome_date": "2026-02-11",
  "outcome_reason": "stop_loss",
  "pick_hash": "450bfea15f5fdbe42a0ec9feb0189674"
}
```

**`scan_date` range:** 2026-02-09 → 2026-05-07

**`scan_time` range:** 2026-02-09 18:52:46 → 2026-05-07 23:54:26

### 51. `challenge_200_trades` — ~620 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (17):** `id` (int), `challenge_date` (date), `mode` (varchar(20)), `ticker` (varchar(10)), `company_name` (varchar(100)), `direction` (varchar(10)), `entry_price` (decimal(12,4)), `exit_price` (decimal(12,4)), `shares` (decimal(12,4)), `invested` (decimal(12,2)), `pnl` (decimal(12,2)), `return_pct` (decimal(10,4)) … +5 more

**Primary Key:** `id`
**Indexed:** `challenge_date`, `ticker`

**`direction` distribution:**
- `LONG`: 620

**Sample Rows:**
```json
{
  "id": 1,
  "challenge_date": "2026-02-10",
  "mode": "consensus",
  "ticker": "XOM",
  "company_name": "Exxon Mobil Corporation",
  "direction": "LONG",
  "entry_price": 149.05,
  "exit_price": 149.05,
  "shares": 6.7092,
  "invested": 1000.01,
  "pnl": 2.73,
  "return_pct": 0.2727,
  "consensus_count": 11,
  "consensus_score": 1079.0,
  "exit_reason": "day_close",
  "algo_notes": "Consensus score: 1079",
  "created_at": "2026-02-10 13:00:42"
}
{
  "id": 2,
  "challenge_date": "2026-02-10",
  "mode": "consensus",
  "ticker": "JNJ",
  "company_name": "Johnson & Johnson",
  "direction": "LONG",
  "entry_price": 239.99,
  "exit_price": 239.99,
  "shares": 4.1668,
  "invested": 999.99,
  "pnl": 17.3,
  "return_pct": 1.7303,
  "consensus_count": 8,
  "consensus_score": 765.0,
  "exit_reason": "day_close",
  "algo_notes": "Consensus score: 765",
  "created_at": "2026-02-10 13:00:42"
}
```

**`challenge_date` range:** 2026-02-10 → 2026-04-27

**`created_at` range:** 2026-02-10 13:00:42 → 2026-04-27 23:57:01

### 52. `mf2_fund_picks` — ~600 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (13):** `id` (int), `symbol` (varchar(20)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_nav` (decimal(12,4)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)), `pick_hash` (varchar(64)) … +1 more

**Primary Key:** `id`
**Indexed:** `symbol`, `algorithm_name`, `pick_date`, `pick_hash`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "RBF460",
  "algorithm_id": 8,
  "algorithm_name": "MF Quality Growth",
  "pick_date": "2025-03-15",
  "pick_time": "2025-03-15 16:00:00",
  "entry_nav": 44.3647,
  "score": 78,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "1y",
  "pick_hash": "",
  "rationale_json": ""
}
{
  "id": 2,
  "symbol": "TDB161",
  "algorithm_id": 1,
  "algorithm_name": "MF Momentum",
  "pick_date": "2025-03-20",
  "pick_time": "2025-03-20 16:00:00",
  "entry_nav": 29.5828,
  "score": 72,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "3m",
  "pick_hash": "",
  "rationale_json": ""
}
```

**`pick_date` range:** 2025-03-15 → 2026-03-29

**`pick_time` range:** 2025-03-15 16:00:00 → 2026-03-29 16:00:00

### 53. `fx_signals` — ~585 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (11):** `id` (int), `pair` (varchar(10)), `strategy_name` (varchar(100)), `signal_date` (date), `signal_time` (datetime), `direction` (varchar(10)), `entry_price` (decimal(12,6)), `stop_loss_price` (decimal(12,6)), `take_profit_price` (decimal(12,6)), `signal_hash` (varchar(64)), `score` (int)

**Primary Key:** `id`
**Indexed:** `pair`, `strategy_name`, `signal_date`

**`direction` distribution:**
- `long`: 390
- `short`: 195

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "AUDCAD",
  "strategy_name": "Mean Reversion",
  "signal_date": "2025-02-10",
  "signal_time": "2026-02-09 06:18:44",
  "direction": "long",
  "entry_price": 0.89693,
  "stop_loss_price": 0.0,
  "take_profit_price": 0.0,
  "signal_hash": "978218eba470d1f8a370217db63d3e964cee104a",
  "score": 0
}
{
  "id": 2,
  "pair": "AUDCAD",
  "strategy_name": "Mean Reversion",
  "signal_date": "2025-03-03",
  "signal_time": "2026-02-09 06:18:44",
  "direction": "long",
  "entry_price": 0.898258,
  "stop_loss_price": 0.0,
  "take_profit_price": 0.0,
  "signal_hash": "8e76e344507df63cc52c1e2bc597078f2d0d856c",
  "score": 0
}
```

**`signal_date` range:** 2025-02-10 → 2026-02-02

**`signal_time` range:** 2026-02-09 06:18:44 → 2026-02-11 00:47:14

### 54. `market_regimes` — ~560 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `trade_date` (date), `spy_close` (decimal(10,2)), `spy_sma200` (decimal(10,2)), `vix_close` (decimal(10,2)), `regime` (varchar(20)), `sp500_close` (decimal(10,2)), `sp500_change_pct` (decimal(8,4)), `source` (varchar(30)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `trade_date`

**Sample Rows:**
```json
{
  "id": 1,
  "trade_date": "2024-02-12",
  "spy_close": 500.98,
  "spy_sma200": 0.0,
  "vix_close": 13.93,
  "regime": "calm",
  "sp500_close": 0.0,
  "sp500_change_pct": 0.0,
  "source": "computed",
  "created_at": null
}
{
  "id": 2,
  "trade_date": "2024-02-13",
  "spy_close": 494.08,
  "spy_sma200": 0.0,
  "vix_close": 15.85,
  "regime": "calm",
  "sp500_close": 0.0,
  "sp500_change_pct": 0.0,
  "source": "computed",
  "created_at": null
}
```

**`trade_date` range:** 2024-02-12 → 2026-05-06

**`created_at` range:** 2026-02-11 02:50:21 → 2026-02-11 02:50:21

### 55. `lm_smart_consensus` — ~552 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (15):** `id` (int), `ticker` (varchar(10)), `calc_date` (date), `overall_score` (int), `technical_score` (int), `smart_money_score` (int), `insider_score` (int), `analyst_score` (int), `momentum_score` (int), `social_score` (int), `signal_direction` (varchar(10)), `confidence` (varchar(20)) … +3 more

**Primary Key:** `id`
**Indexed:** `ticker`, `calc_date`, `overall_score`, `signal_direction`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "calc_date": "2026-02-11",
  "overall_score": 61,
  "technical_score": 48,
  "smart_money_score": 75,
  "insider_score": 38,
  "analyst_score": 55,
  "momentum_score": 53,
  "social_score": 3,
  "signal_direction": "BULLISH",
  "confidence": "MODERATE",
  "regime": "bear",
  "explanation": "{\"technical\":48,\"smart_money\":75,\"insider\":38,\"analyst\":55,\"momentum\":53,\"regime\":\"bear\",\"notes\":[\"AAPL 13F: 1 funds, inc=0, new=1\",\"AAPL insider: MSP...",
  "created_at": "2026-02-11 01:50:16"
}
{
  "id": 2,
  "ticker": "MSFT",
  "calc_date": "2026-02-11",
  "overall_score": 73,
  "technical_score": 48,
  "smart_money_score": 75,
  "insider_score": 50,
  "analyst_score": 88,
  "momentum_score": 67,
  "social_score": 7,
  "signal_direction": "BULLISH",
  "confidence": "MODERATE",
  "regime": "bear",
  "explanation": "{\"technical\":48,\"smart_money\":75,\"insider\":50,\"analyst\":88,\"momentum\":67,\"regime\":\"bear\",\"notes\":[\"MSFT 13F: 1 funds, inc=0, new=1\",\"MSFT target: $596...",
  "created_at": "2026-02-11 01:50:16"
}
```

**`calc_date` range:** 2026-02-11 → 2026-05-08

**`created_at` range:** 2026-02-11 01:50:16 → 2026-05-08 11:27:07

### 56. `lm_sports_odds` — ~502 rows (1MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (13):** `id` (int), `sport` (varchar(50)), `event_id` (varchar(100)), `home_team` (varchar(100)), `away_team` (varchar(100)), `commence_time` (datetime), `bookmaker` (varchar(50)), `bookmaker_key` (varchar(50)), `market` (varchar(20)), `outcome_name` (varchar(100)), `outcome_price` (decimal(10,4)), `outcome_point` (decimal(6,2)) … +1 more

**Primary Key:** `id`
**Indexed:** `sport`, `event_id`, `commence_time`, `bookmaker`

**Sample Rows:**
```json
{
  "id": 74444,
  "sport": "americanfootball_ncaaf",
  "event_id": "123a238486098cc9e8f71fea0cf4e7b0",
  "home_team": "Virginia Cavaliers",
  "away_team": "NC State Wolfpack",
  "commence_time": "2026-08-29 16:00:00",
  "bookmaker": "FanDuel",
  "bookmaker_key": "fanduel",
  "market": "h2h",
  "outcome_name": "NC State Wolfpack",
  "outcome_price": 2.34,
  "outcome_point": null,
  "last_updated": "2026-02-12 02:54:55"
}
{
  "id": 74445,
  "sport": "americanfootball_ncaaf",
  "event_id": "123a238486098cc9e8f71fea0cf4e7b0",
  "home_team": "Virginia Cavaliers",
  "away_team": "NC State Wolfpack",
  "commence_time": "2026-08-29 16:00:00",
  "bookmaker": "FanDuel",
  "bookmaker_key": "fanduel",
  "market": "h2h",
  "outcome_name": "Virginia Cavaliers",
  "outcome_price": 1.62,
  "outcome_point": null,
  "last_updated": "2026-02-12 02:54:55"
}
```

**`commence_time` range:** 2026-04-01 23:40:00 → 2026-09-12 16:00:00

**`last_updated` range:** 2026-02-12 02:54:55 → 2026-04-02 03:53:22

### 57. `goldmine_cursor_predictions` — ~478 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (20):** `id` (int), `prediction_id` (varchar(64)), `asset_class` (varchar(20)), `ticker` (varchar(30)), `algorithm` (varchar(80)), `direction` (varchar(10)), `entry_price` (decimal(16,6)), `target_price` (decimal(16,6)), `stop_loss` (decimal(16,6)), `confidence_score` (int), `source_system` (varchar(50)), `logged_at` (datetime) … +8 more

**Primary Key:** `id`
**Indexed:** `prediction_id`, `asset_class`, `algorithm`, `source_system`, `logged_at`, `market_regime`, `status`

**`asset_class` distribution:**
- `stocks`: 478

**`direction` distribution:**
- `long`: 478

**`source_system` distribution:**
- `findstocks`: 478

**`status` distribution:**
- `open`: 255
- `won`: 99
- `lost`: 86
- `expired`: 38

**Sample Rows:**
```json
{
  "id": 1,
  "prediction_id": "522643b9fbda93b4f0d50f1280b843fc",
  "asset_class": "stocks",
  "ticker": "GME",
  "algorithm": "Volatility-Adjusted Momentum (V2)",
  "direction": "long",
  "entry_price": 24.82,
  "target_price": 26.061,
  "stop_loss": 24.0754,
  "confidence_score": 65,
  "source_system": "findstocks",
  "logged_at": "2026-02-10 16:00:00",
  "market_regime": "unknown",
  "status": "open",
  "exit_price": null,
  "exit_date": null,
  "pnl_pct": null,
  "benchmark_return_pct": null,
  "hold_days": null,
  "resolved_at": null
}
{
  "id": 2,
  "prediction_id": "ac9716e0d16dd3fc932492bb2c5b8360",
  "asset_class": "stocks",
  "ticker": "AMD",
  "algorithm": "Regime-Aware Reversion (V2)",
  "direction": "long",
  "entry_price": 213.57,
  "target_price": 224.2485,
  "stop_loss": 207.1629,
  "confidence_score": 69,
  "source_system": "findstocks",
  "logged_at": "2026-02-10 16:00:00",
  "market_regime": "unknown",
  "status": "open",
  "exit_price": null,
  "exit_date": null,
  "pnl_pct": null,
  "benchmark_return_pct": null,
  "hold_days": null,
  "resolved_at": null
}
```

**`exit_date` range:** 2025-11-17 16:00:00 → 2026-02-06 16:00:00

**`resolved_at` range:** 2026-02-11 00:03:07 → 2026-02-11 00:03:07

### 58. `mf2_backtest_trades` — ~450 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (15):** `id` (int), `backtest_id` (int), `symbol` (varchar(20)), `algorithm_name` (varchar(100)), `entry_date` (date), `entry_nav` (decimal(12,4)), `exit_date` (date), `exit_nav` (decimal(12,4)), `units` (decimal(12,4)), `gross_profit` (decimal(12,2)), `fees_paid` (decimal(8,2)), `net_profit` (decimal(12,2)) … +3 more

**Primary Key:** `id`
**Indexed:** `backtest_id`, `symbol`

**Sample Rows:**
```json
{
  "id": 901,
  "backtest_id": 21,
  "symbol": "RBF460",
  "algorithm_name": "MF Quality Growth",
  "entry_date": "2025-03-15",
  "entry_nav": 44.3647,
  "exit_date": "2025-04-15",
  "exit_nav": 44.6719,
  "units": 45.0809,
  "gross_profit": 0.0,
  "fees_paid": 0.0,
  "net_profit": 11.88,
  "return_pct": 0.5939,
  "exit_reason": "max_hold",
  "hold_days": 21
}
{
  "id": 902,
  "backtest_id": 21,
  "symbol": "RBF460",
  "algorithm_name": "MF Quality Growth",
  "entry_date": "2025-03-15",
  "entry_nav": 44.3647,
  "exit_date": "2025-04-15",
  "exit_nav": 44.6719,
  "units": 45.1344,
  "gross_profit": 0.0,
  "fees_paid": 0.0,
  "net_profit": 11.9,
  "return_pct": 0.5941,
  "exit_reason": "max_hold",
  "hold_days": 21
}
```

**`entry_date` range:** 2025-03-15 → 2025-06-20

**`exit_date` range:** 2025-04-15 → 2026-02-12

### 59. `gm_failure_alerts` — ~414 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (14):** `id` (int), `alert_date` (date), `source_system` (varchar(30)), `alert_type` (varchar(30)), `severity` (varchar(10)), `title` (varchar(200)), `description` (text), `affected_tickers` (text), `metric_value` (decimal(10,4)), `threshold_value` (decimal(10,4)), `page_url` (varchar(200)), `is_active` (int) … +2 more

**Primary Key:** `id`
**Indexed:** `alert_date`, `source_system`, `is_active`

**`source_system` distribution:**
- `consolidated`: 90
- `sports`: 82
- `live_signal`: 64
- `meme`: 63
- `edge`: 58
- `penny`: 56
- `portfolio`: 1

**Sample Rows:**
```json
{
  "id": 1,
  "alert_date": "2026-02-11",
  "source_system": "live_signal",
  "alert_type": "accuracy_drop",
  "severity": "warning",
  "title": "live_signal: Win rate declining (37.4%)",
  "description": "The 30-day win rate is 37.4%, approaching the critical threshold.",
  "affected_tickers": "",
  "metric_value": 37.4,
  "threshold_value": 40.0,
  "page_url": "/live-monitor/live-monitor.html",
  "is_active": 0,
  "resolved_at": "2026-02-11 21:04:28",
  "created_at": "2026-02-11 18:57:30"
}
{
  "id": 2,
  "alert_date": "2026-02-11",
  "source_system": "live_signal",
  "alert_type": "algo_underperform",
  "severity": "critical",
  "title": "live_signal: Algorithm \"Consensus\" failing (0% win rate)",
  "description": "Algorithm \"Consensus\" has only a 0% win rate across 20 trades in the last 30 days. Average return: -3.15%. Consider disabling or re-tuning.",
  "affected_tickers": "",
  "metric_value": 0.0,
  "threshold_value": 20.0,
  "page_url": "/live-monitor/live-monitor.html",
  "is_active": 0,
  "resolved_at": "2026-02-11 21:19:47",
  "created_at": "2026-02-11 21:04:28"
}
```

**`alert_date` range:** 2026-02-11 → 2026-04-30

**`resolved_at` range:** 2026-02-11 21:04:28 → 2026-04-30 00:23:22

### 60. `miracle_audit3` — ~412 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "Tables created + seeded",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 18:52:19"
}
{
  "id": 2,
  "action_type": "setup_schema",
  "details": "Tables created + seeded",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 18:52:24"
}
```

**`created_at` range:** 2026-02-09 18:52:19 → 2026-05-07 23:54:26

### 61. `at_strategy_symbol_performance` — ~410 rows (0MB + 0MB idx)
**Purpose:** Audit: Strategy performance stats

**Columns (18):** `id` (int), `strategy_name` (varchar(100)), `display_name` (varchar(200)), `symbol` (varchar(20)), `portfolio_type` (varchar(50)), `total_trades` (int), `wins` (int), `win_rate` (decimal(5,2)), `avg_pnl_pct` (decimal(8,4)), `profit_factor` (decimal(8,3)), `sharpe` (decimal(8,3)), `max_drawdown_pct` (decimal(8,4)) … +6 more

**Primary Key:** `id`
**Indexed:** `strategy_name`

**Sample Rows:**
```json
{
  "id": 1,
  "strategy_name": "ConnorsR4MeanReversionStrategy",
  "display_name": "ConnorsR4MeanReversionStrategy",
  "symbol": "BTCUSDT",
  "portfolio_type": "baby_strategies",
  "total_trades": 3,
  "wins": 1,
  "win_rate": 33.33,
  "avg_pnl_pct": 0.5633,
  "profit_factor": 2.115,
  "sharpe": 4.66,
  "max_drawdown_pct": 1.51,
  "best_trade_pct": 3.202,
  "worst_trade_pct": -1.2938,
  "test_interval": "1h",
  "test_bars": 1969,
  "is_catered": 0,
  "tested_at": "2026-03-06 21:53:21"
}
{
  "id": 2,
  "strategy_name": "ConnorsR4MeanReversionStrategy",
  "display_name": "ConnorsR4MeanReversionStrategy",
  "symbol": "ETHUSDT",
  "portfolio_type": "baby_strategies",
  "total_trades": 3,
  "wins": 1,
  "win_rate": 33.33,
  "avg_pnl_pct": -0.5033,
  "profit_factor": 0.543,
  "sharpe": -4.844,
  "max_drawdown_pct": 3.27,
  "best_trade_pct": 1.7864,
  "worst_trade_pct": -2.0081,
  "test_interval": "1h",
  "test_bars": 1969,
  "is_catered": 0,
  "tested_at": "2026-03-06 21:53:21"
}
```

### 62. `miracle_learning3` — ~410 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `strategy_name` (varchar(100)), `param_name` (varchar(50)), `old_value` (decimal(10,4)), `new_value` (decimal(10,4)), `reason` (text), `backtest_win_rate` (decimal(5,2)), `backtest_return_pct` (decimal(10,4)), `applied_at` (datetime)

**Primary Key:** `id`
**Indexed:** `strategy_name`, `applied_at`

**Sample Rows:**
```json
{
  "id": 1,
  "strategy_name": "Momentum Continuation",
  "param_name": "default_tp_pct",
  "old_value": 7.0,
  "new_value": 6.2,
  "reason": "Grid search found optimal TP=3%. Shifted 20% toward it. Best WR=50%, PF=2.105",
  "backtest_win_rate": 50.0,
  "backtest_return_pct": 0.5525,
  "applied_at": "2026-02-11 23:56:18"
}
{
  "id": 2,
  "strategy_name": "Momentum Continuation",
  "param_name": "default_sl_pct",
  "old_value": 3.5,
  "new_value": 3.0,
  "reason": "Grid search found optimal SL=1%. Shifted 20% toward it. Best WR=50%, PF=2.105",
  "backtest_win_rate": 50.0,
  "backtest_return_pct": 0.5525,
  "applied_at": "2026-02-11 23:56:18"
}
```

### 63. `ml_feature_store` — ~396 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (52):** `id` (bigint), `pair` (varchar(30)), `asset_class` (varchar(20)), `timestamp` (datetime), `timeframe` (varchar(10)), `close_price` (float), `return_1` (float), `return_5` (float), `return_20` (float), `log_return` (float), `rsi_14` (float), `macd_value` (float) … +40 more

**Primary Key:** `id`
**Indexed:** `pair`, `timeframe`

**`asset_class` distribution:**
- `CRYPTO`: 396

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "XXBTZUSD",
  "asset_class": "CRYPTO",
  "timestamp": "2026-02-14 20:42:23",
  "timeframe": "4H",
  "close_price": 69919.9,
  "return_1": 0.001716,
  "return_5": 0.014156,
  "return_20": 0.051716,
  "log_return": 0.001715,
  "rsi_14": 68.18,
  "macd_value": 349.095,
  "macd_signal": -40.9214,
  "macd_histogram": 390.017,
  "stoch_k": 88.66,
  "stoch_d": 88.66,
  "williams_r": -11.34,
  "cci_20": 107.36,
  "roc_10": 5.69,
  "sma_20": 68031.5,
  "sma_50": 68847.0,
  "ema_9": 69256.7,
  "ema_21": 68663.9,
  "adx_14": 42.39,
  "plus_di": 33.65,
  "minus_di": 13.61,
  "price_vs_sma20": 0.027757,
  "price_vs_sma50": 0.015584,
  "atr_14": 1005.89,
  "bollinger_upper": 70793.5,
  "bollinger_lower": 65269.6,
  "bollinger_width": 0.081195,
  "bollinger_pct_b": 0.8419,
  "realized_vol_20": 0.010841,
  "volume": 26.97,
  "volume_sma_20": 416.63,
  "volume_ratio": 0.0647,
  "obv": -21975.3,
  "hurst_exponent": 0.5776,
  "autocorrelation_1": 0.107,
  "volatility_stability": 0.399,
  "signal_noise_ratio": 18.3778,
  "pattern_detected": "",
  "pattern_strength": 0.0,
  "engines_bullish": 1,
  "engines_bearish": 0,
  "engines_total": 1,
  "engine_agreement": 1.0,
  "target_1h": null,
  "target_4h": null,
  "target_24h": null,
  "target_direction": null
}
{
  "id": 2,
  "pair": "XETHZUSD",
  "asset_class": "CRYPTO",
  "timestamp": "2026-02-14 20:42:23",
  "timeframe": "4H",
  "close_price": 2086.39,
  "return_1": -0.000565,
  "return_5": 0.016061,
  "return_20": 0.08135,
  "log_return": -0.000565,
  "rsi_14": 76.36,
  "macd_value": 19.1772,
  "macd_signal": 3.25147,
  "macd_histogram": 15.9257,
  "stoch_k": 90.68,
  "stoch_d": 90.68,
  "williams_r": -9.32,
  "cci_20": 103.56,
  "roc_10": 7.86,
  "sma_20": 2004.33,
  "sma_50": 2032.53,
  "ema_9": 2060.34,
  "ema_21": 2031.74,
  "adx_14": 54.05,
  "plus_di": 35.9,
  "minus_di": 10.71,
  "price_vs_sma20": 0.040944,
  "price_vs_sma50": 0.0265,
  "atr_14": 35.0457,
  "bollinger_upper": 2124.79,
  "bollinger_lower": 1883.87,
  "bollinger_width": 0.1202,
  "bollinger_pct_b": 0.8406,
  "realized_vol_20": 0.012564,
  "volume": 347.87,
  "volume_sma_20": 2996.27,
  "volume_ratio": 0.1161,
  "obv": -79557.2,
  "hurst_exponent": 0.5658,
  "autocorrelation_1": 0.0262,
  "volatility_stability": 0.4041,
  "signal_noise_ratio": 17.698,
  "pattern_detected": "",
  "pattern_strength": 0.0,
  "engines_bullish": 0,
  "engines_bearish": 0,
  "engines_total": 0,
  "engine_agreement": 0.0,
  "target_1h": null,
  "target_4h": null,
  "target_24h": null,
  "target_direction": null
}
```

**`timestamp` range:** 2026-02-14 20:42:23 → 2026-02-16 19:09:19

**`timeframe` range:** 4H → 4H

### 64. `cr_audit_log` — ~393 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "CR Schema created/verified",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 09:03:37"
}
{
  "id": 2,
  "action_type": "import_picks",
  "details": "Imported 14, skipped 0 (source: seed)",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 09:03:48"
}
```

**`created_at` range:** 2026-02-09 09:03:37 → 2026-05-07 23:53:06

### 65. `stock_earnings` — ~381 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (12):** `id` (int), `ticker` (varchar(10)), `quarter_end` (date), `earnings_date` (date), `eps_actual` (decimal(10,4)), `eps_estimate` (decimal(10,4)), `eps_surprise` (decimal(10,4)), `surprise_pct` (decimal(10,4)), `revenue_actual` (bigint), `revenue_estimate` (bigint), `source` (varchar(20)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `ticker`, `earnings_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "quarter_end": "2025-03-31",
  "earnings_date": null,
  "eps_actual": 1.65,
  "eps_estimate": 1.6225,
  "eps_surprise": 0.03,
  "surprise_pct": 0.0169,
  "revenue_actual": null,
  "revenue_estimate": null,
  "source": "yahoo_v10",
  "updated_at": "2026-04-27 23:50:10"
}
{
  "id": 2,
  "ticker": "AAPL",
  "quarter_end": "2025-06-30",
  "earnings_date": null,
  "eps_actual": 1.57,
  "eps_estimate": 1.4257,
  "eps_surprise": 0.14,
  "surprise_pct": 0.1012,
  "revenue_actual": null,
  "revenue_estimate": null,
  "source": "yahoo_v10",
  "updated_at": "2026-04-27 23:50:10"
}
```

**`updated_at` range:** 2026-02-09 19:50:42 → 2026-04-27 23:51:11

### 66. `fxp_audit_log` — ~380 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "FX Schema created/verified",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 17:57:25"
}
{
  "id": 2,
  "action_type": "import_picks",
  "details": "Imported 16, skipped 0 (source: seed)",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 17:57:31"
}
```

**`created_at` range:** 2026-02-09 17:57:25 → 2026-05-07 23:52:01

### 67. `lm_sports_value_bets` — ~375 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (21):** `id` (int), `event_id` (varchar(100)), `sport` (varchar(50)), `home_team` (varchar(100)), `away_team` (varchar(100)), `commence_time` (datetime), `market` (varchar(20)), `bet_type` (varchar(50)), `outcome_name` (varchar(100)), `best_book` (varchar(50)), `best_book_key` (varchar(50)), `best_odds` (decimal(10,4)) … +9 more

**Primary Key:** `id`
**Indexed:** `event_id`, `sport`, `commence_time`, `ev_pct`, `status`

**`status` distribution:**
- `expired`: 366
- `active`: 9

**Sample Rows:**
```json
{
  "id": 948,
  "event_id": "3abaf28550da137114cba0daec6fe134",
  "sport": "basketball_nba",
  "home_team": "Los Angeles Lakers",
  "away_team": "San Antonio Spurs",
  "commence_time": "2026-02-11 03:30:00",
  "market": "h2h",
  "bet_type": "Los Angeles Lakers ML",
  "outcome_name": "Los Angeles Lakers",
  "best_book": "ESPN BET",
  "best_book_key": "espnbet",
  "best_odds": 6.0,
  "consensus_implied_prob": 0.1786,
  "true_prob": 0.1709,
  "edge_pct": 2.56,
  "ev_pct": 2.56,
  "kelly_fraction": 0.0013,
  "kelly_bet": 1.28,
  "all_odds": "[{\"book_key\":\"fanduel\",\"book_name\":\"FanDuel\",\"price\":6.3,\"is_canadian\":1},{\"book_key\":\"draftkings\",\"book_name\":\"DraftKings\",\"price\":5.9,\"is_canadian\":...",
  "detected_at": "2026-02-11 03:15:58",
  "status": "expired"
}
{
  "id": 1849,
  "event_id": "6c0605c60b07c6bc9b381b4b9c87c8bd",
  "sport": "basketball_ncaab",
  "home_team": "Santa Clara Broncos",
  "away_team": "Seattle Redhawks",
  "commence_time": "2026-02-12 03:00:00",
  "market": "h2h",
  "bet_type": "Seattle Redhawks ML",
  "outcome_name": "Seattle Redhawks",
  "best_book": "DraftKings",
  "best_book_key": "draftkings",
  "best_odds": 7.75,
  "consensus_implied_prob": 0.14,
  "true_prob": 0.1332,
  "edge_pct": 3.23,
  "ev_pct": 3.23,
  "kelly_fraction": 0.0012,
  "kelly_bet": 1.2,
  "all_odds": "[{\"book_key\":\"ballybet\",\"book_name\":\"Ballybet\",\"price\":6.1,\"is_canadian\":0},{\"book_key\":\"betmgm\",\"book_name\":\"BetMGM\",\"price\":7.25,\"is_canadian\":1},{\"...",
  "detected_at": "2026-02-12 02:55:06",
  "status": "expired"
}
```

**`commence_time` range:** 2026-02-11 02:00:00 → 2026-04-03 01:45:00

### 68. `ua_predictions` — ~355 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (22):** `id` (int), `engine_name` (varchar(50)), `engine_signal_id` (varchar(50)), `asset_class` (varchar(20)), `pair` (varchar(30)), `direction` (varchar(10)), `confidence` (float), `entry_price` (float), `tp_price` (float), `sl_price` (float), `tp_pct` (float), `sl_pct` (float) … +10 more

**Primary Key:** `id`
**Indexed:** `engine_name`, `pair`, `status`

**`asset_class` distribution:**
- `CRYPTO`: 355

**`direction` distribution:**
- `LONG`: 210
- `SHORT`: 80
- ``: 65

**`status` distribution:**
- `RESOLVED`: 243
- `ACTIVE`: 112

**Sample Rows:**
```json
{
  "id": 1,
  "engine_name": "Hybrid Engine",
  "engine_signal_id": "32",
  "asset_class": "CRYPTO",
  "pair": "APTUSD",
  "direction": "LONG",
  "confidence": 88.0,
  "entry_price": 0.9993,
  "tp_price": 0.0,
  "sl_price": 0.0,
  "tp_pct": 9.04,
  "sl_pct": 4.65,
  "predictability_score": 42.2,
  "signal_time": "2026-02-14 19:46:34",
  "expires_at": "0000-00-00 00:00:00",
  "status": "RESOLVED",
  "exit_price": 0.9389,
  "pnl_pct": -6.0442,
  "exit_reason": "SL_HIT",
  "resolved_at": "2026-02-15 13:27:03",
  "hold_hours": 0.0,
  "collected_at": "2026-02-14 20:34:45"
}
{
  "id": 2,
  "engine_name": "Hybrid Engine",
  "engine_signal_id": "31",
  "asset_class": "CRYPTO",
  "pair": "XXRPZUSD",
  "direction": "LONG",
  "confidence": 70.0,
  "entry_price": 1.49564,
  "tp_price": 0.0,
  "sl_price": 0.0,
  "tp_pct": 7.64,
  "sl_pct": 3.93,
  "predictability_score": 51.7,
  "signal_time": "2026-02-14 19:46:34",
  "expires_at": "0000-00-00 00:00:00",
  "status": "RESOLVED",
  "exit_price": 1.63732,
  "pnl_pct": 9.4729,
  "exit_reason": "TP_HIT",
  "resolved_at": "2026-02-15 07:56:55",
  "hold_hours": 0.0,
  "collected_at": "2026-02-14 20:34:45"
}
```

**`signal_time` range:** 2026-02-14 00:29:52 → 2026-02-16 19:00:58

**`resolved_at` range:** 2026-02-14 12:31:10 → 2026-02-16 19:10:11

### 69. `consensus_lessons` — ~348 rows (0MB + 0MB idx)
**Purpose:** Consensus: Aggregation

**Columns (10):** `id` (int), `lesson_date` (date), `lesson_type` (varchar(30)), `lesson_title` (varchar(200)), `lesson_text` (text), `confidence` (int), `supporting_data` (text), `applied` (int), `impact_score` (decimal(6,2)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `lesson_date`, `lesson_type`, `confidence`

**Sample Rows:**
```json
{
  "id": 1,
  "lesson_date": "2026-02-12",
  "lesson_type": "risk",
  "lesson_title": "Exit analysis: consensus_dropped exits perform best",
  "lesson_text": "consensus_dropped exits average -3.17% (33.3% WR), while sl_hit exits average -5.16% (0% WR). Consider tightening stop-loss to reduce losses.",
  "confidence": 50,
  "supporting_data": "[{\"reason\":\"consensus_dropped\",\"trades\":3,\"avg_return\":-3.17,\"win_rate\":33.3},{\"reason\":\"sl_hit\",\"trades\":8,\"avg_return\":-5.16,\"win_rate\":0}]",
  "applied": 0,
  "impact_score": 0.0,
  "created_at": "2026-02-12 23:56:00"
}
{
  "id": 2,
  "lesson_date": "2026-02-12",
  "lesson_type": "algo_insight",
  "lesson_title": "Top algorithms: Technical Momentum leads",
  "lesson_text": "Best performing algorithms in consensus picks: Technical Momentum (25% WR, -3.26% avg), Alpha Factor Quality (25% WR, -1.16% avg), Blue Chip Growth (2...",
  "confidence": 75,
  "supporting_data": "[{\"algorithm\":\"Technical Momentum\",\"trades\":4,\"wins\":1,\"win_rate\":25,\"avg_return\":-3.26},{\"algorithm\":\"Alpha Factor Quality\",\"trades\":4,\"wins\":1,\"win_...",
  "applied": 0,
  "impact_score": 0.0,
  "created_at": "2026-02-12 23:56:00"
}
```

**`lesson_date` range:** 2026-02-12 → 2026-04-27

**`created_at` range:** 2026-02-12 23:56:00 → 2026-04-27 23:57:01

### 70. `cw_winners` — ~342 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (16):** `id` (int), `scan_id` (varchar(20)), `pair` (varchar(30)), `price_at_signal` (double), `price_at_resolve` (double), `score` (int), `factors_json` (text), `verdict` (varchar(20)), `target_pct` (double), `risk_pct` (double), `pnl_pct` (double), `outcome` (varchar(20)) … +4 more

**Primary Key:** `id`
**Indexed:** `scan_id`, `pair`, `outcome`, `created_at`

**`outcome` distribution:**
- `loss`: 163
- `win`: 100
- `partial_loss`: 40
- `partial_win`: 39

**Sample Rows:**
```json
{
  "id": 1,
  "scan_id": "20260210113339",
  "pair": "WLD_USDT",
  "price_at_signal": 0.393,
  "price_at_resolve": 0.3806,
  "score": 74,
  "factors_json": "{\"multi_timeframe_momentum\":{\"score\":20,\"max\":20,\"mom_4h\":2.21,\"mom_1h\":2.21},\"volume_surge\":{\"score\":14,\"max\":20,\"ratio\":2.92},\"rsi_sweet_spot\":{\"sco...",
  "verdict": "LEAN_BUY",
  "target_pct": 1.5,
  "risk_pct": 1.5,
  "pnl_pct": -3.1552,
  "outcome": "loss",
  "vol_usd_24h": 33867.92,
  "chg_24h": 3.56,
  "created_at": "2026-02-10 11:33:39",
  "resolved_at": "2026-02-10 15:35:41"
}
{
  "id": 2,
  "scan_id": "20260210113829",
  "pair": "WLD_USDT",
  "price_at_signal": 0.3923,
  "price_at_resolve": 0.3799,
  "score": 80,
  "factors_json": "{\"multi_timeframe_momentum\":{\"score\":20,\"max\":20,\"mom_4h\":2.03,\"mom_1h\":2.78},\"volume_surge\":{\"score\":20,\"max\":20,\"ratio\":3.29},\"rsi_sweet_spot\":{\"sco...",
  "verdict": "BUY",
  "target_pct": 2.0,
  "risk_pct": 1.5,
  "pnl_pct": -3.1608,
  "outcome": "loss",
  "vol_usd_24h": 34302.33,
  "chg_24h": 3.18,
  "created_at": "2026-02-10 11:38:29",
  "resolved_at": "2026-02-10 16:35:13"
}
```

**`created_at` range:** 2026-02-10 11:33:39 → 2026-05-07 18:39:34

**`resolved_at` range:** 2026-02-10 15:35:41 → 2026-05-08 00:48:03

### 71. `mf2_audit_log` — ~328 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "MF Schema v2 created/verified",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 17:57:24"
}
{
  "id": 2,
  "action_type": "import_picks",
  "details": "Imported 15, skipped 0 (source: seed)",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 17:57:31"
}
```

**`created_at` range:** 2026-02-09 17:57:24 → 2026-05-08 12:42:45

### 72. `consensus_tracked` — ~318 rows (0MB + 0MB idx)
**Purpose:** Consensus: Aggregation

**Columns (28):** `id` (int), `ticker` (varchar(10)), `company_name` (varchar(100)), `entry_date` (date), `entry_price` (decimal(12,4)), `consensus_count` (int), `consensus_score` (decimal(10,4)), `direction` (varchar(10)), `source_algos` (text), `target_tp_pct` (decimal(6,2)), `target_sl_pct` (decimal(6,2)), `max_hold_days` (int) … +16 more

**Primary Key:** `id`
**Indexed:** `ticker`, `entry_date`, `status`, `final_return_pct`, `discord_sent`

**`direction` distribution:**
- `LONG`: 318

**`status` distribution:**
- `closed_loss`: 131
- `closed_win`: 104
- `closed_neutral`: 44
- `open`: 39

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "entry_date": "2026-02-10",
  "entry_price": 278.12,
  "consensus_count": 6,
  "consensus_score": 881.0,
  "direction": "LONG",
  "source_algos": "Blue Chip Growth, Alpha Factor Quality, Alpha Factor Earnings, Alpha Factor Momentum, Alpha Factor Growth, Alpha Factor Composite",
  "target_tp_pct": 8.0,
  "target_sl_pct": 4.0,
  "max_hold_days": 14,
  "current_price": 261.73,
  "current_return_pct": -5.8931,
  "peak_price": 278.12,
  "trough_price": 261.73,
  "status": "closed_loss",
  "exit_date": "2026-02-12",
  "exit_price": 261.73,
  "exit_reason": "sl_hit",
  "final_return_pct": -5.8931,
  "hold_days": 2,
  "created_at": "2026-02-10 13:00:42",
  "updated_at": "2026-02-12 23:56:00",
  "discord_sent": 1,
  "discord_channel": "consensus",
  "discord_message_id": null,
  "discord_sent_at": "2026-03-16 14:24:58"
}
{
  "id": 2,
  "ticker": "GM",
  "company_name": "General Motors Company",
  "entry_date": "2026-02-10",
  "entry_price": 84.24,
  "consensus_count": 2,
  "consensus_score": 175.0,
  "direction": "LONG",
  "source_algos": "Technical Momentum, Composite Rating",
  "target_tp_pct": 8.0,
  "target_sl_pct": 4.0,
  "max_hold_days": 14,
  "current_price": 79.93,
  "current_return_pct": -5.1163,
  "peak_price": 84.24,
  "trough_price": 84.24,
  "status": "closed_loss",
  "exit_date": "2026-02-12",
  "exit_price": 79.93,
  "exit_reason": "consensus_dropped",
  "final_return_pct": -5.1163,
  "hold_days": 2,
  "created_at": "2026-02-10 13:00:42",
  "updated_at": "2026-02-12 23:56:00",
  "discord_sent": 0,
  "discord_channel": null,
  "discord_message_id": null,
  "discord_sent_at": null
}
```

**`entry_date` range:** 2026-02-10 → 2026-04-27

**`exit_date` range:** 2026-02-12 → 2026-04-27

### 73. `at_raw_picks_anomaly_log` — ~304 rows (0MB + 0MB idx)
**Purpose:** Audit: Raw signals from all source systems

**Columns (5):** `id` (bigint), `raw_pick_id` (bigint), `reason` (varchar(64)), `original_pnl_pct` (double), `captured_at` (timestamp)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "raw_pick_id": 163,
  "reason": "ZERO_OR_NEAR_ZERO",
  "original_pnl_pct": 0.0,
  "captured_at": "2026-04-02 01:13:58"
}
{
  "id": 2,
  "raw_pick_id": 47,
  "reason": "EXTREME_PNL_OUTLIER",
  "original_pnl_pct": -98.87,
  "captured_at": "2026-04-02 01:13:58"
}
```

### 74. `bt_backtest_runs` — ~285 rows (0MB + 0MB idx)
**Purpose:** Backtesting: Run-level aggregates

**Columns (15):** `id` (char(36)), `source_db` (varchar(200)), `source_table` (varchar(100)), `strategy` (varchar(200)), `symbol` (varchar(50)), `asset_class` (enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')), `total_trades` (int), `wins` (int), `losses` (int), `win_rate` (decimal(5,4)), `profit_factor` (decimal(10,4)), `total_return` (decimal(10,4)) … +3 more

**Primary Key:** `id`
**Indexed:** `strategy`, `symbol`, `asset_class`

**`strategy` distribution:**
- `kimi_signal_tracker`: 19
- `ensemble`: 18
- `opposite_day`: 14
- `Funding Rate Carry`: 11
- `extreme_fear`: 10
- `hurst_regime_adaptive`: 8
- `monthly_seasonality`: 7
- `variance_ratio_momentum`: 7
- `community_ict_fvg_selective`: 7
- `m2_liquidity_lag`: 7
- `autocorrelation_exploiter`: 6
- `fourier_cycle_detector`: 6

**`asset_class` distribution:**
- `CRYPTO`: 285

**Sample Rows:**
```json
{
  "id": "001a8759-51f9-4f63-ba87-9f42f7fd8d8e",
  "source_db": "alpha_engine/data/closed_picks.json",
  "source_table": "closed_picks",
  "strategy": "session_momentum_continuation",
  "symbol": "NZDUSD=X",
  "asset_class": "CRYPTO",
  "total_trades": 1,
  "wins": 1,
  "losses": 0,
  "win_rate": 1.0,
  "profit_factor": 999.999,
  "total_return": 0.0045,
  "sharpe": 0.0,
  "max_drawdown": 0.0,
  "imported_at": "2026-03-06 23:58:10"
}
{
  "id": "00be2d70-728b-47fc-8a54-e574ad26ebaf",
  "source_db": "battleground/data/closed_picks.json",
  "source_table": "closed_picks",
  "strategy": "crypto_keltner_compression_expansion_v1",
  "symbol": "BTCUSDT",
  "asset_class": "CRYPTO",
  "total_trades": 24,
  "wins": 16,
  "losses": 8,
  "win_rate": 0.6667,
  "profit_factor": 4.171,
  "total_return": 10.5921,
  "sharpe": 7.806,
  "max_drawdown": 2.3782,
  "imported_at": "2026-03-06 23:58:10"
}
```

### 75. `gm_system_health` — ~272 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (21):** `id` (int), `snap_date` (date), `source_system` (varchar(30)), `total_picks` (int), `closed_picks` (int), `wins` (int), `losses` (int), `expired` (int), `win_rate` (decimal(6,2)), `avg_return_pct` (decimal(10,4)), `total_return_pct` (decimal(10,4)), `avg_hold_hours` (decimal(10,2)) … +9 more

**Primary Key:** `id`
**Indexed:** `snap_date`, `is_failing`

**`source_system` distribution:**
- `consolidated`: 34
- `edge`: 34
- `horizon`: 34
- `live_signal`: 34
- `meme`: 34
- `penny`: 34
- `sports`: 34
- `top_picks`: 34

**Sample Rows:**
```json
{
  "id": 1,
  "snap_date": "2026-02-10",
  "source_system": "consolidated",
  "total_picks": 58,
  "closed_picks": 0,
  "wins": 0,
  "losses": 0,
  "expired": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "total_return_pct": 0.0,
  "avg_hold_hours": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "accuracy_7d": 0.0,
  "accuracy_30d": 0.0,
  "is_failing": 0,
  "failure_reason": "",
  "created_at": "2026-02-10 23:53:42"
}
{
  "id": 2,
  "snap_date": "2026-02-10",
  "source_system": "live_signal",
  "total_picks": 300,
  "closed_picks": 0,
  "wins": 0,
  "losses": 0,
  "expired": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "total_return_pct": 0.0,
  "avg_hold_hours": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "accuracy_7d": 0.0,
  "accuracy_30d": 0.0,
  "is_failing": 0,
  "failure_reason": "",
  "created_at": "2026-02-10 23:53:42"
}
```

**`snap_date` range:** 2026-02-10 → 2026-04-30

**`created_at` range:** 2026-02-10 23:53:42 → 2026-04-30 00:23:22

### 76. `mf_audit_log` — ~260 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `action_type`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "setup_schema",
  "details": "MF schema created/verified",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 05:39:09"
}
{
  "id": 2,
  "action_type": "fetch_nav",
  "details": "Fetched 10 tickers",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 05:39:17"
}
```

**`created_at` range:** 2026-02-09 05:39:09 → 2026-03-28 21:56:51

### 77. `miracle_picks2` — ~249 rows (0MB + 0MB idx)
**Purpose:** Picks: Storage

**Columns (22):** `id` (int), `ticker` (varchar(10)), `strategy_name` (varchar(100)), `scan_date` (date), `scan_time` (datetime), `entry_price` (decimal(12,4)), `stop_loss_price` (decimal(12,4)), `take_profit_price` (decimal(12,4)), `stop_loss_pct` (decimal(5,2)), `take_profit_pct` (decimal(5,2)), `score` (int), `confidence` (varchar(20)) … +10 more

**Primary Key:** `id`
**Indexed:** `ticker`, `strategy_name`, `scan_date`, `outcome`, `pick_hash`

**`outcome` distribution:**
- `loser`: 117
- `expired`: 115
- `winner`: 14
- `pending`: 3

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AMZN",
  "strategy_name": "Mean Reversion Sniper",
  "scan_date": "2026-02-09",
  "scan_time": "2026-02-09 18:51:39",
  "entry_price": 210.2,
  "stop_loss_price": 203.4316,
  "take_profit_price": 235.1928,
  "stop_loss_pct": 3.22,
  "take_profit_pct": 11.89,
  "score": 78,
  "confidence": "high",
  "signals_json": "{\"zscore\":-2.5271,\"sma20\":235.1875,\"sma50\":232.912,\"vol_ratio\":1.22}",
  "is_cdr": 1,
  "questrade_fee": 0.0,
  "net_profit_if_tp": 118.9,
  "risk_reward_ratio": 3.69,
  "outcome": "loser",
  "outcome_price": 203.4316,
  "outcome_pct": -3.22,
  "outcome_date": "2026-02-11",
  "pick_hash": "9ba0d1fc6910f9e5164e93ac0e2a02bd2a4d4000"
}
{
  "id": 2,
  "ticker": "SMCI",
  "strategy_name": "Earnings Catalyst Runner",
  "scan_date": "2026-02-09",
  "scan_time": "2026-02-09 18:51:39",
  "entry_price": 33.72,
  "stop_loss_price": 32.034,
  "take_profit_price": 37.092,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "score": 60,
  "confidence": "medium",
  "signals_json": "{\"catalyst_return\":13.78,\"catalyst_vol_ratio\":3.59,\"days_ago\":3}",
  "is_cdr": 0,
  "questrade_fee": 34.43,
  "net_profit_if_tp": 65.57,
  "risk_reward_ratio": 2.0,
  "outcome": "loser",
  "outcome_price": 32.034,
  "outcome_pct": -5.0,
  "outcome_date": "2026-02-11",
  "pick_hash": "95315a95c24b41da65a43addb9f1595852fd02ae"
}
```

**`scan_date` range:** 2026-02-09 → 2026-05-06

**`scan_time` range:** 2026-02-09 18:51:39 → 2026-05-06 23:53:56

### 78. `alpha_earnings` — ~242 rows (0MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (8):** `id` (int), `ticker` (varchar(10)), `quarter_end` (date), `eps_actual` (decimal(12,4)), `eps_estimate` (decimal(12,4)), `eps_surprise` (decimal(12,4)), `surprise_pct` (decimal(12,4)), `fetch_date` (date)

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "quarter_end": "2025-03-31",
  "eps_actual": 1.65,
  "eps_estimate": 1.6225,
  "eps_surprise": 0.03,
  "surprise_pct": 0.0169,
  "fetch_date": "2026-04-27"
}
{
  "id": 2,
  "ticker": "AAPL",
  "quarter_end": "2025-06-30",
  "eps_actual": 1.57,
  "eps_estimate": 1.4257,
  "eps_surprise": 0.14,
  "surprise_pct": 0.1012,
  "fetch_date": "2026-04-27"
}
```

**`fetch_date` range:** 2026-02-09 → 2026-04-27

### 79. `lm_sports_daily_picks` — ~222 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (21):** `id` (int), `pick_date` (date), `generated_at` (datetime), `sport` (varchar(50)), `event_id` (varchar(100)), `home_team` (varchar(100)), `away_team` (varchar(100)), `commence_time` (datetime), `market` (varchar(20)), `pick_type` (varchar(50)), `outcome_name` (varchar(100)), `best_book` (varchar(50)) … +9 more

**Primary Key:** `id`
**Indexed:** `pick_date`, `sport`, `event_id`, `result`

**Sample Rows:**
```json
{
  "id": 1,
  "pick_date": "2026-02-11",
  "generated_at": "2026-02-11 03:15:58",
  "sport": "basketball_ncaab",
  "event_id": "692fd5cbb5f2ed0afb60dcab3935315c",
  "home_team": "Gonzaga Bulldogs",
  "away_team": "Washington St Cougars",
  "commence_time": "2026-02-11 04:00:00",
  "market": "h2h",
  "pick_type": "Washington St Cougars ML",
  "outcome_name": "Washington St Cougars",
  "best_book": "Bovada",
  "best_book_key": "bovada",
  "best_odds": 17.0,
  "ev_pct": 3.72,
  "kelly_bet": 0.58,
  "algorithm": "value_bet",
  "confidence": "medium",
  "result": "lost",
  "pnl": -0.58,
  "all_odds": "[{\"book_key\":\"draftkings\",\"book_name\":\"DraftKings\",\"price\":15,\"is_canadian\":1},{\"book_key\":\"espnbet\",\"book_name\":\"ESPN BET\",\"price\":19,\"is_canadian\":1..."
}
{
  "id": 2,
  "pick_date": "2026-02-11",
  "generated_at": "2026-02-11 21:40:49",
  "sport": "basketball_ncaab",
  "event_id": "c65aa660af8547abf095efa913131765",
  "home_team": "Texas Tech Red Raiders",
  "away_team": "Colorado Buffaloes",
  "commence_time": "2026-02-12 01:00:00",
  "market": "h2h",
  "pick_type": "Colorado Buffaloes ML",
  "outcome_name": "Colorado Buffaloes",
  "best_book": "LowVig",
  "best_book_key": "lowvig",
  "best_odds": 8.95,
  "ev_pct": 3.42,
  "kelly_bet": 1.07,
  "algorithm": "value_bet",
  "confidence": "medium",
  "result": "lost",
  "pnl": -1.07,
  "all_odds": "[{\"book_key\":\"fanduel\",\"book_name\":\"FanDuel\",\"price\":7.8,\"is_canadian\":1},{\"book_key\":\"fliff\",\"book_name\":\"Fliff\",\"price\":7.35,\"is_canadian\":0},{\"book..."
}
```

**`pick_date` range:** 2026-02-11 → 2026-04-02

**`generated_at` range:** 2026-02-11 02:36:30 → 2026-04-02 03:53:23

### 80. `lm_market_regime` — ~213 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (18):** `id` (int), `date` (datetime), `hmm_regime` (varchar(20)), `hmm_confidence` (decimal(6,4)), `hmm_persistence` (decimal(6,4)), `hurst` (decimal(6,4)), `hurst_regime` (varchar(20)), `ewma_vol` (decimal(10,8)), `vol_annualized` (decimal(8,4)), `composite_score` (decimal(6,2)), `strategy_toggles` (text), `vix_level` (decimal(8,2)) … +6 more

**Primary Key:** `id`
**Indexed:** `date`, `hmm_regime`

**Sample Rows:**
```json
{
  "id": 1,
  "date": "2026-02-11 21:00:26",
  "hmm_regime": "sideways",
  "hmm_confidence": 0.9994,
  "hmm_persistence": 0.0,
  "hurst": 0.5599,
  "hurst_regime": "trending",
  "ewma_vol": 0.007437,
  "vol_annualized": 0.1181,
  "composite_score": 53.8,
  "strategy_toggles": "{\"momentum\":1,\"reversion\":0.2,\"fundamental\":1,\"sentiment\":0.5,\"ml_alpha\":0.5}",
  "vix_level": null,
  "vix_regime": "normal",
  "yield_curve": "normal",
  "yield_spread": null,
  "macro_score": 60.0,
  "ticker_regimes": "{\"AAPL\":{\"ticker\":\"AAPL\",\"hurst\":0.573,\"hurst_regime\":\"trending\",\"ewma_vol\":0.01361,\"vol_annualized\":0.2161,\"trend_score\":100,\"sma50\":268.28,\"sma200\":...",
  "created_at": "2026-02-11 21:00:26"
}
{
  "id": 2,
  "date": "2026-02-11 21:01:06",
  "hmm_regime": "sideways",
  "hmm_confidence": 0.9994,
  "hmm_persistence": 0.0,
  "hurst": 0.5599,
  "hurst_regime": "trending",
  "ewma_vol": 0.007436,
  "vol_annualized": 0.1181,
  "composite_score": 53.8,
  "strategy_toggles": "{\"momentum\":1,\"reversion\":0.2,\"fundamental\":1,\"sentiment\":0.5,\"ml_alpha\":0.5}",
  "vix_level": null,
  "vix_regime": "normal",
  "yield_curve": "normal",
  "yield_spread": null,
  "macro_score": 60.0,
  "ticker_regimes": "{\"AAPL\":{\"ticker\":\"AAPL\",\"hurst\":0.573,\"hurst_regime\":\"trending\",\"ewma_vol\":0.01361,\"vol_annualized\":0.2161,\"trend_score\":100,\"sma50\":268.28,\"sma200\":...",
  "created_at": "2026-02-11 21:01:06"
}
```

**`date` range:** 2026-02-11 21:00:26 → 2026-05-08 12:00:52

**`created_at` range:** 2026-02-11 21:00:26 → 2026-05-08 12:00:52

### 81. `lm_trades` — ~200 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (27):** `id` (int), `asset_class` (varchar(10)), `symbol` (varchar(20)), `algorithm_name` (varchar(100)), `signal_id` (int), `direction` (varchar(10)), `entry_time` (datetime), `entry_price` (decimal(18,8)), `position_size_units` (decimal(18,8)), `position_value_usd` (decimal(12,2)), `target_tp_pct` (decimal(6,2)), `target_sl_pct` (decimal(6,2)) … +15 more

**Primary Key:** `id`
**Indexed:** `asset_class`, `symbol`, `signal_id`, `entry_time`, `status`

**`asset_class` distribution:**
- `STOCK`: 70
- `FOREX`: 66
- `CRYPTO`: 64

**`direction` distribution:**
- `LONG`: 135
- `SHORT`: 65

**`status` distribution:**
- `closed`: 199
- `open`: 1

**Sample Rows:**
```json
{
  "id": 1,
  "asset_class": "FOREX",
  "symbol": "USDJPY",
  "algorithm_name": "Consensus",
  "signal_id": 4,
  "direction": "LONG",
  "entry_time": "2026-02-09 22:17:24",
  "entry_price": 155.86485,
  "position_size_units": 3.20790736,
  "position_value_usd": 500.0,
  "target_tp_pct": 3.0,
  "target_sl_pct": 2.0,
  "max_hold_hours": 12,
  "current_price": 155.13982,
  "unrealized_pnl_usd": 0.0,
  "unrealized_pct": 0.0,
  "highest_price": 156.16916,
  "lowest_price": 155.13087,
  "status": "closed",
  "exit_time": "2026-02-10 10:41:09",
  "exit_price": 155.13982,
  "exit_reason": "max_hold",
  "realized_pnl_usd": -2.33,
  "realized_pct": -0.4652,
  "fees_usd": 0.0,
  "hold_hours": 12.4,
  "created_at": "2026-02-09 22:17:24"
}
{
  "id": 2,
  "asset_class": "FOREX",
  "symbol": "EURUSD",
  "algorithm_name": "RSI Reversal",
  "signal_id": 1,
  "direction": "LONG",
  "entry_time": "2026-02-09 22:17:31",
  "entry_price": 1.19126,
  "position_size_units": 419.72365395,
  "position_value_usd": 500.0,
  "target_tp_pct": 2.0,
  "target_sl_pct": 1.0,
  "max_hold_hours": 6,
  "current_price": 1.19085,
  "unrealized_pnl_usd": 0.0,
  "unrealized_pct": 0.0,
  "highest_price": 1.19158,
  "lowest_price": 1.1905,
  "status": "closed",
  "exit_time": "2026-02-10 05:18:36",
  "exit_price": 1.19085,
  "exit_reason": "max_hold",
  "realized_pnl_usd": -0.17,
  "realized_pct": -0.0344,
  "fees_usd": 0.0,
  "hold_hours": 7.02,
  "created_at": "2026-02-09 22:17:31"
}
```

**`entry_time` range:** 2026-02-09 22:17:24 → 2026-05-06 23:59:04

**`exit_time` range:** 2026-02-10 05:18:36 → 2026-05-06 23:58:57

### 82. `lm_hour_learning` — ~195 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (17):** `id` (int), `asset_class` (varchar(10)), `algorithm_name` (varchar(100)), `calc_date` (date), `best_tp_pct` (decimal(6,2)), `best_sl_pct` (decimal(6,2)), `best_hold_hours` (int), `best_return_pct` (decimal(10,4)), `best_win_rate` (decimal(5,2)), `best_profit_factor` (decimal(8,4)), `trades_tested` (int), `profitable_combos` (int) … +5 more

**Primary Key:** `id`
**Indexed:** `asset_class`

**`asset_class` distribution:**
- `STOCK`: 72
- `FOREX`: 71
- `CRYPTO`: 52

**Sample Rows:**
```json
{
  "id": 1,
  "asset_class": "CRYPTO",
  "algorithm_name": "",
  "calc_date": "2026-02-15",
  "best_tp_pct": 0.5,
  "best_sl_pct": 3.0,
  "best_hold_hours": 1,
  "best_return_pct": -0.2641,
  "best_win_rate": 0.0,
  "best_profit_factor": 0.0,
  "trades_tested": 1,
  "profitable_combos": 0,
  "total_combos": 392,
  "current_wr": 0.0,
  "optimized_wr": 0.0,
  "verdict": "NO_PROFITABLE_PARAMS",
  "created_at": "2026-02-15 04:26:40"
}
{
  "id": 2,
  "asset_class": "CRYPTO",
  "algorithm_name": "Alpha Predator",
  "calc_date": "2026-02-15",
  "best_tp_pct": 0.5,
  "best_sl_pct": 0.3,
  "best_hold_hours": 1,
  "best_return_pct": -0.6,
  "best_win_rate": 0.0,
  "best_profit_factor": 0.0,
  "trades_tested": 2,
  "profitable_combos": 0,
  "total_combos": 392,
  "current_wr": 0.0,
  "optimized_wr": 0.0,
  "verdict": "NO_PROFITABLE_PARAMS",
  "created_at": "2026-02-15 04:26:40"
}
```

**`calc_date` range:** 2026-02-15 → 2026-05-03

**`created_at` range:** 2026-02-15 04:26:40 → 2026-05-03 03:03:38

### 83. `alpha_macro` — ~181 rows (0MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (14):** `id` (int), `trade_date` (date), `vix_close` (decimal(12,4)), `spy_close` (decimal(12,4)), `spy_sma50` (decimal(12,4)), `spy_sma200` (decimal(12,4)), `tnx_close` (decimal(12,4)), `two_yr_yield` (decimal(12,4)), `yield_spread` (decimal(12,4)), `dxy_close` (decimal(12,4)), `dxy_sma50` (decimal(12,4)), `regime` (varchar(50)) … +2 more

**Primary Key:** `id`
**Indexed:** `trade_date`

**Sample Rows:**
```json
{
  "id": 1,
  "trade_date": "2025-08-11",
  "vix_close": 0.0,
  "spy_close": 0.0,
  "spy_sma50": 0.0,
  "spy_sma200": 0.0,
  "tnx_close": 4.273,
  "two_yr_yield": 4.143,
  "yield_spread": 0.13,
  "dxy_close": 98.52,
  "dxy_sma50": 98.1979,
  "regime": "unknown",
  "regime_score": 50,
  "regime_detail": "{\"vix\":0,\"spy\":0,\"tnx\":4.273,\"yield_spread\":0.13,\"dxy\":98.52,\"spy_above_sma50\":0,\"dxy_above_sma50\":1}"
}
{
  "id": 2,
  "trade_date": "2025-08-12",
  "vix_close": 0.0,
  "spy_close": 0.0,
  "spy_sma50": 0.0,
  "spy_sma200": 0.0,
  "tnx_close": 4.293,
  "two_yr_yield": 4.13,
  "yield_spread": 0.163,
  "dxy_close": 98.1,
  "dxy_sma50": 98.1385,
  "regime": "unknown",
  "regime_score": 50,
  "regime_detail": "{\"vix\":0,\"spy\":0,\"tnx\":4.293,\"yield_spread\":0.163,\"dxy\":98.1,\"spy_above_sma50\":0,\"dxy_above_sma50\":0}"
}
```

**`trade_date` range:** 2025-08-11 → 2026-04-27

### 84. `daytrader_sim_days` — ~176 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (16):** `id` (int), `sim_date` (date), `budget` (decimal(12,2)), `picks_used` (int), `total_invested` (decimal(12,2)), `total_pnl` (decimal(12,2)), `return_pct` (decimal(10,4)), `wins` (int), `losses` (int), `best_pick_ticker` (varchar(10)), `best_pick_pct` (decimal(10,4)), `worst_pick_ticker` (varchar(10)) … +4 more

**Primary Key:** `id`
**Indexed:** `sim_date`

**Sample Rows:**
```json
{
  "id": 1,
  "sim_date": "2026-02-09",
  "budget": 500.0,
  "picks_used": 5,
  "total_invested": 1377.41,
  "total_pnl": 0.0,
  "return_pct": 0.0,
  "wins": 0,
  "losses": 5,
  "best_pick_ticker": "META",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "META",
  "worst_pick_pct": 0.0,
  "algo_version": "original",
  "cumulative_pnl": 0.0,
  "created_at": "2026-02-09 20:41:33"
}
{
  "id": 2,
  "sim_date": "2026-02-09",
  "budget": 500.0,
  "picks_used": 5,
  "total_invested": 1377.41,
  "total_pnl": 0.0,
  "return_pct": 0.0,
  "wins": 0,
  "losses": 5,
  "best_pick_ticker": "META",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "META",
  "worst_pick_pct": 0.0,
  "algo_version": "revised",
  "cumulative_pnl": 0.0,
  "created_at": "2026-02-09 20:41:33"
}
```

**`sim_date` range:** 2026-02-09 → 2026-04-27

**`created_at` range:** 2026-02-09 20:41:33 → 2026-04-27 23:57:00

### 85. `at_incubator_strategies` — ~174 rows (1MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (18):** `perm_id` (varchar(20)), `archetype` (varchar(80)), `seed_strategy` (varchar(100)), `params_json` (json), `combined_sharpe` (decimal(10,4)), `combined_sortino` (decimal(10,4)), `combined_max_dd` (decimal(10,6)), `combined_pf` (decimal(10,4)), `combined_wr` (decimal(6,4)), `combined_trades` (int), `combined_return` (decimal(10,6)), `composite_score` (decimal(10,4)) … +6 more

**Primary Key:** `perm_id`
**Indexed:** `archetype`, `composite_score`, `status`

**`status` distribution:**
- `PAPER_READY`: 225
- `INCUBATOR`: 44

**Sample Rows:**
```json
{
  "perm_id": "00a6494d84f2",
  "archetype": "ichimoku_cloud",
  "seed_strategy": "",
  "params_json": "{\"sl_atr_mult\": 2.589504, \"tp_atr_mult\": 2.132936, \"displacement\": 30, \"kijun_period\": 30, \"max_hold_days\": 7, \"tenkan_period\": 25, \"senkou_b_period\":...",
  "combined_sharpe": 8.088,
  "combined_sortino": 19.245,
  "combined_max_dd": -0.095948,
  "combined_pf": 40.642,
  "combined_wr": 0.4667,
  "combined_trades": 12,
  "combined_return": -0.011195,
  "composite_score": 0.5507,
  "status": "PAPER_READY",
  "ready_for_paper": 1,
  "rejection_reasons": "",
  "per_symbol_json": "{\"BNB-USD\": {\"wins\": 1, \"losses\": 2, \"params\": {\"sl_atr_mult\": 2.589504, \"tp_atr_mult\": 2.132936, \"displacement\": 30, \"kijun_period\": 30, \"max_hold_da...",
  "created_at": "2026-03-22 06:25:28",
  "updated_at": "2026-05-08 06:44:13"
}
{
  "perm_id": "00c6d7704588",
  "archetype": "ichimoku_cloud",
  "seed_strategy": "",
  "params_json": "{\"sl_atr_mult\": 2.718296, \"tp_atr_mult\": 3.702169, \"displacement\": 25, \"kijun_period\": 47, \"max_hold_days\": 13, \"tenkan_period\": 14, \"senkou_b_period\"...",
  "combined_sharpe": 12.435,
  "combined_sortino": 12.435,
  "combined_max_dd": -0.092899,
  "combined_pf": 39.648,
  "combined_wr": 0.5,
  "combined_trades": 10,
  "combined_return": -0.052156,
  "composite_score": 0.5571,
  "status": "PAPER_READY",
  "ready_for_paper": 1,
  "rejection_reasons": "",
  "per_symbol_json": "{\"BNB-USD\": {\"wins\": 1, \"losses\": 1, \"params\": {\"sl_atr_mult\": 2.718296, \"tp_atr_mult\": 3.702169, \"displacement\": 25, \"kijun_period\": 47, \"max_hold_da...",
  "created_at": "2026-03-24 06:56:11",
  "updated_at": "2026-05-04 07:08:55"
}
```

**`created_at` range:** 2026-03-10 06:18:23 → 2026-05-08 06:44:22

**`updated_at` range:** 2026-03-13 06:20:42 → 2026-05-08 06:44:25

### 86. `cp_signals` — ~174 rows (0MB + 0MB idx)
**Purpose:** Signals: Tracking

**Columns (11):** `id` (int), `pair` (varchar(15)), `strategy_name` (varchar(100)), `signal_date` (date), `signal_time` (datetime), `direction` (varchar(10)), `entry_price` (decimal(18,8)), `stop_loss_price` (decimal(18,8)), `take_profit_price` (decimal(18,8)), `signal_hash` (varchar(64)), `score` (int)

**Primary Key:** `id`
**Indexed:** `pair`, `strategy_name`, `signal_date`

**`direction` distribution:**
- `long`: 174

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "AAVE-USD",
  "strategy_name": "Trend Following",
  "signal_date": "2025-02-09",
  "signal_time": "2026-02-09 06:18:44",
  "direction": "long",
  "entry_price": 239.33306885,
  "stop_loss_price": 0.0,
  "take_profit_price": 0.0,
  "signal_hash": "51f0838d746a25e4c353101f0e6cc81b67b75bfd",
  "score": 0
}
{
  "id": 2,
  "pair": "AAVE-USD",
  "strategy_name": "Trend Following",
  "signal_date": "2025-03-01",
  "signal_time": "2026-02-09 06:18:44",
  "direction": "long",
  "entry_price": 192.57632446,
  "stop_loss_price": 0.0,
  "take_profit_price": 0.0,
  "signal_hash": "654bf3116632e1b190997c8b13747a97c8e70a97",
  "score": 0
}
```

**`signal_date` range:** 2025-02-09 → 2026-02-01

**`signal_time` range:** 2026-02-09 06:18:44 → 2026-02-09 06:18:45

### 87. `lm_intelligence` — ~169 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (8):** `id` (int), `metric_name` (varchar(100)), `asset_class` (varchar(20)), `symbol` (varchar(30)), `metric_value` (decimal(18,8)), `metric_label` (varchar(100)), `metadata` (text), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `metric_name`, `asset_class`, `symbol`, `updated_at`

**`asset_class` distribution:**
- `STOCK`: 146
- `ALL`: 14
- `CRYPTO`: 7
- `FOREX`: 2

**Sample Rows:**
```json
{
  "id": 1,
  "metric_name": "test_metric",
  "asset_class": "ALL",
  "symbol": "",
  "metric_value": 42.0,
  "metric_label": "test",
  "metadata": "",
  "updated_at": "2026-02-11 05:23:26"
}
{
  "id": 2,
  "metric_name": "test_py2",
  "asset_class": "ALL",
  "symbol": "",
  "metric_value": 99.0,
  "metric_label": "test_python",
  "metadata": "",
  "updated_at": "2026-02-11 05:23:42"
}
```

**`updated_at` range:** 2026-02-11 05:23:26 → 2026-05-08 12:00:51

### 88. `eh_grade_history` — ~168 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `engine_name` (varchar(60)), `health_score` (float), `health_grade` (varchar(2)), `win_rate` (float), `total_pnl` (float), `resolved_signals` (int), `snapshot_at` (datetime)

**Primary Key:** `id`
**Indexed:** `engine_name`

**Sample Rows:**
```json
{
  "id": 1,
  "engine_name": "Hybrid Engine",
  "health_score": 84.9,
  "health_grade": "A",
  "win_rate": 100.0,
  "total_pnl": 45.8121,
  "resolved_signals": 4,
  "snapshot_at": "2026-02-14 21:20:50"
}
{
  "id": 2,
  "engine_name": "TV Technicals",
  "health_score": 62.2,
  "health_grade": "C",
  "win_rate": 43.1,
  "total_pnl": -13.1852,
  "resolved_signals": 51,
  "snapshot_at": "2026-02-14 21:20:50"
}
```

### 89. `stocks` — ~153 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (4):** `ticker` (varchar(10)), `company_name` (varchar(200)), `sector` (varchar(100)), `market_cap` (varchar(20))

**Primary Key:** `ticker`

**Sample Rows:**
```json
{
  "ticker": "GM",
  "company_name": "General Motors Company",
  "sector": "",
  "market_cap": ""
}
{
  "ticker": "PFE",
  "company_name": "Pfizer Inc.",
  "sector": "Healthcare",
  "market_cap": ""
}
```

### 90. `algorithms` — ~142 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20)), `pros` (text), `cons` (text)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "CAN SLIM",
  "family": "CAN SLIM",
  "description": "O'Neil growth screener. RS Rating >=90, Stage-2 Uptrend, 52W High proximity, volume surge.",
  "algo_type": "growth",
  "ideal_timeframe": "3m",
  "pros": null,
  "cons": null
}
{
  "id": 2,
  "name": "CAN SLIM + 1",
  "family": "CAN SLIM",
  "description": "CAN SLIM variant with additional momentum filter.",
  "algo_type": "growth",
  "ideal_timeframe": "3m",
  "pros": null,
  "cons": null
}
```

**`ideal_timeframe` range:** 10d → 90d

### 91. `gm_news_sentiment` — ~140 rows (0MB + 0MB idx)
**Purpose:** Goldmine: Unified picks

**Columns (13):** `id` (int), `ticker` (varchar(10)), `fetch_date` (date), `articles_analyzed` (int), `sentiment_score` (decimal(6,4)), `positive_count` (int), `negative_count` (int), `neutral_count` (int), `buzz_score` (decimal(8,4)), `sector_avg_sentiment` (decimal(6,4)), `relative_sentiment` (decimal(6,4)), `source` (varchar(20)) … +1 more

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`, `sentiment_score`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "fetch_date": "2026-02-11",
  "articles_analyzed": 248,
  "sentiment_score": 0.2258,
  "positive_count": 100,
  "negative_count": 44,
  "neutral_count": 104,
  "buzz_score": 35.43,
  "sector_avg_sentiment": 0.1795,
  "relative_sentiment": 0.0463,
  "source": "finnhub",
  "created_at": "2026-02-11 01:18:56"
}
{
  "id": 2,
  "ticker": "MSFT",
  "fetch_date": "2026-02-11",
  "articles_analyzed": 249,
  "sentiment_score": 0.1606,
  "positive_count": 92,
  "negative_count": 52,
  "neutral_count": 105,
  "buzz_score": 35.57,
  "sector_avg_sentiment": 0.1795,
  "relative_sentiment": -0.0189,
  "source": "finnhub",
  "created_at": "2026-02-11 01:18:56"
}
```

**`fetch_date` range:** 2026-02-11 → 2026-02-16

**`sentiment_score` range:** -0.1235 → 0.4583

### 92. `miracle_results2` — ~140 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (21):** `id` (int), `portfolio_id` (int), `strategy_name` (varchar(100)), `period` (varchar(20)), `calc_date` (date), `total_picks` (int), `winners` (int), `losers` (int), `pending_count` (int), `win_rate` (decimal(5,2)), `avg_gain_pct` (decimal(10,4)), `avg_loss_pct` (decimal(10,4)) … +9 more

**Primary Key:** `id`
**Indexed:** `strategy_name`, `calc_date`

**Sample Rows:**
```json
{
  "id": 1,
  "portfolio_id": 0,
  "strategy_name": "_overall",
  "period": "daily",
  "calc_date": "2026-02-09",
  "total_picks": 25,
  "winners": 0,
  "losers": 0,
  "pending_count": 25,
  "win_rate": 0.0,
  "avg_gain_pct": 0.0,
  "avg_loss_pct": 0.0,
  "total_pnl": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "expectancy": 0.0,
  "created_at": "2026-02-09 22:49:05"
}
{
  "id": 2,
  "portfolio_id": 0,
  "strategy_name": "_overall",
  "period": "daily",
  "calc_date": "2026-02-10",
  "total_picks": 50,
  "winners": 0,
  "losers": 0,
  "pending_count": 50,
  "win_rate": 0.0,
  "avg_gain_pct": 0.0,
  "avg_loss_pct": 0.0,
  "total_pnl": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "expectancy": 0.0,
  "created_at": "2026-02-10 03:31:01"
}
```

**`calc_date` range:** 2026-02-09 → 2026-05-07

**`created_at` range:** 2026-02-09 22:49:05 → 2026-05-07 23:54:20

### 93. `lm_breaker_log` — ~133 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (10):** `id` (int), `trigger_time` (datetime), `breaker_type` (varchar(50)), `trigger_value` (varchar(200)), `threshold` (varchar(100)), `action_taken` (varchar(200)), `is_active` (tinyint), `expires_at` (datetime), `resolved_at` (datetime), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `trigger_time`, `breaker_type`, `is_active`

**Sample Rows:**
```json
{
  "id": 1,
  "trigger_time": "2026-02-14 08:16:29",
  "breaker_type": "loss_streak",
  "trigger_value": "5 consecutive losses",
  "threshold": "5 consecutive losses",
  "action_taken": "Pause all trading for 3 hours",
  "is_active": 0,
  "expires_at": "2026-02-14 11:16:29",
  "resolved_at": "2026-02-14 11:28:55",
  "created_at": "2026-02-14 08:16:29"
}
{
  "id": 2,
  "trigger_time": "2026-02-14 22:46:51",
  "breaker_type": "loss_streak",
  "trigger_value": "5 consecutive losses",
  "threshold": "5 consecutive losses",
  "action_taken": "Pause all trading for 3 hours",
  "is_active": 0,
  "expires_at": "2026-02-15 01:46:51",
  "resolved_at": "2026-02-15 02:46:51",
  "created_at": "2026-02-14 22:46:51"
}
```

**`trigger_time` range:** 2026-02-14 08:16:29 → 2026-04-29 11:15:40

**`resolved_at` range:** 2026-02-14 11:28:55 → 2026-04-29 14:27:59

### 94. `lm_sports_credit_usage` — ~132 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `request_time` (datetime), `sport` (varchar(50)), `credits_used` (int), `credits_remaining` (int)

**Primary Key:** `id`
**Indexed:** `request_time`

**Sample Rows:**
```json
{
  "id": 1,
  "request_time": "2026-02-10 22:07:50",
  "sport": "americanfootball_ncaaf",
  "credits_used": 6,
  "credits_remaining": 494
}
{
  "id": 2,
  "request_time": "2026-02-10 22:07:51",
  "sport": "basketball_nba",
  "credits_used": 6,
  "credits_remaining": 488
}
```

**`request_time` range:** 2026-02-10 22:07:50 → 2026-04-02 03:53:22

### 95. `challenge_200_days` — ~124 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (21):** `id` (int), `challenge_date` (date), `mode` (varchar(20)), `capital` (decimal(12,2)), `picks_count` (int), `total_invested` (decimal(12,2)), `daily_pnl` (decimal(12,2)), `daily_return_pct` (decimal(10,4)), `target_amount` (decimal(12,2)), `target_hit` (int), `wins` (int), `losses` (int) … +9 more

**Primary Key:** `id`
**Indexed:** `challenge_date`, `mode`

**Sample Rows:**
```json
{
  "id": 1,
  "challenge_date": "2026-02-10",
  "mode": "consensus",
  "capital": 5000.0,
  "picks_count": 5,
  "total_invested": 5000.0,
  "daily_pnl": -13.12,
  "daily_return_pct": -0.2624,
  "target_amount": 200.0,
  "target_hit": 0,
  "wins": 2,
  "losses": 3,
  "best_pick": "JNJ",
  "best_pick_pct": 1.7303,
  "worst_pick": "NVDA",
  "worst_pick_pct": -1.9978,
  "cumulative_pnl": -13.12,
  "cumulative_days": 1,
  "win_streak": -1,
  "lessons_json": "{\"trades\":[\"XOM: +0.2727%\",\"JNJ: +1.7303%\",\"NVDA: -1.9978%\",\"GOOGL: -1.2268%\",\"UPS: -0.0904%\"],\"mode\":\"consensus\"}",
  "created_at": "2026-02-10 13:00:42"
}
{
  "id": 2,
  "challenge_date": "2026-02-10",
  "mode": "ml",
  "capital": 5000.0,
  "picks_count": 5,
  "total_invested": 5000.01,
  "daily_pnl": 19.95,
  "daily_return_pct": 0.399,
  "target_amount": 200.0,
  "target_hit": 0,
  "wins": 3,
  "losses": 2,
  "best_pick": "AAPL",
  "best_pick_pct": 3.2171,
  "worst_pick": "NVDA",
  "worst_pick_pct": -1.9978,
  "cumulative_pnl": 19.95,
  "cumulative_days": 1,
  "win_streak": 1,
  "lessons_json": "{\"trades\":[\"XOM: +0.2727%\",\"JNJ: +1.7303%\",\"NVDA: -1.9978%\",\"AAPL: +3.2171%\",\"GOOGL: -1.2268%\"],\"mode\":\"ml\"}",
  "created_at": "2026-02-10 13:00:42"
}
```

**`challenge_date` range:** 2026-02-10 → 2026-04-27

**`created_at` range:** 2026-02-10 13:00:42 → 2026-04-27 23:57:01

### 96. `at_signal_outcomes` — ~121 rows (0MB + 0MB idx)
**Purpose:** Audit: Signal outcome tracking

**Columns (15):** `id` (int), `symbol` (varchar(50)), `direction` (varchar(10)), `entry_price` (decimal(18,8)), `take_profit` (decimal(18,8)), `stop_loss` (decimal(18,8)), `exit_price` (decimal(18,8)), `outcome` (varchar(20)), `pnl_pct` (decimal(10,4)), `source_system` (varchar(100)), `strategy` (varchar(100)), `asset_class` (varchar(20)) … +3 more

**Primary Key:** `id`
**Indexed:** `symbol`, `outcome`, `source_system`

**`direction` distribution:**
- `LONG`: 106
- `SHORT`: 15

**`outcome` distribution:**
- `LOSS`: 49
- `OPEN`: 38
- `EXPIRED`: 13
- `WIN`: 13
- `CLOSED`: 6
- `SL_HIT`: 2

**`source_system` distribution:**
- `kimi_riseoftheclaw`: 39
- `kimi_signal_tracker`: 23
- `opposite_day`: 15
- `paper_trading`: 10
- `bundle_babies`: 6
- `Funding Rate Carry`: 4
- `paper_alpha_arena`: 4
- `paper_kimi_academic`: 4
- `paper_leap`: 4
- `paper_correlation`: 3
- `paper_hoffman_irb`: 3
- `Correlation - KAMA Adaptive`: 2

**`strategy` distribution:**
- `None`: 38
- `funding_rate_carry`: 13
- `corr_vwap_reversion`: 4
- `leap_elliott_impulse`: 4
- `cci-crypto-reversal`: 4
- `keltner-bounce`: 4
- `crypto-fear-reversal-scout`: 4
- `crypto-bb-squeeze-scout`: 3
- `williams-r-scout`: 3
- `bollinger-squeeze`: 3
- `stocktwits-bull-scout`: 3
- `alpha_drawdown_responsive`: 3

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "ATOM-USD",
  "direction": "LONG",
  "entry_price": 2.23789716,
  "take_profit": 2.577023,
  "stop_loss": 2.034422,
  "exit_price": 1.834,
  "outcome": "LOSS",
  "pnl_pct": -18.0481,
  "source_system": "kimi_signal_tracker",
  "strategy": null,
  "asset_class": "CRYPTO",
  "opened_at": null,
  "closed_at": null,
  "created_at": "2026-03-04 17:59:31"
}
{
  "id": 2,
  "symbol": "APT21794-USD",
  "direction": "LONG",
  "entry_price": 0.92000026,
  "take_profit": 1.136049,
  "stop_loss": 0.790371,
  "exit_price": 0.948,
  "outcome": "WIN",
  "pnl_pct": 3.0434,
  "source_system": "kimi_signal_tracker",
  "strategy": null,
  "asset_class": "CRYPTO",
  "opened_at": null,
  "closed_at": null,
  "created_at": "2026-03-04 17:59:31"
}
```

**`closed_at` range:** 2026-03-04 05:36:47 → 2026-03-04 08:47:58

**`created_at` range:** 2026-03-04 17:59:31 → 2026-03-05 17:51:05

### 97. `stock_fundamentals` — ~119 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (28):** `id` (int), `ticker` (varchar(10)), `trailing_eps` (decimal(10,4)), `forward_eps` (decimal(10,4)), `trailing_pe` (decimal(10,4)), `forward_pe` (decimal(10,4)), `peg_ratio` (decimal(10,4)), `dividend_rate` (decimal(10,4)), `dividend_yield` (decimal(10,6)), `trailing_annual_div_rate` (decimal(10,4)), `trailing_annual_div_yield` (decimal(10,6)), `five_yr_avg_div_yield` (decimal(10,6)) … +16 more

**Primary Key:** `id`
**Indexed:** `ticker`

**Sample Rows:**
```json
{
  "id": 2116,
  "ticker": "AAPL",
  "trailing_eps": 7.89,
  "forward_eps": 9.3519,
  "trailing_pe": 33.9176,
  "forward_pe": 28.6156,
  "peg_ratio": 2.44,
  "dividend_rate": 1.04,
  "dividend_yield": 0.0038,
  "trailing_annual_div_rate": 1.03,
  "trailing_annual_div_yield": 0.0038,
  "five_yr_avg_div_yield": 0.51,
  "payout_ratio": 0.1304,
  "ex_dividend_date": "2026-02-09",
  "next_earnings_date": "2026-04-30",
  "price_to_book": 44.6165,
  "enterprise_to_revenue": 9.073,
  "total_revenue": 435617005568,
  "ebitda": 152901992448,
  "total_debt": 90509000704,
  "current_ratio": 0.974,
  "roe": 1.5202,
  "gross_margins": 0.4733,
  "operating_margins": 0.3537,
  "recommendation_key": "buy",
  "target_mean_price": 297.7055,
  "source": "yahoo_v10",
  "updated_at": "2026-04-27 23:50:10"
}
{
  "id": 2117,
  "ticker": "ABBV",
  "trailing_eps": 2.36,
  "forward_eps": 16.0752,
  "trailing_pe": 83.6356,
  "forward_pe": 12.2786,
  "peg_ratio": 0.47,
  "dividend_rate": 6.92,
  "dividend_yield": 0.0348,
  "trailing_annual_div_rate": 6.65,
  "trailing_annual_div_yield": 0.033466,
  "five_yr_avg_div_yield": 3.65,
  "payout_ratio": 2.7679,
  "ex_dividend_date": "2026-04-15",
  "next_earnings_date": "2026-04-29",
  "price_to_book": 0.0,
  "enterprise_to_revenue": 6.778,
  "total_revenue": 61160001536,
  "ebitda": 29254000640,
  "total_debt": 68400001024,
  "current_ratio": 0.671,
  "roe": 62.25,
  "gross_margins": 0.7162,
  "operating_margins": 0.3411,
  "recommendation_key": "buy",
  "target_mean_price": 249.2667,
  "source": "yahoo_v10",
  "updated_at": "2026-04-27 23:50:11"
}
```

**`ex_dividend_date` range:** 1995-04-27 → 2026-07-01

**`next_earnings_date` range:** 2025-12-18 → 2026-07-24

### 98. `whatif_scenarios` — ~114 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (6):** `id` (int), `scenario_name` (varchar(200)), `query_text` (text), `params_json` (text), `results_json` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "scenario_name": "momentum_ride",
  "query_text": "",
  "params_json": "{\"scenario\":\"momentum_ride\",\"algorithms\":\"\",\"take_profit\":50,\"stop_loss\":10,\"max_hold_days\":30,\"initial_capital\":10000,\"commission\":10,\"slippage\":0.5}",
  "results_json": "{\"total_trades\":25,\"winning_trades\":6,\"losing_trades\":19,\"win_rate\":24,\"avg_win_pct\":3.6951,\"avg_loss_pct\":5.0271,\"total_return_pct\":-5.5426,\"final_va...",
  "created_at": "2026-02-09 05:18:51"
}
{
  "id": 2,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"take_profit\":10,\"stop_loss\":5,\"max_hold_days\":7,\"initial_capital\":10000,\"commission\":10,\"slippage\":0.5}",
  "results_json": "{\"total_trades\":451,\"winning_trades\":33,\"losing_trades\":418,\"win_rate\":7.32,\"avg_win_pct\":1.6636,\"avg_loss_pct\":11.2195,\"total_return_pct\":-96.7769,\"f...",
  "created_at": "2026-02-09 17:16:44"
}
```

**`created_at` range:** 2026-02-09 05:18:51 → 2026-05-06 12:03:46

### 99. `fx_audit_log` — ~89 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "seed_signals",
  "details": "Seeded 195 signals, skipped 0 duplicates",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 06:18:44"
}
{
  "id": 2,
  "action_type": "backtest",
  "details": "Backtest: 183 trades, 1.77% return",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 06:18:55"
}
```

**`created_at` range:** 2026-02-09 06:18:44 → 2026-02-17 22:34:51

### 100. `lm_analyst_ratings` — ~84 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `ticker` (varchar(10)), `period` (date), `strong_buy` (int), `buy` (int), `hold` (int), `sell` (int), `strong_sell` (int), `fetch_date` (date), `created_at` (datetime), `source` (varchar(30))

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`

**Sample Rows:**
```json
{
  "id": 97,
  "ticker": "AAPL",
  "period": "2026-02-01",
  "strong_buy": 14,
  "buy": 21,
  "hold": 17,
  "sell": 2,
  "strong_sell": 0,
  "fetch_date": "2026-05-08",
  "created_at": "2026-02-11 02:52:26",
  "source": "finnhub"
}
{
  "id": 98,
  "ticker": "MSFT",
  "period": "2026-02-01",
  "strong_buy": 25,
  "buy": 37,
  "hold": 4,
  "sell": 0,
  "strong_sell": 0,
  "fetch_date": "2026-05-08",
  "created_at": "2026-02-11 02:52:26",
  "source": "finnhub"
}
```

**`fetch_date` range:** 2026-02-16 → 2026-05-08

**`created_at` range:** 2026-02-11 02:52:26 → 2026-05-06 11:31:12

### 101. `ss_baselines` — ~82 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (11):** `id` (int), `pair` (varchar(30)), `asset_class` (varchar(15)), `avg_volume_24h` (decimal(20,4)), `avg_price_change_1h` (decimal(8,4)), `avg_price_change_4h` (decimal(8,4)), `avg_price_change_24h` (decimal(8,4)), `volatility_1h` (decimal(8,4)), `volatility_24h` (decimal(8,4)), `scan_count` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `pair`

**`asset_class` distribution:**
- `CRYPTO`: 82

**Sample Rows:**
```json
{
  "id": 1,
  "pair": "BTC_USDT",
  "asset_class": "CRYPTO",
  "avg_volume_24h": 17485504085.182,
  "avg_price_change_1h": 0.1981,
  "avg_price_change_4h": 0.0,
  "avg_price_change_24h": 1.5511,
  "volatility_1h": 0.1095,
  "volatility_24h": 1.3267,
  "scan_count": 30,
  "updated_at": "2026-03-16 14:02:02"
}
{
  "id": 2,
  "pair": "ETH_USDT",
  "asset_class": "CRYPTO",
  "avg_volume_24h": 10630839577.723,
  "avg_price_change_1h": 0.2689,
  "avg_price_change_4h": 0.0,
  "avg_price_change_24h": 3.7282,
  "volatility_1h": 0.1859,
  "volatility_24h": 3.6934,
  "scan_count": 30,
  "updated_at": "2026-03-16 14:02:02"
}
```

**`updated_at` range:** 2026-02-15 22:44:32 → 2026-03-16 14:02:02

### 102. `lm_sports_ml_predictions` — ~79 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (16):** `id` (int), `value_bet_id` (int), `event_id` (varchar(100)), `sport` (varchar(50)), `home_team` (varchar(100)), `away_team` (varchar(100)), `outcome_name` (varchar(100)), `market` (varchar(20)), `ev_pct` (decimal(6,2)), `best_odds` (decimal(10,4)), `ml_win_prob` (decimal(6,4)), `ml_prediction` (varchar(20)) … +4 more

**Primary Key:** `id`
**Indexed:** `event_id`, `ml_win_prob`, `ml_prediction`, `predicted_at`

**Sample Rows:**
```json
{
  "id": 1,
  "value_bet_id": 2261,
  "event_id": "807a75ef0e64ad954b61a995289651d7",
  "sport": "basketball_ncaab",
  "home_team": "Gardner-Webb Bulldogs",
  "away_team": "Winthrop Eagles",
  "outcome_name": "Gardner-Webb Bulldogs",
  "market": "h2h",
  "ev_pct": 23.14,
  "best_odds": 17.0,
  "ml_win_prob": 0.1124,
  "ml_prediction": "skip",
  "ml_confidence": "low",
  "ml_should_bet": 0,
  "model_type": "php_heuristic_v1",
  "predicted_at": "2026-02-12 21:05:06"
}
{
  "id": 2,
  "value_bet_id": 2262,
  "event_id": "088f3788bb56116d37897dbf35a9c4f5",
  "sport": "soccer_usa_mls",
  "home_team": "Seattle Sounders FC",
  "away_team": "Colorado Rapids",
  "outcome_name": "Under",
  "market": "totals",
  "ev_pct": 18.58,
  "best_odds": 2.3,
  "ml_win_prob": 0.6055,
  "ml_prediction": "strong_take",
  "ml_confidence": "high",
  "ml_should_bet": 1,
  "model_type": "php_heuristic_v1",
  "predicted_at": "2026-02-12 21:05:06"
}
```

### 103. `miracle_results3` — ~78 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (21):** `id` (int), `portfolio_id` (int), `strategy_name` (varchar(100)), `period` (varchar(20)), `calc_date` (date), `total_picks` (int), `winners` (int), `losers` (int), `pending_count` (int), `win_rate` (decimal(5,2)), `avg_gain_pct` (decimal(10,4)), `avg_loss_pct` (decimal(10,4)) … +9 more

**Primary Key:** `id`
**Indexed:** `strategy_name`, `calc_date`

**Sample Rows:**
```json
{
  "id": 1,
  "portfolio_id": 0,
  "strategy_name": "_overall",
  "period": "daily",
  "calc_date": "2026-02-10",
  "total_picks": 30,
  "winners": 0,
  "losers": 0,
  "pending_count": 0,
  "win_rate": 0.0,
  "avg_gain_pct": 0.0,
  "avg_loss_pct": 0.0,
  "total_pnl": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "expectancy": 0.0,
  "created_at": "2026-02-10 03:23:39"
}
{
  "id": 2,
  "portfolio_id": 0,
  "strategy_name": "_overall",
  "period": "daily",
  "calc_date": "2026-02-10",
  "total_picks": 30,
  "winners": 0,
  "losers": 0,
  "pending_count": 0,
  "win_rate": 0.0,
  "avg_gain_pct": 0.0,
  "avg_loss_pct": 0.0,
  "total_pnl": 0.0,
  "best_pick_ticker": "",
  "best_pick_pct": 0.0,
  "worst_pick_ticker": "",
  "worst_pick_pct": 0.0,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "expectancy": 0.0,
  "created_at": "2026-02-10 03:23:48"
}
```

**`calc_date` range:** 2026-02-10 → 2026-05-07

**`created_at` range:** 2026-02-10 03:23:39 → 2026-05-07 23:54:26

### 104. `mf2_tracked_picks` — ~75 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (18):** `id` (int), `symbol` (varchar(20)), `algorithm_name` (varchar(100)), `pick_date` (date), `entry_nav` (decimal(12,4)), `current_nav` (decimal(12,4)), `current_return_pct` (decimal(8,4)), `status` (enum('open','closed')), `exit_date` (date), `exit_nav` (decimal(12,4)), `exit_reason` (varchar(50)), `final_return_pct` (decimal(8,4)) … +6 more

**Primary Key:** `id`
**Indexed:** `symbol`, `status`

**`status` distribution:**
- `open`: 40
- `closed`: 35

**Sample Rows:**
```json
{
  "id": 46,
  "symbol": "RBF460",
  "algorithm_name": "MF Quality Growth",
  "pick_date": "2025-03-15",
  "entry_nav": 44.3647,
  "current_nav": 43.551,
  "current_return_pct": -1.8341,
  "status": "closed",
  "exit_date": "2026-02-12",
  "exit_nav": 43.551,
  "exit_reason": "max_hold",
  "final_return_pct": -1.8341,
  "peak_nav": 44.3647,
  "trough_nav": 43.551,
  "hold_days": 334,
  "score": 78.0,
  "rating": "Buy",
  "created_at": "2026-02-12 23:50:23"
}
{
  "id": 47,
  "symbol": "TDB161",
  "algorithm_name": "MF Momentum",
  "pick_date": "2025-03-20",
  "entry_nav": 29.5828,
  "current_nav": 31.0324,
  "current_return_pct": 4.9001,
  "status": "closed",
  "exit_date": "2026-02-12",
  "exit_nav": 31.0324,
  "exit_reason": "max_hold",
  "final_return_pct": 4.9001,
  "peak_nav": 31.0324,
  "trough_nav": 29.5828,
  "hold_days": 329,
  "score": 72.0,
  "rating": "Buy",
  "created_at": "2026-02-12 23:50:23"
}
```

**`pick_date` range:** 2025-03-15 → 2026-02-15

**`exit_date` range:** 2026-02-12 → 2026-02-15

### 105. `lm_sports_bets` — ~74 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (26):** `id` (int), `event_id` (varchar(100)), `sport` (varchar(50)), `home_team` (varchar(100)), `away_team` (varchar(100)), `commence_time` (datetime), `game_date` (date), `bet_type` (varchar(30)), `market` (varchar(20)), `pick` (varchar(100)), `pick_point` (decimal(6,2)), `bookmaker` (varchar(50)) … +14 more

**Primary Key:** `id`
**Indexed:** `event_id`, `sport`, `game_date`, `algorithm`, `status`, `placed_at`

**`status` distribution:**
- `settled`: 74

**Sample Rows:**
```json
{
  "id": 1,
  "event_id": "0eca9e653250e1c78dfb71afa036a390",
  "sport": "basketball_ncaab",
  "home_team": "Saint Mary's Gaels",
  "away_team": "Pepperdine Waves",
  "commence_time": "2026-02-12 03:00:00",
  "game_date": "2026-02-11",
  "bet_type": "moneyline",
  "market": "h2h",
  "pick": "Pepperdine Waves",
  "pick_point": null,
  "bookmaker": "ESPN BET",
  "bookmaker_key": "espnbet",
  "odds": 31.0,
  "implied_prob": 0.0323,
  "bet_amount": 5.0,
  "potential_payout": 155.0,
  "algorithm": "value_bet",
  "ev_pct": 24.32,
  "status": "settled",
  "result": "lost",
  "pnl": -5.0,
  "settled_at": "2026-02-12 04:59:56",
  "actual_home_score": 88,
  "actual_away_score": 60,
  "placed_at": "2026-02-11 16:22:24"
}
{
  "id": 2,
  "event_id": "088f3788bb56116d37897dbf35a9c4f5",
  "sport": "soccer_usa_mls",
  "home_team": "Seattle Sounders FC",
  "away_team": "Colorado Rapids",
  "commence_time": "2026-02-23 02:15:00",
  "game_date": "2026-02-22",
  "bet_type": "total",
  "market": "totals",
  "pick": "Under",
  "pick_point": 2.5,
  "bookmaker": "Fliff",
  "bookmaker_key": "fliff",
  "odds": 2.3,
  "implied_prob": 0.4348,
  "bet_amount": 35.55,
  "potential_payout": 81.77,
  "algorithm": "value_bet",
  "ev_pct": 18.58,
  "status": "settled",
  "result": "void",
  "pnl": 0.0,
  "settled_at": "2026-03-16 15:21:34",
  "actual_home_score": null,
  "actual_away_score": null,
  "placed_at": "2026-02-11 16:22:24"
}
```

**`commence_time` range:** 2026-02-11 03:30:00 → 2026-03-28 01:41:00

**`game_date` range:** 2026-02-10 → 2026-03-27

### 106. `miracle_watchlist2` — ~68 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `ticker` (varchar(10)), `company_name` (varchar(200)), `sector` (varchar(100)), `reason` (text), `is_cdr` (tinyint), `added_date` (date), `source` (varchar(50)), `active` (tinyint)

**Primary Key:** `id`
**Indexed:** `ticker`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "sector": "Technology",
  "reason": "CDR available, mega-cap tech leader",
  "is_cdr": 1,
  "added_date": "2026-02-09",
  "source": "seed",
  "active": 1
}
{
  "id": 2,
  "ticker": "AMD",
  "company_name": "Advanced Micro Devices",
  "sector": "Technology",
  "reason": "CDR available, high-beta semiconductor",
  "is_cdr": 1,
  "added_date": "2026-02-09",
  "source": "seed",
  "active": 1
}
```

**`added_date` range:** 2026-02-09 → 2026-02-09

### 107. `lm_price_cache` — ~66 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (21):** `id` (int), `asset_class` (varchar(10)), `symbol` (varchar(20)), `price` (decimal(18,8)), `bid_price` (decimal(18,8)), `ask_price` (decimal(18,8)), `spread_pct` (decimal(8,4)), `volume_24h` (decimal(24,2)), `change_1h_pct` (decimal(10,4)), `change_24h_pct` (decimal(10,4)), `high_24h` (decimal(18,8)), `low_24h` (decimal(18,8)) … +9 more

**Primary Key:** `id`
**Indexed:** `asset_class`, `last_updated`

**`asset_class` distribution:**
- `CRYPTO`: 32
- ``: 12
- `STOCK`: 12
- `FOREX`: 10

**Sample Rows:**
```json
{
  "id": 1,
  "asset_class": "CRYPTO",
  "symbol": "BTCUSD",
  "price": 80294.14,
  "bid_price": 80283.0,
  "ask_price": 80283.1,
  "spread_pct": 0.0001,
  "volume_24h": 101977347.92,
  "change_1h_pct": 0.0,
  "change_24h_pct": 0.5185,
  "high_24h": 80522.9,
  "low_24h": 79168.1,
  "data_source": "freecryptoapi (binance) +kraken",
  "data_delay_seconds": 5,
  "last_updated": "2026-05-08 14:19:48",
  "prev_close": 0.0,
  "day_high": 0.0,
  "day_low": 0.0,
  "volume": 0,
  "source": "finnhub",
  "updated_at": null
}
{
  "id": 2,
  "asset_class": "CRYPTO",
  "symbol": "ETHUSD",
  "price": 2287.87,
  "bid_price": 2288.58,
  "ask_price": 2288.73,
  "spread_pct": 0.0066,
  "volume_24h": 37416501.51,
  "change_1h_pct": 0.0,
  "change_24h_pct": -0.0537,
  "high_24h": 2313.65,
  "low_24h": 2265.02,
  "data_source": "freecryptoapi (binance) +kraken",
  "data_delay_seconds": 5,
  "last_updated": "2026-05-08 14:19:48",
  "prev_close": 0.0,
  "day_high": 0.0,
  "day_low": 0.0,
  "volume": 0,
  "source": "finnhub",
  "updated_at": null
}
```

**`last_updated` range:** 0000-00-00 00:00:00 → 2026-05-08 14:19:51

**`updated_at` range:** 2026-02-11 02:50:21 → 2026-02-11 02:50:21

### 108. `consensus_performance_daily` — ~62 rows (0MB + 0MB idx)
**Purpose:** Consensus: Aggregation

**Columns (18):** `id` (int), `track_date` (date), `open_positions` (int), `total_closed` (int), `total_wins` (int), `total_losses` (int), `win_rate` (decimal(6,2)), `total_pnl_pct` (decimal(10,4)), `avg_win_pct` (decimal(10,4)), `avg_loss_pct` (decimal(10,4)), `best_ticker` (varchar(10)), `best_return_pct` (decimal(10,4)) … +6 more

**Primary Key:** `id`
**Indexed:** `track_date`

**Sample Rows:**
```json
{
  "id": 1,
  "track_date": "2026-02-10",
  "open_positions": 58,
  "total_closed": 0,
  "total_wins": 0,
  "total_losses": 0,
  "win_rate": 0.0,
  "total_pnl_pct": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 0.0,
  "best_ticker": "",
  "best_return_pct": 0.0,
  "worst_ticker": "",
  "worst_return_pct": 0.0,
  "avg_hold_days": 0.0,
  "current_streak": 0,
  "portfolio_value": 10000.0,
  "created_at": "2026-02-10 13:00:42"
}
{
  "id": 2,
  "track_date": "2026-02-11",
  "open_positions": 65,
  "total_closed": 0,
  "total_wins": 0,
  "total_losses": 0,
  "win_rate": 0.0,
  "total_pnl_pct": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 0.0,
  "best_ticker": "",
  "best_return_pct": 0.0,
  "worst_ticker": "",
  "worst_return_pct": 0.0,
  "avg_hold_days": 0.0,
  "current_streak": 0,
  "portfolio_value": 10000.0,
  "created_at": "2026-02-11 00:03:28"
}
```

**`track_date` range:** 2026-02-10 → 2026-04-27

**`created_at` range:** 2026-02-10 13:00:42 → 2026-04-27 23:57:01

### 109. `pf_challenge_positions` — ~62 rows (0MB + 0MB idx)
**Purpose:** Challenge: PF positions

**Columns (26):** `id` (int), `portfolio_id` (varchar(50)), `position_id` (varchar(20)), `symbol` (varchar(20)), `direction` (varchar(10)), `strategy` (varchar(100)), `source_system` (varchar(50)), `entry_price` (decimal(20,8)), `take_profit` (decimal(20,8)), `stop_loss` (decimal(20,8)), `exit_price` (decimal(20,8)), `size_usd` (decimal(12,2)) … +14 more

**Primary Key:** `id`
**Indexed:** `portfolio_id`, `symbol`, `status`

**`direction` distribution:**
- `LONG`: 54
- `SHORT`: 8

**`strategy` distribution:**
- `incubator_gainer_composite`: 19
- `multi_period_rsi_confluence_xrp`: 11
- `drawdown_recovery_rsi_eth`: 8
- `order_book_imbalance`: 6
- `crypto_winners`: 5
- `super signal (super) via predictions`: 3
- `drawdown_recovery_rsi`: 2
- `crypto_keltner_compression_expansion_v1`: 2
- `multi_period_rsi_confluence_eth`: 2
- `super signal (super) via alpha_engine`: 1
- `stochrsi_macd_combo`: 1
- `Short-Term Reversal`: 1

**`source_system` distribution:**
- `incubator_gainer`: 19
- `fc_crypto_pro`: 14
- `battleground`: 9
- `alpha_engine_fast`: 6
- `crypto_winners`: 5
- `super_signals`: 4
- `aggregated_picks`: 2
- `fast_stocks_competition`: 2
- `rapid_fire`: 1

**`status` distribution:**
- `OPEN`: 33
- `SL_HIT`: 20
- `TP_HIT`: 9

**Sample Rows:**
```json
{
  "id": 1,
  "portfolio_id": "score_leaders",
  "position_id": "faf6ce378104",
  "symbol": "BNB-USD",
  "direction": "SHORT",
  "strategy": "order_book_imbalance",
  "source_system": "alpha_engine_fast",
  "entry_price": 644.82,
  "take_profit": 632.48,
  "stop_loss": 655.07,
  "exit_price": 0.0,
  "size_usd": 656.1,
  "pnl_pct": -0.1555,
  "pnl_usd": -1.02,
  "net_pnl_usd": 0.0,
  "commission_entry": 0.98,
  "commission_exit": 0.0,
  "exit_reason": "",
  "status": "OPEN",
  "opened_at": "2026-03-10T07:00:26.228025-05:00",
  "closed_at": "",
  "rr_ratio": 1.33,
  "sys_wr": 50.0,
  "sys_pf": 1.33,
  "confidence": 0.84,
  "created_at": "2026-03-10 19:00:57"
}
{
  "id": 2,
  "portfolio_id": "score_leaders",
  "position_id": "c557dbf77e89",
  "symbol": "ETHUSDT",
  "direction": "LONG",
  "strategy": "drawdown_recovery_rsi_eth",
  "source_system": "fc_crypto_pro",
  "entry_price": 2055.62,
  "take_profit": 2083.409401,
  "stop_loss": 2038.015404,
  "exit_price": 2050.8,
  "size_usd": 784.56,
  "pnl_pct": 0.6436,
  "pnl_usd": 5.05,
  "net_pnl_usd": -7.25,
  "commission_entry": 1.18,
  "commission_exit": 0.0,
  "exit_reason": "SL",
  "status": "OPEN",
  "opened_at": "2026-03-10T09:51:59.321690-05:00",
  "closed_at": "2026-03-10T07:53:10.279782-05:00",
  "rr_ratio": 1.58,
  "sys_wr": 60.8,
  "sys_pf": 2.34,
  "confidence": 0.62,
  "created_at": "2026-03-10 19:00:57"
}
```

**`created_at` range:** 2026-03-10 19:00:57 → 2026-03-10 19:00:58

### 110. `miracle_watchlist3` — ~56 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `ticker` (varchar(10)), `company_name` (varchar(200)), `sector` (varchar(50)), `is_cdr` (tinyint), `is_canadian` (tinyint), `reason` (text), `added_date` (date), `source` (varchar(50)), `active` (tinyint)

**Primary Key:** `id`
**Indexed:** `ticker`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "sector": "Technology",
  "is_cdr": 1,
  "is_canadian": 0,
  "reason": "Initial seed",
  "added_date": "2026-02-09",
  "source": "seed",
  "active": 1
}
{
  "id": 2,
  "ticker": "AMD",
  "company_name": "Advanced Micro Devices",
  "sector": "Technology",
  "is_cdr": 1,
  "is_canadian": 0,
  "reason": "Initial seed",
  "added_date": "2026-02-09",
  "source": "seed",
  "active": 1
}
```

**`added_date` range:** 2026-02-09 → 2026-02-09

### 111. `penny_picks_daily` — ~54 rows (0MB + 0MB idx)
**Purpose:** Penny Stocks: Pick data

**Columns (13):** `id` (int), `snap_date` (date), `total_scored` (int), `top_picks_count` (int), `avg_score` (decimal(5,2)), `buy_count` (int), `strong_buy_count` (int), `active_picks` (int), `closed_picks` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(8,2)), `total_return_pct` (decimal(8,2)) … +1 more

**Primary Key:** `id`
**Indexed:** `snap_date`

**Sample Rows:**
```json
{
  "id": 1,
  "snap_date": "2026-02-11",
  "total_scored": 20,
  "top_picks_count": 20,
  "avg_score": 65.83,
  "buy_count": 15,
  "strong_buy_count": 0,
  "active_picks": 20,
  "closed_picks": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "total_return_pct": 0.0,
  "created_at": "2026-02-11 19:12:36"
}
{
  "id": 3,
  "snap_date": "2026-02-12",
  "total_scored": 20,
  "top_picks_count": 20,
  "avg_score": 66.79,
  "buy_count": 17,
  "strong_buy_count": 0,
  "active_picks": 40,
  "closed_picks": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "total_return_pct": 0.0,
  "created_at": "2026-02-12 12:52:31"
}
```

**`snap_date` range:** 2026-02-11 → 2026-04-27

**`created_at` range:** 2026-02-11 19:12:36 → 2026-04-27 12:40:52

### 112. `strategy_health` — ~54 rows (0MB + 0MB idx)
**Purpose:** Strategy: Health monitoring

**Columns (20):** `id` (int), `source_system` (varchar(100)), `strategy` (varchar(200)), `asset_class` (varchar(20)), `total_trades` (int), `wins` (int), `losses` (int), `win_rate` (decimal(5,4)), `avg_win_pct` (decimal(10,4)), `avg_loss_pct` (decimal(10,4)), `expectancy` (decimal(10,4)), `fees_adj_expect` (decimal(10,4)) … +8 more

**Primary Key:** `id`
**Indexed:** `source_system`, `tier`

**`source_system` distribution:**
- `cw_winners`: 34
- `kimi_riseoftheclaw`: 16
- `Funding Rate Carry`: 1
- `IRB Hoffman`: 1
- `kimi_signal_tracker`: 1
- `opposite_day`: 1

**`strategy` distribution:**
- `unknown`: 2
- `crypto_winner_scan`: 1
- `cw_AAVE_USDT`: 1
- `cw_ADA_USDT`: 1
- `cw_ALGO_USDT`: 1
- `cw_ARB_USDT`: 1
- `cw_ATOM_USDT`: 1
- `cw_AVAX_USDT`: 1
- `cw_BCH_USDT`: 1
- `cw_BTC_USDT`: 1
- `cw_DOGE_USDT`: 1
- `cw_DOT_USDT`: 1

**`asset_class` distribution:**
- `CRYPTO`: 52
- `MEMECOIN`: 2

**Sample Rows:**
```json
{
  "id": 1,
  "source_system": "kimi_signal_tracker",
  "strategy": "unknown",
  "asset_class": "CRYPTO",
  "total_trades": 5,
  "wins": 0,
  "losses": 5,
  "win_rate": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 9.5438,
  "expectancy": -9.5438,
  "fees_adj_expect": -9.6938,
  "profit_factor": 0.0,
  "rolling_30d_wr": null,
  "tier": "BANNED",
  "tier_changed_at": null,
  "tier_reason": "still banned — insufficient recovery",
  "wf_passed": null,
  "wf_last_checked": null,
  "last_evaluated": "2026-05-08 12:24:10"
}
{
  "id": 3,
  "source_system": "kimi_riseoftheclaw",
  "strategy": "pairs-trading",
  "asset_class": "CRYPTO",
  "total_trades": 2,
  "wins": 0,
  "losses": 2,
  "win_rate": 0.0,
  "avg_win_pct": 0.0,
  "avg_loss_pct": 6.0957,
  "expectancy": -6.0957,
  "fees_adj_expect": -6.2457,
  "profit_factor": 0.0,
  "rolling_30d_wr": null,
  "tier": "INCUBATOR",
  "tier_changed_at": null,
  "tier_reason": "collecting data (2 trades)",
  "wf_passed": null,
  "wf_last_checked": null,
  "last_evaluated": "2026-05-08 12:24:10"
}
```

### 113. `alpha_universe` — ~52 rows (0MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (7):** `ticker` (varchar(10)), `company_name` (varchar(200)), `sector` (varchar(100)), `industry` (varchar(200)), `market_cap_tier` (varchar(20)), `added_date` (date), `active` (tinyint)

**Primary Key:** `ticker`
**Indexed:** `sector`, `active`

**Sample Rows:**
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap_tier": "mega",
  "added_date": "2026-02-09",
  "active": 1
}
{
  "ticker": "MSFT",
  "company_name": "Microsoft Corp",
  "sector": "Technology",
  "industry": "Software - Infrastructure",
  "market_cap_tier": "mega",
  "added_date": "2026-02-09",
  "active": 1
}
```

**`added_date` range:** 2026-02-09 → 2026-02-09

### 114. `pf_pair_patterns` — ~51 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `pair` (varchar(30)), `asset_class` (varchar(15)), `pattern_name` (varchar(50)), `occurrences` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(8,4)), `avg_duration_hours` (decimal(8,2)), `last_triggered` (datetime), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `pair`, `win_rate`

**`asset_class` distribution:**
- `CRYPTO`: 39
- `STOCK`: 7
- `FOREX`: 5

**Sample Rows:**
```json
{
  "id": 44828,
  "pair": "AAVEUSD",
  "asset_class": "CRYPTO",
  "pattern_name": "MOMENTUM_STREAK",
  "occurrences": 18,
  "win_rate": 55.56,
  "avg_return_pct": 0.5668,
  "avg_duration_hours": 0.0,
  "last_triggered": null,
  "updated_at": "2026-04-30 03:01:02"
}
{
  "id": 44830,
  "pair": "ADAUSD",
  "asset_class": "CRYPTO",
  "pattern_name": "MOMENTUM_STREAK",
  "occurrences": 12,
  "win_rate": 58.33,
  "avg_return_pct": 0.3393,
  "avg_duration_hours": 0.0,
  "last_triggered": null,
  "updated_at": "2026-04-30 03:01:02"
}
```

**`updated_at` range:** 2026-04-30 03:01:02 → 2026-04-30 03:01:02

### 115. `strategy_test_runs` — ~51 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (18):** `run_id` (bigint), `strategy_id` (varchar(128)), `test_layer` (varchar(32)), `symbol` (varchar(64)), `asset_class` (varchar(32)), `period_start` (datetime), `period_end` (datetime), `trades` (int), `win_rate` (decimal(8,4)), `profit_factor` (decimal(10,4)), `sharpe` (decimal(10,4)), `max_drawdown` (decimal(10,4)) … +6 more

**Primary Key:** `run_id`
**Indexed:** `strategy_id`, `test_layer`

**`asset_class` distribution:**
- `CRYPTO`: 51

**Sample Rows:**
```json
{
  "run_id": 1,
  "strategy_id": "hs_lb_None",
  "test_layer": "backtest",
  "symbol": null,
  "asset_class": "CRYPTO",
  "period_start": null,
  "period_end": null,
  "trades": 13,
  "win_rate": 92.3,
  "profit_factor": 8.86,
  "sharpe": 19.914,
  "max_drawdown": 0.0,
  "p_value": 1.4e-05,
  "q_value_bh": null,
  "p_value_bonf": null,
  "pass_flag": 1,
  "metadata_json": "{\"source\": \"walkforward_results.json\", \"lineage\": \"backtest\", \"source_systems\": [\"copy_trader_highscore\"], \"final_score\": 0.6549, \"wf_oos_wr\": null, \"...",
  "created_at": "2026-04-03 00:25:22"
}
{
  "run_id": 2,
  "strategy_id": "gainer_compression_relaxed_mut",
  "test_layer": "backtest",
  "symbol": null,
  "asset_class": "CRYPTO",
  "period_start": null,
  "period_end": null,
  "trades": 11,
  "win_rate": 81.8,
  "profit_factor": 8.45,
  "sharpe": 19.175,
  "max_drawdown": 2.46,
  "p_value": 0.000134,
  "q_value_bh": null,
  "p_value_bonf": null,
  "pass_flag": 1,
  "metadata_json": "{\"source\": \"walkforward_results.json\", \"lineage\": \"backtest\", \"source_systems\": [\"dna_winner_picks\"], \"final_score\": 0.6287, \"wf_oos_wr\": null, \"wf_fo...",
  "created_at": "2026-04-03 00:25:22"
}
```

**`created_at` range:** 2026-04-03 00:25:22 → 2026-04-03 00:25:42

### 116. `backtest_trades` — ~50 rows (0MB + 0MB idx)
**Purpose:** Backtesting

**Columns (15):** `id` (int), `backtest_id` (int), `ticker` (varchar(10)), `algorithm_name` (varchar(100)), `entry_date` (date), `entry_price` (decimal(12,4)), `exit_date` (date), `exit_price` (decimal(12,4)), `shares` (int), `gross_profit` (decimal(12,2)), `commission_paid` (decimal(8,2)), `net_profit` (decimal(12,2)) … +3 more

**Primary Key:** `id`
**Indexed:** `backtest_id`, `ticker`

**Sample Rows:**
```json
{
  "id": 1,
  "backtest_id": 1,
  "ticker": "ABBV",
  "algorithm_name": "Technical Momentum",
  "entry_date": "2026-01-28",
  "entry_price": 225.0497,
  "exit_date": "2026-02-05",
  "exit_price": 217.9249,
  "shares": 4,
  "gross_profit": -28.5,
  "commission_paid": 20.0,
  "net_profit": -48.5,
  "return_pct": -5.3876,
  "exit_reason": "max_hold",
  "hold_days": 7
}
{
  "id": 2,
  "backtest_id": 1,
  "ticker": "AMZN",
  "algorithm_name": "Technical Momentum",
  "entry_date": "2026-01-28",
  "entry_price": 245.9034,
  "exit_date": "2026-02-05",
  "exit_price": 221.5766,
  "shares": 4,
  "gross_profit": -97.31,
  "commission_paid": 20.0,
  "net_profit": -117.31,
  "return_pct": -11.9262,
  "exit_reason": "max_hold",
  "hold_days": 7
}
```

**`entry_date` range:** 2026-01-28 → 2026-02-06

**`exit_date` range:** 2026-01-28 → 2026-02-06

### 117. `meme_ml_signals` — ~50 rows (0MB + 0MB idx)
**Purpose:** Memecoins: Signal data

**Columns (8):** `id` (int), `signal_id` (varchar(50)), `coin_symbol` (varchar(20)), `features_json` (text), `outcome` (varchar(10)), `profit_loss_pct` (decimal(10,2)), `created_at` (datetime), `resolved_at` (datetime)

**Primary Key:** `id`
**Indexed:** `signal_id`, `coin_symbol`, `outcome`, `created_at`

**`outcome` distribution:**
- `win`: 30
- `loss`: 20

**Sample Rows:**
```json
{
  "id": 1,
  "signal_id": null,
  "coin_symbol": "PEPE",
  "features_json": "{\"explosive_volume\":22,\"parabolic_momentum\":18,\"rsi_hype_zone\":14,\"social_momentum_proxy\":12,\"volume_concentration\":9,\"breakout_4h\":8,\"low_market_cap_...",
  "outcome": "win",
  "profit_loss_pct": 45.2,
  "created_at": "2026-01-13 22:27:24",
  "resolved_at": "2026-01-13 22:27:24"
}
{
  "id": 2,
  "signal_id": null,
  "coin_symbol": "SHIB",
  "features_json": "{\"explosive_volume\":20,\"parabolic_momentum\":17,\"rsi_hype_zone\":13,\"social_momentum_proxy\":11,\"volume_concentration\":8,\"breakout_4h\":7,\"low_market_cap_...",
  "outcome": "win",
  "profit_loss_pct": 38.5,
  "created_at": "2026-01-14 10:27:24",
  "resolved_at": "2026-01-14 10:27:24"
}
```

**`created_at` range:** 2026-01-13 22:27:24 → 2026-02-07 10:27:24

**`resolved_at` range:** 2026-01-13 22:27:24 → 2026-02-07 10:27:24

### 118. `meme_signal_results` — ~50 rows (0MB + 0MB idx)
**Purpose:** Memecoins: Signal data

**Columns (7):** `id` (int), `signal_id` (varchar(50)), `outcome` (varchar(10)), `profit_loss_pct` (decimal(10,2)), `max_profit_pct` (decimal(10,2)), `max_loss_pct` (decimal(10,2)), `resolved_at` (datetime)

**Primary Key:** `id`
**Indexed:** `signal_id`, `outcome`

**`outcome` distribution:**
- `win`: 30
- `loss`: 20

**Sample Rows:**
```json
{
  "id": 1,
  "signal_id": "meme_20260113_0",
  "outcome": "win",
  "profit_loss_pct": 45.2,
  "max_profit_pct": null,
  "max_loss_pct": null,
  "resolved_at": "2026-01-13 22:31:05"
}
{
  "id": 2,
  "signal_id": "meme_20260114_1",
  "outcome": "win",
  "profit_loss_pct": 38.5,
  "max_profit_pct": null,
  "max_loss_pct": null,
  "resolved_at": "2026-01-14 10:31:05"
}
```

**`resolved_at` range:** 2026-01-13 22:31:05 → 2026-02-07 10:31:05

### 119. `meme_signals` — ~50 rows (0MB + 0MB idx)
**Purpose:** Memecoins: Signal data

**Columns (13):** `id` (int), `signal_id` (varchar(50)), `coin_symbol` (varchar(20)), `explosive_volume` (decimal(5,2)), `parabolic_momentum` (decimal(5,2)), `rsi_hype_zone` (decimal(5,2)), `social_momentum_proxy` (decimal(5,2)), `volume_concentration` (decimal(5,2)), `breakout_4h` (decimal(5,2)), `low_market_cap_bonus` (decimal(5,2)), `tier` (varchar(10)), `total_score` (int) … +1 more

**Primary Key:** `id`
**Indexed:** `signal_id`, `coin_symbol`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "signal_id": "meme_20260113_0",
  "coin_symbol": "PEPE",
  "explosive_volume": 22.0,
  "parabolic_momentum": 18.0,
  "rsi_hype_zone": 14.0,
  "social_momentum_proxy": 12.0,
  "volume_concentration": 9.0,
  "breakout_4h": 8.0,
  "low_market_cap_bonus": 5.0,
  "tier": "tier1",
  "total_score": 88,
  "created_at": "2026-01-13 22:29:27"
}
{
  "id": 2,
  "signal_id": "meme_20260114_1",
  "coin_symbol": "SHIB",
  "explosive_volume": 20.0,
  "parabolic_momentum": 17.0,
  "rsi_hype_zone": 13.0,
  "social_momentum_proxy": 11.0,
  "volume_concentration": 8.0,
  "breakout_4h": 7.0,
  "low_market_cap_bonus": 5.0,
  "tier": "tier1",
  "total_score": 81,
  "created_at": "2026-01-14 10:29:27"
}
```

**`created_at` range:** 2026-01-13 22:29:27 → 2026-02-07 10:29:27

### 120. `pf_fingerprints` — ~47 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (23):** `id` (int), `pair` (varchar(30)), `asset_class` (varchar(15)), `behavior_type` (varchar(30)), `momentum_corr` (decimal(8,4)), `mean_revert_score` (decimal(8,4)), `trend_score` (decimal(8,4)), `breakout_score` (decimal(8,4)), `pump_susceptibility` (decimal(8,4)), `avg_volatility_pct` (decimal(8,4)), `optimal_tp_pct` (decimal(6,2)), `optimal_sl_pct` (decimal(6,2)) … +11 more

**Primary Key:** `id`
**Indexed:** `pair`, `asset_class`, `behavior_type`, `win_rate`

**`asset_class` distribution:**
- `CRYPTO`: 27
- `STOCK`: 12
- `FOREX`: 8

**Sample Rows:**
```json
{
  "id": 41068,
  "pair": "AAVEUSD",
  "asset_class": "CRYPTO",
  "behavior_type": "TRENDING",
  "momentum_corr": 0.2368,
  "mean_revert_score": 0.0,
  "trend_score": 47.8197,
  "breakout_score": 0.1159,
  "pump_susceptibility": 27.8333,
  "avg_volatility_pct": 0.1523,
  "optimal_tp_pct": 0.5,
  "optimal_sl_pct": 0.2,
  "optimal_hold_hours": 24,
  "best_algorithm": "",
  "best_algo_wr": 0.0,
  "best_hour_utc": -1,
  "best_session": "NY_AFTERNOON",
  "total_signals": 1037,
  "total_wins": 0,
  "win_rate": 0.0,
  "avg_pnl_pct": -0.0006,
  "pattern_json": "{\"momentum_autocorr\":0.2368,\"recovery_rate\":30.6,\"streak_rate\":62.1,\"pnl_variance\":0.0232,\"total_signals\":1037,\"algo_breakdown\":[{\"algo\":\"Awesome Osci...",
  "updated_at": "2026-04-30 03:01:02"
}
{
  "id": 41069,
  "pair": "ADAUSD",
  "asset_class": "CRYPTO",
  "behavior_type": "PUMP_SUSCEPTIBLE",
  "momentum_corr": 0.0664,
  "mean_revert_score": 0.0,
  "trend_score": 6.639,
  "breakout_score": 0.0928,
  "pump_susceptibility": 32.0435,
  "avg_volatility_pct": 0.1363,
  "optimal_tp_pct": 0.5,
  "optimal_sl_pct": 0.2,
  "optimal_hold_hours": 24,
  "best_algorithm": "",
  "best_algo_wr": 0.0,
  "best_hour_utc": -1,
  "best_session": "NY_CLOSE",
  "total_signals": 970,
  "total_wins": 0,
  "win_rate": 0.0,
  "avg_pnl_pct": -0.0035,
  "pattern_json": "{\"momentum_autocorr\":0.0664,\"recovery_rate\":32.3,\"streak_rate\":54.5,\"pnl_variance\":0.0186,\"total_signals\":970,\"algo_breakdown\":[{\"algo\":\"MACD Crossove...",
  "updated_at": "2026-04-30 03:01:02"
}
```

**`updated_at` range:** 2026-04-30 03:01:02 → 2026-04-30 03:01:02

### 121. `lm_challenger_showdown` — ~46 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (20):** `id` (int), `period_start` (date), `period_end` (date), `challenger_trades` (int), `challenger_wins` (int), `challenger_win_rate` (decimal(5,2)), `challenger_pnl` (decimal(12,2)), `challenger_sharpe` (decimal(6,3)), `challenger_max_dd` (decimal(6,2)), `best_algo_name` (varchar(100)), `best_algo_trades` (int), `best_algo_wins` (int) … +8 more

**Primary Key:** `id`
**Indexed:** `period_start`, `snapshot_date`

**Sample Rows:**
```json
{
  "id": 1,
  "period_start": "2026-01-12",
  "period_end": "2026-02-11",
  "challenger_trades": 0,
  "challenger_wins": 0,
  "challenger_win_rate": 0.0,
  "challenger_pnl": 0.0,
  "challenger_sharpe": 0.0,
  "challenger_max_dd": 0.0,
  "best_algo_name": "",
  "best_algo_trades": 0,
  "best_algo_wins": 0,
  "best_algo_win_rate": 0.0,
  "best_algo_pnl": 0.0,
  "best_algo_sharpe": 0.0,
  "best_algo_max_dd": 0.0,
  "challenger_rank": 1,
  "total_algos": 0,
  "snapshot_date": "2026-02-11",
  "created_at": "2026-02-11 01:50:27"
}
{
  "id": 2,
  "period_start": "2026-01-13",
  "period_end": "2026-02-12",
  "challenger_trades": 0,
  "challenger_wins": 0,
  "challenger_win_rate": 0.0,
  "challenger_pnl": 0.0,
  "challenger_sharpe": 0.0,
  "challenger_max_dd": 0.0,
  "best_algo_name": "",
  "best_algo_trades": 0,
  "best_algo_wins": 0,
  "best_algo_win_rate": 0.0,
  "best_algo_pnl": 0.0,
  "best_algo_sharpe": 0.0,
  "best_algo_max_dd": 0.0,
  "challenger_rank": 1,
  "total_algos": 0,
  "snapshot_date": "2026-02-12",
  "created_at": "2026-02-12 02:39:52"
}
```

**`snapshot_date` range:** 2026-02-11 → 2026-05-08

**`created_at` range:** 2026-02-11 01:50:27 → 2026-05-08 11:27:08

### 122. `portfolios` — ~39 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (13):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `algorithm_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `commission_buy` (decimal(6,2)), `commission_sell` (decimal(6,2)), `stop_loss_pct` (decimal(5,2)), `take_profit_pct` (decimal(5,2)), `max_hold_days` (int), `slippage_pct` (decimal(5,4)) … +1 more

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Day Trader (EOD Exit)",
  "description": null,
  "strategy_type": "daytrader",
  "algorithm_filter": "",
  "initial_capital": 10000.0,
  "commission_buy": 10.0,
  "commission_sell": 10.0,
  "stop_loss_pct": 3.0,
  "take_profit_pct": 5.0,
  "max_hold_days": 1,
  "slippage_pct": 0.005,
  "created_at": "2026-02-09 04:51:01"
}
{
  "id": 2,
  "name": "Day Trader (2-Day Max)",
  "description": null,
  "strategy_type": "daytrader",
  "algorithm_filter": "",
  "initial_capital": 10000.0,
  "commission_buy": 10.0,
  "commission_sell": 10.0,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "max_hold_days": 2,
  "slippage_pct": 0.005,
  "created_at": "2026-02-09 04:51:01"
}
```

**`created_at` range:** 2026-02-09 04:51:01 → 2026-02-09 18:22:38

### 123. `ps_scores` — ~36 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (19):** `id` (int), `pair` (varchar(30)), `asset_class` (varchar(20)), `hurst_exponent` (float), `hurst_regime` (varchar(20)), `autocorrelation_1` (float), `autocorrelation_5` (float), `volatility_stability` (float), `signal_noise_ratio` (float), `engine_agreement` (float), `engines_bullish` (int), `engines_bearish` (int) … +7 more

**Primary Key:** `id`
**Indexed:** `pair`

**`asset_class` distribution:**
- `CRYPTO`: 36

**Sample Rows:**
```json
{
  "id": 649,
  "pair": "XXBTZUSD",
  "asset_class": "CRYPTO",
  "hurst_exponent": 0.568,
  "hurst_regime": "RANDOM",
  "autocorrelation_1": 0.1047,
  "autocorrelation_5": -0.0826,
  "volatility_stability": 0.3969,
  "signal_noise_ratio": 18.3568,
  "engine_agreement": 0.75,
  "engines_bullish": 3,
  "engines_bearish": 0,
  "engines_total": 4,
  "historical_tp_rate": 0.0,
  "historical_signals": 0,
  "predictability_score": 51.7,
  "predictability_grade": "C",
  "best_strategy": "MULTI_INDICATOR",
  "computed_at": "2026-02-16 19:09:30"
}
{
  "id": 650,
  "pair": "XETHZUSD",
  "asset_class": "CRYPTO",
  "hurst_exponent": 0.5509,
  "hurst_regime": "RANDOM",
  "autocorrelation_1": 0.0255,
  "autocorrelation_5": -0.0632,
  "volatility_stability": 0.4027,
  "signal_noise_ratio": 17.4837,
  "engine_agreement": 0.5,
  "engines_bullish": 1,
  "engines_bearish": 2,
  "engines_total": 4,
  "historical_tp_rate": 0.0,
  "historical_signals": 0,
  "predictability_score": 39.7,
  "predictability_grade": "D",
  "best_strategy": "MULTI_INDICATOR",
  "computed_at": "2026-02-16 19:09:30"
}
```

### 124. `mf_selections` — ~34 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (11):** `id` (int), `ticker` (varchar(15)), `strategy_id` (int), `strategy_name` (varchar(200)), `select_date` (date), `nav_at_select` (decimal(12,4)), `category` (varchar(150)), `expense_ratio` (decimal(5,4)), `morningstar_rating` (tinyint), `rationale` (text), `select_hash` (varchar(64))

**Primary Key:** `id`
**Indexed:** `ticker`, `strategy_name`, `select_date`

**`category` distribution:**
- `Large Blend`: 15
- `Large Growth`: 6
- `Allocation 50-70% Eq`: 2
- `Health`: 2
- `Large Value`: 2
- `Multisector Bond`: 1
- `Intermediate Core Bond`: 1
- `Allocation 60-70% Eq`: 1
- `Allocation 30-50% Eq`: 1
- `Foreign Large Value`: 1
- `Foreign Large Blend`: 1
- `Foreign Large Growth`: 1

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "FCNTX",
  "strategy_id": 1,
  "strategy_name": "Growth Leaders",
  "select_date": "2026-02-06",
  "nav_at_select": 24.54,
  "category": "Large Growth",
  "expense_ratio": 0.0039,
  "morningstar_rating": 4,
  "rationale": "Auto-matched: Equity / Large Growth / 4 stars",
  "select_hash": "adda22e5dbc194f2b177cbe819bd50b3e91d71df"
}
{
  "id": 2,
  "ticker": "FXAIX",
  "strategy_id": 1,
  "strategy_name": "Growth Leaders",
  "select_date": "2026-02-06",
  "nav_at_select": 240.95,
  "category": "Large Blend",
  "expense_ratio": 0.0015,
  "morningstar_rating": 5,
  "rationale": "Auto-matched: Equity / Large Blend / 5 stars",
  "select_hash": "0817d716a89c515685d1479a75855169c2290369"
}
```

**`select_date` range:** 2026-02-06 → 2026-02-06

### 125. `strategy_symbol_coverage` — ~34 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (7):** `strategy_id` (varchar(128)), `symbol` (varchar(64)), `asset_class` (varchar(32)), `tested_backtest` (tinyint(1)), `tested_walkforward` (tinyint(1)), `tested_forward` (tinyint(1)), `last_result_at` (datetime)

**Primary Key:** `strategy_id`, `symbol`

**`asset_class` distribution:**
- `CRYPTO`: 34

**Sample Rows:**
```json
{
  "strategy_id": "cftc_cot_commercial_signal",
  "symbol": "CL=F",
  "asset_class": "CRYPTO",
  "tested_backtest": 0,
  "tested_walkforward": 0,
  "tested_forward": 1,
  "last_result_at": null
}
{
  "strategy_id": "cta_commodity_momentum_term",
  "symbol": "SI=F",
  "asset_class": "CRYPTO",
  "tested_backtest": 0,
  "tested_walkforward": 0,
  "tested_forward": 1,
  "last_result_at": null
}
```

### 126. `lm_nba_team_stats` — ~30 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (30):** `id` (int), `team_id` (varchar(20)), `abbreviation` (varchar(10)), `name` (varchar(100)), `short_name` (varchar(60)), `conference` (varchar(20)), `division` (varchar(30)), `wins` (int), `losses` (int), `win_pct` (decimal(5,3)), `home_wins` (int), `home_losses` (int) … +18 more

**Primary Key:** `id`
**Indexed:** `team_id`

**Sample Rows:**
```json
{
  "id": 61,
  "team_id": "11",
  "abbreviation": "IND",
  "name": "Indiana Pacers",
  "short_name": "Pacers",
  "conference": "Eastern Conference",
  "division": "",
  "wins": 15,
  "losses": 40,
  "win_pct": 0.273,
  "home_wins": 10,
  "home_losses": 18,
  "away_wins": 5,
  "away_losses": 22,
  "streak": "W2",
  "last10_wins": 5,
  "last10_losses": 5,
  "ppg": 111.1,
  "opp_ppg": 118.6,
  "rpg": 0.0,
  "apg": 0.0,
  "fg_pct": 0.0,
  "three_pct": 0.0,
  "ft_pct": 0.0,
  "pace": 0.0,
  "off_rating": 0.0,
  "def_rating": 0.0,
  "net_rating": 0.0,
  "source": "espn",
  "updated_at": "2026-02-12 05:25:22"
}
{
  "id": 62,
  "team_id": "27",
  "abbreviation": "WSH",
  "name": "Washington Wizards",
  "short_name": "Wizards",
  "conference": "Eastern Conference",
  "division": "",
  "wins": 14,
  "losses": 39,
  "win_pct": 0.264,
  "home_wins": 9,
  "home_losses": 18,
  "away_wins": 5,
  "away_losses": 21,
  "streak": "L3",
  "last10_wins": 4,
  "last10_losses": 6,
  "ppg": 112.2,
  "opp_ppg": 123.1,
  "rpg": 0.0,
  "apg": 0.0,
  "fg_pct": 0.0,
  "three_pct": 0.0,
  "ft_pct": 0.0,
  "pace": 0.0,
  "off_rating": 0.0,
  "def_rating": 0.0,
  "net_rating": 0.0,
  "source": "espn",
  "updated_at": "2026-02-12 05:25:22"
}
```

**`updated_at` range:** 2026-02-12 05:25:22 → 2026-02-12 05:25:22

### 127. `at_permutation_snapshots` — ~28 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (20):** `id` (int), `snapshot_type` (enum('SYSTEM','STRATEGY')), `permutation_id` (varchar(100)), `permutation_name` (varchar(200)), `category` (varchar(50)), `systems` (json), `strategies` (json), `min_agreement` (int), `trust_score` (decimal(5,1)), `trust_tier` (varchar(50)), `total_trades` (int), `wins` (int) … +8 more

**Primary Key:** `id`
**Indexed:** `snapshot_type`, `permutation_id`, `trust_score`, `snapshot_at`

**`category` distribution:**
- `None`: 13
- `confluence`: 3
- `category`: 3
- `trend`: 2
- `strict`: 2
- `momentum`: 1
- `breakout`: 1
- `volatility`: 1
- `prop_firm`: 1
- `hybrid`: 1

**Sample Rows:**
```json
{
  "id": 1,
  "snapshot_type": "SYSTEM",
  "permutation_id": "solo_battleground",
  "permutation_name": "Solo: Battleground",
  "category": null,
  "systems": "[\"battleground\"]",
  "strategies": "[]",
  "min_agreement": 1,
  "trust_score": 84.1,
  "trust_tier": "Highly Trusted",
  "total_trades": 669,
  "wins": 403,
  "losses": 266,
  "win_rate": 60.2,
  "total_pnl": 3101.4607,
  "avg_pnl": 4.64,
  "profit_factor": 1.61,
  "active_pick_count": 2,
  "closed_pick_count": 669,
  "snapshot_at": "2026-03-08 23:41:11"
}
{
  "id": 2,
  "snapshot_type": "SYSTEM",
  "permutation_id": "solo_claude",
  "permutation_name": "Solo: Claude Gainer",
  "category": null,
  "systems": "[\"claude_gainer_ml_perf\"]",
  "strategies": "[]",
  "min_agreement": 1,
  "trust_score": 70.0,
  "trust_tier": "Highly Trusted",
  "total_trades": 10,
  "wins": 7,
  "losses": 3,
  "win_rate": 70.0,
  "total_pnl": 120.44,
  "avg_pnl": 12.04,
  "profit_factor": 2.8,
  "active_pick_count": 0,
  "closed_pick_count": 10,
  "snapshot_at": "2026-03-08 23:41:14"
}
```

### 128. `lm_algo_health` — ~28 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `algorithm_name` (varchar(100)), `asset_class` (varchar(20)), `rolling_sharpe_30d` (decimal(8,4)), `rolling_win_rate_30d` (decimal(6,4)), `rolling_pnl_30d` (decimal(12,4)), `online_weight` (decimal(8,6)), `decay_status` (varchar(20)), `trades_30d` (int), `consecutive_losses` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**`asset_class` distribution:**
- `STOCK`: 12
- `FOREX`: 10
- `CRYPTO`: 6

**Sample Rows:**
```json
{
  "id": 111,
  "algorithm_name": "Consensus",
  "asset_class": "FOREX",
  "rolling_sharpe_30d": -37.6193,
  "rolling_win_rate_30d": 0.0,
  "rolling_pnl_30d": -0.6543,
  "online_weight": 0.5,
  "decay_status": "decayed",
  "trades_30d": 2,
  "consecutive_losses": 2,
  "updated_at": "2026-02-16 12:02:20"
}
{
  "id": 112,
  "algorithm_name": "RSI Reversal",
  "asset_class": "FOREX",
  "rolling_sharpe_30d": 0.0,
  "rolling_win_rate_30d": 0.0,
  "rolling_pnl_30d": -0.0344,
  "online_weight": 1.0,
  "decay_status": "healthy",
  "trades_30d": 1,
  "consecutive_losses": 1,
  "updated_at": "2026-02-16 12:02:20"
}
```

**`updated_at` range:** 2026-02-12 12:02:59 → 2026-05-08 12:00:51

### 129. `portfolio_snapshots` — ~26 rows (0MB + 0MB idx)
**Purpose:** Portfolio: Snapshots

**Columns (19):** `id` (int), `portfolio_id` (varchar(50)), `portfolio_name` (varchar(100)), `methodology` (varchar(50)), `category` (varchar(20)), `status` (varchar(20)), `equity` (decimal(15,2)), `initial_capital` (decimal(15,2)), `pnl_pct` (decimal(8,4)), `pnl_usd` (decimal(12,2)), `win_rate` (decimal(5,2)), `total_trades` (int) … +7 more

**Primary Key:** `id`
**Indexed:** `portfolio_id`, `snapshot_at`

**`category` distribution:**
- `signal`: 24
- `hoffman_htf`: 2

**`status` distribution:**
- `ACTIVE`: 26

**Sample Rows:**
```json
{
  "id": 1,
  "portfolio_id": "score_leaders",
  "portfolio_name": "Score Leaders",
  "methodology": "score",
  "category": "signal",
  "status": "ACTIVE",
  "equity": 10027.99,
  "initial_capital": 10000.0,
  "pnl_pct": 0.2799,
  "pnl_usd": 27.99,
  "win_rate": 60.0,
  "total_trades": 5,
  "open_positions": 3,
  "max_drawdown_pct": 0.2772,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "total_commission": 15.64,
  "resets": 0,
  "snapshot_at": "2026-03-10 14:00:17"
}
{
  "id": 2,
  "portfolio_id": "proven_only",
  "portfolio_name": "Proven Only",
  "methodology": "proven",
  "category": "signal",
  "status": "ACTIVE",
  "equity": 10023.28,
  "initial_capital": 10000.0,
  "pnl_pct": 0.2328,
  "pnl_usd": 23.28,
  "win_rate": 60.0,
  "total_trades": 5,
  "open_positions": 3,
  "max_drawdown_pct": 0.2618,
  "sharpe_ratio": 0.0,
  "profit_factor": 0.0,
  "total_commission": 22.13,
  "resets": 0,
  "snapshot_at": "2026-03-10 14:00:17"
}
```

### 130. `super_strategy_candidates` — ~26 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `strategy_id` (varchar(128)), `symbols_passed` (int), `asset_classes_passed` (int), `regimes_passed` (int), `concentration_ratio` (decimal(10,4)), `fisher_p` (decimal(12,8)), `status` (varchar(32)), `notes` (text), `updated_at` (datetime)

**Primary Key:** `strategy_id`

**`status` distribution:**
- `INVERSE_VALIDATED`: 12
- `VIABLE`: 6
- `STRONG`: 5
- `VARIANT_ACCEPTED`: 3

**Sample Rows:**
```json
{
  "strategy_id": "atr_regime_rsi",
  "symbols_passed": 1,
  "asset_classes_passed": 1,
  "regimes_passed": 0,
  "concentration_ratio": null,
  "fisher_p": 0.026373,
  "status": "STRONG",
  "notes": "WR=80.0% PF=3.99 Trades=15 Lineage=walkforward",
  "updated_at": "2026-04-03 00:25:22"
}
{
  "strategy_id": "claude_gainer_ml_inverse",
  "symbols_passed": 1,
  "asset_classes_passed": 1,
  "regimes_passed": 0,
  "concentration_ratio": null,
  "fisher_p": null,
  "status": "INVERSE_VALIDATED",
  "notes": "WR=80.0% PF=19.5616 Trades=10 Lineage=inverse_of:claude_gainer_ml",
  "updated_at": "2026-04-03 00:25:22"
}
```

**`updated_at` range:** 2026-04-03 00:25:22 → 2026-04-03 00:25:22

### 131. `algorithm_performance` — ~23 rows (0MB + 0MB idx)
**Purpose:** Algo: Performance tracking

**Columns (10):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "Adversarial Trend (V2)",
  "strategy_type": "learning_scan",
  "total_picks": 18,
  "total_trades": 18,
  "win_rate": 5.56,
  "avg_return_pct": -3.4014,
  "best_for": "No profitable params found",
  "worst_for": "Current default: -5.0421% return",
  "updated_at": "2026-05-03 16:15:21"
}
{
  "id": 2,
  "algorithm_name": "Blue Chip Growth",
  "strategy_type": "learning_scan",
  "total_picks": 298,
  "total_trades": 298,
  "win_rate": 7.05,
  "avg_return_pct": -6.4194,
  "best_for": "No profitable params found",
  "worst_for": "Current default: -76.8463% return",
  "updated_at": "2026-03-11 22:59:14"
}
```

**`updated_at` range:** 2026-02-16 00:17:55 → 2026-05-03 16:20:06

### 132. `crypto_exchange_netflow` — ~20 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (6):** `id` (int), `blockchain` (varchar(20)), `exchange_name` (varchar(50)), `netflow_24h` (decimal(20,8)), `netflow_7d` (decimal(20,8)), `calculated_at` (timestamp)

**Primary Key:** `id`
**Indexed:** `blockchain`

**Sample Rows:**
```json
{
  "id": 1,
  "blockchain": "ETH",
  "exchange_name": "binance",
  "netflow_24h": 0.0,
  "netflow_7d": 0.0,
  "calculated_at": "2026-02-12 22:19:48"
}
{
  "id": 2,
  "blockchain": "ETH",
  "exchange_name": "coinbase",
  "netflow_24h": 0.0,
  "netflow_7d": 0.0,
  "calculated_at": "2026-02-12 22:19:48"
}
```

### 133. `mf_funds` — ~20 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (13):** `ticker` (varchar(15)), `fund_name` (varchar(300)), `category` (varchar(150)), `family` (varchar(150)), `expense_ratio` (decimal(5,4)), `min_investment` (decimal(12,2)), `load_type` (varchar(30)), `front_load_pct` (decimal(5,2)), `back_load_pct` (decimal(5,2)), `morningstar_rating` (tinyint), `asset_class` (varchar(50)), `inception_date` (date) … +1 more

**Primary Key:** `ticker`

**`category` distribution:**
- `Large Blend`: 5
- `Large Growth`: 2
- `Health`: 2
- `Allocation 50-70% Eq`: 2
- `Intermediate Core Bond`: 1
- `Allocation 60-70% Eq`: 1
- `Multisector Bond`: 1
- `Foreign Large Growth`: 1
- `Foreign Large Value`: 1
- `Allocation 30-50% Eq`: 1
- `Large Value`: 1
- `Foreign Large Blend`: 1

**`asset_class` distribution:**
- `Equity`: 8
- `Balanced`: 4
- `International`: 3
- `Bond`: 2
- `Sector`: 2
- `Real Estate`: 1

**Sample Rows:**
```json
{
  "ticker": "VFIAX",
  "fund_name": "Vanguard 500 Index Fund Admiral",
  "category": "Large Blend",
  "family": "Vanguard",
  "expense_ratio": 0.0004,
  "min_investment": 3000.0,
  "load_type": "no-load",
  "front_load_pct": 0.0,
  "back_load_pct": 0.0,
  "morningstar_rating": 5,
  "asset_class": "Equity",
  "inception_date": null,
  "net_assets": ""
}
{
  "ticker": "FXAIX",
  "fund_name": "Fidelity 500 Index Fund",
  "category": "Large Blend",
  "family": "Fidelity",
  "expense_ratio": 0.0015,
  "min_investment": 0.0,
  "load_type": "no-load",
  "front_load_pct": 0.0,
  "back_load_pct": 0.0,
  "morningstar_rating": 5,
  "asset_class": "Equity",
  "inception_date": null,
  "net_assets": ""
}
```

### 134. `cp_audit_log` — ~19 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `action_type` (varchar(50)), `details` (text), `ip_address` (varchar(45)), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "action_type": "seed_signals",
  "details": "Seeded 174 signals, skipped 0",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 06:18:45"
}
{
  "id": 2,
  "action_type": "backtest",
  "details": "Backtest: 174 trades, -6.2421% return",
  "ip_address": "74.14.165.178",
  "created_at": "2026-02-09 06:18:55"
}
```

**`created_at` range:** 2026-02-09 06:18:45 → 2026-02-16 23:20:05

### 135. `now_strategy_stats` — ~17 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (13):** `strategy` (varchar(50)), `total_picks` (int), `wins_1_5` (int), `losses_1_5` (int), `wins_2_0` (int), `losses_2_0` (int), `expired` (int), `win_rate_1_5` (decimal(5,2)), `win_rate_2_0` (decimal(5,2)), `avg_pnl_pct` (decimal(8,4)), `best_trade_pct` (decimal(8,4)), `worst_trade_pct` (decimal(8,4)) … +1 more

**Primary Key:** `strategy`

**`strategy` distribution:**
- `bollinger_squeeze`: 1
- `ema_stack`: 1
- `funding_reversal`: 1
- `macd_crossover`: 1
- `macd_rsi_confluence`: 1
- `rsi_bounce`: 1
- `rsi_overbought`: 1
- `st_atr_vol_breakout`: 1
- `st_bb_squeeze_expansion`: 1
- `st_fear_greed_contrarian`: 1
- `st_momentum_compression`: 1
- `st_multi_day_momentum`: 1

**Sample Rows:**
```json
{
  "strategy": "bollinger_squeeze",
  "total_picks": 4199,
  "wins_1_5": 34,
  "losses_1_5": 63,
  "wins_2_0": 22,
  "losses_2_0": 63,
  "expired": 4102,
  "win_rate_1_5": 35.05,
  "win_rate_2_0": 25.88,
  "avg_pnl_pct": -0.0144,
  "best_trade_pct": 18.4506,
  "worst_trade_pct": -8.408,
  "last_updated": "2026-05-08 13:58:30"
}
{
  "strategy": "ema_stack",
  "total_picks": 8337,
  "wins_1_5": 411,
  "losses_1_5": 667,
  "wins_2_0": 223,
  "losses_2_0": 684,
  "expired": 7259,
  "win_rate_1_5": 38.13,
  "win_rate_2_0": 24.59,
  "avg_pnl_pct": 0.0249,
  "best_trade_pct": 16.1508,
  "worst_trade_pct": -14.2222,
  "last_updated": "2026-05-08 13:58:30"
}
```

**`last_updated` range:** 2026-05-08 13:58:30 → 2026-05-08 13:58:30

### 136. `fx_pair_picks` — ~16 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (13):** `id` (int), `symbol` (varchar(20)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_price` (decimal(12,6)), `direction` (varchar(10)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)) … +1 more

**Primary Key:** `id`
**Indexed:** `symbol`, `algorithm_name`, `pick_date`, `pick_hash`

**`direction` distribution:**
- `LONG`: 10
- `SHORT`: 6

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "EURUSD",
  "algorithm_id": 1,
  "algorithm_name": "FX Trend Following",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_price": 1.0845,
  "direction": "LONG",
  "score": 82,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "1d",
  "pick_hash": ""
}
{
  "id": 2,
  "symbol": "EURUSD",
  "algorithm_id": 2,
  "algorithm_name": "FX Momentum",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_price": 1.082,
  "direction": "LONG",
  "score": 75,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "4h",
  "pick_hash": ""
}
```

**`pick_date` range:** 2026-02-09 → 2026-02-09

**`pick_time` range:** 2026-02-09 16:00:00 → 2026-02-09 16:00:00

### 137. `cp_pairs` — ~15 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (6):** `pair` (varchar(15)), `pair_name` (varchar(100)), `base_asset` (varchar(10)), `quote_asset` (varchar(10)), `category` (varchar(50)), `yahoo_ticker` (varchar(20))

**Primary Key:** `pair`

**`category` distribution:**
- `large_cap`: 6
- `mid_cap`: 5
- `meme`: 2
- `defi`: 2

**Sample Rows:**
```json
{
  "pair": "BTC-USD",
  "pair_name": "Bitcoin / USD",
  "base_asset": "BTC",
  "quote_asset": "USD",
  "category": "large_cap",
  "yahoo_ticker": "BTC-USD"
}
{
  "pair": "ETH-USD",
  "pair_name": "Ethereum / USD",
  "base_asset": "ETH",
  "quote_asset": "USD",
  "category": "large_cap",
  "yahoo_ticker": "ETH-USD"
}
```

### 138. `fx_pairs` — ~15 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (7):** `pair` (varchar(10)), `pair_name` (varchar(100)), `base_currency` (varchar(5)), `quote_currency` (varchar(5)), `category` (varchar(50)), `pip_value` (decimal(10,6)), `yahoo_ticker` (varchar(20))

**Primary Key:** `pair`

**`category` distribution:**
- `major`: 7
- `cross`: 7
- `exotic`: 1

**Sample Rows:**
```json
{
  "pair": "EURUSD",
  "pair_name": "Euro / US Dollar",
  "base_currency": "EUR",
  "quote_currency": "USD",
  "category": "major",
  "pip_value": 0.0001,
  "yahoo_ticker": "EURUSD=X"
}
{
  "pair": "GBPUSD",
  "pair_name": "British Pound / US Dollar",
  "base_currency": "GBP",
  "quote_currency": "USD",
  "category": "major",
  "pip_value": 0.0001,
  "yahoo_ticker": "GBPUSD=X"
}
```

### 139. `lm_discovered_movers` — ~15 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (10):** `id` (int), `symbol` (varchar(20)), `binance_symbol` (varchar(20)), `price` (decimal(18,8)), `change_24h_pct` (decimal(10,4)), `volume_usd` (decimal(24,2)), `direction` (varchar(10)), `signal_count` (int), `signals` (text), `discovered_at` (datetime)

**Primary Key:** `id`
**Indexed:** `symbol`, `discovered_at`

**`direction` distribution:**
- `LOSER`: 8
- `GAINER`: 7

**Sample Rows:**
```json
{
  "id": 16,
  "symbol": "STABLEUSD",
  "binance_symbol": "STABLEUSDT",
  "price": 0.02160715,
  "change_24h_pct": 13.9032,
  "volume_usd": 32779051.0,
  "direction": "GAINER",
  "signal_count": 0,
  "signals": "[]",
  "discovered_at": "2026-02-10 04:02:04"
}
{
  "id": 17,
  "symbol": "ZROUSD",
  "binance_symbol": "ZROUSDT",
  "price": 1.92,
  "change_24h_pct": 12.0655,
  "volume_usd": 109271255.0,
  "direction": "GAINER",
  "signal_count": 0,
  "signals": "[]",
  "discovered_at": "2026-02-10 04:02:04"
}
```

### 140. `lm_ml_status` — ~15 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (25):** `id` (int), `algorithm_name` (varchar(100)), `asset_class` (varchar(20)), `closed_trades` (int), `min_trades_needed` (int), `ml_ready` (tinyint), `current_tp` (decimal(5,2)), `current_sl` (decimal(5,2)), `current_hold` (int), `param_source` (varchar(20)), `current_win_rate` (decimal(5,2)), `current_sharpe` (decimal(8,4)) … +13 more

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**`asset_class` distribution:**
- `STOCK`: 7
- `FOREX`: 4
- `CRYPTO`: 4

**`status` distribution:**
- `backtest_only`: 11
- `collecting_data`: 4

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "Consensus",
  "asset_class": "FOREX",
  "closed_trades": 2,
  "min_trades_needed": 20,
  "ml_ready": 0,
  "current_tp": 3.0,
  "current_sl": 2.0,
  "current_hold": 12,
  "param_source": "learned",
  "current_win_rate": 0.0,
  "current_sharpe": null,
  "current_pf": 0.0,
  "total_pnl": -3.28,
  "last_optimization": null,
  "optimization_count": 0,
  "best_sharpe_ever": null,
  "backtest_sharpe": null,
  "backtest_grade": null,
  "backtest_trades": 0,
  "forward_backtest_overlap": 0,
  "status": "collecting_data",
  "status_reason": "Need 18 more trades for grid search optimization",
  "updated_at": "2026-02-12 21:15:23",
  "created_at": "2026-02-12 21:15:23"
}
{
  "id": 2,
  "algorithm_name": "RSI Reversal",
  "asset_class": "FOREX",
  "closed_trades": 1,
  "min_trades_needed": 20,
  "ml_ready": 0,
  "current_tp": 2.0,
  "current_sl": 1.0,
  "current_hold": 6,
  "param_source": "learned",
  "current_win_rate": 0.0,
  "current_sharpe": null,
  "current_pf": 0.0,
  "total_pnl": -0.17,
  "last_optimization": null,
  "optimization_count": 0,
  "best_sharpe_ever": null,
  "backtest_sharpe": null,
  "backtest_grade": null,
  "backtest_trades": 0,
  "forward_backtest_overlap": 0,
  "status": "collecting_data",
  "status_reason": "Need 19 more trades for grid search optimization",
  "updated_at": "2026-02-12 21:15:23",
  "created_at": "2026-02-12 21:15:23"
}
```

**`updated_at` range:** 2026-02-12 21:15:23 → 2026-02-12 21:15:23

**`created_at` range:** 2026-02-12 21:15:23 → 2026-02-12 21:15:23

### 141. `lm_sports_bankroll` — ~15 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `snapshot_date` (date), `bankroll` (decimal(10,2)), `total_bets` (int), `total_wins` (int), `total_losses` (int), `total_pushes` (int), `win_rate` (decimal(5,2)), `total_wagered` (decimal(10,2)), `total_pnl` (decimal(10,2)), `roi_pct` (decimal(6,2))

**Primary Key:** `id`
**Indexed:** `snapshot_date`

**Sample Rows:**
```json
{
  "id": 9,
  "snapshot_date": "2026-02-11",
  "bankroll": 1013.14,
  "total_bets": 3,
  "total_wins": 1,
  "total_losses": 2,
  "total_pushes": 0,
  "win_rate": 33.33,
  "total_wagered": 51.86,
  "total_pnl": 13.14,
  "roi_pct": 25.34
}
{
  "id": 19,
  "snapshot_date": "2026-02-12",
  "bankroll": 1016.66,
  "total_bets": 9,
  "total_wins": 2,
  "total_losses": 7,
  "total_pushes": 0,
  "win_rate": 22.22,
  "total_wagered": 83.84,
  "total_pnl": 16.66,
  "roi_pct": 19.87
}
```

**`snapshot_date` range:** 2026-02-11 → 2026-03-28

### 142. `mf2_funds` — ~15 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (9):** `symbol` (varchar(20)), `fund_name` (varchar(300)), `fund_family` (varchar(200)), `category` (varchar(200)), `asset_class` (varchar(50)), `expense_ratio` (decimal(6,4)), `min_investment` (decimal(12,2)), `inception_date` (date), `morningstar_rating` (tinyint)

**Primary Key:** `symbol`

**`category` distribution:**
- `Canadian Equity`: 2
- `US Equity`: 2
- `Canadian Bond`: 2
- `Canadian Balanced`: 2
- `Canadian Dividend`: 2
- `Global Equity`: 1
- `International Equity`: 1
- `Canadian Equity Index`: 1
- `US Equity Index`: 1
- `Emerging Markets`: 1

**`asset_class` distribution:**
- `Equity`: 11
- `Fixed Income`: 2
- `Balanced`: 2

**Sample Rows:**
```json
{
  "symbol": "RBF460",
  "fund_name": "RBC Canadian Equity Fund",
  "fund_family": "RBC",
  "category": "Canadian Equity",
  "asset_class": "Equity",
  "expense_ratio": 1.71,
  "min_investment": 0.0,
  "inception_date": null,
  "morningstar_rating": 4
}
{
  "symbol": "TDB161",
  "fund_name": "TD Canadian Equity Fund",
  "fund_family": "TD",
  "category": "Canadian Equity",
  "asset_class": "Equity",
  "expense_ratio": 1.97,
  "min_investment": 0.0,
  "inception_date": null,
  "morningstar_rating": 3
}
```

### 143. `mf_fund_picks` — ~15 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (13):** `id` (int), `symbol` (varchar(20)), `algorithm_id` (int), `algorithm_name` (varchar(100)), `pick_date` (date), `pick_time` (datetime), `entry_nav` (decimal(12,4)), `score` (int), `rating` (varchar(20)), `risk_level` (varchar(20)), `timeframe` (varchar(20)), `pick_hash` (varchar(64)) … +1 more

**Primary Key:** `id`
**Indexed:** `symbol`, `algorithm_name`, `pick_date`, `pick_hash`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "RBF460",
  "algorithm_id": 8,
  "algorithm_name": "MF Quality Growth",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_nav": 48.52,
  "score": 78,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "1y",
  "pick_hash": "",
  "rationale_json": ""
}
{
  "id": 2,
  "symbol": "TDB161",
  "algorithm_id": 1,
  "algorithm_name": "MF Momentum",
  "pick_date": "2026-02-09",
  "pick_time": "2026-02-09 16:00:00",
  "entry_nav": 32.15,
  "score": 72,
  "rating": "Buy",
  "risk_level": "Medium",
  "timeframe": "3m",
  "pick_hash": "",
  "rationale_json": ""
}
```

**`pick_date` range:** 2026-02-09 → 2026-02-09

**`pick_time` range:** 2026-02-09 16:00:00 → 2026-02-09 16:00:00

### 144. `KIMI_GOLDMINE_SOURCES` — ~14 rows (0MB + 0MB idx)
**Purpose:** Kimi System: Data

**Columns (31):** `id` (int), `source_type` (enum('stock','penny_stock','crypto','meme_coin','forex','mutual_fund','sports','alpha_engine')), `source_name` (varchar(100)), `source_slug` (varchar(100)), `algorithm_name` (varchar(100)), `algorithm_slug` (varchar(100)), `display_name` (varchar(200)), `description` (text), `strategy_type` (varchar(100)), `ideal_timeframe` (varchar(50)), `risk_level` (enum('low','medium','high','very_high')), `is_active` (tinyint(1)) … +19 more

**Primary Key:** `id`
**Indexed:** `source_type`, `source_slug`, `is_active`, `current_goldmine_status`

**Sample Rows:**
```json
{
  "id": 1,
  "source_type": "stock",
  "source_name": "findstocks_portfolio2",
  "source_slug": "findstocks-portfolio2",
  "algorithm_name": "Alpha Forge Ultimate",
  "algorithm_slug": "alpha_forge_ultimate",
  "display_name": "Alpha Forge Ultimate",
  "description": "Multi-factor ensemble with regime weighting",
  "strategy_type": "multi_factor",
  "ideal_timeframe": "medium_term",
  "risk_level": "high",
  "is_active": 1,
  "auto_import": 1,
  "import_frequency": null,
  "source_api_endpoint": "findstocks/portfolio2/api/consolidated_picks.php",
  "source_db_table": "stock_picks",
  "min_win_rate_for_goldmine": 55.0,
  "min_return_for_goldmine": 10.0,
  "min_sharpe_for_goldmine": 1.0,
  "min_samples_for_goldmine": 10,
  "current_goldmine_status": 0,
  "goldmine_achieved_date": null,
  "goldmine_lost_date": null,
  "total_goldmine_periods": 0,
  "total_picks_all_time": 0,
  "total_wins_all_time": 0,
  "avg_return_all_time": null,
  "best_streak": 0,
  "worst_streak": 0,
  "created_at": "2026-02-11 00:39:36",
  "updated_at": "2026-02-11 00:39:36"
}
{
  "id": 2,
  "source_type": "stock",
  "source_name": "findstocks_portfolio2",
  "source_slug": "findstocks-portfolio2",
  "algorithm_name": "God-Mode Standard",
  "algorithm_slug": "god_mode_standard",
  "display_name": "God-Mode Standard",
  "description": "Meta-learner ensemble: regime-aware, Kelly-sized",
  "strategy_type": "ensemble",
  "ideal_timeframe": "medium_term",
  "risk_level": "medium",
  "is_active": 1,
  "auto_import": 1,
  "import_frequency": null,
  "source_api_endpoint": "findstocks/portfolio2/api/consolidated_picks.php",
  "source_db_table": "stock_picks",
  "min_win_rate_for_goldmine": 55.0,
  "min_return_for_goldmine": 10.0,
  "min_sharpe_for_goldmine": 1.0,
  "min_samples_for_goldmine": 10,
  "current_goldmine_status": 0,
  "goldmine_achieved_date": null,
  "goldmine_lost_date": null,
  "total_goldmine_periods": 0,
  "total_picks_all_time": 0,
  "total_wins_all_time": 0,
  "avg_return_all_time": null,
  "best_streak": 0,
  "worst_streak": 0,
  "created_at": "2026-02-11 00:39:36",
  "updated_at": "2026-02-11 00:39:36"
}
```

**`ideal_timeframe` range:** long_term → very_short

### 145. `crypto_assets` — ~14 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `symbol` (varchar(20)), `name` (varchar(100)), `asset_type` (enum('major','altcoin','meme','defi','nft','layer2')), `market_cap_category` (enum('mega','large','mid','small','micro','nano')), `is_meme` (tinyint(1)), `blockchain` (varchar(50)), `created_at` (timestamp), `updated_at` (timestamp)

**Primary Key:** `id`
**Indexed:** `symbol`, `asset_type`, `is_meme`

**Sample Rows:**
```json
{
  "id": 1,
  "symbol": "BTC",
  "name": "Bitcoin",
  "asset_type": "major",
  "market_cap_category": "mega",
  "is_meme": 0,
  "blockchain": null,
  "created_at": "2026-02-14 20:48:40",
  "updated_at": "2026-02-14 20:48:40"
}
{
  "id": 2,
  "symbol": "ETH",
  "name": "Ethereum",
  "asset_type": "major",
  "market_cap_category": "mega",
  "is_meme": 0,
  "blockchain": null,
  "created_at": "2026-02-14 20:48:40",
  "updated_at": "2026-02-14 20:48:40"
}
```

**`created_at` range:** 2026-02-14 20:48:40 → 2026-02-14 20:48:40

**`updated_at` range:** 2026-02-14 20:48:40 → 2026-02-14 20:48:40

### 146. `lm_nba_games_today` — ~14 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (13):** `id` (int), `game_id` (varchar(30)), `game_date` (date), `home_team` (varchar(100)), `away_team` (varchar(100)), `home_abbr` (varchar(10)), `away_abbr` (varchar(10)), `venue` (varchar(100)), `start_time` (varchar(30)), `status` (varchar(30)), `home_score` (int), `away_score` (int) … +1 more

**Primary Key:** `id`
**Indexed:** `game_id`

**`status` distribution:**
- `STATUS_FINAL`: 13
- `STATUS_IN_PROGRESS`: 1

**Sample Rows:**
```json
{
  "id": 29,
  "game_id": "401810630",
  "game_date": "2026-02-12",
  "home_team": "Charlotte Hornets",
  "away_team": "Atlanta Hawks",
  "home_abbr": "CHA",
  "away_abbr": "ATL",
  "venue": "Spectrum Center",
  "start_time": "00:00",
  "status": "STATUS_FINAL",
  "home_score": 110,
  "away_score": 107,
  "updated_at": "2026-02-12 05:25:22"
}
{
  "id": 30,
  "game_id": "401810631",
  "game_date": "2026-02-12",
  "home_team": "Cleveland Cavaliers",
  "away_team": "Washington Wizards",
  "home_abbr": "CLE",
  "away_abbr": "WSH",
  "venue": "Rocket Arena",
  "start_time": "00:00",
  "status": "STATUS_FINAL",
  "home_score": 138,
  "away_score": 113,
  "updated_at": "2026-02-12 05:25:22"
}
```

**`game_date` range:** 2026-02-12 → 2026-02-12

**`start_time` range:** 00:00 → 03:00

### 147. `ml_learning_curve` — ~14 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `engine_name` (varchar(50)), `data_date` (date), `sample_count` (int), `rolling_win_rate` (float), `rolling_sharpe` (float), `rolling_profit_factor` (float), `improvement_rate` (float)

**Primary Key:** `id`
**Indexed:** `engine_name`

**Sample Rows:**
```json
{
  "id": 1,
  "engine_name": "Hybrid Engine",
  "data_date": "2026-02-14",
  "sample_count": 31,
  "rolling_win_rate": 0.0,
  "rolling_sharpe": 0.0,
  "rolling_profit_factor": 0.0,
  "improvement_rate": 0.0
}
{
  "id": 2,
  "engine_name": "TV Technicals",
  "data_date": "2026-02-14",
  "sample_count": 51,
  "rolling_win_rate": 0.0,
  "rolling_sharpe": 0.0,
  "rolling_profit_factor": 0.0,
  "improvement_rate": 0.0
}
```

**`data_date` range:** 2026-02-14 → 2026-02-16

### 148. `eh_alerts` — ~13 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (8):** `id` (int), `engine_name` (varchar(60)), `alert_type` (varchar(30)), `severity` (varchar(15)), `message` (text), `old_grade` (varchar(2)), `new_grade` (varchar(2)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `engine_name`

**Sample Rows:**
```json
{
  "id": 1,
  "engine_name": "Crypto Winners",
  "alert_type": "DEGRADATION",
  "severity": "CRITICAL",
  "message": "Crypto Winners grade changed: D -> F",
  "old_grade": "D",
  "new_grade": "F",
  "created_at": "2026-02-15 03:27:42"
}
{
  "id": 2,
  "engine_name": "Academic Edge",
  "alert_type": "IMPROVEMENT",
  "severity": "INFO",
  "message": "Academic Edge grade changed: F -> C",
  "old_grade": "F",
  "new_grade": "C",
  "created_at": "2026-02-15 07:12:51"
}
```

**`created_at` range:** 2026-02-15 03:27:42 → 2026-02-16 13:45:49

### 149. `eh_engine_grades` — ~12 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (15):** `id` (int), `engine_name` (varchar(60)), `health_score` (float), `health_grade` (varchar(2)), `total_signals` (int), `resolved_signals` (int), `win_rate` (float), `total_pnl` (float), `avg_pnl` (float), `sharpe_estimate` (float), `data_freshness_hours` (float), `signal_frequency_daily` (float) … +3 more

**Primary Key:** `id`
**Indexed:** `engine_name`

**Sample Rows:**
```json
{
  "id": 157,
  "engine_name": "Hybrid Engine",
  "health_score": 50.0,
  "health_grade": "C",
  "total_signals": 50,
  "resolved_signals": 28,
  "win_rate": 25.0,
  "total_pnl": -31.0538,
  "avg_pnl": -1.1091,
  "sharpe_estimate": -0.57,
  "data_freshness_hours": 4.7,
  "signal_frequency_daily": 22.35,
  "recommendation": "MONITOR",
  "details": "WR: 25% (10pts) | PnL: -31.05% (0pts) | Volume: 50 signals (15pts) | Fresh: 4.7h (15pts) | Confidence: 28 resolved (10pts)",
  "graded_at": "2026-02-16 19:10:11"
}
{
  "id": 158,
  "engine_name": "TV Technicals",
  "health_score": 60.0,
  "health_grade": "C",
  "total_signals": 141,
  "resolved_signals": 141,
  "win_rate": 37.6,
  "total_pnl": -35.9347,
  "avg_pnl": -0.2549,
  "sharpe_estimate": -0.62,
  "data_freshness_hours": 5.4,
  "signal_frequency_daily": 78.93,
  "recommendation": "MONITOR",
  "details": "WR: 37.6% (15pts) | PnL: -35.93% (0pts) | Volume: 141 signals (15pts) | Fresh: 5.4h (15pts) | Confidence: 141 resolved (15pts)",
  "graded_at": "2026-02-16 19:10:11"
}
```

### 150. `lm_bridge_options` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (9):** `id` (int), `ticker` (varchar(10)), `spot_price` (decimal(12,2)), `net_gex` (decimal(20,0)), `gex_signal` (varchar(30)), `pc_oi_ratio` (decimal(8,3)), `pcr_signal` (varchar(30)), `unusual_count` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `ticker`

**Sample Rows:**
```json
{
  "id": 25,
  "ticker": "AAPL",
  "spot_price": 255.78,
  "net_gex": 0.0,
  "gex_signal": "NEGATIVE_GAMMA",
  "pc_oi_ratio": 0.0,
  "pcr_signal": "EXTREME_CALLS",
  "unusual_count": 0,
  "updated_at": "2026-02-16 12:02:38"
}
{
  "id": 26,
  "ticker": "MSFT",
  "spot_price": 401.32,
  "net_gex": 0.0,
  "gex_signal": "NEGATIVE_GAMMA",
  "pc_oi_ratio": 0.0,
  "pcr_signal": "EXTREME_CALLS",
  "unusual_count": 0,
  "updated_at": "2026-02-16 12:02:38"
}
```

**`updated_at` range:** 2026-02-16 12:02:38 → 2026-02-16 12:02:38

### 151. `lm_conviction_history` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (17):** `id` (int), `ticker` (varchar(10)), `calc_date` (date), `conviction_score` (int), `conviction_label` (varchar(20)), `whale_score` (int), `insider_score` (int), `analyst_score` (int), `crowd_score` (int), `fear_greed_score` (int), `regime_score` (int), `value_score` (int) … +5 more

**Primary Key:** `id`
**Indexed:** `ticker`, `calc_date`, `conviction_score`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "calc_date": "2026-02-11",
  "conviction_score": 67,
  "conviction_label": "bullish",
  "whale_score": 80,
  "insider_score": 68,
  "analyst_score": 64,
  "crowd_score": 66,
  "fear_greed_score": 56,
  "regime_score": 58,
  "value_score": 59,
  "growth_score": 87,
  "momentum_score": 44,
  "entry_price": 273.68,
  "detail_json": "{\"whale\":{\"score\":80,\"detail\":\"funds=1 bull=1 bear=0 new=1 exits=0 val=$87785M\"},\"insider\":{\"score\":68,\"detail\":\"analyst_fallback analyst_proxy br=0.6...",
  "created_at": "2026-02-11 03:55:13"
}
{
  "id": 2,
  "ticker": "MSFT",
  "calc_date": "2026-02-11",
  "conviction_score": 79,
  "conviction_label": "strong_bullish",
  "whale_score": 80,
  "insider_score": 89,
  "analyst_score": 86,
  "crowd_score": 76,
  "fear_greed_score": 60,
  "regime_score": 59,
  "value_score": 88,
  "growth_score": 92,
  "momentum_score": 47,
  "entry_price": 413.27,
  "detail_json": "{\"whale\":{\"score\":80,\"detail\":\"funds=1 bull=1 bear=0 new=1 exits=0 val=$568279M\"},\"insider\":{\"score\":89,\"detail\":\"analyst_fallback analyst_proxy br=0....",
  "created_at": "2026-02-11 03:55:13"
}
```

**`calc_date` range:** 2026-02-11 → 2026-02-11

**`created_at` range:** 2026-02-11 03:55:13 → 2026-02-11 03:55:14

### 152. `lm_conviction_performance` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (17):** `id` (int), `ticker` (varchar(10)), `conviction_date` (date), `conviction_score` (int), `conviction_label` (varchar(20)), `entry_price` (decimal(12,2)), `price_7d` (decimal(12,2)), `price_14d` (decimal(12,2)), `price_30d` (decimal(12,2)), `return_7d` (decimal(8,4)), `return_14d` (decimal(8,4)), `return_30d` (decimal(8,4)) … +5 more

**Primary Key:** `id`
**Indexed:** `ticker`, `conviction_date`, `conviction_score`, `filled_7d`, `filled_30d`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "conviction_date": "2026-02-11",
  "conviction_score": 67,
  "conviction_label": "bullish",
  "entry_price": 273.68,
  "price_7d": 0.0,
  "price_14d": 0.0,
  "price_30d": 0.0,
  "return_7d": 0.0,
  "return_14d": 0.0,
  "return_30d": 0.0,
  "outcome_30d": "pending",
  "filled_7d": 0,
  "filled_14d": 0,
  "filled_30d": 0,
  "created_at": "2026-02-11 03:55:13"
}
{
  "id": 2,
  "ticker": "MSFT",
  "conviction_date": "2026-02-11",
  "conviction_score": 79,
  "conviction_label": "strong_bullish",
  "entry_price": 413.27,
  "price_7d": 0.0,
  "price_14d": 0.0,
  "price_30d": 0.0,
  "return_7d": 0.0,
  "return_14d": 0.0,
  "return_30d": 0.0,
  "outcome_30d": "pending",
  "filled_7d": 0,
  "filled_14d": 0,
  "filled_30d": 0,
  "created_at": "2026-02-11 03:55:13"
}
```

**`conviction_date` range:** 2026-02-11 → 2026-02-11

**`created_at` range:** 2026-02-11 03:55:13 → 2026-02-11 03:55:14

### 153. `lm_multi_dimensional` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (16):** `id` (int), `ticker` (varchar(10)), `calc_date` (date), `whale_score` (int), `insider_score` (int), `analyst_score` (int), `crowd_score` (int), `fear_greed_score` (int), `regime_score` (int), `value_score` (int), `growth_score` (int), `momentum_score` (int) … +4 more

**Primary Key:** `id`
**Indexed:** `ticker`, `calc_date`, `conviction_score`

**Sample Rows:**
```json
{
  "id": 97,
  "ticker": "AAPL",
  "calc_date": "2026-02-11",
  "whale_score": 80,
  "insider_score": 68,
  "analyst_score": 64,
  "crowd_score": 66,
  "fear_greed_score": 56,
  "regime_score": 58,
  "value_score": 59,
  "growth_score": 87,
  "momentum_score": 44,
  "conviction_score": 67,
  "conviction_label": "bullish",
  "dimension_detail": "{\"whale\":{\"score\":80,\"detail\":\"funds=1 bull=1 bear=0 new=1 exits=0 val=$87785M\"},\"insider\":{\"score\":68,\"detail\":\"analyst_fallback analyst_proxy br=0.6...",
  "created_at": "2026-02-11 03:55:13"
}
{
  "id": 98,
  "ticker": "MSFT",
  "calc_date": "2026-02-11",
  "whale_score": 80,
  "insider_score": 89,
  "analyst_score": 86,
  "crowd_score": 76,
  "fear_greed_score": 60,
  "regime_score": 59,
  "value_score": 88,
  "growth_score": 92,
  "momentum_score": 47,
  "conviction_score": 79,
  "conviction_label": "strong_bullish",
  "dimension_detail": "{\"whale\":{\"score\":80,\"detail\":\"funds=1 bull=1 bear=0 new=1 exits=0 val=$568279M\"},\"insider\":{\"score\":89,\"detail\":\"analyst_fallback analyst_proxy br=0....",
  "created_at": "2026-02-11 03:55:13"
}
```

**`calc_date` range:** 2026-02-11 → 2026-02-11

**`created_at` range:** 2026-02-11 03:55:13 → 2026-02-11 03:55:14

### 154. `lm_price_targets` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `ticker` (varchar(10)), `target_high` (decimal(12,2)), `target_low` (decimal(12,2)), `target_mean` (decimal(12,2)), `target_median` (decimal(12,2)), `last_updated` (date), `fetch_date` (date), `created_at` (datetime), `num_analysts` (int), `source` (varchar(30))

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`

**Sample Rows:**
```json
{
  "id": 25,
  "ticker": "AAPL",
  "target_high": 350.0,
  "target_low": 205.0,
  "target_mean": 293.07,
  "target_median": 300.0,
  "last_updated": "0000-00-00",
  "fetch_date": "2026-02-11",
  "created_at": "2026-02-11 02:56:23",
  "num_analysts": 41,
  "source": "yahoo"
}
{
  "id": 26,
  "ticker": "MSFT",
  "target_high": 730.0,
  "target_low": 392.0,
  "target_mean": 596.18,
  "target_median": 600.0,
  "last_updated": "0000-00-00",
  "fetch_date": "2026-02-11",
  "created_at": "2026-02-11 02:56:23",
  "num_analysts": 53,
  "source": "yahoo"
}
```

**`last_updated` range:** 0000-00-00 → 0000-00-00

**`fetch_date` range:** 2026-02-11 → 2026-02-11

### 155. `lm_wsb_sentiment` — ~12 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `ticker` (varchar(10)), `scan_date` (date), `mentions_24h` (int), `sentiment` (decimal(5,3)), `total_upvotes` (int), `wsb_score` (decimal(8,2)), `top_post_title` (varchar(200)), `created_at` (datetime), `top_posts` (text), `fetch_date` (date)

**Primary Key:** `id`
**Indexed:** `ticker`, `scan_date`, `wsb_score`

**Sample Rows:**
```json
{
  "id": 25,
  "ticker": "MSFT",
  "scan_date": "0000-00-00",
  "mentions_24h": 30,
  "sentiment": 0.875,
  "total_upvotes": 0,
  "wsb_score": 76.25,
  "top_post_title": "",
  "created_at": "2026-02-11 02:50:21",
  "top_posts": "[\"$MSFT\",\"$MSFT this was the last day to load up under $410\",\"$MSFT I sure hope so. 176 calls on deck\"]",
  "fetch_date": "2026-02-11"
}
{
  "id": 26,
  "ticker": "GOOGL",
  "scan_date": "0000-00-00",
  "mentions_24h": 30,
  "sentiment": 0.846,
  "total_upvotes": 0,
  "wsb_score": 75.38,
  "top_post_title": "",
  "created_at": "2026-02-11 02:50:21",
  "top_posts": "[\"$GOOG $GOOGL Now, I know a lot of you are expecting a further run out of Google, as if this hasn&#39;t already run 100% \",\"$TSLA $META $NVDA $GOOGL ...",
  "fetch_date": "2026-02-11"
}
```

**`scan_date` range:** 0000-00-00 → 0000-00-00

**`sentiment` range:** -0.429 → 1.000

### 156. `mf2_portfolios` — ~12 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (15):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `algorithm_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `commission_buy` (decimal(6,2)), `commission_sell` (decimal(6,2)), `redemption_fee_pct` (decimal(5,2)), `target_return_pct` (decimal(5,2)), `stop_loss_pct` (decimal(5,2)), `max_hold_days` (int) … +3 more

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Conservative Income",
  "description": "Bond/income funds, long hold, low risk.",
  "strategy_type": "conservative",
  "algorithm_filter": "MF Diversified Income",
  "initial_capital": 10000.0,
  "commission_buy": 0.0,
  "commission_sell": 0.0,
  "redemption_fee_pct": 0.0,
  "target_return_pct": 8.0,
  "stop_loss_pct": 5.0,
  "max_hold_days": 180,
  "position_size_pct": 25.0,
  "max_positions": 4,
  "created_at": "2026-02-09 17:57:24"
}
{
  "id": 2,
  "name": "Ultra Safe (Index Only)",
  "description": "Low-cost index funds, buy and hold.",
  "strategy_type": "conservative",
  "algorithm_filter": "MF Expense Optimizer",
  "initial_capital": 10000.0,
  "commission_buy": 0.0,
  "commission_sell": 0.0,
  "redemption_fee_pct": 0.0,
  "target_return_pct": 10.0,
  "stop_loss_pct": 8.0,
  "max_hold_days": 365,
  "position_size_pct": 20.0,
  "max_positions": 5,
  "created_at": "2026-02-09 17:57:24"
}
```

**`created_at` range:** 2026-02-09 17:57:24 → 2026-02-09 17:57:24

### 157. `cp_strategies` — ~10 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (5):** `id` (int), `name` (varchar(100)), `description` (text), `strategy_type` (varchar(50)), `ideal_timeframe` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "HODL",
  "description": "Buy and hold long-term through volatility.",
  "strategy_type": "hold",
  "ideal_timeframe": "1w"
}
{
  "id": 2,
  "name": "DCA",
  "description": "Dollar Cost Average — buy fixed amounts at regular intervals.",
  "strategy_type": "dca",
  "ideal_timeframe": "1w"
}
```

**`ideal_timeframe` range:** 15m → 4h

### 158. `cr_pairs` — ~10 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (5):** `symbol` (varchar(20)), `base_asset` (varchar(20)), `quote_asset` (varchar(10)), `category` (varchar(50)), `pair_name` (varchar(200))

**Primary Key:** `symbol`

**`category` distribution:**
- `altcoin`: 6
- `major`: 2
- `defi`: 2

**Sample Rows:**
```json
{
  "symbol": "BTCUSD",
  "base_asset": "BTC",
  "quote_asset": "USD",
  "category": "major",
  "pair_name": "Bitcoin / USD"
}
{
  "symbol": "ETHUSD",
  "base_asset": "ETH",
  "quote_asset": "USD",
  "category": "major",
  "pair_name": "Ethereum / USD"
}
```

### 159. `cr_portfolios` — ~10 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (12):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `algorithm_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `stop_loss_pct` (decimal(5,2)), `take_profit_pct` (decimal(5,2)), `max_hold_days` (int), `position_size_pct` (decimal(5,2)), `max_positions` (int), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "HODLer (1 Year)",
  "description": "Buy and hold for 1 year. No targets, no stops. Pure conviction.",
  "strategy_type": "hodl",
  "algorithm_filter": "",
  "initial_capital": 10000.0,
  "stop_loss_pct": 999.0,
  "take_profit_pct": 999.0,
  "max_hold_days": 365,
  "position_size_pct": 25.0,
  "max_positions": 4,
  "created_at": "2026-02-09 09:03:37"
}
{
  "id": 2,
  "name": "DCA Weekly",
  "description": "Dollar cost average weekly into top crypto. Systematic accumulation.",
  "strategy_type": "dca",
  "algorithm_filter": "CR DCA",
  "initial_capital": 10000.0,
  "stop_loss_pct": 999.0,
  "take_profit_pct": 999.0,
  "max_hold_days": 365,
  "position_size_pct": 10.0,
  "max_positions": 10,
  "created_at": "2026-02-09 09:03:37"
}
```

**`created_at` range:** 2026-02-09 09:03:37 → 2026-02-09 09:03:37

### 160. `fx_portfolios` — ~10 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (14):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `algorithm_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `leverage` (int), `spread_pips` (decimal(6,2)), `stop_loss_pips` (decimal(8,2)), `take_profit_pips` (decimal(8,2)), `max_hold_days` (int), `position_size_pct` (decimal(5,2)) … +2 more

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Scalper",
  "description": "Tight stops, quick 10-20 pip targets. High frequency.",
  "strategy_type": "scalp",
  "algorithm_filter": "FX Scalper",
  "initial_capital": 10000.0,
  "leverage": 50,
  "spread_pips": 1.0,
  "stop_loss_pips": 15.0,
  "take_profit_pips": 20.0,
  "max_hold_days": 1,
  "position_size_pct": 2.0,
  "max_positions": 10,
  "created_at": "2026-02-09 09:03:38"
}
{
  "id": 2,
  "name": "Day Trader",
  "description": "Intraday positions closed by end of session. 30-50 pip targets.",
  "strategy_type": "day_trade",
  "algorithm_filter": "FX Momentum,FX Breakout",
  "initial_capital": 10000.0,
  "leverage": 30,
  "spread_pips": 1.5,
  "stop_loss_pips": 30.0,
  "take_profit_pips": 50.0,
  "max_hold_days": 1,
  "position_size_pct": 3.0,
  "max_positions": 8,
  "created_at": "2026-02-09 09:03:38"
}
```

**`created_at` range:** 2026-02-09 09:03:38 → 2026-02-09 09:03:38

### 161. `fxp_portfolios` — ~10 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (14):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `algorithm_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `leverage` (int), `spread_pips` (decimal(6,2)), `stop_loss_pips` (decimal(8,2)), `take_profit_pips` (decimal(8,2)), `max_hold_days` (int), `position_size_pct` (decimal(5,2)) … +2 more

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Scalper",
  "description": "Tight stops, quick 10-20 pip targets. High frequency.",
  "strategy_type": "scalp",
  "algorithm_filter": "FX Scalper",
  "initial_capital": 10000.0,
  "leverage": 50,
  "spread_pips": 1.0,
  "stop_loss_pips": 15.0,
  "take_profit_pips": 20.0,
  "max_hold_days": 1,
  "position_size_pct": 2.0,
  "max_positions": 10,
  "created_at": "2026-02-09 17:57:25"
}
{
  "id": 2,
  "name": "Day Trader",
  "description": "Intraday positions closed by end of session. 30-50 pip targets.",
  "strategy_type": "day_trade",
  "algorithm_filter": "FX Momentum,FX Breakout",
  "initial_capital": 10000.0,
  "leverage": 30,
  "spread_pips": 1.5,
  "stop_loss_pips": 30.0,
  "take_profit_pips": 50.0,
  "max_hold_days": 1,
  "position_size_pct": 3.0,
  "max_positions": 8,
  "created_at": "2026-02-09 17:57:25"
}
```

**`created_at` range:** 2026-02-09 17:57:25 → 2026-02-09 17:57:25

### 162. `lm_bridge_onchain` — ~10 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `metric_name` (varchar(50)), `metric_value` (decimal(20,4)), `metric_label` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `metric_name`

**Sample Rows:**
```json
{
  "id": 1,
  "metric_name": "btc_hash_rate",
  "metric_value": 1126217288099.0,
  "metric_label": "",
  "updated_at": "2026-02-15 16:20:01"
}
{
  "id": 2,
  "metric_name": "btc_difficulty",
  "metric_value": 125864590119490.0,
  "metric_label": "",
  "updated_at": "2026-02-15 16:20:01"
}
```

**`updated_at` range:** 2026-02-15 16:20:01 → 2026-02-15 16:20:01

### 163. `lm_insider_sentiment` — ~10 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (9):** `id` (int), `ticker` (varchar(10)), `year` (int), `month` (int), `mspr` (decimal(10,4)), `change_val` (decimal(18,2)), `fetch_date` (date), `created_at` (datetime), `source` (varchar(30))

**Primary Key:** `id`
**Indexed:** `ticker`, `fetch_date`

**Sample Rows:**
```json
{
  "id": 16,
  "ticker": "AAPL",
  "year": 2026,
  "month": 2,
  "mspr": 25.6516,
  "change_val": 6732.0,
  "fetch_date": "2026-05-08",
  "created_at": "2026-02-11 11:38:41",
  "source": "finnhub"
}
{
  "id": 15,
  "ticker": "AAPL",
  "year": 2025,
  "month": 11,
  "mspr": -100.0,
  "change_val": -7502.0,
  "fetch_date": "2026-05-08",
  "created_at": "2026-02-11 11:38:41",
  "source": "finnhub"
}
```

**`fetch_date` range:** 2026-05-08 → 2026-05-08

**`created_at` range:** 2026-02-11 11:38:41 → 2026-04-06 11:15:59

### 164. `mf2_algo_performance` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (10):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "MF Balanced Composite",
  "strategy_type": "learning_scan",
  "total_picks": 1,
  "total_trades": 40,
  "win_rate": 97.5,
  "avg_return_pct": 31.876,
  "best_for": "Profitable: TR:10% SL:3% Hold:63d",
  "worst_for": "Default: 31.876%",
  "updated_at": "2026-05-08 12:40:22"
}
{
  "id": 2,
  "algorithm_name": "MF Diversified Income",
  "strategy_type": "learning_scan",
  "total_picks": 2,
  "total_trades": 80,
  "win_rate": 48.75,
  "avg_return_pct": -30.7455,
  "best_for": "No profitable params",
  "worst_for": "Default: -30.7455%",
  "updated_at": "2026-05-08 12:40:43"
}
```

**`updated_at` range:** 2026-05-08 12:40:22 → 2026-05-08 12:42:45

### 165. `mf2_algorithms` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (8):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20)), `pros` (text), `cons` (text)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "MF Momentum",
  "family": "Momentum",
  "description": "Selects funds with strongest 3/6/12 month returns. Momentum factor investing for mutual funds.",
  "algo_type": "momentum",
  "ideal_timeframe": "3m",
  "pros": null,
  "cons": null
}
{
  "id": 2,
  "name": "MF Value Tilt",
  "family": "Value",
  "description": "Favors funds with below-average P/E, P/B ratios. Deep value approach.",
  "algo_type": "value",
  "ideal_timeframe": "6m",
  "pros": null,
  "cons": null
}
```

**`ideal_timeframe` range:** 1m → 6m

### 166. `mf2_backtest_results` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (29):** `id` (int), `portfolio_id` (int), `run_name` (varchar(200)), `algorithm_filter` (varchar(500)), `strategy_type` (varchar(50)), `start_date` (date), `end_date` (date), `initial_capital` (decimal(12,2)), `final_value` (decimal(12,2)), `total_return_pct` (decimal(10,4)), `annualized_return_pct` (decimal(10,4)), `total_trades` (int) … +17 more

**Primary Key:** `id`
**Indexed:** `portfolio_id`, `strategy_type`

**Sample Rows:**
```json
{
  "id": 21,
  "portfolio_id": 0,
  "run_name": "Short Tactical (1 Month)",
  "algorithm_filter": "",
  "strategy_type": "tactical",
  "start_date": "2025-03-15",
  "end_date": "2025-07-21",
  "initial_capital": 10000.0,
  "final_value": 10020.29,
  "total_return_pct": 0.2029,
  "annualized_return_pct": 0.0,
  "total_trades": 45,
  "winning_trades": 24,
  "losing_trades": 21,
  "win_rate": 53.33,
  "avg_win_pct": 0.8027,
  "avg_loss_pct": 0.8671,
  "best_trade_pct": 1.462,
  "worst_trade_pct": -1.7024,
  "max_drawdown_pct": 1.6054,
  "total_fees": 82.26,
  "sharpe_ratio": 0.3859,
  "sortino_ratio": 0.0,
  "profit_factor": 1.0555,
  "expectancy": 0.0235,
  "avg_hold_days": 21.0,
  "fee_drag_pct": 0.8226,
  "params_json": "",
  "created_at": "2026-02-12 23:45:51"
}
{
  "id": 22,
  "portfolio_id": 0,
  "run_name": "Monthly Momentum",
  "algorithm_filter": "",
  "strategy_type": "momentum",
  "start_date": "2025-03-15",
  "end_date": "2025-08-01",
  "initial_capital": 10000.0,
  "final_value": 10138.4,
  "total_return_pct": 1.384,
  "annualized_return_pct": 0.0,
  "total_trades": 45,
  "winning_trades": 21,
  "losing_trades": 24,
  "win_rate": 46.67,
  "avg_win_pct": 1.2337,
  "avg_loss_pct": 0.7898,
  "best_trade_pct": 3.1752,
  "worst_trade_pct": -2.523,
  "max_drawdown_pct": 2.0636,
  "total_fees": 118.39,
  "sharpe_ratio": 1.8745,
  "sortino_ratio": 0.0,
  "profit_factor": 1.3598,
  "expectancy": 0.1545,
  "avg_hold_days": 30.0,
  "fee_drag_pct": 1.1839,
  "params_json": "",
  "created_at": "2026-02-12 23:45:51"
}
```

**`start_date` range:** 2025-03-15 → 2025-03-15

**`end_date` range:** 2025-07-21 → 2026-02-12

### 167. `mf_algo_performance` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (10):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "MF Balanced Composite",
  "strategy_type": "learning_scan",
  "total_picks": 0,
  "total_trades": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "best_for": "No profitable params",
  "worst_for": "Default: 0%",
  "updated_at": "2026-02-09 17:17:55"
}
{
  "id": 2,
  "algorithm_name": "MF Diversified Income",
  "strategy_type": "learning_scan",
  "total_picks": 0,
  "total_trades": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "best_for": "No profitable params",
  "worst_for": "Default: 0%",
  "updated_at": "2026-02-09 17:17:55"
}
```

**`updated_at` range:** 2026-02-09 17:17:55 → 2026-02-09 17:17:56

### 168. `mf_algorithms` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (8):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20)), `pros` (text), `cons` (text)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "MF Momentum",
  "family": "Momentum",
  "description": "Selects funds with strongest 3/6/12 month returns. Momentum factor investing for mutual funds.",
  "algo_type": "momentum",
  "ideal_timeframe": "3m",
  "pros": null,
  "cons": null
}
{
  "id": 2,
  "name": "MF Value Tilt",
  "family": "Value",
  "description": "Favors funds with below-average P/E, P/B ratios. Deep value approach.",
  "algo_type": "value",
  "ideal_timeframe": "6m",
  "pros": null,
  "cons": null
}
```

**`ideal_timeframe` range:** 1m → 6m

### 169. `mf_strategies` — ~10 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (7):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `selection_criteria` (text), `ideal_timeframe` (varchar(30)), `risk_level` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Growth Leaders",
  "description": "Morningstar 5-star large-cap growth funds with low expense ratios.",
  "strategy_type": "growth",
  "selection_criteria": "Morningstar >= 4, Expense < 0.50%, Large Cap Growth",
  "ideal_timeframe": "1y",
  "risk_level": "Medium"
}
{
  "id": 2,
  "name": "Income Focus",
  "description": "High-yield bond and dividend-focused funds.",
  "strategy_type": "income",
  "selection_criteria": "Yield >= 3%, Bond/Dividend category",
  "ideal_timeframe": "1y",
  "risk_level": "Low"
}
```

**`ideal_timeframe` range:** 1y → 6m

### 170. `walk_forward_summary` — ~10 rows (0MB + 0MB idx)
**Purpose:** Validation: Walk-forward

**Columns (16):** `id` (int), `source_table` (varchar(30)), `algorithm_name` (varchar(100)), `strategy_name` (varchar(100)), `total_folds` (int), `avg_wf_efficiency` (decimal(8,4)), `avg_oos_win_rate` (decimal(5,2)), `avg_oos_return` (decimal(10,4)), `avg_is_win_rate` (decimal(5,2)), `avg_is_return` (decimal(10,4)), `best_robust_tp` (decimal(6,2)), `best_robust_sl` (decimal(6,2)) … +4 more

**Primary Key:** `id`
**Indexed:** `source_table`

**Sample Rows:**
```json
{
  "id": 1,
  "source_table": "stock_picks",
  "algorithm_name": "Adversarial Trend (V2)",
  "strategy_name": "",
  "total_folds": 0,
  "avg_wf_efficiency": 0.0,
  "avg_oos_win_rate": 0.0,
  "avg_oos_return": 0.0,
  "avg_is_win_rate": 0.0,
  "avg_is_return": 0.0,
  "best_robust_tp": 0.0,
  "best_robust_sl": 0.0,
  "best_robust_hold": 0,
  "overfitting_flag": 0,
  "naive_is_return": 0.0,
  "updated_at": "2026-02-09 21:07:52"
}
{
  "id": 2,
  "source_table": "stock_picks",
  "algorithm_name": "Alpha Factor Composite",
  "strategy_name": "",
  "total_folds": 0,
  "avg_wf_efficiency": 0.0,
  "avg_oos_win_rate": 0.0,
  "avg_oos_return": 0.0,
  "avg_is_win_rate": 0.0,
  "avg_is_return": 0.0,
  "best_robust_tp": 0.0,
  "best_robust_sl": 0.0,
  "best_robust_hold": 0,
  "overfitting_flag": 0,
  "naive_is_return": 0.0,
  "updated_at": "2026-02-09 21:07:52"
}
```

**`updated_at` range:** 2026-02-09 21:07:52 → 2026-02-09 21:11:32

### 171. `goldmine_cursor_data_health` — ~9 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (7):** `id` (int), `checked_at` (datetime), `source_system` (varchar(50)), `last_data_time` (datetime), `hours_stale` (decimal(8,2)), `status` (varchar(20)), `details` (text)

**Primary Key:** `id`
**Indexed:** `source_system`, `status`

**`source_system` distribution:**
- `findstocks`: 3
- `goldmine_cursor`: 3
- `live-monitor-sports`: 3

**`status` distribution:**
- `dead`: 4
- `ok`: 3
- `warning`: 2

**Sample Rows:**
```json
{
  "id": 1,
  "checked_at": "2026-02-11 00:00:04",
  "source_system": "findstocks",
  "last_data_time": "2026-02-10 00:00:00",
  "hours_stale": 24.0,
  "status": "ok",
  "details": ""
}
{
  "id": 2,
  "checked_at": "2026-02-11 00:00:04",
  "source_system": "live-monitor-sports",
  "last_data_time": null,
  "hours_stale": null,
  "status": "dead",
  "details": "Table exists but no data"
}
```

**`last_data_time` range:** 2026-02-10 00:00:00 → 2026-02-10 16:00:00

### 172. `lm_conviction_stats` — ~9 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (12):** `id` (int), `stat_period` (varchar(20)), `conviction_bucket` (varchar(20)), `total_signals` (int), `wins` (int), `losses` (int), `pending_count` (int), `win_rate` (decimal(5,2)), `avg_return` (decimal(8,4)), `max_return` (decimal(8,4)), `min_return` (decimal(8,4)), `calculated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `stat_period`

**Sample Rows:**
```json
{
  "id": 1,
  "stat_period": "7d",
  "conviction_bucket": "70-79",
  "total_signals": 6,
  "wins": 0,
  "losses": 0,
  "pending_count": 6,
  "win_rate": 0.0,
  "avg_return": 0.0,
  "max_return": 0.0,
  "min_return": 0.0,
  "calculated_at": "2026-02-11 03:55:14"
}
{
  "id": 2,
  "stat_period": "7d",
  "conviction_bucket": "60-69",
  "total_signals": 5,
  "wins": 0,
  "losses": 0,
  "pending_count": 5,
  "win_rate": 0.0,
  "avg_return": 0.0,
  "max_return": 0.0,
  "min_return": 0.0,
  "calculated_at": "2026-02-11 03:55:14"
}
```

### 173. `lm_kelly_fractions` — ~9 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (11):** `id` (int), `algorithm_name` (varchar(100)), `asset_class` (varchar(20)), `win_rate` (decimal(6,4)), `avg_win_pct` (decimal(8,4)), `avg_loss_pct` (decimal(8,4)), `full_kelly` (decimal(8,6)), `half_kelly` (decimal(8,6)), `sample_size` (int), `updated_at` (datetime), `vol_adjusted_kelly` (decimal(8,6))

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**`asset_class` distribution:**
- `FOREX`: 5
- `STOCK`: 2
- `CRYPTO`: 2

**Sample Rows:**
```json
{
  "id": 10010,
  "algorithm_name": "Ichimoku Cloud",
  "asset_class": "CRYPTO",
  "win_rate": 0.3913,
  "avg_win_pct": 3.1487,
  "avg_loss_pct": 2.6067,
  "full_kelly": -0.1126,
  "half_kelly": 0.0,
  "sample_size": 23,
  "updated_at": "2026-05-08 14:20:01",
  "vol_adjusted_kelly": 0.0
}
{
  "id": 10011,
  "algorithm_name": "StochRSI Crossover",
  "asset_class": "CRYPTO",
  "win_rate": 0.4,
  "avg_win_pct": 0.9971,
  "avg_loss_pct": 2.0047,
  "full_kelly": -0.8063,
  "half_kelly": 0.0,
  "sample_size": 30,
  "updated_at": "2026-05-08 14:20:01",
  "vol_adjusted_kelly": 0.0
}
```

**`updated_at` range:** 2026-05-08 14:20:01 → 2026-05-08 14:20:01

### 174. `mf2_tracking_lessons` — ~9 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (10):** `id` (int), `lesson_date` (date), `lesson_type` (varchar(50)), `lesson_title` (varchar(200)), `lesson_text` (text), `confidence` (decimal(5,2)), `supporting_data` (text), `applied` (tinyint), `impact_score` (decimal(5,2)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `lesson_date`, `lesson_type`

**Sample Rows:**
```json
{
  "id": 1,
  "lesson_date": "2026-02-12",
  "lesson_type": "pattern",
  "lesson_title": "Optimal pick score: very high (80+)",
  "lesson_text": "Picks with score very high (80+) show 57.1% win rate (avg -0.86% return) across 7 trades.",
  "confidence": 51.0,
  "supporting_data": "[{\"bracket\":\"high (60-80)\",\"trades\":13,\"avg_return\":0.81,\"win_rate\":53.8},{\"bracket\":\"very high (80+)\",\"trades\":7,\"avg_return\":-0.86,\"win_rate\":57.1}]",
  "applied": 0,
  "impact_score": null,
  "created_at": "2026-02-12 23:31:19"
}
{
  "id": 2,
  "lesson_date": "2026-02-12",
  "lesson_type": "insight",
  "lesson_title": "MF tracking: 55% win rate across 20 trades",
  "lesson_text": "Mutual fund performance tracking shows 55% win rate with 0.22% average return per trade across 20 closed positions. Performance is moderate. Consider ...",
  "confidence": 70.0,
  "supporting_data": "",
  "applied": 0,
  "impact_score": null,
  "created_at": "2026-02-12 23:31:19"
}
```

**`lesson_date` range:** 2026-02-12 → 2026-02-15

**`created_at` range:** 2026-02-12 23:31:19 → 2026-02-15 01:15:10

### 175. `cr_algo_performance` — ~8 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (10):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "CR Altcoin Rotation",
  "strategy_type": "learning_scan",
  "total_picks": 2,
  "total_trades": 136,
  "win_rate": 0.0,
  "avg_return_pct": -93.9208,
  "best_for": "No profitable params",
  "worst_for": "Default: -93.9208%",
  "updated_at": "2026-05-08 06:18:56"
}
{
  "id": 2,
  "algorithm_name": "CR Breakout",
  "strategy_type": "learning_scan",
  "total_picks": 1,
  "total_trades": 68,
  "win_rate": 0.0,
  "avg_return_pct": -75.3439,
  "best_for": "No profitable params",
  "worst_for": "Default: -75.3439%",
  "updated_at": "2026-05-08 06:19:25"
}
```

**`updated_at` range:** 2026-05-07 05:41:34 → 2026-05-08 06:23:27

### 176. `cr_algorithms` — ~8 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (6):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "CR Momentum",
  "family": "Momentum",
  "description": "RSI + volume surge detection. Buys when RSI crosses above 30 with above-average volume. Sells when RSI exceeds 70.",
  "algo_type": "momentum",
  "ideal_timeframe": "1w"
}
{
  "id": 2,
  "name": "CR DCA",
  "family": "DCA",
  "description": "Dollar Cost Averaging - systematic buying at regular intervals regardless of price. Reduces impact of volatility.",
  "algo_type": "dca",
  "ideal_timeframe": "1m"
}
```

**`ideal_timeframe` range:** 1d → 6m

### 177. `fx_algo_performance` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (11):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `avg_pips` (decimal(10,2)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "FX Breakout",
  "strategy_type": "learning_scan",
  "total_picks": 0,
  "total_trades": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "avg_pips": 0.0,
  "best_for": "No profitable params",
  "worst_for": "Default: 0%",
  "updated_at": "2026-02-09 17:29:35"
}
{
  "id": 2,
  "algorithm_name": "FX CAD Focus",
  "strategy_type": "learning_scan",
  "total_picks": 0,
  "total_trades": 0,
  "win_rate": 0.0,
  "avg_return_pct": 0.0,
  "avg_pips": 0.0,
  "best_for": "No profitable params",
  "worst_for": "Default: 0%",
  "updated_at": "2026-02-09 17:29:35"
}
```

**`updated_at` range:** 2026-02-09 17:29:35 → 2026-02-09 17:29:36

### 178. `fx_algorithms` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (6):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "FX Trend Following",
  "family": "Trend",
  "description": "200 SMA crossover direction. Goes long above SMA, short below. Classic trend system for forex.",
  "algo_type": "trend",
  "ideal_timeframe": "1d"
}
{
  "id": 2,
  "name": "FX Momentum",
  "family": "Momentum",
  "description": "RSI + MACD divergence system. Identifies momentum shifts using multi-indicator confirmation.",
  "algo_type": "momentum",
  "ideal_timeframe": "4h"
}
```

**`ideal_timeframe` range:** 15m → 4h

### 179. `fx_strategies` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex: Signals/backtests

**Columns (5):** `id` (int), `name` (varchar(100)), `description` (text), `strategy_type` (varchar(50)), `ideal_timeframe` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Trend Following",
  "description": "Follow the prevailing trend using moving average crossovers.",
  "strategy_type": "trend",
  "ideal_timeframe": "1d"
}
{
  "id": 2,
  "name": "Mean Reversion",
  "description": "Trade when price deviates significantly from its average.",
  "strategy_type": "mean_revert",
  "ideal_timeframe": "4h"
}
```

**`ideal_timeframe` range:** 15m → 4h

### 180. `fxp_algo_performance` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (11):** `id` (int), `algorithm_name` (varchar(100)), `strategy_type` (varchar(50)), `total_picks` (int), `total_trades` (int), `win_rate` (decimal(5,2)), `avg_return_pct` (decimal(10,4)), `avg_pips` (decimal(10,2)), `best_for` (varchar(200)), `worst_for` (varchar(200)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 1,
  "algorithm_name": "FX Breakout",
  "strategy_type": "learning_scan",
  "total_picks": 2,
  "total_trades": 148,
  "win_rate": 50.0,
  "avg_return_pct": 10.9516,
  "avg_pips": 3478.0,
  "best_for": "Profitable: TP:300 SL:25 Hold:30d",
  "worst_for": "Default: 10.9516%",
  "updated_at": "2026-05-08 06:19:08"
}
{
  "id": 2,
  "algorithm_name": "FX CAD Focus",
  "strategy_type": "learning_scan",
  "total_picks": 1,
  "total_trades": 74,
  "win_rate": 0.0,
  "avg_return_pct": -10.8119,
  "avg_pips": -3811.0,
  "best_for": "No profitable params",
  "worst_for": "Default: -10.8119%",
  "updated_at": "2026-05-08 06:19:34"
}
```

**`updated_at` range:** 2026-05-03 09:50:05 → 2026-05-08 06:23:49

### 181. `fxp_algorithms` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (6):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `algo_type` (varchar(50)), `ideal_timeframe` (varchar(20))

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "FX Trend Following",
  "family": "Trend",
  "description": "200 SMA crossover direction. Goes long above SMA, short below. Classic trend system for forex.",
  "algo_type": "trend",
  "ideal_timeframe": "1d"
}
{
  "id": 2,
  "name": "FX Momentum",
  "family": "Momentum",
  "description": "RSI + MACD divergence system. Identifies momentum shifts using multi-indicator confirmation.",
  "algo_type": "momentum",
  "ideal_timeframe": "4h"
}
```

**`ideal_timeframe` range:** 15m → 4h

### 182. `fxp_pairs` — ~8 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (5):** `symbol` (varchar(20)), `base_currency` (varchar(10)), `quote_currency` (varchar(10)), `category` (varchar(30)), `pip_value` (decimal(10,6))

**Primary Key:** `symbol`

**`category` distribution:**
- `major`: 5
- `minor`: 2
- `cad`: 1

**Sample Rows:**
```json
{
  "symbol": "EURUSD",
  "base_currency": "EUR",
  "quote_currency": "USD",
  "category": "major",
  "pip_value": 0.0001
}
{
  "symbol": "GBPUSD",
  "base_currency": "GBP",
  "quote_currency": "USD",
  "category": "major",
  "pip_value": 0.0001
}
```

### 183. `lm_alert_configs` — ~8 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (8):** `id` (int), `alert_type` (varchar(30)), `alert_name` (varchar(100)), `threshold_value` (int), `threshold_direction` (varchar(10)), `cooldown_hours` (int), `is_active` (tinyint), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `alert_type`

**Sample Rows:**
```json
{
  "id": 1,
  "alert_type": "conviction_jump",
  "alert_name": "Conviction Jump (+10 in 7d)",
  "threshold_value": 10,
  "threshold_direction": "above",
  "cooldown_hours": 72,
  "is_active": 1,
  "created_at": "2026-02-11 03:54:16"
}
{
  "id": 2,
  "alert_type": "conviction_drop",
  "alert_name": "Conviction Drop (-10 in 7d)",
  "threshold_value": -10,
  "threshold_direction": "below",
  "cooldown_hours": 24,
  "is_active": 1,
  "created_at": "2026-02-11 03:54:16"
}
```

**`created_at` range:** 2026-02-11 03:54:16 → 2026-02-11 03:54:16

### 184. `mf_portfolios` — ~8 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (14):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_type` (varchar(50)), `strategy_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `commission_buy` (decimal(6,2)), `commission_sell` (decimal(6,2)), `hold_period_days` (int), `rebalance_freq` (varchar(20)), `target_return_pct` (decimal(5,2)), `stop_loss_pct` (decimal(5,2)) … +2 more

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Conservative Income",
  "description": null,
  "strategy_type": "income",
  "strategy_filter": "",
  "initial_capital": 10000.0,
  "commission_buy": 0.0,
  "commission_sell": 0.0,
  "hold_period_days": 365,
  "rebalance_freq": "quarterly",
  "target_return_pct": 5.0,
  "stop_loss_pct": 3.0,
  "expense_drag_annual": 0.004,
  "created_at": "2026-02-09 05:39:09"
}
{
  "id": 2,
  "name": "Balanced Growth",
  "description": null,
  "strategy_type": "balanced",
  "strategy_filter": "",
  "initial_capital": 10000.0,
  "commission_buy": 0.0,
  "commission_sell": 0.0,
  "hold_period_days": 180,
  "rebalance_freq": "quarterly",
  "target_return_pct": 10.0,
  "stop_loss_pct": 8.0,
  "expense_drag_annual": 0.005,
  "created_at": "2026-02-09 05:39:09"
}
```

**`created_at` range:** 2026-02-09 05:39:09 → 2026-02-09 05:39:09

### 185. `mf_whatif_scenarios` — ~8 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (6):** `id` (int), `scenario_name` (varchar(200)), `query_text` (text), `params_json` (text), `results_json` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "scenario_name": "short_tactical",
  "query_text": "",
  "params_json": "{\"scenario\":\"short_tactical\",\"algorithms\":\"\",\"target_return\":5,\"stop_loss\":3,\"max_hold_days\":21,\"initial_capital\":10000,\"redemption_fee\":0}",
  "results_json": "{\"total_trades\":0,\"winning_trades\":0,\"losing_trades\":0,\"win_rate\":0,\"avg_win_pct\":null,\"avg_loss_pct\":null,\"total_return_pct\":0,\"final_value\":10000,\"m...",
  "created_at": "2026-02-09 08:41:49"
}
{
  "id": 2,
  "scenario_name": "short_tactical",
  "query_text": "",
  "params_json": "{\"scenario\":\"short_tactical\",\"algorithms\":\"\",\"target_return\":5,\"stop_loss\":3,\"max_hold_days\":21,\"initial_capital\":10000,\"redemption_fee\":0}",
  "results_json": "{\"total_trades\":0,\"winning_trades\":0,\"losing_trades\":0,\"win_rate\":0,\"avg_win_pct\":null,\"avg_loss_pct\":null,\"total_return_pct\":0,\"final_value\":10000,\"m...",
  "created_at": "2026-02-09 08:41:55"
}
```

**`created_at` range:** 2026-02-09 08:41:49 → 2026-02-09 08:41:58

### 186. `miracle_portfolios2` — ~8 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `position_size_pct` (decimal(5,2)), `max_positions` (int), `fee_model` (varchar(20)), `prefer_cdr` (tinyint), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "DayTrades Miracle All-In",
  "description": "All 8 strategies, CDR preferred, aggressive sizing",
  "strategy_filter": "",
  "initial_capital": 10000.0,
  "position_size_pct": 20.0,
  "max_positions": 5,
  "fee_model": "questrade",
  "prefer_cdr": 1,
  "created_at": "2026-02-09 18:51:10"
}
{
  "id": 2,
  "name": "CDR-Only Miracle",
  "description": "Only CDR tickers for zero-fee day trading",
  "strategy_filter": "CDR Zero-Fee Play",
  "initial_capital": 10000.0,
  "position_size_pct": 25.0,
  "max_positions": 4,
  "fee_model": "questrade",
  "prefer_cdr": 1,
  "created_at": "2026-02-09 18:51:10"
}
```

**`created_at` range:** 2026-02-09 18:51:10 → 2026-02-09 18:51:10

### 187. `miracle_strategies2` — ~8 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `scan_type` (varchar(50)), `ideal_hold` (varchar(20)), `default_tp_pct` (decimal(5,2)), `default_sl_pct` (decimal(5,2)), `enabled` (tinyint)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Gap Up Momentum",
  "family": "momentum",
  "description": "Stocks gapping up >3% from previous close with volume >2x average. Targets continuation of gap momentum. Best for first 30 min of trading.",
  "scan_type": "gap_scanner",
  "ideal_hold": "1d",
  "default_tp_pct": 12.02,
  "default_sl_pct": 4.42,
  "enabled": 0
}
{
  "id": 2,
  "name": "Volume Surge Breakout",
  "family": "breakout",
  "description": "Unusual volume (>3x 20-day avg) with price breaking 20-day high. RSI < 80 filter prevents chasing overextended moves. ATR-based targets.",
  "scan_type": "volume_scanner",
  "ideal_hold": "1-2d",
  "default_tp_pct": 7.65,
  "default_sl_pct": 3.5,
  "enabled": 1
}
```

### 188. `miracle_strategies3` — ~8 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (11):** `id` (int), `name` (varchar(100)), `family` (varchar(50)), `description` (text), `scan_type` (varchar(50)), `ideal_hold` (varchar(20)), `default_tp_pct` (decimal(5,2)), `default_sl_pct` (decimal(5,2)), `min_score` (int), `enabled` (tinyint), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Gap Up Momentum",
  "family": "momentum",
  "description": "Stocks gapping up >3% with 2x+ volume at open. Best in first 30 min of trading.",
  "scan_type": "gap_up",
  "ideal_hold": "1d",
  "default_tp_pct": 7.4,
  "default_sl_pct": 2.6,
  "min_score": 60,
  "enabled": 1,
  "created_at": "2026-02-09 18:52:19"
}
{
  "id": 2,
  "name": "Volume Surge Breakout",
  "family": "breakout",
  "description": "Unusual volume >3x 20-day avg with price breaking 20-day high. RSI < 80 filter.",
  "scan_type": "volume_surge",
  "ideal_hold": "1d",
  "default_tp_pct": 6.0,
  "default_sl_pct": 3.0,
  "min_score": 55,
  "enabled": 1,
  "created_at": "2026-02-09 18:52:19"
}
```

**`created_at` range:** 2026-02-09 18:52:19 → 2026-02-09 18:52:19

### 189. `goldmine_cursor_algo_scorecard` — ~7 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (22):** `id` (int), `week_start` (date), `week_end` (date), `asset_class` (varchar(20)), `algorithm` (varchar(80)), `total_picks` (int), `wins` (int), `losses` (int), `win_rate` (decimal(6,2)), `avg_gain_pct` (decimal(8,4)), `avg_loss_pct` (decimal(8,4)), `profit_factor` (decimal(8,4)) … +10 more

**Primary Key:** `id`
**Indexed:** `week_start`, `verdict`

**`asset_class` distribution:**
- `stocks`: 7

**Sample Rows:**
```json
{
  "id": 8,
  "week_start": "2026-02-16",
  "week_end": "2026-02-15",
  "asset_class": "stocks",
  "algorithm": "Cursor Genius",
  "total_picks": 49,
  "wins": 33,
  "losses": 16,
  "win_rate": 67.35,
  "avg_gain_pct": 5.0,
  "avg_loss_pct": -3.0,
  "profit_factor": 3.4375,
  "expectancy": 2.3878,
  "sharpe_ratio": 0.6365,
  "sortino_ratio": null,
  "max_drawdown_pct": 3.0,
  "benchmark_return_pct": 0.0,
  "alpha_pct": 117.0,
  "deflated_sharpe": null,
  "regime": "unknown",
  "verdict": "hidden_winner",
  "snapshot_at": "2026-02-11 00:27:45"
}
{
  "id": 9,
  "week_start": "2026-02-16",
  "week_end": "2026-02-15",
  "asset_class": "stocks",
  "algorithm": "Sector Momentum",
  "total_picks": 10,
  "wins": 6,
  "losses": 4,
  "win_rate": 60.0,
  "avg_gain_pct": 5.0,
  "avg_loss_pct": -3.0,
  "profit_factor": 2.5,
  "expectancy": 1.8,
  "sharpe_ratio": 0.4593,
  "sortino_ratio": null,
  "max_drawdown_pct": 3.0,
  "benchmark_return_pct": 0.0,
  "alpha_pct": 18.0,
  "deflated_sharpe": null,
  "regime": "unknown",
  "verdict": "hidden_winner",
  "snapshot_at": "2026-02-11 00:27:45"
}
```

### 190. `lm_quant_bridge` — ~6 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (7):** `id` (int), `module_name` (varchar(50)), `run_source` (varchar(30)), `status` (varchar(20)), `result_data` (longtext), `summary` (text), `run_at` (datetime)

**Primary Key:** `id`
**Indexed:** `module_name`, `status`, `run_at`

**`status` distribution:**
- `success`: 6

**Sample Rows:**
```json
{
  "id": 1,
  "module_name": "cusum_detector",
  "run_source": "github",
  "status": "success",
  "result_data": "{\"algo_health\": [{\"algorithm_name\": \"StochRSI Crossover\", \"total_trades\": 11, \"change_points_detected\": 0, \"n_segments\": 1, \"decay_status\": \"dead\", \"r...",
  "summary": "1 algos: 0 healthy, 1 warning/decayed",
  "run_at": "2026-02-15 14:19:59"
}
{
  "id": 2,
  "module_name": "options_flow",
  "run_source": "github",
  "status": "success",
  "result_data": "{\"options_data\": [{\"ticker\": \"AAPL\", \"spot_price\": 255.78, \"net_gex\": 0.0, \"call_gex\": 0.0, \"put_gex\": 0.0, \"gex_signal\": \"NEGATIVE_GAMMA\", \"gex_inter...",
  "summary": "12 tickers analyzed",
  "run_at": "2026-02-15 14:20:12"
}
```

### 191. `mc_scan_log` — ~6 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (11):** `id` (int), `scan_id` (varchar(20)), `pair` (varchar(30)), `price` (double), `score` (int), `factors_json` (text), `verdict` (varchar(20)), `chg_24h` (double), `vol_usd_24h` (double), `tier` (varchar(10)), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `scan_id`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "scan_id": "20260210213821",
  "pair": "PEPE_USDT",
  "price": 3.63e-06,
  "score": 8,
  "factors_json": "{\"explosive_volume\":{\"score\":0,\"max\":25,\"ratio\":0.9,\"recent_avg\":157620000},\"parabolic_momentum\":{\"score\":0,\"max\":20,\"mom_15m\":-0.74,\"mom_5m\":-0.74},\"...",
  "verdict": "SKIP",
  "chg_24h": -4.4,
  "vol_usd_24h": 123816.86,
  "tier": "tier1",
  "created_at": "2026-02-10 21:38:21"
}
{
  "id": 2,
  "scan_id": "20260210213821",
  "pair": "SHIB_USDT",
  "price": 5.981e-06,
  "score": 8,
  "factors_json": "{\"explosive_volume\":{\"score\":0,\"max\":25,\"ratio\":0,\"recent_avg\":6603333.33},\"parabolic_momentum\":{\"score\":0,\"max\":20,\"mom_15m\":-0.43,\"mom_5m\":-0.43},\"r...",
  "verdict": "SKIP",
  "chg_24h": -2.4,
  "vol_usd_24h": 154901.68,
  "tier": "tier1",
  "created_at": "2026-02-10 21:38:21"
}
```

**`created_at` range:** 2026-02-10 21:38:21 → 2026-02-10 21:38:31

### 192. `miracle_portfolios3` — ~6 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (10):** `id` (int), `name` (varchar(200)), `description` (text), `strategy_filter` (varchar(500)), `initial_capital` (decimal(12,2)), `position_size_pct` (decimal(5,2)), `max_positions` (int), `fee_model` (varchar(20)), `prefer_cdr` (tinyint), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `name`

**Sample Rows:**
```json
{
  "id": 1,
  "name": "Miracle Aggressive",
  "description": "High-risk day trades. All strategies, max 8 positions.",
  "strategy_filter": "",
  "initial_capital": 10000.0,
  "position_size_pct": 12.5,
  "max_positions": 8,
  "fee_model": "questrade",
  "prefer_cdr": 1,
  "created_at": "2026-02-09 18:52:19"
}
{
  "id": 2,
  "name": "Miracle Conservative",
  "description": "Lower-risk picks only. Score >= 70, CDR preferred.",
  "strategy_filter": "cdr_priority,oversold_bounce,mean_reversion",
  "initial_capital": 10000.0,
  "position_size_pct": 8.0,
  "max_positions": 4,
  "fee_model": "questrade",
  "prefer_cdr": 1,
  "created_at": "2026-02-09 18:52:19"
}
```

**`created_at` range:** 2026-02-09 18:52:19 → 2026-02-09 18:52:19

### 193. `at_futures_symbol_edge` — ~4 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (11):** `symbol` (varchar(32)), `asset_class` (varchar(20)), `strategy` (varchar(80)), `is_validated_strategy` (tinyint(1)), `sample_size` (int), `win_rate_pct` (decimal(6,2)), `profit_factor` (decimal(8,3)), `expectancy_pct` (decimal(8,3)), `edge_label` (varchar(64)), `evidence_source` (varchar(255)), `last_updated_utc` (varchar(40))

**Primary Key:** `symbol`

**`asset_class` distribution:**
- `FUTURES`: 4

**`strategy` distribution:**
- `cta_golden_cross_200`: 1
- `cta_cross_asset_tsmom`: 1
- `futures_connors_rsi2`: 1
- `futures_momentum`: 1

**Sample Rows:**
```json
{
  "symbol": "COMEX:HG1!",
  "asset_class": "FUTURES",
  "strategy": "cta_golden_cross_200",
  "is_validated_strategy": 1,
  "sample_size": 164,
  "win_rate_pct": 49.0,
  "profit_factor": 1.25,
  "expectancy_pct": 0.1,
  "edge_label": "proxy_commodity_positive",
  "evidence_source": "joint_filtered_commodity_lean_2026-04-04.json",
  "last_updated_utc": "2026-04-09T20:56:29.731599+00:00"
}
{
  "symbol": "COMEX:SI1!",
  "asset_class": "FUTURES",
  "strategy": "cta_cross_asset_tsmom",
  "is_validated_strategy": 1,
  "sample_size": null,
  "win_rate_pct": 60.0,
  "profit_factor": null,
  "expectancy_pct": null,
  "edge_label": "strategy_forward_wr_positive",
  "evidence_source": "joint_filtered_commodity_lean_2026-04-04.json:picks[SI=F]",
  "last_updated_utc": "2026-04-09T20:56:29.731599+00:00"
}
```

**`is_validated_strategy` range:** 1 → 1

**`last_updated_utc` range:** 2026-04-09T20:56:29.731599+00:00 → 2026-04-09T20:56:29.731599+00:00

### 194. `lm_injury_intel_cache` — ~4 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(100)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 25,
  "cache_key": "inj_basketball_nba",
  "cache_data": "{\"atl\":{\"name\":\"Atlanta Hawks\",\"abbreviation\":\"ATL\",\"out\":0,\"questionable\":0,\"total_injured\":0,\"players_out\":[]},\"bos\":{\"name\":\"Boston Celtics\",\"abbre...",
  "source": "espn_teams",
  "updated_at": "2026-04-04 18:03:47"
}
{
  "id": 26,
  "cache_key": "inj_baseball_mlb",
  "cache_data": "{\"ari\":{\"name\":\"Arizona Diamondbacks\",\"abbreviation\":\"ARI\",\"out\":0,\"questionable\":0,\"total_injured\":0,\"players_out\":[]},\"ath\":{\"name\":\"Athletics\",\"abb...",
  "source": "espn_teams",
  "updated_at": "2026-04-04 18:03:47"
}
```

**`updated_at` range:** 2026-04-04 18:03:47 → 2026-04-04 18:03:48

### 195. `lm_meta_labeler` — ~4 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (10):** `id` (int), `trained_at` (datetime), `training_samples` (int), `positive_rate` (decimal(6,4)), `avg_precision` (decimal(6,4)), `avg_recall` (decimal(6,4)), `avg_f1` (decimal(6,4)), `cv_results` (text), `top_features` (text), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `trained_at`

**Sample Rows:**
```json
{
  "id": 1,
  "trained_at": "2026-02-15 15:47:26",
  "training_samples": 0,
  "positive_rate": 0.0,
  "avg_precision": 0.5262,
  "avg_recall": 0.0,
  "avg_f1": 0.5226,
  "cv_results": "[{\"fold\":1,\"train_size\":372,\"test_size\":372,\"purge_gap\":3,\"precision\":0.6339,\"recall\":0.725,\"f1\":0.6764,\"accuracy\":0.7016,\"auc\":0.7556,\"log_loss\":0.61...",
  "top_features": "[{\"name\":\"algo_consecutive_losses\",\"importance\":0.1355},{\"name\":\"asset_crypto\",\"importance\":0.0855},{\"name\":\"asset_forex\",\"importance\":0.0786},{\"name\"...",
  "created_at": "2026-02-15 15:47:26"
}
{
  "id": 2,
  "trained_at": "2026-04-19 15:25:55",
  "training_samples": 819,
  "positive_rate": 0.0,
  "avg_precision": 0.0,
  "avg_recall": 0.0,
  "avg_f1": 0.0,
  "cv_results": "[{\"fold\":1,\"precision\":0,\"recall\":0,\"f1\":0,\"test_size\":136,\"positive_rate\":0},{\"fold\":2,\"precision\":0,\"recall\":0,\"f1\":0,\"test_size\":136,\"positive_rate...",
  "top_features": "[{\"name\":\"strength\",\"importance\":0},{\"name\":\"tp_sl_ratio\",\"importance\":0},{\"name\":\"hold_hours\",\"importance\":0},{\"name\":\"composite_score\",\"importance\":...",
  "created_at": "2026-04-19 15:25:55"
}
```

**`created_at` range:** 2026-02-15 15:47:26 → 2026-04-26 15:28:32

### 196. `lm_opportunities` — ~4 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (21):** `id` (int), `scan_id` (varchar(40)), `asset_class` (varchar(10)), `symbol` (varchar(20)), `current_price` (decimal(18,8)), `entry_price` (decimal(18,8)), `direction` (varchar(10)), `trend_strength` (varchar(20)), `confidence_score` (int), `signal_count` (int), `momentum_signals` (text), `volume_confirmation` (varchar(255)) … +9 more

**Primary Key:** `id`
**Indexed:** `scan_id`, `confidence_score`, `scan_time`

**`asset_class` distribution:**
- `CRYPTO`: 4

**`direction` distribution:**
- `SHORT`: 3
- `BUY`: 1

**Sample Rows:**
```json
{
  "id": 1,
  "scan_id": "1ba244d6584b88d10c4ec499fc563af4",
  "asset_class": "CRYPTO",
  "symbol": "DOTUSD",
  "current_price": 1.276,
  "entry_price": 1.276,
  "direction": "SHORT",
  "trend_strength": "weak",
  "confidence_score": 52,
  "signal_count": 3,
  "momentum_signals": "[\"ADX Trend Strength: ADX(28.7) > 25 = strong trend. +DI=11.8 -DI=29.8 spread=17.9\",\"Trend Sniper: Trend Sniper: -46 composite (0\\/6 bullish) regime=b...",
  "volume_confirmation": "$1.3M 24h volume",
  "key_reason_now": "3 algorithms simultaneously flash bearish on this asset. Led by Ichimoku Cloud (strength 68): price below cloud + Kijun > Tenkan. T=1.2891 K=1.306 Clo...",
  "holding_period": "1-day",
  "avg_tp_pct": 1.67,
  "avg_sl_pct": 0.83,
  "data_source": "freecryptoapi (binance) +kraken",
  "data_latency_seconds": 5,
  "notes": "24h change: -3.84%. Data latency: 5s. Avg TP: 1.67%, Avg SL: 0.83%",
  "signal_ids": "[458,457,459]",
  "scan_time": "2026-02-10 12:15:17"
}
{
  "id": 2,
  "scan_id": "1ba244d6584b88d10c4ec499fc563af4",
  "asset_class": "CRYPTO",
  "symbol": "INJUSD",
  "current_price": 3.055,
  "entry_price": 3.055,
  "direction": "SHORT",
  "trend_strength": "weak",
  "confidence_score": 51,
  "signal_count": 3,
  "momentum_signals": "[\"Ichimoku Cloud: price below cloud + Kijun > Tenkan. T=3.0855 K=3.128 Cloud=3.1068-3.128\",\"ADX Trend Strength: ADX(27) > 25 = strong trend. +DI=14.1 ...",
  "volume_confirmation": "$168.6K 24h volume",
  "key_reason_now": "3 algorithms simultaneously flash bearish on this asset. Led by Ichimoku Cloud (strength 67): price below cloud + Kijun > Tenkan. T=3.0855 K=3.128 Clo...",
  "holding_period": "1-day",
  "avg_tp_pct": 1.67,
  "avg_sl_pct": 0.83,
  "data_source": "freecryptoapi (binance) +kraken",
  "data_latency_seconds": 5,
  "notes": "24h change: -3.87%. Data latency: 5s. Avg TP: 1.67%, Avg SL: 0.83%",
  "signal_ids": "[499,498,497]",
  "scan_time": "2026-02-10 12:15:17"
}
```

**`scan_time` range:** 2026-02-10 12:15:17 → 2026-02-10 12:15:17

### 197. `stock_analyst_recs` — ~4 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (9):** `id` (int), `ticker` (varchar(10)), `period` (varchar(10)), `strong_buy` (int), `buy` (int), `hold_count` (int), `sell` (int), `strong_sell` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `ticker`

**Sample Rows:**
```json
{
  "id": 16,
  "ticker": "BAC",
  "period": "-3m",
  "strong_buy": 7,
  "buy": 14,
  "hold_count": 4,
  "sell": 0,
  "strong_sell": 0,
  "updated_at": "2026-02-09 22:10:33"
}
{
  "id": 15,
  "ticker": "BAC",
  "period": "-2m",
  "strong_buy": 7,
  "buy": 14,
  "hold_count": 4,
  "sell": 0,
  "strong_sell": 0,
  "updated_at": "2026-02-09 22:10:33"
}
```

**`updated_at` range:** 2026-02-09 22:10:33 → 2026-02-09 22:10:33

### 198. `cr_whatif_scenarios` — ~3 rows (0MB + 0MB idx)
**Purpose:** Crypto: Backtests/signals

**Columns (6):** `id` (int), `scenario_name` (varchar(200)), `query_text` (text), `params_json` (text), `results_json` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"take_profit\":20,\"stop_loss\":10,\"max_hold_days\":90,\"initial_capital\":10000,\"trading_fee\":0.1}",
  "results_json": "{\"total_trades\":84,\"winning_trades\":10,\"losing_trades\":74,\"win_rate\":11.9,\"avg_win_pct\":19.8199,\"avg_loss_pct\":6.9594,\"total_return_pct\":-47.8884,\"fin...",
  "created_at": "2026-02-14 06:13:37"
}
{
  "id": 2,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"take_profit\":20,\"stop_loss\":10,\"max_hold_days\":90,\"initial_capital\":10000,\"trading_fee\":0.1}",
  "results_json": "{\"total_trades\":84,\"winning_trades\":10,\"losing_trades\":74,\"win_rate\":11.9,\"avg_win_pct\":19.8199,\"avg_loss_pct\":6.9594,\"total_return_pct\":-47.8884,\"fin...",
  "created_at": "2026-02-14 17:00:04"
}
```

**`created_at` range:** 2026-02-14 06:13:37 → 2026-03-28 18:33:41

### 199. `fxp_whatif_scenarios` — ~3 rows (0MB + 0MB idx)
**Purpose:** Forex Pro: Backtests

**Columns (6):** `id` (int), `scenario_name` (varchar(200)), `query_text` (text), `params_json` (text), `results_json` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"take_profit_pips\":100,\"stop_loss_pips\":50,\"max_hold_days\":30,\"initial_capital\":10000,\"leverage\":10,\"spread_pips\":1.5}",
  "results_json": "{\"total_trades\":96,\"winning_trades\":40,\"losing_trades\":56,\"win_rate\":41.67,\"avg_win_pips\":94.57,\"avg_loss_pips\":37.21,\"total_return_pct\":63.2726,\"fina...",
  "created_at": "2026-02-14 07:34:34"
}
{
  "id": 2,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"take_profit_pips\":100,\"stop_loss_pips\":50,\"max_hold_days\":30,\"initial_capital\":10000,\"leverage\":10,\"spread_pips\":1.5}",
  "results_json": "{\"total_trades\":96,\"winning_trades\":40,\"losing_trades\":56,\"win_rate\":41.67,\"avg_win_pips\":94.57,\"avg_loss_pips\":37.21,\"total_return_pct\":63.2726,\"fina...",
  "created_at": "2026-02-14 15:03:42"
}
```

**`created_at` range:** 2026-02-14 07:34:34 → 2026-02-16 11:25:23

### 200. `lm_conviction_alerts` — ~3 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (8):** `id` (int), `alert_type` (varchar(30)), `ticker` (varchar(10)), `message` (varchar(255)), `severity` (varchar(10)), `details_json` (text), `is_read` (tinyint), `created_at` (datetime)

**Primary Key:** `id`
**Indexed:** `alert_type`, `ticker`, `is_read`, `created_at`

**Sample Rows:**
```json
{
  "id": 1,
  "alert_type": "whale_accumulation",
  "ticker": "GOOGL",
  "message": "GOOGL: Smart money accumulating (whale score 85)",
  "severity": "info",
  "details_json": "{\"whale_score\":85}",
  "is_read": 1,
  "created_at": "2026-02-11 03:55:14"
}
{
  "id": 2,
  "alert_type": "whale_accumulation",
  "ticker": "AMZN",
  "message": "AMZN: Smart money accumulating (whale score 85)",
  "severity": "info",
  "details_json": "{\"whale_score\":85}",
  "is_read": 1,
  "created_at": "2026-02-11 03:55:14"
}
```

**`created_at` range:** 2026-02-11 03:55:14 → 2026-02-11 03:55:14

### 201. `lm_fear_greed` — ~3 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (7):** `id` (int), `source` (varchar(20)), `score` (int), `classification` (varchar(30)), `components` (text), `fetch_date` (date), `fetch_time` (datetime)

**Primary Key:** `id`
**Indexed:** `source`, `fetch_date`

**`classification` distribution:**
- `extreme_fear`: 1
- `greed`: 1
- `neutral`: 1

**Sample Rows:**
```json
{
  "id": 10,
  "source": "crypto",
  "score": 11,
  "classification": "extreme_fear",
  "components": "{\"score\":11,\"classification\":\"extreme_fear\",\"label\":\"Extreme Fear\",\"source\":\"alternative.me\",\"timestamp\":1770768000,\"history\":[{\"score\":11,\"date\":\"202...",
  "fetch_date": "2026-02-11",
  "fetch_time": "2026-02-11 02:51:02"
}
{
  "id": 11,
  "source": "cnn",
  "score": 70,
  "classification": "greed",
  "components": "{\"score\":70,\"classification\":\"greed\",\"source\":\"vix_regime\",\"vix\":17.79,\"vix_score\":74,\"regime\":\"moderate_bull\",\"regime_score\":65,\"trade_date\":\"2026-02...",
  "fetch_date": "2026-02-11",
  "fetch_time": "2026-02-11 02:51:02"
}
```

**`fetch_date` range:** 2026-02-11 → 2026-02-11

**`fetch_time` range:** 2026-02-11 02:51:02 → 2026-02-11 02:51:02

### 202. `lm_schedule_intel_cache` — ~3 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(100)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 10,
  "cache_key": "sched_basketball_nba",
  "cache_data": "{\"wsh\":{\"name\":\"Washington Wizards\",\"abbreviation\":\"WSH\",\"is_back_to_back\":false,\"rest_days\":3,\"is_road_trip\":false,\"games_last_7\":2,\"last_game_date\":...",
  "source": "espn_scoreboard",
  "updated_at": "2026-04-04 18:03:44"
}
{
  "id": 14,
  "cache_key": "sched_baseball_mlb",
  "cache_data": "{\"bal\":{\"name\":\"Baltimore Orioles\",\"abbreviation\":\"BAL\",\"is_back_to_back\":false,\"rest_days\":2,\"is_road_trip\":false,\"games_last_7\":3,\"last_game_date\":\"...",
  "source": "espn_scoreboard",
  "updated_at": "2026-04-28 18:39:14"
}
```

**`updated_at` range:** 2026-04-04 18:03:44 → 2026-04-28 18:39:14

### 203. `lm_scraped_data` — ~3 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (6):** `id` (int), `ticker` (varchar(10)), `data_type` (varchar(30)), `data_json` (text), `scraped_at` (datetime), `expires_at` (datetime)

**Primary Key:** `id`
**Indexed:** `ticker`, `expires_at`

**Sample Rows:**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "data_type": "options",
  "data_json": "{\"score\":85,\"detail\":\"bullish_flow pcr=0 unusual\",\"put_call_ratio\":0,\"unusual_activity\":true}",
  "scraped_at": "2026-02-11 03:40:25",
  "expires_at": "2026-02-11 03:55:25"
}
{
  "id": 2,
  "ticker": "AAPL",
  "data_type": "short_interest",
  "data_json": "{\"score\":50,\"detail\":\"no_data\",\"short_pct_float\":0,\"days_to_cover\":0,\"squeeze_potential\":\"low\"}",
  "scraped_at": "2026-02-11 03:40:25",
  "expires_at": "2026-02-11 15:40:25"
}
```

### 204. `mf2_tracking_daily` — ~3 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (14):** `id` (int), `track_date` (date), `open_positions` (int), `total_closed` (int), `total_wins` (int), `total_losses` (int), `win_rate` (decimal(5,2)), `avg_win_pct` (decimal(8,4)), `avg_loss_pct` (decimal(8,4)), `avg_return_pct` (decimal(8,4)), `best_symbol` (varchar(20)), `worst_symbol` (varchar(20)) … +2 more

**Primary Key:** `id`
**Indexed:** `track_date`

**Sample Rows:**
```json
{
  "id": 2,
  "track_date": "2026-02-12",
  "open_positions": 10,
  "total_closed": 20,
  "total_wins": 11,
  "total_losses": 9,
  "win_rate": 55.0,
  "avg_win_pct": 4.9386,
  "avg_loss_pct": -5.5369,
  "avg_return_pct": 0.2246,
  "best_symbol": "TDB902",
  "worst_symbol": "TDB911",
  "avg_hold_days": 215.1,
  "created_at": "2026-02-12 23:50:48"
}
{
  "id": 3,
  "track_date": "2026-02-13",
  "open_positions": 20,
  "total_closed": 25,
  "total_wins": 12,
  "total_losses": 13,
  "win_rate": 48.0,
  "avg_win_pct": 5.1215,
  "avg_loss_pct": -6.7305,
  "avg_return_pct": -1.0415,
  "best_symbol": "TDB902",
  "worst_symbol": "TDB911",
  "avg_hold_days": 172.0,
  "created_at": "2026-02-13 23:59:15"
}
```

**`track_date` range:** 2026-02-12 → 2026-02-15

**`created_at` range:** 2026-02-12 23:50:48 → 2026-02-15 01:15:10

### 205. `ml_platform_daily` — ~3 rows (0MB + 0MB idx)
**Purpose:** Daily: Aggregated data

**Columns (20):** `id` (int), `metric_date` (date), `total_signals_generated` (int), `signals_crypto` (int), `signals_stocks` (int), `signals_forex` (int), `signals_sports` (int), `resolved_today` (int), `wins_today` (int), `losses_today` (int), `daily_win_rate` (float), `daily_pnl` (float) … +8 more

**Primary Key:** `id`
**Indexed:** `metric_date`

**Sample Rows:**
```json
{
  "id": 1,
  "metric_date": "2026-02-14",
  "total_signals_generated": 205,
  "signals_crypto": 175,
  "signals_stocks": 0,
  "signals_forex": 30,
  "signals_sports": 0,
  "resolved_today": 0,
  "wins_today": 0,
  "losses_today": 0,
  "daily_win_rate": 0.0,
  "daily_pnl": 0.0,
  "cumulative_pnl": 0.0,
  "avg_predictability": 46.5,
  "high_pred_win_rate": 0.0,
  "low_pred_win_rate": 0.0,
  "engines_active": 2,
  "engines_total": 13,
  "api_uptime_pct": 100.0,
  "created_at": "2026-02-14 20:42:23"
}
{
  "id": 6,
  "metric_date": "2026-02-15",
  "total_signals_generated": 780,
  "signals_crypto": 685,
  "signals_stocks": 0,
  "signals_forex": 95,
  "signals_sports": 0,
  "resolved_today": 66,
  "wins_today": 22,
  "losses_today": 44,
  "daily_win_rate": 33.3,
  "daily_pnl": -65.76,
  "cumulative_pnl": -13.91,
  "avg_predictability": 46.9,
  "high_pred_win_rate": 0.0,
  "low_pred_win_rate": 0.0,
  "engines_active": 5,
  "engines_total": 13,
  "api_uptime_pct": 100.0,
  "created_at": "2026-02-15 19:01:20"
}
```

**`metric_date` range:** 2026-02-14 → 2026-02-16

**`api_uptime_pct` range:** 100.0 → 100.0

### 206. `ml_regime_snapshots` — ~3 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (14):** `id` (int), `snapshot_date` (date), `asset_class` (varchar(20)), `btc_trend` (varchar(10)), `market_fear_greed` (int), `avg_hurst` (float), `avg_correlation` (float), `volatility_percentile` (float), `trending_pairs` (int), `mean_reverting_pairs` (int), `random_pairs` (int), `recommended_strategy` (varchar(30)) … +2 more

**Primary Key:** `id`
**Indexed:** `snapshot_date`

**`asset_class` distribution:**
- `CRYPTO`: 3

**Sample Rows:**
```json
{
  "id": 1,
  "snapshot_date": "2026-02-14",
  "asset_class": "CRYPTO",
  "btc_trend": "BULLISH",
  "market_fear_greed": 50,
  "avg_hurst": 0.5697,
  "avg_correlation": 0.0,
  "volatility_percentile": 50.0,
  "trending_pairs": 6,
  "mean_reverting_pairs": 0,
  "random_pairs": 30,
  "recommended_strategy": "MULTI_INDICATOR",
  "regime_confidence": 0.83,
  "created_at": "2026-02-14 20:42:23"
}
{
  "id": 6,
  "snapshot_date": "2026-02-15",
  "asset_class": "CRYPTO",
  "btc_trend": "NEUTRAL",
  "market_fear_greed": 50,
  "avg_hurst": 0.5685,
  "avg_correlation": 0.0,
  "volatility_percentile": 50.0,
  "trending_pairs": 4,
  "mean_reverting_pairs": 0,
  "random_pairs": 32,
  "recommended_strategy": "MULTI_INDICATOR",
  "regime_confidence": 0.89,
  "created_at": "2026-02-15 19:01:20"
}
```

**`snapshot_date` range:** 2026-02-14 → 2026-02-16

**`created_at` range:** 2026-02-14 20:42:23 → 2026-02-16 19:09:19

### 207. `report_cache` — ~3 rows (1MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (3):** `cache_key` (varchar(50)), `cache_data` (longtext), `updated_at` (datetime)

**Primary Key:** `cache_key`

**Sample Rows:**
```json
{
  "cache_key": "daily_summary",
  "cache_data": "{\"generated_at\":\"2026-02-16 22:57:16\",\"scenarios\":[{\"name\":\"daytrader_eod\",\"params\":{\"name\":\"daytrader_eod\",\"tp\":5,\"sl\":3,\"hold\":1,\"comm\":10,\"vol\":\"of...",
  "updated_at": "2026-02-16 22:59:06"
}
{
  "cache_key": "stats_snapshot",
  "cache_data": "{\"timestamp\":\"2026-02-16 22:59:06\",\"elapsed_seconds\":115.12,\"steps\":[{\"name\":\"Import Picks\",\"status\":\"ok\",\"imported\":0,\"skipped\":35},{\"name\":\"Fetch Pr...",
  "updated_at": "2026-02-16 22:59:06"
}
```

**`updated_at` range:** 2026-02-16 22:59:06 → 2026-05-08 12:29:56

### 208. `simulation_meta` — ~3 rows (0MB + 0MB idx)
**Purpose:** Misc/Unknown

**Columns (3):** `meta_key` (varchar(50)), `meta_value` (text), `updated_at` (datetime)

**Primary Key:** `meta_key`

**Sample Rows:**
```json
{
  "meta_key": "status",
  "meta_value": "running",
  "updated_at": "2026-04-26 06:54:07"
}
{
  "meta_key": "total_combos",
  "meta_value": "216672",
  "updated_at": "2026-04-26 06:54:07"
}
```

**`updated_at` range:** 2026-04-26 06:54:07 → 2026-04-26 06:54:07

### 209. `backtest_results` — ~2 rows (0MB + 0MB idx)
**Purpose:** Backtesting

**Columns (24):** `id` (int), `portfolio_id` (int), `run_name` (varchar(200)), `algorithm_filter` (varchar(500)), `strategy_type` (varchar(50)), `start_date` (date), `end_date` (date), `initial_capital` (decimal(12,2)), `final_value` (decimal(12,2)), `total_return_pct` (decimal(10,4)), `total_trades` (int), `winning_trades` (int) … +12 more

**Primary Key:** `id`
**Indexed:** `portfolio_id`, `strategy_type`

**Sample Rows:**
```json
{
  "id": 1,
  "portfolio_id": 0,
  "run_name": "custom_tp999_sl999_7d",
  "algorithm_filter": "",
  "strategy_type": "custom",
  "start_date": "2026-01-28",
  "end_date": "2026-02-06",
  "initial_capital": 10000.0,
  "final_value": 9169.72,
  "total_return_pct": -8.3028,
  "total_trades": 25,
  "winning_trades": 4,
  "losing_trades": 21,
  "win_rate": 16.0,
  "avg_win_pct": 3.401,
  "avg_loss_pct": 5.7533,
  "max_drawdown_pct": 8.3028,
  "total_commissions": 500.0,
  "sharpe_ratio": -0.7838,
  "sortino_ratio": -0.5775,
  "profit_factor": 0.1215,
  "expectancy": -4.2886,
  "params_json": "{\"algorithms\":\"\",\"strategy\":\"custom\",\"take_profit_pct\":999,\"stop_loss_pct\":999,\"max_hold_days\":7,\"initial_capital\":10000,\"commission\":10,\"slippage_pct...",
  "created_at": "2026-02-09 05:04:32"
}
{
  "id": 2,
  "portfolio_id": 0,
  "run_name": "custom_tp999_sl999_1d",
  "algorithm_filter": "",
  "strategy_type": "custom",
  "start_date": "2026-01-28",
  "end_date": "2026-02-06",
  "initial_capital": 10000.0,
  "final_value": 9260.9,
  "total_return_pct": -7.391,
  "total_trades": 25,
  "winning_trades": 1,
  "losing_trades": 24,
  "win_rate": 4.0,
  "avg_win_pct": 0.6229,
  "avg_loss_pct": 3.7802,
  "max_drawdown_pct": 7.391,
  "total_commissions": 500.0,
  "sharpe_ratio": -2.7603,
  "sortino_ratio": -0.9217,
  "profit_factor": 0.0071,
  "expectancy": -3.6041,
  "params_json": "{\"algorithms\":\"\",\"strategy\":\"custom\",\"take_profit_pct\":999,\"stop_loss_pct\":999,\"max_hold_days\":1,\"initial_capital\":10000,\"commission\":10,\"slippage_pct...",
  "created_at": "2026-02-09 05:04:33"
}
```

**`start_date` range:** 2026-01-28 → 2026-01-28

**`end_date` range:** 2026-02-06 → 2026-02-06

### 210. `lm_algo_performance` — ~2 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (20):** `id` (int), `snap_date` (date), `algorithm_name` (varchar(100)), `asset_class` (varchar(10)), `param_source` (varchar(10)), `signals_count` (int), `trades_count` (int), `wins` (int), `losses` (int), `expired` (int), `total_pnl_pct` (decimal(12,4)), `avg_pnl_pct` (decimal(10,4)) … +8 more

**Primary Key:** `id`
**Indexed:** `snap_date`, `algorithm_name`, `param_source`

**`asset_class` distribution:**
- `FOREX`: 2

**Sample Rows:**
```json
{
  "id": 1,
  "snap_date": "2026-02-10",
  "algorithm_name": "Consensus",
  "asset_class": "FOREX",
  "param_source": "learned",
  "signals_count": 58,
  "trades_count": 2,
  "wins": 0,
  "losses": 2,
  "expired": 2,
  "total_pnl_pct": -0.6543,
  "avg_pnl_pct": -0.3272,
  "win_rate": 0.0,
  "best_trade_pct": -0.1891,
  "worst_trade_pct": -0.4652,
  "avg_hold_hours": 12.3,
  "tp_used": 3.0,
  "sl_used": 2.0,
  "hold_used": 12,
  "created_at": "2026-02-10 21:39:17"
}
{
  "id": 2,
  "snap_date": "2026-02-10",
  "algorithm_name": "RSI Reversal",
  "asset_class": "FOREX",
  "param_source": "learned",
  "signals_count": 12,
  "trades_count": 1,
  "wins": 0,
  "losses": 1,
  "expired": 1,
  "total_pnl_pct": -0.0344,
  "avg_pnl_pct": -0.0344,
  "win_rate": 0.0,
  "best_trade_pct": -0.0344,
  "worst_trade_pct": -0.0344,
  "avg_hold_hours": 7.0,
  "tp_used": 2.0,
  "sl_used": 1.0,
  "hold_used": 6,
  "created_at": "2026-02-10 21:39:17"
}
```

**`snap_date` range:** 2026-02-10 → 2026-02-10

**`created_at` range:** 2026-02-10 21:39:17 → 2026-02-10 21:39:17

### 211. `mf2_whatif_scenarios` — ~2 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (6):** `id` (int), `scenario_name` (varchar(200)), `query_text` (text), `params_json` (text), `results_json` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"target_return\":10,\"stop_loss\":8,\"max_hold_days\":90,\"initial_capital\":10000,\"redemption_fee\":0}",
  "results_json": "{\"total_trades\":72,\"winning_trades\":30,\"losing_trades\":42,\"win_rate\":41.67,\"avg_win_pct\":6.4587,\"avg_loss_pct\":51.2546,\"total_return_pct\":-98.7817,\"fi...",
  "created_at": "2026-02-14 06:40:53"
}
{
  "id": 2,
  "scenario_name": "",
  "query_text": "",
  "params_json": "{\"scenario\":\"\",\"algorithms\":\"\",\"target_return\":10,\"stop_loss\":8,\"max_hold_days\":90,\"initial_capital\":10000,\"redemption_fee\":0}",
  "results_json": "{\"total_trades\":79,\"winning_trades\":30,\"losing_trades\":49,\"win_rate\":37.97,\"avg_win_pct\":6.1887,\"avg_loss_pct\":58.3019,\"total_return_pct\":-99.751,\"fin...",
  "created_at": "2026-03-29 03:28:52"
}
```

**`created_at` range:** 2026-02-14 06:40:53 → 2026-03-29 03:28:52

### 212. `mf_report_cache` — ~2 rows (0MB + 0MB idx)
**Purpose:** Mutual Funds: Backtests

**Columns (3):** `cache_key` (varchar(50)), `cache_data` (longtext), `updated_at` (datetime)

**Primary Key:** `cache_key`

**Sample Rows:**
```json
{
  "cache_key": "daily_summary",
  "cache_data": "{\"updated_at\":\"2026-03-28 21:56:51\",\"nav_fetched\":0,\"import\":{\"ok\":true,\"imported\":0,\"skipped\":34,\"strategies_matched\":9,\"funds_checked\":20},\"analysis...",
  "updated_at": "2026-03-28 21:56:51"
}
{
  "cache_key": "stats_snapshot",
  "cache_data": "{\"timestamp\":\"2026-03-28 21:56:51\",\"elapsed_seconds\":0.77,\"steps\":[{\"name\":\"Fetch NAV\",\"status\":\"no_new\",\"tickers_fetched\":0},{\"name\":\"Import Funds\",\"...",
  "updated_at": "2026-03-28 21:56:51"
}
```

**`updated_at` range:** 2026-03-28 21:56:51 → 2026-03-28 21:56:51

### 213. `alpha_status` — ~1 rows (0MB + 0MB idx)
**Purpose:** Alpha Engine: Picks/performance

**Columns (11):** `id` (int), `last_refresh_start` (datetime), `last_refresh_end` (datetime), `last_refresh_status` (varchar(20)), `next_expected_refresh` (datetime), `universe_count` (int), `factors_computed` (int), `picks_generated` (int), `current_regime` (varchar(50)), `regime_detail` (text), `summary_json` (text)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "last_refresh_start": "2026-04-27 21:54:46",
  "last_refresh_end": "2026-04-27 21:55:28",
  "last_refresh_status": "completed",
  "next_expected_refresh": "2026-04-28 21:30:00",
  "universe_count": 52,
  "factors_computed": 52,
  "picks_generated": 90,
  "current_regime": "calm_bull",
  "regime_detail": null,
  "summary_json": "{\"regime\":\"calm_bull\",\"factors_computed\":52,\"picks_generated\":90,\"consensus_picks\":10,\"strategies\":[\"Alpha Factor Momentum\",\"Alpha Factor Quality\",\"Al..."
}
```

### 214. `lm_bridge_cusum` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (9):** `id` (int), `algorithm_name` (varchar(100)), `decay_status` (varchar(20)), `recommended_weight` (decimal(6,3)), `last_sharpe` (decimal(8,4)), `last_win_rate` (decimal(6,4)), `change_points` (int), `total_trades` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `algorithm_name`

**Sample Rows:**
```json
{
  "id": 2,
  "algorithm_name": "StochRSI Crossover",
  "decay_status": "dead",
  "recommended_weight": 0.0,
  "last_sharpe": -9.5583,
  "last_win_rate": 0.2,
  "change_points": 0,
  "total_trades": 10,
  "updated_at": "2026-02-15 15:19:04"
}
```

**`updated_at` range:** 2026-02-15 15:19:04 → 2026-02-15 15:19:04

### 215. `lm_mlb_stats_cache` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(50)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 7,
  "cache_key": "mlb_teams",
  "cache_data": "{\"nyy\":{\"name\":\"New York Yankees\",\"short_name\":\"Yankees\",\"abbreviation\":\"NYY\",\"wins\":6,\"losses\":1,\"win_pct\":0.857,\"conference\":\"American League\",\"runs...",
  "source": "espn_api",
  "updated_at": "2026-04-04 18:03:44"
}
```

**`updated_at` range:** 2026-04-04 18:03:44 → 2026-04-04 18:03:44

### 216. `lm_nba_stats_cache` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(50)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 8,
  "cache_key": "nba_teams",
  "cache_data": "{\"okc\":{\"name\":\"Oklahoma City Thunder\",\"short_name\":\"Thunder\",\"abbreviation\":\"OKC\",\"wins\":61,\"losses\":16,\"win_pct\":0.792,\"conference\":\"Western Confere...",
  "source": "espn_api+scoreboard",
  "updated_at": "2026-04-04 18:03:44"
}
```

**`updated_at` range:** 2026-04-04 18:03:44 → 2026-04-04 18:03:44

### 217. `lm_nfl_stats_cache` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(50)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 7,
  "cache_key": "nfl_teams",
  "cache_data": "{\"sea\":{\"name\":\"Seattle Seahawks\",\"short_name\":\"Seahawks\",\"abbreviation\":\"SEA\",\"wins\":14,\"losses\":3,\"ties\":0,\"win_pct\":0.824,\"conference\":\"National Fo...",
  "source": "espn_api",
  "updated_at": "2026-04-04 18:03:44"
}
```

**`updated_at` range:** 2026-04-04 18:03:44 → 2026-04-04 18:03:44

### 218. `lm_nhl_stats_cache` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (5):** `id` (int), `cache_key` (varchar(50)), `cache_data` (longtext), `source` (varchar(100)), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `cache_key`

**Sample Rows:**
```json
{
  "id": 7,
  "cache_key": "nhl_teams",
  "cache_data": "{\"col\":{\"name\":\"Colorado Avalanche\",\"short_name\":\"Avalanche\",\"abbreviation\":\"COL\",\"wins\":49,\"losses\":15,\"otl\":10,\"points\":108,\"pts_pct\":0.73,\"gp\":74,\"...",
  "source": "espn_api",
  "updated_at": "2026-04-04 18:03:44"
}
```

**`updated_at` range:** 2026-04-04 18:03:44 → 2026-04-04 18:03:44

### 219. `lm_webhook_config` — ~1 rows (0MB + 0MB idx)
**Purpose:** Live Market: Signals

**Columns (6):** `id` (int), `webhook_url` (varchar(500)), `is_active` (tinyint), `last_sent` (datetime), `last_response` (text), `created_at` (datetime)

**Primary Key:** `id`

**Sample Rows:**
```json
{
  "id": 1,
  "webhook_url": "",
  "is_active": 0,
  "last_sent": null,
  "last_response": null,
  "created_at": "2026-02-11 03:54:16"
}
```

**`created_at` range:** 2026-02-11 03:54:16 → 2026-02-11 03:54:16

### 220. `mc_daily_snapshots` — ~1 rows (0MB + 0MB idx)
**Purpose:** Daily: Aggregated data

**Columns (12):** `id` (int), `snapshot_date` (date), `signals` (int), `wins` (int), `losses` (int), `win_rate` (double), `avg_pnl` (double), `total_pnl` (double), `best_trade` (double), `worst_trade` (double), `unique_coins` (int), `updated_at` (datetime)

**Primary Key:** `id`
**Indexed:** `snapshot_date`

**Sample Rows:**
```json
{
  "id": 1,
  "snapshot_date": "2026-02-10",
  "signals": 0,
  "wins": 0,
  "losses": 0,
  "win_rate": 0.0,
  "avg_pnl": 0.0,
  "total_pnl": 0.0,
  "best_trade": 0.0,
  "worst_trade": 0.0,
  "unique_coins": 0,
  "updated_at": "2026-02-10 21:38:48"
}
```

**`snapshot_date` range:** 2026-02-10 → 2026-02-10

**`updated_at` range:** 2026-02-10 21:38:48 → 2026-02-10 21:38:48

---

## 🐛 Outlier & Bug Analysis (Key Tables)

### `consensus_tracked`

- Total rows: 318
- Closed with exit_price=0: 5 (1%)
- Exact 0% returns: 83 (26%)
- Whole-dollar entry prices: 6 (1%)
- 2026+ dates: 318 (100%)
- ⚠️ VERDICT: Largely synthetic/generated data — do NOT use for live trading decisions

### `trading_picks`

- Total rows: 63,934
-   OPEN: 49,389
-   active: 4,830
-   LOST: 3,067
-   WON: 2,547
-   EXPIRED: 1,358
-   SL_HIT: 818
-   TP_HIT: 629
-   LOSS: 546
-   CLOSED: 177
-   SIGNAL: 152
- Bad entry_price: 553 rows
- Extreme PnL (>500% or <-100%): 8 rows
- Date range: 2026-02-17 20:22:40 → 2026-05-08 13:52:37

### `at_raw_picks`

- Total rows: 136,056
-   OPEN: 68,344
-   EXPIRED: 51,155
-   CLOSED: 11,440
-   LOST: 2,929
-   WON: 2,188
- Stale picks: 0
- Banned picks: 0
- Date range: 2026-03-06 21:01:22 → 2026-05-08 14:27:13
- Source systems:
-   incubator_gainer: 21,336
-   AlphaEngine: 13,498
-   quan_engine: 13,255
-   alpha_engine: 12,641
-   Predictions: 12,539
-   ml_crypto_pred: 11,156
-   smart_money: 9,129
-   battleground: 7,191
-   audit_trail_local: 7,065
-   KIMI_RiseOfTheClaw: 2,909

### `at_consensus_picks`

- Total rows: 11,436
-   LOST: 5,357
-   WON: 3,288
-   OPEN: 2,251
-   EXPIRED: 540
- Bad entry_price: 929

### `bt_backtest_trades`

- Error: (2013, 'Lost connection to MySQL server during query (timed out)')

### `pf_challenge_positions`

- Error: (0, '')

### `at_discord_notifications`

- Error: (0, '')

### `stock_picks`

- Error: (0, '')

---

## 💡 Future Actions & Enhancements

### 🚨 Critical Issues

1. **`consensus_tracked`: Synthetic data problem** — The majority of rows have 2026 future dates, whole-dollar prices, and exact 0% returns. This data was generated/synthetic and should be clearly labeled as such in all dashboards. Consider purging or moving to a `_synthetic` table.
2. **`bt_backtest_trades`: Dominant storage consumer** — At 1.27M+ rows / 1.4GB, this single table dominates DB size. Plan to migrate to the separate `ejaguiar1_backtests` DB as outlined in the archive plan.
3. **Zero exit prices** — Several tables have rows with exit_price=0 on closed positions. This breaks P&L calculations. Add validation in the ingest pipeline.

### 📊 Data Quality Improvements

4. **Add automated quality gates** — Implement pre-insert validation: reject picks with entry_price ≤ 0, confidence > 1.0, impossible P&L ranges
5. **Standardize status values** — Audit shows inconsistent casing and variations (e.g. WON vs won, LOST vs loss). Create an ENUM or CHECK constraint.
6. **Add created_at default** — Many tables lack DEFAULT CURRENT_TIMESTAMP, making time-based queries fragile
7. **Dedup strategy audit** — Some tables have 5-10 duplicate groups with identical symbol+direction+price. Review dedup_hash logic.

### 🔧 Infrastructure Enhancements

8. **Table cleanup sweep** — 280+ tables, many empty or stale. Archive tables unused for 90+ days to reduce `SHOW TABLES` overhead
9. **Add DB health heartbeat** — Currently no automated DB size/row count monitoring. Create a weekly cron that alerts if any table grows >20% unexpectedly
10. **Query performance** — Add composite indexes on (symbol, status, created_at) for the most-queried tables (at_raw_picks, trading_picks, at_consensus_picks)
11. **Split read/write paths** — Heavy backtest writes should not compete with dashboard reads. The `BACKTESTS_DB_NAME` env var already supports this; provision `ejaguiar1_backtests`
12. **Document the `trading_picks` vs `at_raw_picks` distinction** — These tables overlap in purpose but have different schemas. Consolidate or clearly document when to use each.

### 📈 Monitoring Suggestions

13. **Weekly stale-table report** — Auto-detect tables with 0 rows or no UPDATE_TIME in 90+ days
14. **PnL sanity alerts** — Flag any new row with pnl_pct > 200% or < -99% (likely data entry bugs)
15. **Growth rate tracking** — Log total DB size weekly; alert if growth exceeds disk quota (50webs shared hosting limits)

---

## 📋 Report Summary

- **Tables:** 322
- **Tables with data:** 220
- **Approx. total rows:** 2,258,424
- **Data size:** 1,789MB
- **Index size:** 318MB
- **Key tables audited in depth:** 8

*Generated by `tmp/comprehensive_db_audit.py`*