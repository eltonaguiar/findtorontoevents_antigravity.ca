-- TOP 10: Asset-Class Performance Queries (Schema-Compatible)
-- DB: ejaguiar1_stocks
-- Notes:
--  - at_raw_picks / at_consensus_picks status enums: OPEN, WON, LOST, EXPIRED, CLOSED
--  - at_signal_outcomes may not exist in all environments (query 4 marked optional)

-- Q1: Asset Class Overview (Win Rate, PF, Expectancy)
SELECT
    COALESCE(asset_class, 'UNKNOWN') AS asset_class,
    COUNT(*) AS total_picks,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0),
        2
    ) AS win_rate_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct
FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
  AND pnl_pct IS NOT NULL
GROUP BY COALESCE(asset_class, 'UNKNOWN')
ORDER BY profit_factor DESC;

-- Q2: Strategy Laggards (Worst Performers)
SELECT
    COALESCE(asset_class, 'UNKNOWN') AS asset_class,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    COUNT(*) AS total_picks,
    ROUND(SUM(CASE WHEN status IN ('WON','LOST') THEN pnl_pct ELSE 0 END), 4) AS total_pnl,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
GROUP BY COALESCE(asset_class, 'UNKNOWN'), COALESCE(strategy, 'UNKNOWN')
HAVING COUNT(*) >= 10 AND profit_factor < 1.0
ORDER BY total_pnl ASC
LIMIT 20;

-- Q3: Consensus Agreement Impact
SELECT
    COALESCE(ac.asset_class, 'UNKNOWN') AS asset_class,
    COALESCE(ac.consensus_tier, 'UNKNOWN') AS consensus_tier,
    COUNT(*) AS total_picks,
    ROUND(
        100.0 * SUM(CASE WHEN ac.status = 'WON' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN ac.status IN ('WON','LOST') THEN 1 ELSE 0 END), 0),
        2
    ) AS win_rate_pct,
    ROUND(AVG(CASE WHEN ac.status IN ('WON','LOST') THEN ac.pnl_pct END), 4) AS avg_pnl_pct
FROM at_consensus_picks ac
WHERE ac.status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
GROUP BY COALESCE(ac.asset_class, 'UNKNOWN'), COALESCE(ac.consensus_tier, 'UNKNOWN')
ORDER BY asset_class, consensus_tier;

-- Q4: TP/SL Geometry Analysis (OPTIONAL - requires at_signal_outcomes)
-- SELECT
--     COALESCE(asset_class, 'UNKNOWN') AS asset_class,
--     ROUND(AVG(ABS(take_profit - entry_price) / NULLIF(ABS(stop_loss - entry_price), 0)), 4) AS avg_risk_reward,
--     SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) AS tp_hits,
--     SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) AS sl_hits,
--     ROUND(
--         100.0 * SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) /
--         NULLIF(SUM(CASE WHEN exit_reason IN ('TP_HIT', 'SL_HIT') THEN 1 ELSE 0 END), 0),
--         2
--     ) AS tp_hit_rate_pct
-- FROM at_signal_outcomes
-- WHERE status IN ('WON', 'LOST')
-- GROUP BY COALESCE(asset_class, 'UNKNOWN')
-- ORDER BY tp_hit_rate_pct DESC;

-- Q5: Strategy Winners by asset class
SELECT
    COALESCE(asset_class, 'UNKNOWN') AS asset_class,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    COUNT(*) AS total_picks,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
GROUP BY COALESCE(asset_class, 'UNKNOWN'), COALESCE(strategy, 'UNKNOWN')
HAVING COUNT(*) >= 10 AND profit_factor >= 1.2
ORDER BY profit_factor DESC
LIMIT 20;

-- Q6: Filter reasons by asset class (selection bias)
SELECT
    COALESCE(asset_class, 'UNKNOWN') AS asset_class,
    filter_reason,
    COUNT(*) AS filtered_count
FROM at_filter_log
WHERE created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY COALESCE(asset_class, 'UNKNOWN'), filter_reason
ORDER BY asset_class, filtered_count DESC;

-- Q7: Backtest vs forward drift (asset class)
SELECT
    b.asset_class,
    ROUND(AVG(b.pnl_pct), 4) AS bt_avg_pnl,
    ROUND(AVG(f.pnl_pct), 4) AS fwd_avg_pnl,
    ROUND(AVG(f.pnl_pct) - AVG(b.pnl_pct), 4) AS pnl_drift
FROM bt_backtest_trades b
JOIN at_raw_picks f
  ON f.symbol = b.symbol
 AND COALESCE(f.strategy, '') = COALESCE(b.strategy, '')
 AND DATE(f.recorded_at) BETWEEN DATE(b.entry_time) AND DATE_ADD(DATE(b.entry_time), INTERVAL 7 DAY)
WHERE b.status IN ('WON','LOST')
  AND f.status IN ('WON','LOST')
GROUP BY b.asset_class
ORDER BY pnl_drift ASC;

-- Q8: Source system performance
SELECT
    source_system,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY source_system, asset_class
HAVING COUNT(*) >= 20
ORDER BY avg_pnl_pct DESC;

-- Q9: Monthly trend by asset class
SELECT
    DATE_FORMAT(recorded_at, '%Y-%m') AS ym,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct
FROM at_raw_picks
GROUP BY DATE_FORMAT(recorded_at, '%Y-%m'), asset_class
ORDER BY ym DESC, asset_class;

-- Q10: Open-risk backlog by asset class
SELECT
    asset_class,
    COUNT(*) AS open_count,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, recorded_at, NOW())), 2) AS avg_hours_open,
    MAX(TIMESTAMPDIFF(HOUR, recorded_at, NOW())) AS max_hours_open
FROM at_raw_picks
WHERE status = 'OPEN'
GROUP BY asset_class
ORDER BY open_count DESC, max_hours_open DESC;

