-- ═══════════════════════════════════════════════════════════════
-- PHASE 4: PROFESSIONAL-GRADE ENHANCEMENTS
-- Advanced analytics for institutional-level performance tracking
-- ═══════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────
-- 1. DRAWDOWN ANALYSIS
-- ───────────────────────────────────────────────────────────────

-- Max Drawdown by System
CREATE OR REPLACE VIEW v_max_drawdown_by_system AS
WITH running_pnl AS (
    SELECT 
        system,
        entry_timestamp,
        pnl_usd,
        SUM(pnl_usd) OVER (PARTITION BY system ORDER BY entry_timestamp) as cumulative_pnl,
        MAX(SUM(pnl_usd) OVER (PARTITION BY system ORDER BY entry_timestamp)) 
            OVER (PARTITION BY system ORDER BY entry_timestamp) as peak_pnl
    FROM unified_predictions
    WHERE outcome IS NOT NULL AND is_backtest = 0
),
drawdowns AS (
    SELECT 
        system,
        entry_timestamp,
        cumulative_pnl,
        peak_pnl,
        (cumulative_pnl - peak_pnl) as drawdown,
        CASE 
            WHEN peak_pnl > 0 THEN ((cumulative_pnl - peak_pnl) / peak_pnl) * 100
            ELSE 0
        END as drawdown_pct
    FROM running_pnl
)
SELECT 
    system,
    ROUND(MIN(drawdown), 2) as max_drawdown_usd,
    ROUND(MIN(drawdown_pct), 2) as max_drawdown_pct,
    (SELECT entry_timestamp FROM drawdowns d2 
     WHERE d2.system = d.system AND d2.drawdown = MIN(d.drawdown) LIMIT 1) as worst_drawdown_date
FROM drawdowns d
GROUP BY system
ORDER BY max_drawdown_pct ASC;

-- Max Drawdown by Algorithm
CREATE OR REPLACE VIEW v_max_drawdown_by_algorithm AS
WITH running_pnl AS (
    SELECT 
        system,
        algorithm,
        entry_timestamp,
        pnl_pct,
        SUM(pnl_pct) OVER (PARTITION BY system, algorithm ORDER BY entry_timestamp) as cumulative_pnl,
        MAX(SUM(pnl_pct) OVER (PARTITION BY system, algorithm ORDER BY entry_timestamp)) 
            OVER (PARTITION BY system, algorithm ORDER BY entry_timestamp) as peak_pnl
    FROM unified_predictions
    WHERE outcome IS NOT NULL AND is_backtest = 0
),
drawdowns AS (
    SELECT 
        system,
        algorithm,
        (cumulative_pnl - peak_pnl) as drawdown_pct
    FROM running_pnl
)
SELECT 
    system,
    algorithm,
    ROUND(MIN(drawdown_pct), 2) as max_drawdown_pct
FROM drawdowns
GROUP BY system, algorithm
HAVING COUNT(*) >= 10
ORDER BY max_drawdown_pct ASC;

-- ───────────────────────────────────────────────────────────────
-- 2. CORRELATION MATRIX
-- ───────────────────────────────────────────────────────────────

-- Cross-System Correlation
CREATE OR REPLACE VIEW v_system_correlation AS
SELECT 
    a.system as system_a,
    b.system as system_b,
    COUNT(*) as overlapping_days,
    ROUND(
        (COUNT(*) * SUM(a.daily_pnl * b.daily_pnl) - SUM(a.daily_pnl) * SUM(b.daily_pnl)) /
        SQRT(
            (COUNT(*) * SUM(a.daily_pnl * a.daily_pnl) - SUM(a.daily_pnl) * SUM(a.daily_pnl)) *
            (COUNT(*) * SUM(b.daily_pnl * b.daily_pnl) - SUM(b.daily_pnl) * SUM(b.daily_pnl))
        ),
        3
    ) as correlation
FROM (
    SELECT system, DATE(entry_timestamp) as trade_date, SUM(pnl_pct) as daily_pnl
    FROM unified_predictions
    WHERE outcome IS NOT NULL AND is_backtest = 0
    GROUP BY system, DATE(entry_timestamp)
) a
JOIN (
    SELECT system, DATE(entry_timestamp) as trade_date, SUM(pnl_pct) as daily_pnl
    FROM unified_predictions
    WHERE outcome IS NOT NULL AND is_backtest = 0
    GROUP BY system, DATE(entry_timestamp)
) b ON a.trade_date = b.trade_date AND a.system < b.system
GROUP BY a.system, b.system
HAVING overlapping_days >= 30
ORDER BY correlation DESC;

-- ───────────────────────────────────────────────────────────────
-- 3. ADVANCED RISK METRICS
-- ───────────────────────────────────────────────────────────────

-- Sortino Ratio (Downside Deviation)
CREATE OR REPLACE VIEW v_sortino_ratio AS
SELECT 
    system,
    algorithm,
    COUNT(*) as total_trades,
    ROUND(AVG(pnl_pct), 4) as avg_return,
    ROUND(STDDEV(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE NULL END), 4) as downside_deviation,
    ROUND(
        AVG(pnl_pct) / NULLIF(STDDEV(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE NULL END), 0),
        4
    ) as sortino_ratio
FROM unified_predictions
WHERE outcome IS NOT NULL AND is_backtest = 0
GROUP BY system, algorithm
HAVING total_trades >= 10
ORDER BY sortino_ratio DESC;

-- Calmar Ratio (Return / Max Drawdown)
CREATE OR REPLACE VIEW v_calmar_ratio AS
SELECT 
    l.system,
    l.algorithm,
    l.total_pnl_pct as total_return,
    d.max_drawdown_pct,
    ROUND(
        l.total_pnl_pct / NULLIF(ABS(d.max_drawdown_pct), 0),
        4
    ) as calmar_ratio
FROM v_algorithm_leaderboard l
JOIN v_max_drawdown_by_algorithm d 
    ON l.system = d.system AND l.algorithm = d.algorithm
ORDER BY calmar_ratio DESC;

-- Value at Risk (VaR) - 95th Percentile Loss
CREATE OR REPLACE VIEW v_value_at_risk AS
SELECT 
    system,
    algorithm,
    COUNT(*) as total_trades,
    ROUND(AVG(pnl_pct), 4) as avg_return,
    ROUND(
        (SELECT pnl_pct 
         FROM unified_predictions p2 
         WHERE p2.system = p.system 
           AND p2.algorithm = p.algorithm 
           AND p2.outcome IS NOT NULL 
           AND p2.is_backtest = 0
         ORDER BY pnl_pct ASC 
         LIMIT 1 OFFSET FLOOR(COUNT(*) * 0.05)),
        4
    ) as var_95_pct
FROM unified_predictions p
WHERE outcome IS NOT NULL AND is_backtest = 0
GROUP BY system, algorithm
HAVING total_trades >= 20
ORDER BY var_95_pct ASC;

-- ───────────────────────────────────────────────────────────────
-- 4. BACKTEST VS LIVE PERFORMANCE
-- ───────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_backtest_vs_live AS
SELECT 
    algorithm,
    MAX(CASE WHEN is_backtest = 1 THEN total_trades ELSE 0 END) as backtest_trades,
    MAX(CASE WHEN is_backtest = 0 THEN total_trades ELSE 0 END) as live_trades,
    ROUND(MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END), 4) as backtest_avg_pnl,
    ROUND(MAX(CASE WHEN is_backtest = 0 THEN avg_pnl ELSE 0 END), 4) as live_avg_pnl,
    ROUND(MAX(CASE WHEN is_backtest = 1 THEN sharpe ELSE 0 END), 4) as backtest_sharpe,
    ROUND(MAX(CASE WHEN is_backtest = 0 THEN sharpe ELSE 0 END), 4) as live_sharpe,
    ROUND(
        (MAX(CASE WHEN is_backtest = 0 THEN avg_pnl ELSE 0 END) - 
         MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END)) /
        NULLIF(MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END), 0) * 100,
        2
    ) as performance_degradation_pct
FROM (
    SELECT 
        algorithm,
        is_backtest,
        COUNT(*) as total_trades,
        AVG(pnl_pct) as avg_pnl,
        AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0) as sharpe
    FROM unified_predictions
    WHERE outcome IS NOT NULL
    GROUP BY algorithm, is_backtest
) subq
GROUP BY algorithm
HAVING backtest_trades >= 10 AND live_trades >= 10
ORDER BY performance_degradation_pct DESC;

-- ───────────────────────────────────────────────────────────────
-- 5. WIN/LOSS STREAKS
-- ───────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_win_loss_streaks AS
WITH streaks AS (
    SELECT 
        system,
        algorithm,
        entry_timestamp,
        outcome,
        CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END as is_win,
        ROW_NUMBER() OVER (PARTITION BY system, algorithm ORDER BY entry_timestamp) as rn,
        ROW_NUMBER() OVER (
            PARTITION BY system, algorithm, CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END 
            ORDER BY entry_timestamp
        ) as streak_rn
    FROM unified_predictions
    WHERE outcome IS NOT NULL AND is_backtest = 0
),
streak_groups AS (
    SELECT 
        system,
        algorithm,
        is_win,
        COUNT(*) as streak_length,
        MIN(entry_timestamp) as streak_start,
        MAX(entry_timestamp) as streak_end
    FROM streaks
    GROUP BY system, algorithm, is_win, (rn - streak_rn)
)
SELECT 
    system,
    algorithm,
    MAX(CASE WHEN is_win = 1 THEN streak_length ELSE 0 END) as max_win_streak,
    MAX(CASE WHEN is_win = 0 THEN streak_length ELSE 0 END) as max_loss_streak,
    ROUND(AVG(CASE WHEN is_win = 1 THEN streak_length ELSE NULL END), 2) as avg_win_streak,
    ROUND(AVG(CASE WHEN is_win = 0 THEN streak_length ELSE NULL END), 2) as avg_loss_streak
FROM streak_groups
GROUP BY system, algorithm
ORDER BY max_win_streak DESC;

-- ───────────────────────────────────────────────────────────────
-- 6. COMPREHENSIVE RISK DASHBOARD VIEW
-- ───────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_risk_dashboard AS
SELECT 
    l.system,
    l.algorithm,
    l.total_trades,
    l.win_rate_pct,
    l.avg_pnl_pct,
    l.sharpe_ratio,
    s.sortino_ratio,
    c.calmar_ratio,
    d.max_drawdown_pct,
    v.var_95_pct,
    w.max_win_streak,
    w.max_loss_streak,
    CASE 
        WHEN l.sharpe_ratio >= 2.0 AND d.max_drawdown_pct >= -10 THEN 'A+'
        WHEN l.sharpe_ratio >= 1.5 AND d.max_drawdown_pct >= -15 THEN 'A'
        WHEN l.sharpe_ratio >= 1.0 AND d.max_drawdown_pct >= -20 THEN 'B'
        WHEN l.sharpe_ratio >= 0.5 THEN 'C'
        ELSE 'D'
    END as risk_grade
FROM v_algorithm_leaderboard l
LEFT JOIN v_sortino_ratio s ON l.system = s.system AND l.algorithm = s.algorithm
LEFT JOIN v_calmar_ratio c ON l.system = c.system AND l.algorithm = c.algorithm
LEFT JOIN v_max_drawdown_by_algorithm d ON l.system = d.system AND l.algorithm = d.algorithm
LEFT JOIN v_value_at_risk v ON l.system = v.system AND l.algorithm = v.algorithm
LEFT JOIN v_win_loss_streaks w ON l.system = w.system AND l.algorithm = w.algorithm
ORDER BY l.sharpe_ratio DESC;
