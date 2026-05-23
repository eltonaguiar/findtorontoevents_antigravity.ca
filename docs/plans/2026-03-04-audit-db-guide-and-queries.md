# Audit DB Guide & Performance Queries Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a comprehensive `ejaguiar1_stocks` database guide to AUDIT_BLUEPRINT.md with real queries for pick performance, strategy stats, forward-test vs backtest separation, and system-level scorecards.

**Architecture:** Update AUDIT_BLUEPRINT.md with a new "ejaguiar1_stocks Database Guide" section that maps every relevant table, clarifies forward-test vs backtest data, and provides copy-paste SQL queries for the user's key questions. Also create a `audit_trail/queries.sql` file with all queries for quick reference.

**Tech Stack:** MySQL 8.x (ejaguiar1_stocks on MariaDB), SQL queries

---

### Task 1: Create queries.sql with all performance queries

**Files:**
- Create: `audit_trail/queries.sql`

**Step 1: Write the queries file**

```sql
-- ============================================================
-- Audit Trail Query Library for ejaguiar1_stocks
-- ============================================================
-- Usage: Copy-paste individual queries into your MySQL client.
-- All queries are self-contained and can run independently.
-- ============================================================

-- ============================================================
-- SECTION 1: PICK PERFORMANCE (Realized + Unrealized P/L)
-- ============================================================

-- Q1: All latest picks with realized P/L (closed) or unrealized P/L (open)
-- NOTE: For open picks, current_return_pct is based on last price update.
--       For real-time unrealized P/L, compare entry_price to live market price.

-- 1a: From at_raw_picks (audit trail — all systems combined)
SELECT
    symbol,
    asset_class,
    direction,
    source_system,
    strategy,
    entry_price,
    CASE
        WHEN status IN ('WON','LOST','CLOSED','EXPIRED') THEN 'CLOSED'
        ELSE 'OPEN'
    END AS position_state,
    status,
    exit_price,
    pnl_pct AS realized_pnl_pct,
    -- For open picks: derive unrealized P/L from take_profit proximity
    CASE
        WHEN status = 'OPEN' AND entry_price > 0 THEN
            CONCAT('Entry: ', entry_price, ' | TP: ', COALESCE(take_profit,'N/A'), ' | SL: ', COALESCE(stop_loss,'N/A'))
        ELSE NULL
    END AS open_position_info,
    signal_timestamp,
    confidence
FROM at_raw_picks
WHERE entry_price > 0
ORDER BY signal_timestamp DESC
LIMIT 100;

-- 1b: From consensus_tracked (stock consensus picks with live price tracking)
SELECT
    ticker AS symbol,
    'EQUITY' AS asset_class,
    direction,
    source_algos AS strategies,
    entry_price,
    current_price,
    CASE
        WHEN status = 'open' THEN 'OPEN'
        ELSE 'CLOSED'
    END AS position_state,
    CASE
        WHEN status = 'open' THEN current_return_pct
        ELSE final_return_pct
    END AS pnl_pct,
    CASE
        WHEN status = 'open' THEN
            ROUND((current_price - entry_price) / entry_price * 100, 2)
        ELSE NULL
    END AS unrealized_pnl_pct,
    exit_reason,
    entry_date,
    exit_date,
    hold_days,
    peak_price,
    trough_price
FROM consensus_tracked
ORDER BY entry_date DESC;

-- 1c: From tracked_portfolio_picks (portfolio-tracked picks with live prices)
SELECT
    ticker AS symbol,
    algorithm AS strategy,
    entry_price,
    current_price,
    status,
    current_return_pct,
    CASE
        WHEN status = 'active' THEN
            ROUND((current_price - entry_price) / entry_price * 100, 2)
        ELSE NULL
    END AS unrealized_pnl_pct,
    CASE
        WHEN status != 'active' THEN
            ROUND((exit_price - entry_price) / entry_price * 100, 2)
        ELSE NULL
    END AS realized_pnl_pct,
    exit_reason,
    entry_date,
    exit_date,
    days_held
FROM tracked_portfolio_picks
ORDER BY entry_date DESC;


-- ============================================================
-- SECTION 2: FORWARD-TEST vs BACKTEST SEPARATION
-- ============================================================
-- IMPORTANT: Forward-test data = REAL picks generated in production.
-- Backtest data = historical simulation, NOT real predictions.
--
-- FORWARD-TEST tables (real production data):
--   at_raw_picks            — picks from live aggregator runs
--   at_consensus_picks      — consensus picks sent to Discord
--   consensus_tracked       — stock consensus with live tracking
--   tracked_portfolio_picks — portfolio picks with live prices
--   stock_picks             — live stock algorithm picks
--   alpha_picks             — live alpha factor picks
--   crypto_signals          — live crypto signals
--   fx_signals              — live forex signals
--   penny_picks             — live penny stock picks
--   KIMI_GOLDMINE_PICKS     — live KIMI goldmine picks
--   gm_unified_picks        — unified goldmine picks
--   lm_signals              — live market signals
--   meme_signals            — live meme coin signals
--
-- BACKTEST tables (historical simulation):
--   cr_backtest_results     — crypto backtest summaries
--   cr_backtest_trades      — crypto backtest individual trades
--   fx_backtest_results     — forex backtest summaries
--   fx_backtest_trades      — forex backtest trades
--   fxp_backtest_results    — forex pro backtest summaries
--   fxp_backtest_trades     — forex pro backtest trades
--   mf_backtest_results     — mutual fund backtest summaries
--   mf_backtest_trades      — mutual fund backtest trades
--   mf2_backtest_results    — mutual fund v2 backtest summaries
--   mf2_backtest_trades     — mutual fund v2 backtest trades
--   bt_backtest_trades      — imported SQLite backtest trades (our new table)
--   bt_backtest_runs        — imported SQLite backtest summaries (our new table)
--   backtest_trades         — general backtest trades
--   walk_forward_results    — walk-forward validation results
--   walk_forward_summary    — walk-forward summaries


-- ============================================================
-- SECTION 3: STATS BY DASHBOARD / WEBPAGE / STRATEGY
-- ============================================================

-- Q3a: Alpha Engine dashboard (findtorontoevents.ca/alpha/) — strategy performance
-- This queries at_raw_picks for the alpha_engine source system
SELECT
    strategy,
    asset_class,
    COUNT(*) AS total_picks,
    SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS still_open,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
    , 1) AS win_rate_pct,
    ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) AS avg_pnl_pct,
    ROUND(SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END), 2) AS total_pnl_pct,
    ROUND(
        SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END), 0)
    , 2) AS profit_factor
FROM at_raw_picks
WHERE source_system = 'alpha_engine'
  AND status IN ('WON', 'LOST', 'OPEN')
GROUP BY strategy, asset_class
ORDER BY total_picks DESC;

-- Q3b: Specific strategy deep-dive (e.g. autocorrelation_exploiter)
SELECT
    symbol,
    direction,
    entry_price,
    take_profit,
    stop_loss,
    confidence,
    status,
    exit_price,
    pnl_pct,
    signal_timestamp
FROM at_raw_picks
WHERE source_system = 'alpha_engine'
  AND strategy = 'autocorrelation_exploiter'
ORDER BY signal_timestamp DESC;

-- Q3c: Stats by dashboard/source system (all dashboards combined)
SELECT
    source_system AS dashboard,
    COUNT(*) AS total_forward_picks,
    SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_picks,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
    , 1) AS win_rate_pct,
    ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) AS avg_pnl_pct,
    ROUND(SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END), 2) AS cumulative_pnl_pct,
    ROUND(
        SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END), 0)
    , 2) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'OPEN')
GROUP BY source_system
ORDER BY total_forward_picks DESC;

-- Q3d: Stock dashboard (findtorontoevents.ca/investments/)
-- Uses the existing stock_picks + algorithm_performance tables
SELECT
    sp.algorithm_name,
    COUNT(*) AS total_picks,
    ap.win_rate,
    ap.avg_return_pct,
    ap.best_for,
    ap.worst_for,
    ap.updated_at
FROM stock_picks sp
LEFT JOIN algorithm_performance ap
    ON sp.algorithm_name = ap.algorithm_name
GROUP BY sp.algorithm_name
ORDER BY COUNT(*) DESC;


-- ============================================================
-- SECTION 4: SYSTEMS WITH 50+ FORWARD TESTS — SCORECARD
-- ============================================================

-- Q4a: Systems with 50+ forward-tested picks — full scorecard
-- This is the KEY query: which systems have enough data to trust?
SELECT
    source_system,
    strategy,
    asset_class,
    COUNT(*) AS total_picks,
    SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END) AS resolved,
    SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_now,

    -- Win Rate
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
    , 1) AS win_rate_pct,

    -- P/L
    ROUND(SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END), 2) AS total_pnl_pct,
    ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) AS avg_pnl_pct,

    -- Profit Factor = gross wins / gross losses
    ROUND(
        SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END), 0)
    , 2) AS profit_factor,

    -- Max Drawdown approximation (worst single trade)
    ROUND(MIN(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) AS worst_trade_pnl_pct,

    -- Avg Win / Avg Loss
    ROUND(AVG(CASE WHEN status='WON' THEN pnl_pct END), 2) AS avg_win_pct,
    ROUND(AVG(CASE WHEN status='LOST' THEN pnl_pct END), 2) AS avg_loss_pct,

    -- Expectancy = (WR * AvgWin) - ((1-WR) * |AvgLoss|)
    ROUND(
        (SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) * 1.0 /
         NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0))
        * AVG(CASE WHEN status='WON' THEN pnl_pct END)
        -
        (1 - SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) * 1.0 /
         NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0))
        * ABS(AVG(CASE WHEN status='LOST' THEN pnl_pct END))
    , 2) AS expectancy_pct

FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'OPEN')
  AND entry_price > 0
GROUP BY source_system, strategy, asset_class
HAVING total_picks >= 50
ORDER BY total_pnl_pct DESC;

-- Q4b: System-level scorecard (grouped by source_system only)
SELECT
    source_system,
    COUNT(*) AS total_picks,
    SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END) AS resolved,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
    , 1) AS win_rate_pct,
    ROUND(SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END), 2) AS total_pnl_pct,
    ROUND(
        SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END), 0)
    , 2) AS profit_factor,
    ROUND(MIN(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) AS max_single_loss_pct
FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'OPEN')
GROUP BY source_system
HAVING total_picks >= 50
ORDER BY total_pnl_pct DESC;

-- Q4c: Walk-forward validation results (shows if backtest holds out-of-sample)
SELECT
    algorithm_name,
    strategy_name,
    source_table,
    COUNT(*) AS folds,
    ROUND(AVG(is_win_rate), 1) AS avg_in_sample_wr,
    ROUND(AVG(oos_win_rate), 1) AS avg_out_of_sample_wr,
    ROUND(AVG(wf_efficiency), 2) AS walk_forward_efficiency,
    ROUND(AVG(oos_profit_factor), 2) AS avg_oos_profit_factor,
    SUM(oos_trades) AS total_oos_trades
FROM walk_forward_results
GROUP BY algorithm_name, strategy_name, source_table
HAVING total_oos_trades >= 20
ORDER BY avg_oos_profit_factor DESC;


-- ============================================================
-- SECTION 5: DISCORD SEND AUDIT
-- ============================================================

-- Q5a: All picks sent to Discord (from at_discord_sent)
SELECT
    channel,
    symbol,
    asset_class,
    direction,
    entry_price,
    confidence,
    strategy,
    source_system,
    sent_at
FROM at_discord_sent
ORDER BY sent_at DESC
LIMIT 50;

-- Q5b: Discord send rate by channel
SELECT
    channel,
    COUNT(*) AS total_sent,
    COUNT(DISTINCT symbol) AS unique_symbols,
    MIN(sent_at) AS first_send,
    MAX(sent_at) AS last_send
FROM at_discord_sent
GROUP BY channel;


-- ============================================================
-- SECTION 6: BACKTEST vs FORWARD COMPARISON
-- ============================================================

-- Q6: Compare backtest performance to forward-test performance
-- for strategies that have BOTH backtest and forward data
SELECT
    fw.strategy,
    fw.asset_class,
    fw.forward_picks,
    fw.forward_wr,
    fw.forward_avg_pnl,
    fw.forward_pf,
    bt.backtest_trades,
    bt.backtest_avg_pnl
FROM (
    -- Forward-test stats
    SELECT strategy, asset_class,
        COUNT(*) AS forward_picks,
        ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)*100.0/
              NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END),0),1) AS forward_wr,
        ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END),2) AS forward_avg_pnl,
        ROUND(SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END)/
              NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END),0),2) AS forward_pf
    FROM at_raw_picks
    WHERE status IN ('WON','LOST')
    GROUP BY strategy, asset_class
) fw
LEFT JOIN (
    -- Backtest stats
    SELECT strategy,
        COUNT(*) AS backtest_trades,
        ROUND(AVG(pnl_pct),2) AS backtest_avg_pnl
    FROM bt_backtest_trades
    WHERE pnl_pct IS NOT NULL
    GROUP BY strategy
) bt ON fw.strategy = bt.strategy
WHERE fw.forward_picks >= 5
ORDER BY fw.forward_picks DESC;


-- ============================================================
-- SECTION 7: ROLLING ALGORITHM PERFORMANCE (existing tables)
-- ============================================================

-- Q7: Latest rolling performance from algorithm_rolling_perf
SELECT
    source_table,
    algorithm_name,
    period,
    total_picks,
    resolved_picks,
    wins,
    losses,
    win_rate,
    avg_return_pct,
    profit_factor,
    calc_date
FROM algorithm_rolling_perf
WHERE calc_date = (SELECT MAX(calc_date) FROM algorithm_rolling_perf)
ORDER BY profit_factor DESC;
```

**Step 2: Verify the file is valid SQL**

Run: `py -c "open('audit_trail/queries.sql').read(); print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add audit_trail/queries.sql
git commit -m "feat: add SQL query library for audit trail performance analysis"
```

---

### Task 2: Update AUDIT_BLUEPRINT.md with ejaguiar1_stocks Database Guide

**Files:**
- Modify: `AUDIT_BLUEPRINT.md` (append new sections)

**Step 1: Add the database guide section**

Append the following sections to AUDIT_BLUEPRINT.md after the existing "Future Phases" section:

```markdown
---

## ejaguiar1_stocks Database Guide

### Overview

`ejaguiar1_stocks` is the production MySQL database (MariaDB 8.4.7) with **280+ tables** covering stocks, crypto, forex, penny stocks, memecoins, and sports betting. Despite the name, it tracks ALL asset classes.

### Forward-Test vs Backtest Data

> **CRITICAL DISTINCTION:** Forward-test data = real production picks generated by live algorithms. Backtest data = historical simulation on past prices. Always check which table you're querying.

#### Forward-Test Tables (REAL picks, trust these)

| Table | Asset Class | Description | Rows |
|-------|------------|-------------|------|
| `at_raw_picks` | ALL | Audit trail — every pick from every system | 3,793+ |
| `at_consensus_picks` | ALL | Multi-system consensus picks | growing |
| `consensus_tracked` | EQUITY | Stock consensus with live price tracking | 138 |
| `tracked_portfolio_picks` | EQUITY | Portfolio picks with live prices | varies |
| `stock_picks` | EQUITY | Live stock algorithm picks | 3,988 |
| `alpha_picks` | EQUITY | Alpha factor model picks | 1,708 |
| `crypto_signals` | CRYPTO | Live crypto signals | growing |
| `fx_signals` | FOREX | Live forex signals | growing |
| `penny_picks` | PENNY_STOCK | Live penny stock picks | varies |
| `KIMI_GOLDMINE_PICKS` | ALL | KIMI goldmine picks | varies |
| `gm_unified_picks` | ALL | Unified goldmine picks | varies |
| `lm_signals` | ALL | Live market signals | varies |
| `meme_signals` | MEMECOIN | Live meme coin signals | varies |

#### Backtest Tables (SIMULATION, use for research only)

| Table | Asset Class | Description |
|-------|------------|-------------|
| `cr_backtest_results` | CRYPTO | Crypto backtest run summaries |
| `cr_backtest_trades` | CRYPTO | Individual crypto backtest trades |
| `fx_backtest_results` / `fx_backtest_trades` | FOREX | Forex backtests |
| `fxp_backtest_results` / `fxp_backtest_trades` | FOREX | Forex Pro backtests |
| `mf_backtest_results` / `mf_backtest_trades` | EQUITY | Mutual fund backtests |
| `mf2_backtest_results` / `mf2_backtest_trades` | EQUITY | Mutual fund v2 backtests |
| `bt_backtest_trades` / `bt_backtest_runs` | ALL | Imported SQLite backtests (new) |
| `backtest_trades` | EQUITY | General stock backtests |
| `walk_forward_results` / `walk_forward_summary` | ALL | Walk-forward validation |

#### Performance & Analytics Tables

| Table | Purpose |
|-------|---------|
| `algorithm_performance` | Algorithm win rates and returns (23 algos) |
| `algorithm_rolling_perf` | Rolling 7d/30d/90d performance by algorithm (1,348 snapshots) |
| `consensus_performance_daily` | Daily consensus portfolio P&L tracking |
| `consensus_lessons` | Lessons learned from closed positions |
| `at_strategy_stats` | Audit trail strategy-level stats (new) |
| `at_discord_sent` | Discord notification history (new) |

### Dashboard → Table Mapping

| Dashboard URL | Primary Tables | Asset Classes |
|---------------|---------------|---------------|
| `/alpha/` | `at_raw_picks` (source=alpha_engine), `alpha_picks` | CRYPTO, FOREX, EQUITY |
| `/investments/` | `stock_picks`, `algorithm_performance`, `consensus_tracked` | EQUITY |
| `/investments/penny-stocks.html` | `penny_picks`, `penny_picks_daily` | PENNY_STOCK |
| `riseoftheclaw.html` (KIMI) | `KIMI_GOLDMINE_PICKS`, `KIMI_GOLDMINE_PERFORMANCE` | CRYPTO |
| `/monitor/` (cross-aggregator) | `at_consensus_picks`, `at_discord_sent` | ALL |
| Mercury2 | `at_raw_picks` (source=mercury2) | CRYPTO |
| Battleground | `at_raw_picks` (source=battleground) | CRYPTO |

### Key Queries

All queries are in `audit_trail/queries.sql`. Quick reference:

#### Latest picks with P/L

```sql
-- Open picks (unrealized P/L — needs live price comparison)
SELECT symbol, direction, entry_price, take_profit, stop_loss,
       confidence, strategy, signal_timestamp
FROM at_raw_picks
WHERE status = 'OPEN' AND source_system = 'alpha_engine'
ORDER BY signal_timestamp DESC;

-- Closed picks (realized P/L)
SELECT symbol, direction, entry_price, exit_price, pnl_pct,
       status, strategy, signal_timestamp
FROM at_raw_picks
WHERE status IN ('WON','LOST') AND source_system = 'alpha_engine'
ORDER BY signal_timestamp DESC;
```

> **Note on unrealized P/L:** The `at_raw_picks` table stores entry prices but not current prices. For open picks, compare `entry_price` against live market data. The `consensus_tracked` and `tracked_portfolio_picks` tables DO track `current_price` and `current_return_pct` for stock picks.

#### Strategy performance for a specific dashboard

```sql
-- Example: Alpha Engine autocorrelation_exploiter (10 forward-tested picks)
SELECT strategy,
    COUNT(*) AS picks,
    SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) AS wins,
    ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)*100.0/
          NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END),0),1) AS wr,
    ROUND(AVG(pnl_pct),2) AS avg_pnl,
    ROUND(SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END)/
          NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END),0),2) AS pf
FROM at_raw_picks
WHERE source_system = 'alpha_engine' AND strategy = 'autocorrelation_exploiter'
GROUP BY strategy;
```

#### Systems with 50+ forward tests — full scorecard

```sql
SELECT source_system, strategy,
    COUNT(*) AS picks,
    ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)*100.0/
          NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END),0),1) AS win_rate,
    ROUND(SUM(pnl_pct),2) AS total_pnl,
    ROUND(SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END)/
          NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END),0),2) AS profit_factor,
    ROUND(MIN(pnl_pct),2) AS max_loss
FROM at_raw_picks
WHERE status IN ('WON','LOST','OPEN') AND entry_price > 0
GROUP BY source_system, strategy
HAVING picks >= 50
ORDER BY total_pnl DESC;
```

#### Forward vs backtest comparison

```sql
-- Do backtest results hold up in forward testing?
SELECT fw.strategy, fw.forward_picks, fw.forward_wr,
       bt.backtest_trades, bt.backtest_avg_pnl
FROM (
    SELECT strategy, COUNT(*) AS forward_picks,
        ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)*100.0/
              NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END),0),1) AS forward_wr
    FROM at_raw_picks WHERE status IN ('WON','LOST')
    GROUP BY strategy
) fw
LEFT JOIN (
    SELECT strategy, COUNT(*) AS backtest_trades,
           ROUND(AVG(pnl_pct),2) AS backtest_avg_pnl
    FROM bt_backtest_trades WHERE pnl_pct IS NOT NULL
    GROUP BY strategy
) bt ON fw.strategy = bt.strategy
WHERE fw.forward_picks >= 5
ORDER BY fw.forward_picks DESC;
```

### Forward-Test Data Summary (as of 2026-03-04)

| Source System | Forward Picks | Top Strategies |
|---------------|---------------|----------------|
| alpha_engine | 188 closed + 29 open | variance_ratio_momentum (11), hurst_regime_adaptive (11), autocorrelation_exploiter (10) |
| battleground | 180 closed | Various ensemble strategies |
| mercury2 | 46 closed + 2 open | Mercury2 ensemble signals |
| ml_clawsofdoom | 31 closed | Claws of Doom system |
| ml_predictor | 34 closed | ML crypto predictor |
| stock_picks (MySQL) | 3,988 | Technical Momentum, Blue Chip Growth, Cursor Genius |
| consensus_tracked | 138 | Multi-algo consensus |
```

**Step 2: Verify the AUDIT_BLUEPRINT.md is valid**

Run: `py -c "open('AUDIT_BLUEPRINT.md').read(); print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add AUDIT_BLUEPRINT.md
git commit -m "docs: add ejaguiar1_stocks database guide with performance queries"
```

---

### Task 3: Commit queries.sql + updated AUDIT_BLUEPRINT.md together

**Step 1: Run final verification**

Run: `wc -l audit_trail/queries.sql AUDIT_BLUEPRINT.md`
Expected: Both files exist with substantial content

**Step 2: Commit both files**

```bash
git add audit_trail/queries.sql AUDIT_BLUEPRINT.md
git commit -m "docs: add ejaguiar1_stocks database guide + SQL query library

- queries.sql: 7 sections covering pick P/L, forward vs backtest,
  strategy stats by dashboard, 50+ picks scorecards, Discord audit,
  forward vs backtest comparison, rolling performance
- AUDIT_BLUEPRINT.md: full database guide with table map, dashboard
  mapping, forward vs backtest separation, and key query examples"
```
