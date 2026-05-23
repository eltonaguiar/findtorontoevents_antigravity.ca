-- Asset-Class Performance Analysis Pack
-- =====================================
-- Scope: ejaguiar1_stocks audit-trail schema
-- Core tables used:
--   at_raw_picks, at_consensus_picks, at_filter_log, bt_backtest_trades, at_strategy_stats
-- Optional tables (if present in live DB):
--   trading_picks, at_signal_outcomes, at_strategy_symbol_performance

-- ---------------------------------------------------------------------------
-- Q1. Asset class overview (forward picks): win rate, PF, expectancy
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    COUNT(*) AS total_picks,
    SUM(status = 'WON') AS wins,
    SUM(status = 'LOST') AS losses,
    ROUND(
        100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0),
        2
    ) AS win_rate_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS expectancy_pct,
    SUM(status = 'OPEN') AS still_open
FROM at_raw_picks
GROUP BY asset_class
ORDER BY profit_factor DESC, expectancy_pct DESC;

-- ---------------------------------------------------------------------------
-- Q2. Asset class x strategy matrix (forward picks)
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    COUNT(*) AS total_picks,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY asset_class, COALESCE(strategy, 'UNKNOWN')
HAVING COUNT(*) >= 10
ORDER BY asset_class, profit_factor DESC, total_picks DESC;

-- ---------------------------------------------------------------------------
-- Q3. Source-system quality by asset class
-- ---------------------------------------------------------------------------
SELECT
    source_system,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY source_system, asset_class
HAVING COUNT(*) >= 20
ORDER BY profit_factor DESC;

-- ---------------------------------------------------------------------------
-- Q4. Consensus tier impact by asset class
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    COALESCE(consensus_tier, 'UNKNOWN') AS consensus_tier,
    COUNT(*) AS total_picks,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct
FROM at_consensus_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY asset_class, COALESCE(consensus_tier, 'UNKNOWN')
ORDER BY asset_class, consensus_tier;

-- ---------------------------------------------------------------------------
-- Q5. Agreement-count effect (does higher agreement help?)
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    agreement_count,
    COUNT(*) AS total_picks,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct
FROM at_consensus_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY asset_class, agreement_count
ORDER BY asset_class, agreement_count;

-- ---------------------------------------------------------------------------
-- Q6. Trade geometry sanity (forward): average RR and invalid geometry count
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    COUNT(*) AS total_closed,
    ROUND(AVG(risk_reward), 4) AS avg_risk_reward,
    SUM(
        CASE
            WHEN direction = 'LONG'
                 AND (take_profit <= entry_price OR stop_loss >= entry_price)
            THEN 1
            WHEN direction = 'SHORT'
                 AND (take_profit >= entry_price OR stop_loss <= entry_price)
            THEN 1
            ELSE 0
        END
    ) AS invalid_geometry_rows
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY asset_class
ORDER BY invalid_geometry_rows DESC, avg_risk_reward ASC;

-- ---------------------------------------------------------------------------
-- Q7. Strategy laggards (min sample, PF < 1)
-- ---------------------------------------------------------------------------
SELECT
    source_system,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(SUM(CASE WHEN status IN ('WON','LOST') THEN pnl_pct ELSE 0 END), 4) AS total_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY source_system, COALESCE(strategy, 'UNKNOWN'), asset_class
HAVING COUNT(*) >= 20 AND profit_factor < 1.0
ORDER BY total_pnl_pct ASC
LIMIT 50;

-- ---------------------------------------------------------------------------
-- Q8. Strategy winners (min sample, PF > 1.2)
-- ---------------------------------------------------------------------------
SELECT
    source_system,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct,
    ROUND(
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
        4
    ) AS profit_factor
FROM at_raw_picks
WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
GROUP BY source_system, COALESCE(strategy, 'UNKNOWN'), asset_class
HAVING COUNT(*) >= 20 AND profit_factor > 1.2
ORDER BY profit_factor DESC
LIMIT 50;

-- ---------------------------------------------------------------------------
-- Q9. Filter rejection analysis (selection bias by asset class)
-- ---------------------------------------------------------------------------
SELECT
    filter_reason,
    asset_class,
    COUNT(*) AS rejected_count,
    COUNT(DISTINCT source_system) AS source_count,
    MAX(created_at) AS last_seen_at
FROM at_filter_log
GROUP BY filter_reason, asset_class
ORDER BY rejected_count DESC
LIMIT 100;

-- ---------------------------------------------------------------------------
-- Q10. Backtest vs forward drift by asset class
-- ---------------------------------------------------------------------------
SELECT
    b.asset_class,
    ROUND(100.0 * SUM(b.status = 'WON') / NULLIF(SUM(b.status IN ('WON','LOST')), 0), 2) AS bt_wr_pct,
    ROUND(AVG(CASE WHEN b.status IN ('WON','LOST') THEN b.pnl_pct END), 4) AS bt_avg_pnl_pct,
    ROUND(f.fwd_wr_pct, 2) AS fwd_wr_pct,
    ROUND(f.fwd_avg_pnl_pct, 4) AS fwd_avg_pnl_pct,
    ROUND(f.fwd_wr_pct - (100.0 * SUM(b.status = 'WON') / NULLIF(SUM(b.status IN ('WON','LOST')), 0)), 2) AS wr_decay_pct
FROM bt_backtest_trades b
JOIN (
    SELECT
        asset_class,
        100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0) AS fwd_wr_pct,
        AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END) AS fwd_avg_pnl_pct
    FROM at_raw_picks
    GROUP BY asset_class
) f
    ON f.asset_class = b.asset_class
WHERE b.status IN ('WON','LOST')
GROUP BY b.asset_class, f.fwd_wr_pct, f.fwd_avg_pnl_pct
ORDER BY wr_decay_pct ASC;

-- ---------------------------------------------------------------------------
-- Q11. Time trend by month and asset class
-- ---------------------------------------------------------------------------
SELECT
    DATE_FORMAT(recorded_at, '%Y-%m') AS ym,
    asset_class,
    COUNT(*) AS total_picks,
    ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS avg_pnl_pct,
    ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct
FROM at_raw_picks
GROUP BY DATE_FORMAT(recorded_at, '%Y-%m'), asset_class
ORDER BY ym DESC, asset_class;

-- ---------------------------------------------------------------------------
-- Q12. Open-position backlog (age risk by asset class)
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    COUNT(*) AS open_count,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, recorded_at, NOW())), 2) AS avg_hours_open,
    MAX(TIMESTAMPDIFF(HOUR, recorded_at, NOW())) AS max_hours_open
FROM at_raw_picks
WHERE status = 'OPEN'
GROUP BY asset_class
ORDER BY open_count DESC, max_hours_open DESC;

-- ---------------------------------------------------------------------------
-- Q13. Optional: trading_picks status quality (if table exists in live DB)
-- ---------------------------------------------------------------------------
-- SELECT
--     COALESCE(category, 'UNKNOWN') AS category,
--     COUNT(*) AS total_terminal,
--     SUM(status IN ('WON','LOST','EXPIRED')) AS canonical_terminal,
--     SUM(status = 'CLOSED') AS closed_ambiguous,
--     SUM((exit_price IS NULL OR exit_price = 0) AND status IN ('WON','LOST','EXPIRED','CLOSED')) AS missing_exit_price
-- FROM trading_picks
-- WHERE status NOT IN ('OPEN','ACTIVE')
-- GROUP BY COALESCE(category, 'UNKNOWN')
-- ORDER BY missing_exit_price DESC;

-- ---------------------------------------------------------------------------
-- Q14. Optional: trading_picks pnl scaling anomalies (if table exists)
-- ---------------------------------------------------------------------------
-- SELECT
--     id, symbol, direction, status, pnl_pct, entry_price, exit_price
-- FROM trading_picks
-- WHERE status NOT IN ('OPEN','ACTIVE')
--   AND pnl_pct IS NOT NULL
--   AND ABS(pnl_pct) > 25
-- ORDER BY ABS(pnl_pct) DESC
-- LIMIT 100;

-- ---------------------------------------------------------------------------
-- Q15. Optional: at_signal_outcomes TP/SL hit profile (if table exists)
-- ---------------------------------------------------------------------------
-- SELECT
--     COALESCE(asset_class, 'UNKNOWN') AS asset_class,
--     SUM(exit_reason = 'TP_HIT') AS tp_hits,
--     SUM(exit_reason = 'SL_HIT') AS sl_hits,
--     ROUND(100.0 * SUM(exit_reason = 'TP_HIT') / NULLIF(SUM(exit_reason IN ('TP_HIT','SL_HIT')), 0), 2) AS tp_hit_rate_pct,
--     ROUND(AVG(pnl_pct), 4) AS avg_pnl_pct
-- FROM at_signal_outcomes
-- WHERE status IN ('WON','LOST','CLOSED_TP','CLOSED_SL')
-- GROUP BY COALESCE(asset_class, 'UNKNOWN')
-- ORDER BY tp_hit_rate_pct DESC;

-- ---------------------------------------------------------------------------
-- Q16. Dashboard snapshot: best/worst asset class by expectancy
-- ---------------------------------------------------------------------------
SELECT
    x.asset_class,
    x.total_picks,
    x.win_rate_pct,
    x.profit_factor,
    x.expectancy_pct,
    CASE
        WHEN x.expectancy_pct = (SELECT MAX(expectancy_pct) FROM (
            SELECT asset_class,
                   AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END) AS expectancy_pct
            FROM at_raw_picks
            GROUP BY asset_class
        ) m) THEN 'BEST_EXPECTANCY'
        WHEN x.expectancy_pct = (SELECT MIN(expectancy_pct) FROM (
            SELECT asset_class,
                   AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END) AS expectancy_pct
            FROM at_raw_picks
            GROUP BY asset_class
        ) n) THEN 'WORST_EXPECTANCY'
        ELSE 'MID'
    END AS rank_flag
FROM (
    SELECT
        asset_class,
        COUNT(*) AS total_picks,
        ROUND(100.0 * SUM(status = 'WON') / NULLIF(SUM(status IN ('WON','LOST')), 0), 2) AS win_rate_pct,
        ROUND(
            SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) /
            NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0),
            4
        ) AS profit_factor,
        ROUND(AVG(CASE WHEN status IN ('WON','LOST') THEN pnl_pct END), 4) AS expectancy_pct
    FROM at_raw_picks
    GROUP BY asset_class
) x
ORDER BY x.expectancy_pct DESC;

