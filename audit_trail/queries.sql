-- ============================================================================
-- AUDIT TRAIL QUERY LIBRARY -- ejaguiar1_stocks
-- Generated: 2026-03-04
-- ============================================================================


-- ############################################################################
-- SECTION 1: PICK PERFORMANCE
-- Latest picks with realized P/L (closed) and unrealized P/L (open).
-- ############################################################################

-- 1a) at_raw_picks -- All picks with realized/unrealized P/L
-- Answers: What is the current P/L on every raw pick across all systems?
SELECT
    id,
    source_system,
    symbol,
    asset_class,
    direction,
    strategy,
    status,
    entry_price,
    take_profit,
    stop_loss,
    exit_price,
    signal_timestamp,
    CASE
        WHEN status IN ('WON', 'LOST', 'CLOSED') THEN pnl_pct
        ELSE NULL  -- open picks need live price; see note below
    END AS realized_pnl_pct,
    CASE
        WHEN status = 'OPEN' THEN CONCAT('OPEN -- needs live price comparison')
        ELSE CONCAT(status, ' @ ', COALESCE(exit_price, 'N/A'))
    END AS pnl_note,
    confidence
FROM at_raw_picks
ORDER BY signal_timestamp DESC;

-- 1b) consensus_tracked -- Consensus picks with live price tracking
-- Answers: How are consensus stock picks performing right now vs entry?
SELECT
    ticker,
    direction,
    entry_price,
    current_price,
    current_return_pct   AS unrealized_pnl_pct,
    status,
    final_return_pct     AS realized_pnl_pct,
    exit_reason,
    source_algos,
    peak_price,
    trough_price,
    CASE
        WHEN status = 'OPEN'
            THEN ROUND(
                (COALESCE(peak_price, current_price) - entry_price)
                / NULLIF(entry_price, 0) * 100, 2)
        ELSE NULL
    END AS peak_unrealized_pct
FROM consensus_tracked
ORDER BY
    CASE WHEN status = 'OPEN' THEN 0 ELSE 1 END,
    current_return_pct DESC;

-- 1c) tracked_portfolio_picks -- Portfolio picks with live prices
-- Answers: What is every portfolio pick's current standing?
SELECT
    ticker,
    algorithm,
    entry_price,
    current_price,
    current_return_pct   AS unrealized_pnl_pct,
    status,
    exit_price,
    exit_reason,
    CASE
        WHEN status = 'OPEN' AND current_price IS NOT NULL
            THEN ROUND(
                (current_price - entry_price)
                / NULLIF(entry_price, 0) * 100, 2)
        ELSE NULL
    END AS calc_unrealized_pct
FROM tracked_portfolio_picks
ORDER BY
    CASE WHEN status = 'OPEN' THEN 0 ELSE 1 END,
    current_return_pct DESC;


-- ############################################################################
-- SECTION 2: FORWARD-TEST vs BACKTEST SEPARATION
-- CRITICAL: Users must know which data is real production vs historical sim.
-- ############################################################################

/*
 +------------------------------------------------------------------------+
 |  FORWARD-TEST TABLES (real production data, live or recently tracked):  |
 |                                                                         |
 |    at_raw_picks           -- Audit trail raw picks (live scanner output) |
 |    at_consensus_picks     -- Consensus picks (live cross-system agree)   |
 |    at_discord_sent        -- Discord notifications actually sent         |
 |    consensus_tracked      -- Stock consensus with LIVE price tracking    |
 |    tracked_portfolio_picks-- Portfolio picks with LIVE price tracking    |
 |    stock_picks            -- Live stock picks from running algorithms    |
 |    alpha_picks            -- Live alpha factor picks                     |
 |    algorithm_performance  -- Aggregated stats from live picks            |
 |    algorithm_rolling_perf -- Rolling performance windows (live + bt)     |
 |                                                                         |
 |  BACKTEST TABLES (historical simulation, NOT real money/real signals):   |
 |                                                                         |
 |    bt_backtest_trades     -- Imported backtest trade records             |
 |    cr_backtest_results    -- Crypto backtest summary statistics          |
 |    cr_backtest_trades     -- Crypto backtest individual trades           |
 |    walk_forward_results   -- Walk-forward validation (IS + OOS splits)   |
 |                                                                         |
 |  NOTE: algorithm_rolling_perf spans both -- check source_table column   |
 |  to distinguish forward-test rows from backtest rows.                   |
 +------------------------------------------------------------------------+
*/


-- ############################################################################
-- SECTION 3: STATS BY DASHBOARD / STRATEGY
-- Performance sliced by source system (dashboard) and individual strategy.
-- ############################################################################

-- 3a) Performance by source_system (each source_system maps to a dashboard)
-- Answers: Which dashboard/system is producing the best results?
SELECT
    source_system,
    COUNT(*)                                              AS total_picks,
    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END)    AS open_picks,
    SUM(CASE WHEN status = 'WON'  THEN 1 ELSE 0 END)    AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END)    AS losses,
    SUM(CASE WHEN status IN ('EXPIRED','CLOSED') THEN 1 ELSE 0 END) AS other_closed,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
        * 100, 2
    )                                                     AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST','CLOSED') THEN pnl_pct END), 2)
                                                          AS avg_pnl_pct,
    ROUND(SUM(CASE WHEN status IN ('WON','LOST','CLOSED') THEN pnl_pct ELSE 0 END), 2)
                                                          AS total_pnl_pct
FROM at_raw_picks
GROUP BY source_system
ORDER BY win_rate_pct DESC;

-- 3b) Strategy drill-down within at_raw_picks
-- Answers: How does a specific strategy (e.g. autocorrelation_exploiter) perform?
SELECT
    strategy,
    source_system,
    COUNT(*)                                              AS total_picks,
    SUM(CASE WHEN status = 'WON'  THEN 1 ELSE 0 END)    AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END)    AS losses,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
        * 100, 2
    )                                                     AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST','CLOSED') THEN pnl_pct END), 2)
                                                          AS avg_pnl_pct,
    ROUND(MIN(CASE WHEN status = 'LOST' THEN pnl_pct END), 2)
                                                          AS worst_loss_pct,
    ROUND(MAX(CASE WHEN status = 'WON'  THEN pnl_pct END), 2)
                                                          AS best_win_pct
FROM at_raw_picks
GROUP BY strategy, source_system
ORDER BY total_picks DESC, win_rate_pct DESC;

-- 3c) Stock dashboard stats from stock_picks + algorithm_performance
-- Answers: Which stock algorithms have the best track record?
SELECT
    sp.algorithm_name,
    ap.strategy_type,
    COUNT(sp.ticker)        AS live_pick_count,
    ap.total_picks          AS historical_total_picks,
    ROUND(ap.win_rate, 2)   AS win_rate_pct,
    ROUND(ap.avg_return_pct, 2) AS avg_return_pct,
    ap.best_for,
    ap.worst_for,
    ROUND(AVG(sp.score), 2) AS avg_live_score,
    ROUND(AVG(sp.rating), 2) AS avg_live_rating
FROM stock_picks sp
LEFT JOIN algorithm_performance ap
    ON sp.algorithm_name = ap.algorithm_name
GROUP BY sp.algorithm_name, ap.strategy_type,
         ap.total_picks, ap.win_rate, ap.avg_return_pct,
         ap.best_for, ap.worst_for
ORDER BY ap.win_rate DESC, live_pick_count DESC;


-- ############################################################################
-- SECTION 4: SYSTEMS WITH 50+ FORWARD TESTS -- SCORECARD
-- The key query: only systems with enough data to trust.
-- ############################################################################

-- 4a) Strategy-level scorecard (50+ resolved forward-test picks)
-- Answers: Which strategies have statistically meaningful forward-test records?
SELECT
    strategy,
    source_system,
    COUNT(*)                                                          AS total_resolved,
    SUM(CASE WHEN status = 'WON'  THEN 1 ELSE 0 END)                AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END)                AS losses,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                                 AS win_rate_pct,
    ROUND(SUM(COALESCE(pnl_pct, 0)), 2)                              AS total_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0)
    , 2)                                                              AS profit_factor,
    ROUND(MIN(pnl_pct), 2)                                           AS worst_trade_pct,
    ROUND(AVG(CASE WHEN status = 'WON'  THEN pnl_pct END), 2)       AS avg_win_pct,
    ROUND(AVG(CASE WHEN status = 'LOST' THEN pnl_pct END), 2)       AS avg_loss_pct,
    ROUND(
        (SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))
        * AVG(CASE WHEN status = 'WON' THEN pnl_pct ELSE NULL END)
        +
        (SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))
        * AVG(CASE WHEN status = 'LOST' THEN pnl_pct ELSE NULL END)
    , 2)                                                              AS expectancy_pct
FROM at_raw_picks
WHERE status IN ('WON', 'LOST')
GROUP BY strategy, source_system
HAVING COUNT(*) >= 50
ORDER BY expectancy_pct DESC, profit_factor DESC;

-- 4b) System-level rollup (50+ resolved forward-test picks per system)
-- Answers: At the system level, which dashboards have proven forward-test results?
SELECT
    source_system,
    COUNT(*)                                                          AS total_resolved,
    SUM(CASE WHEN status = 'WON'  THEN 1 ELSE 0 END)                AS wins,
    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END)                AS losses,
    ROUND(
        SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                                 AS win_rate_pct,
    ROUND(SUM(COALESCE(pnl_pct, 0)), 2)                              AS total_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0)
    , 2)                                                              AS profit_factor,
    ROUND(MIN(pnl_pct), 2)                                           AS worst_trade_pct,
    ROUND(AVG(CASE WHEN status = 'WON'  THEN pnl_pct END), 2)       AS avg_win_pct,
    ROUND(AVG(CASE WHEN status = 'LOST' THEN pnl_pct END), 2)       AS avg_loss_pct,
    ROUND(
        (SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))
        * AVG(CASE WHEN status = 'WON' THEN pnl_pct ELSE NULL END)
        +
        (SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))
        * AVG(CASE WHEN status = 'LOST' THEN pnl_pct ELSE NULL END)
    , 2)                                                              AS expectancy_pct
FROM at_raw_picks
WHERE status IN ('WON', 'LOST')
GROUP BY source_system
HAVING COUNT(*) >= 50
ORDER BY expectancy_pct DESC, profit_factor DESC;


-- ############################################################################
-- SECTION 5: DISCORD SEND AUDIT
-- All picks sent to Discord plus send rate analytics.
-- ############################################################################

-- 5a) Full Discord send history
-- Answers: What picks were sent to Discord, when, and to which channel?
SELECT
    channel,
    symbol,
    asset_class,
    direction,
    entry_price,
    confidence,
    strategy,
    source_system,
    dedup_key,
    sent_at
FROM at_discord_sent
ORDER BY sent_at DESC;

-- 5b) Send rate by channel
-- Answers: How many picks does each Discord channel receive, and how often?
SELECT
    channel,
    COUNT(*)                                            AS total_sent,
    COUNT(DISTINCT DATE(sent_at))                       AS active_days,
    ROUND(
        COUNT(*)
        / NULLIF(COUNT(DISTINCT DATE(sent_at)), 0), 2
    )                                                   AS avg_picks_per_day,
    MIN(sent_at)                                        AS first_send,
    MAX(sent_at)                                        AS last_send,
    COUNT(DISTINCT symbol)                              AS unique_symbols,
    COUNT(DISTINCT source_system)                       AS source_systems_count
FROM at_discord_sent
GROUP BY channel
ORDER BY total_sent DESC;

-- 5c) Discord sends by asset class and direction
-- Answers: What is the distribution of Discord alerts by asset class?
SELECT
    channel,
    asset_class,
    direction,
    COUNT(*)                                            AS picks_sent,
    ROUND(AVG(confidence), 2)                           AS avg_confidence
FROM at_discord_sent
GROUP BY channel, asset_class, direction
ORDER BY channel, picks_sent DESC;


-- ############################################################################
-- SECTION 6: FORWARD vs BACKTEST COMPARISON
-- Join forward results against backtest results to see if backtests hold up.
-- ############################################################################

-- 6a) Forward vs backtest by strategy (at_raw_picks vs bt_backtest_trades)
-- Answers: Do backtest win rates match real forward-test performance?
SELECT
    fwd.strategy,
    fwd.source_system,
    fwd.fwd_total,
    fwd.fwd_win_rate_pct,
    fwd.fwd_avg_pnl_pct,
    bt.bt_total,
    bt.bt_win_rate_pct,
    bt.bt_avg_pnl_pct,
    ROUND(fwd.fwd_win_rate_pct - bt.bt_win_rate_pct, 2)  AS win_rate_decay_pct,
    ROUND(fwd.fwd_avg_pnl_pct - bt.bt_avg_pnl_pct, 2)   AS avg_pnl_decay_pct
FROM (
    SELECT
        strategy,
        source_system,
        COUNT(*)  AS fwd_total,
        ROUND(
            SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
            * 100, 2
        ) AS fwd_win_rate_pct,
        ROUND(AVG(CASE WHEN status IN ('WON','LOST','CLOSED') THEN pnl_pct END), 2)
          AS fwd_avg_pnl_pct
    FROM at_raw_picks
    WHERE status IN ('WON', 'LOST', 'CLOSED')
    GROUP BY strategy, source_system
) fwd
INNER JOIN (
    SELECT
        strategy,
        COUNT(*)  AS bt_total,
        ROUND(
            SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
            * 100, 2
        ) AS bt_win_rate_pct,
        ROUND(AVG(pnl_pct), 2) AS bt_avg_pnl_pct
    FROM bt_backtest_trades
    WHERE status IN ('WON', 'LOST')
    GROUP BY strategy
) bt ON fwd.strategy = bt.strategy
ORDER BY win_rate_decay_pct ASC;

-- 6b) Walk-forward validation: in-sample vs out-of-sample efficiency
-- Answers: Which strategies maintained their edge in walk-forward OOS tests?
SELECT
    algorithm_name,
    strategy_name,
    ROUND(is_win_rate, 2)       AS in_sample_win_rate,
    ROUND(oos_win_rate, 2)      AS out_of_sample_win_rate,
    ROUND(wf_efficiency, 2)     AS walk_forward_efficiency,
    ROUND(oos_profit_factor, 2) AS oos_profit_factor,
    oos_trades,
    CASE
        WHEN wf_efficiency >= 0.70 THEN 'ROBUST'
        WHEN wf_efficiency >= 0.50 THEN 'ACCEPTABLE'
        WHEN wf_efficiency >= 0.30 THEN 'MARGINAL'
        ELSE 'OVERFIT'
    END                         AS robustness_grade
FROM walk_forward_results
WHERE oos_trades >= 20
ORDER BY wf_efficiency DESC, oos_profit_factor DESC;

-- 6c) Crypto backtest summary stats
-- Answers: What are the aggregate crypto backtest performance benchmarks?
SELECT
    ROUND(win_rate, 2)          AS win_rate_pct,
    ROUND(sharpe_ratio, 2)      AS sharpe_ratio,
    ROUND(profit_factor, 2)     AS profit_factor,
    ROUND(max_drawdown_pct, 2)  AS max_drawdown_pct
FROM cr_backtest_results
ORDER BY sharpe_ratio DESC;


-- ############################################################################
-- SECTION 7: ROLLING ALGORITHM PERFORMANCE
-- Query algorithm_rolling_perf for latest rolling stats.
-- ############################################################################

-- 7a) Latest rolling performance per algorithm
-- Answers: What is the most recent rolling performance window for each algorithm?
SELECT
    rp.source_table,
    rp.algorithm_name,
    rp.period,
    rp.calc_date,
    rp.total_picks,
    rp.wins,
    rp.losses,
    ROUND(rp.win_rate, 2)        AS win_rate_pct,
    ROUND(rp.avg_return_pct, 2)  AS avg_return_pct,
    ROUND(rp.profit_factor, 2)   AS profit_factor
FROM algorithm_rolling_perf rp
INNER JOIN (
    SELECT source_table, algorithm_name, period, MAX(calc_date) AS max_date
    FROM algorithm_rolling_perf
    GROUP BY source_table, algorithm_name, period
) latest
    ON  rp.source_table   = latest.source_table
    AND rp.algorithm_name = latest.algorithm_name
    AND rp.period         = latest.period
    AND rp.calc_date      = latest.max_date
ORDER BY rp.source_table, rp.win_rate DESC;

-- 7b) Rolling performance trend (last 5 windows per algorithm)
-- Answers: Is each algorithm's performance improving or degrading over time?
SELECT
    source_table,
    algorithm_name,
    period,
    calc_date,
    total_picks,
    ROUND(win_rate, 2)        AS win_rate_pct,
    ROUND(avg_return_pct, 2)  AS avg_return_pct,
    ROUND(profit_factor, 2)   AS profit_factor
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY source_table, algorithm_name, period
            ORDER BY calc_date DESC
        ) AS rn
    FROM algorithm_rolling_perf
) ranked
WHERE rn <= 5
ORDER BY source_table, algorithm_name, period, calc_date DESC;

-- 7c) Forward-test vs backtest rolling comparison
-- Answers: Are forward-test rolling stats diverging from backtest rolling stats?
SELECT
    fwd.algorithm_name,
    fwd.period,
    fwd.calc_date                               AS fwd_calc_date,
    ROUND(fwd.win_rate, 2)                      AS fwd_win_rate_pct,
    ROUND(fwd.avg_return_pct, 2)                AS fwd_avg_return_pct,
    ROUND(fwd.profit_factor, 2)                 AS fwd_profit_factor,
    bt.calc_date                                AS bt_calc_date,
    ROUND(bt.win_rate, 2)                       AS bt_win_rate_pct,
    ROUND(bt.avg_return_pct, 2)                 AS bt_avg_return_pct,
    ROUND(bt.profit_factor, 2)                  AS bt_profit_factor,
    ROUND(fwd.win_rate - bt.win_rate, 2)        AS win_rate_gap,
    ROUND(fwd.profit_factor - bt.profit_factor, 2) AS pf_gap
FROM algorithm_rolling_perf fwd
INNER JOIN algorithm_rolling_perf bt
    ON  fwd.algorithm_name = bt.algorithm_name
    AND fwd.period         = bt.period
WHERE fwd.source_table LIKE '%raw_picks%'
  AND bt.source_table  LIKE '%backtest%'
  AND fwd.calc_date = (
      SELECT MAX(calc_date) FROM algorithm_rolling_perf
      WHERE source_table = fwd.source_table
        AND algorithm_name = fwd.algorithm_name
        AND period = fwd.period
  )
  AND bt.calc_date = (
      SELECT MAX(calc_date) FROM algorithm_rolling_perf
      WHERE source_table = bt.source_table
        AND algorithm_name = bt.algorithm_name
        AND period = bt.period
  )
ORDER BY win_rate_gap ASC;
