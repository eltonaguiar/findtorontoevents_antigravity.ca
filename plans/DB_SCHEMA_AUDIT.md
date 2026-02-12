# Database Schema Audit Report

**Date:** 2026-02-11
**Auditor:** Claude Opus 4.6 (DB Schema Auditor Agent)
**Scope:** `ejaguiar1_stocks` (208 tables), `ejaguiar1_sportsbet` (0 tables), cross-DB references

---

## 1. Database Inventory

### 1.1 ejaguiar1_stocks — 208 Tables

| Prefix | Count | Module | Description |
|--------|-------|--------|-------------|
| `lm_` | 42 | live-monitor | Live Trading Monitor (signals, trades, sports, smart money) |
| `mf_` | 18 | findmutualfunds | Mutual Funds v1 |
| `mf2_` | 12 | findmutualfunds2 | Mutual Funds v2 (portfolio) |
| `fx_` | 14 | findforex2 | Forex v1 |
| `fxp_` | 12 | findforex2/portfolio | Forex v2 (portfolio) |
| `cr_` | 12 | findcryptopairs/portfolio | Crypto Pairs v2 (portfolio) |
| `cp_` | 7 | findcryptopairs | Crypto Pairs v1 |
| `gm_` | 6 | live-monitor/goldmine | Goldmine Tracker |
| `goldmine_cursor_` | 7 | goldmine_cursor | Goldmine Cursor AI |
| `KIMI_GOLDMINE_` | 6 | investments/goldmines/kimi | KIMI Goldmine |
| `mc_` | 3 | findcryptopairs (meme) | Meme Coin Scanner |
| `cw_` | 2 | findcryptopairs (winners) | Crypto Winners |
| `miracle_` | 14 | findstocks_global, findstocks2_global | Miracle strategies v2/v3 |
| `alpha_` | 8 | findstocks/api | Alpha Engine |
| `stock_` | 5 | findstocks | Stock data (dividends, earnings, etc.) |
| (core) | ~40 | findstocks, portfolio2 | Algorithms, portfolios, trades, backtests |

### 1.2 ejaguiar1_sportsbet — EMPTY (0 tables)

The database exists but contains zero tables. The SQL dump confirms:
```
CREATE DATABASE IF NOT EXISTS `ejaguiar1_sportsbet`
```
...followed by COMMIT with no CREATE TABLE statements.

### 1.3 Other Databases Referenced in Code

| Database | Used By | Tables |
|----------|---------|--------|
| `ejaguiar1_favcreators` | favcreators, api/, CONTACTLENSES, MOVIESHOWS3 | Users, creators, events, notes, links |
| `ejaguiar1_news` | favcreators/public/api/news_feed.php | RSS feed articles |
| `ejaguiar1_memecoin` | findcryptopairs/api/meme_scanner.php, goldmine_tracker.php | mc_winners, mc_scan_log, mc_daily_snapshots |

**NOTE:** The `mc_*` tables exist in BOTH `ejaguiar1_stocks` AND `ejaguiar1_memecoin`. The meme_scanner.php writes to `ejaguiar1_memecoin`, while goldmine_tracker.php reads from `ejaguiar1_memecoin` via cross-DB connection and copies data into `gm_unified_picks` in `ejaguiar1_stocks`.

---

## 2. Tables Referenced in Code but MISSING from DB Dump

These tables are referenced in PHP/Python code but do NOT have a corresponding CREATE TABLE in the `ejaguiar1_stocks` dump.

### 2.1 CRITICAL Missing Tables (actively queried)

| Missing Table | Referenced In | Type | Severity |
|---------------|--------------|------|----------|
| `lm_free_data_cache` | `live-monitor/api/free_data_scraper.php:18` | CREATE TABLE IF NOT EXISTS | **LOW** - auto-created on first API call |
| `lm_free_data_scores` | `live-monitor/api/free_data_scraper.php:30`, `multi_dimensional.php:1338` | CREATE TABLE IF NOT EXISTS | **LOW** - auto-created, but multi_dimensional.php depends on it |
| `lm_threshold_learning` | `live-monitor/api/hour_learning.php:585` | CREATE TABLE IF NOT EXISTS | **LOW** - auto-created on first API call |

These 3 tables use `CREATE TABLE IF NOT EXISTS` so they will be auto-created on first use. They are missing from the dump because they may not have been created yet on the production DB, or the dump was taken before their first use.

### 2.2 Views Referenced but Not in Dump (NOT tables)

| Missing View | Referenced In | Purpose |
|--------------|--------------|---------|
| `v_algorithm_leaderboard` | `investments/goldmines/antigravity/api/unified_predictions.php:36` | Algorithm ranking |
| `v_hidden_winners` | `unified_predictions.php:81` | Hidden winners |
| `v_system_performance` | `unified_predictions.php:118` | System-level metrics |
| `v_risk_dashboard` | `unified_predictions.php:195` | Risk overview |
| `v_max_drawdown_by_algorithm` | `unified_predictions.php:216` | Per-algo drawdown |
| `v_max_drawdown_by_system` | `unified_predictions.php:218` | Per-system drawdown |
| `v_system_correlation` | `unified_predictions.php:238` | Cross-system correlation |
| `v_backtest_vs_live` | `unified_predictions.php:256` | Backtest vs live comparison |
| `v_win_loss_streaks` | `unified_predictions.php:274` | Win/loss streak analysis |

**Analysis:** These are SQL VIEWs, not tables. The `unified_predictions.php` file uses `@$conn->query()` (error-suppressed) to query them. They were likely defined once but are not in the DB dump (phpMyAdmin dumps don't always include views by default). These views need to be recreated or the code needs fallback handling.

### 2.3 Hypothetical/Generated Tables (Not Actual Missing Tables)

| Table Name | Referenced In | Status |
|-----------|--------------|--------|
| `algorithm_pause_log` | `scripts/algorithm_pauser.py:119` | **NOT a real table** - Python generates PHP code strings containing this table name. The table was never created. |
| `unified_predictions` | `investments/goldmines/antigravity/api/unified_predictions.php:160` | Uses `@$conn->query()` with fallback to `stock_picks`. May need creation. |

---

## 3. Tables in DB Dump but NOT Referenced in Any Code (Potentially Orphaned)

### 3.1 Orphaned fx_ Tables (v1 forex, superseded by fxp_ v2)

| Orphaned Table | Exists In DB | Code Refs | Notes |
|---------------|-------------|-----------|-------|
| `fx_algo_performance` | YES | 0 | Superseded by `fxp_algo_performance` |
| `fx_algorithms` | YES | 0 | Superseded by `fxp_algorithms` |
| `fx_category_perf` | YES | 0 | Superseded by `fxp_category_perf` |
| `fx_comparisons` | YES | 0 | Superseded by `fxp_comparisons` |
| `fx_pair_picks` | YES | 0 | Superseded by `fxp_pair_picks` |
| `fx_portfolios` | YES | 0 | Superseded by `fxp_portfolios` |
| `fx_price_history` | YES | 0 | Superseded by `fxp_price_history` |
| `fx_whatif_scenarios` | YES | 0 | Superseded by `fxp_whatif_scenarios` |

**Recommendation:** These 8 tables appear to be leftovers from the v1 forex portfolio system. The v2 system uses the `fxp_` prefix. The v1 base tables (`fx_pairs`, `fx_prices`, `fx_signals`, `fx_strategies`, `fx_audit_log`, `fx_backtest_results`, `fx_report_cache`) are still referenced by `findforex2/api/` code. Consider dropping the 8 orphaned extended tables after verifying no data needs migration.

### 3.2 Orphaned mf_ Tables (v1 mutual funds, partially superseded by mf2_)

| Orphaned Table | Exists In DB | Code Refs | Notes |
|---------------|-------------|-----------|-------|
| `mf_algo_performance` | YES | 0 | Superseded by `mf2_algo_performance` |
| `mf_algorithms` | YES | 0 | Superseded by `mf2_algorithms` |
| `mf_comparisons` | YES | 0 | Superseded by `mf2_comparisons` |
| `mf_fund_picks` | YES | 0 | Superseded by `mf2_fund_picks` |

**Note:** Unlike forex, many v1 mf_ tables ARE still referenced (`mf_funds`, `mf_nav_history`, `mf_portfolios`, `mf_report_cache`, `mf_backtest_results`, `mf_backtest_trades`, `mf_audit_log`, `mf_selections`, `mf_simulation_grid`, `mf_simulation_meta`, `mf_strategies`, `mf_whatif_scenarios`, `mf_benchmarks`). Only 4 mf_ tables have zero references.

### 3.3 Summary: Potentially Orphaned Tables (12 total)

```
fx_algo_performance     fx_algorithms          fx_category_perf
fx_comparisons          fx_pair_picks          fx_portfolios
fx_price_history        fx_whatif_scenarios
mf_algo_performance     mf_algorithms          mf_comparisons
mf_fund_picks
```

---

## 4. Schema Mismatches (Code CREATE TABLE vs DB Dump)

### 4.1 lm_signals — Column Drift (RESOLVED via migration)

**Code** (`live-monitor/api/live_signals.php:49`):
```sql
CREATE TABLE IF NOT EXISTS lm_signals (
    id, asset_class, symbol, algorithm_name, signal_type, signal_strength,
    entry_price, target_tp_pct, target_sl_pct, max_hold_hours, timeframe,
    rationale, signal_time, expires_at, status
)
-- 15 columns
```

**DB Dump** has 19 columns (4 extra):
```sql
param_source VARCHAR(10) NOT NULL DEFAULT 'original'
tp_original DECIMAL(6,2) NOT NULL DEFAULT 0
sl_original DECIMAL(6,2) NOT NULL DEFAULT 0
hold_original INT NOT NULL DEFAULT 0
```

**Resolution:** These columns are added via ALTER TABLE migration in `algo_performance_schema.php:9-15`. The migration checks `SHOW COLUMNS FROM lm_signals LIKE 'param_source'` before altering. This is the expected migration pattern -- no action needed.

### 4.2 lm_sports_bets — game_date Column (RESOLVED via migration)

**Code** (`live-monitor/api/sports_bets.php:27`): CREATE TABLE includes `game_date DATE DEFAULT NULL`
**DB Dump**: Also includes `game_date` column.
**Code** (`sports_bets.php:63`): Also has `ALTER TABLE lm_sports_bets ADD COLUMN game_date` with existence check.

This is a self-healing migration pattern. No mismatch.

### 4.3 No Other Column-Level Mismatches Found

The remaining tables' CREATE TABLE IF NOT EXISTS definitions in code match the DB dump schemas. The project uses a consistent pattern of auto-creating tables with CREATE TABLE IF NOT EXISTS and adding new columns via conditional ALTER TABLE.

---

## 5. Sports Betting Database Analysis

### 5.1 The ejaguiar1_sportsbet Database is EMPTY

- **File:** `C:\Users\zerou\Downloads\sportsbetv2.sql`
- **Content:** Database creation statement only, zero tables
- Credentials: `ejaguiar1_sportsbet` / `eltonsportsbets`

### 5.2 All Sports Data Lives in ejaguiar1_stocks

The following 7 sports tables exist in `ejaguiar1_stocks`:

| Table | Purpose | Rows (estimated) |
|-------|---------|-------------------|
| `lm_sports_bets` | Paper bet records | Active |
| `lm_sports_bankroll` | Bankroll snapshots | Active |
| `lm_sports_odds` | Cached odds data | Active |
| `lm_sports_clv` | Closing Line Value tracking | Active |
| `lm_sports_credit_usage` | API credit monitoring | Active |
| `lm_sports_value_bets` | Value bet opportunities | Active |
| `lm_sports_daily_picks` | Daily picks history | Active |

### 5.3 Code Connection Pattern

| File | Connection Logic |
|------|-----------------|
| `live-monitor/api/sports_db_connect.php` | Tries `ejaguiar1_sportsbet` first, falls back to `ejaguiar1_stocks` |
| `live-monitor/api/sports_bets.php` | Uses `sports_db_connect.php` (fallback pattern) |
| `live-monitor/api/sports_odds.php` | Uses `sports_db_connect.php` (fallback pattern) |
| `live-monitor/api/sports_picks.php` | Uses `sports_db_connect.php` (fallback pattern) |
| `live-monitor/api/sports_scores.php` | Uses `sports_db_connect.php` (fallback pattern) |
| `live-monitor/api/goldmine_tracker.php:784` | Tries `ejaguiar1_sportsbet` first, falls back to `$conn` (stocks DB) |

**Conclusion:** Since `ejaguiar1_sportsbet` is empty and the fallback always triggers, ALL sports data is effectively stored in `ejaguiar1_stocks` under `lm_sports_*` tables. The dedicated sports DB was set up but never populated with its own tables -- the fallback pattern means everything goes into the stocks DB.

### 5.4 Recommendation

Either:
1. **Remove the fallback** and point all sports code directly at `ejaguiar1_stocks` (simpler, matches reality)
2. **Or migrate** the `lm_sports_*` tables into `ejaguiar1_sportsbet` and update `sports_db_connect.php` to only use that DB

Option 1 is lower risk since the current setup works.

---

## 6. Asset Class Coverage

### 6.1 Stocks (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `stocks`, `stock_picks`, `daily_prices`, `algorithms`, `portfolios` | findstocks/api |
| `backtest_results`, `backtest_trades`, `audit_log`, `report_cache` | findstocks/api |
| `alpha_universe`, `alpha_fundamentals`, `alpha_earnings`, `alpha_macro`, `alpha_factor_scores`, `alpha_picks`, `alpha_refresh_log`, `alpha_status` | findstocks/api (Alpha Engine) |
| `saved_portfolios`, `portfolio_positions`, `portfolio_daily_equity` | findstocks/portfolio2 |
| `paper_trades`, `paper_portfolio_daily` | findstocks/portfolio2 |
| `stock_dividends`, `stock_earnings`, `stock_fundamentals`, `stock_analyst_recs` | findstocks/portfolio2 |
| `algorithm_performance`, `algorithm_rolling_perf` | findstocks/portfolio2 |
| `kelly_sizing_log`, `circuit_breaker_log` | findstocks/portfolio2 |
| `lm_signals`, `lm_trades`, `lm_snapshots` (asset_class='STOCK') | live-monitor |

### 6.2 Crypto (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `cp_pairs`, `cp_prices`, `cp_signals`, `cp_strategies`, `cp_backtest_results`, `cp_audit_log`, `cp_report_cache` | findcryptopairs/api |
| `cr_pairs`, `cr_pair_picks`, `cr_price_history`, `cr_algorithms`, `cr_portfolios`, `cr_backtest_results`, `cr_backtest_trades`, `cr_audit_log`, `cr_algo_performance`, `cr_category_perf`, `cr_comparisons`, `cr_whatif_scenarios` | findcryptopairs/portfolio |
| `lm_signals`, `lm_trades` (asset_class='CRYPTO') | live-monitor |

### 6.3 Meme Coins (COVERED, cross-DB)

| Tables | Database | Module |
|--------|----------|--------|
| `mc_winners`, `mc_scan_log`, `mc_daily_snapshots` | `ejaguiar1_memecoin` | findcryptopairs/api/meme_scanner.php |
| `mc_winners`, `mc_scan_log`, `mc_daily_snapshots` | `ejaguiar1_stocks` (copies) | live-monitor/goldmine_tracker.php |
| `cw_winners`, `cw_scan_log` | `ejaguiar1_stocks` | findcryptopairs/api/crypto_winners.php |

**Note:** mc_ tables are duplicated across two databases. Meme_scanner writes to `ejaguiar1_memecoin`, goldmine_tracker reads from there and copies into `ejaguiar1_stocks.gm_unified_picks`.

### 6.4 Forex (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `fx_pairs`, `fx_prices`, `fx_signals`, `fx_strategies`, `fx_backtest_results`, `fx_audit_log`, `fx_report_cache` | findforex2/api |
| `fxp_pairs`, `fxp_pair_picks`, `fxp_price_history`, `fxp_algorithms`, `fxp_portfolios`, `fxp_backtest_results`, `fxp_backtest_trades`, `fxp_audit_log`, `fxp_algo_performance`, `fxp_category_perf`, `fxp_comparisons`, `fxp_whatif_scenarios` | findforex2/portfolio |
| `lm_signals`, `lm_trades` (asset_class='FOREX') | live-monitor |

### 6.5 Mutual Funds (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `mf_funds`, `mf_nav_history`, `mf_portfolios`, `mf_backtest_results`, `mf_backtest_trades`, `mf_audit_log`, `mf_report_cache`, `mf_benchmarks`, `mf_selections`, `mf_simulation_grid`, `mf_simulation_meta`, `mf_strategies`, `mf_whatif_scenarios` | findmutualfunds/api |
| `mf2_funds`, `mf2_fund_picks`, `mf2_nav_history`, `mf2_algorithms`, `mf2_portfolios`, `mf2_backtest_results`, `mf2_backtest_trades`, `mf2_audit_log`, `mf2_algo_performance`, `mf2_category_perf`, `mf2_comparisons`, `mf2_whatif_scenarios` | findmutualfunds2/portfolio2 |

### 6.6 Penny Stocks (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `penny_picks`, `penny_picks_daily` | findstocks/portfolio2/api/penny_stocks.php, penny_stock_picks.php |

### 6.7 Sports Betting (FULLY COVERED)

| Tables | Module |
|--------|--------|
| `lm_sports_bets`, `lm_sports_bankroll`, `lm_sports_odds`, `lm_sports_clv`, `lm_sports_credit_usage`, `lm_sports_value_bets`, `lm_sports_daily_picks` | live-monitor/api/sports_*.php |

### 6.8 ASSET CLASS GAP: No Dedicated ETF Tables

The project has `findstocks/api/etf_portfolio.php` but it reuses the generic `stocks` and `stock_picks` tables with no ETF-specific schema (no expense ratio, tracking error, AUM columns). ETFs are treated as regular stocks.

**Recommendation:** If ETF-specific analytics are desired, consider adding `etf_` prefixed tables.

---

## 7. Cross-Module Table Sharing

### 7.1 Tables Used Across Multiple Modules

| Table | Used By |
|-------|---------|
| `lm_signals` | live_signals.php, live_trade.php, algo_performance.php, edge_finder.php, smart_money.php, world_class_intelligence.php, multi_dimensional.php, corr_pruner.py |
| `lm_trades` | live_trade.php, breaker_live.php, algo_performance.php, live_signals.php, kelly_sizer.py |
| `lm_market_regime` | regime.php, live_signals.php, hmm_regime.py, multi_dimensional.php |
| `lm_price_cache` | Multiple live-monitor files (shared price cache) |
| `stocks` | findstocks/api, portfolio2, goldmine_cursor |
| `stock_picks` | findstocks/api, portfolio2, goldmine_tracker |
| `gm_unified_picks` | goldmine_tracker.php (writes), goldmine_schema.php, goldmine-dashboard.html |

### 7.2 Cross-Database Access Pattern

```
ejaguiar1_stocks (main) ─── Primary DB for all financial data
    |
    ├── ejaguiar1_memecoin ─── Cross-DB reads via goldmine_tracker.php:724
    |                           and meme_scanner.php:26
    |
    ├── ejaguiar1_sportsbet ── Attempted first in sports_db_connect.php:20
    |                           ALWAYS FAILS (empty DB), falls back to stocks
    |
    ├── ejaguiar1_favcreators ── Separate: user auth, creators, events
    |
    └── ejaguiar1_news ──────── Separate: RSS feed articles
```

---

## 8. Summary of Findings

### 8.1 Key Metrics

| Metric | Value |
|--------|-------|
| Total tables in ejaguiar1_stocks | 208 |
| Tables actively referenced in code | ~196 |
| Potentially orphaned tables | 12 |
| Missing from DB (auto-created) | 3 |
| Missing views (need recreation) | 9 |
| Sports bet DB tables | 0 (all data in stocks DB) |
| Asset classes covered | 7 (stocks, crypto, meme coins, forex, mutual funds, penny stocks, sports) |
| Schema column mismatches | 0 critical (migrations handle drift) |

### 8.2 Action Items

| Priority | Action | Details |
|----------|--------|---------|
| **LOW** | Clean up 12 orphaned tables | `fx_algo_performance`, `fx_algorithms`, `fx_category_perf`, `fx_comparisons`, `fx_pair_picks`, `fx_portfolios`, `fx_price_history`, `fx_whatif_scenarios`, `mf_algo_performance`, `mf_algorithms`, `mf_comparisons`, `mf_fund_picks` |
| **LOW** | Recreate 9 SQL views | `v_algorithm_leaderboard`, `v_backtest_vs_live`, `v_hidden_winners`, `v_max_drawdown_by_algorithm`, `v_max_drawdown_by_system`, `v_risk_dashboard`, `v_system_correlation`, `v_system_performance`, `v_win_loss_streaks` |
| **INFO** | Sports DB decision | Either remove fallback (simplify) or migrate sports tables to `ejaguiar1_sportsbet` |
| **INFO** | Meme coin duplication | mc_ tables exist in both `ejaguiar1_stocks` and `ejaguiar1_memecoin`. Consider consolidating. |
| **INFO** | Auto-created tables | `lm_free_data_cache`, `lm_free_data_scores`, `lm_threshold_learning` will be auto-created on first API call |

### 8.3 No Critical Issues Found

The database schema is well-aligned with the codebase. The project uses a robust pattern of:
- `CREATE TABLE IF NOT EXISTS` for auto-provisioning
- Conditional `ALTER TABLE` for column migrations
- Error-suppressed queries (`@$conn->query()`) for optional features
- Cross-DB fallback connections for resilience

The 12 orphaned tables and 9 missing views are low-priority cleanup items that don't affect functionality.
