-- ═══════════════════════════════════════════════════════════════
-- UNIFIED PREDICTIONS TABLE - Phase 3 Implementation
-- Tracks all predictions across 7 systems with algorithm attribution
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS unified_predictions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- System & Algorithm Attribution
    system VARCHAR(50) NOT NULL,           -- crypto, meme, sports, stocks, forex, mutual_funds, penny
    algorithm VARCHAR(100) NOT NULL,        -- specific algo name (e.g., "Momentum Breakout", "CAN SLIM")
    algorithm_family VARCHAR(50),           -- family grouping (e.g., "Technical", "Fundamental", "ML")
    
    -- Asset Information
    asset VARCHAR(100) NOT NULL,           -- ticker, pair, event_id, fund symbol
    asset_type VARCHAR(20),                -- stock, crypto, forex_pair, sports_event, fund
    
    -- Entry Details
    entry_timestamp DATETIME NOT NULL,
    entry_price DECIMAL(18,8),
    entry_signal VARCHAR(50),              -- buy, sell, long, short, over, under
    confidence VARCHAR(20),                -- high, medium, low (or A+, A, B, etc.)
    score INT,                             -- algorithm-specific score
    
    -- Exit Details
    exit_timestamp DATETIME,
    exit_price DECIMAL(18,8),
    exit_reason VARCHAR(50),               -- target_hit, stop_loss, time_limit, manual
    
    -- Performance Metrics
    outcome VARCHAR(20),                   -- win, loss, partial_win, pending
    pnl_pct DECIMAL(10,4),                -- percentage profit/loss
    pnl_usd DECIMAL(10,2),                -- dollar profit/loss (for paper trading)
    hold_duration_hours DECIMAL(10,2),    -- hours between entry and exit
    
    -- Risk Metrics
    risk_pct DECIMAL(6,2),                -- risk taken as % of capital
    reward_risk_ratio DECIMAL(6,2),       -- reward/risk ratio
    max_drawdown_pct DECIMAL(6,2),        -- max drawdown during hold
    
    -- Market Context
    market_regime VARCHAR(30),            -- bull, bear, sideways, high_vol, low_vol
    vix_at_entry DECIMAL(6,2),           -- VIX level at entry (for stocks)
    
    -- Metadata
    is_backtest BOOLEAN DEFAULT 0,        -- 0 = live, 1 = backtest
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Additional Data (JSON for flexibility)
    metadata_json TEXT,                   -- store additional system-specific data
    
    -- Indexes for Performance
    INDEX idx_system (system),
    INDEX idx_algorithm (algorithm),
    INDEX idx_asset (asset),
    INDEX idx_outcome (outcome),
    INDEX idx_entry_timestamp (entry_timestamp),
    INDEX idx_system_algo (system, algorithm),
    INDEX idx_backtest (is_backtest),
    INDEX idx_composite (system, algorithm, outcome, is_backtest)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════
-- HELPER VIEWS
-- ═══════════════════════════════════════════════════════════════

-- Algorithm Leaderboard (Live Only)
CREATE OR REPLACE VIEW v_algorithm_leaderboard AS
SELECT 
    system,
    algorithm,
    algorithm_family,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
    ROUND(STDDEV(pnl_pct), 4) as volatility,
    ROUND(AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0), 4) as sharpe_ratio,
    ROUND(SUM(pnl_pct), 2) as total_pnl_pct,
    ROUND(AVG(hold_duration_hours), 2) as avg_hold_hours,
    MAX(entry_timestamp) as last_trade_date
FROM unified_predictions
WHERE outcome IS NOT NULL 
  AND is_backtest = 0
GROUP BY system, algorithm, algorithm_family
HAVING total_trades >= 10  -- minimum 10 trades for statistical significance
ORDER BY sharpe_ratio DESC;

-- Hidden Winners (High Sharpe, Low Correlation)
CREATE OR REPLACE VIEW v_hidden_winners AS
SELECT 
    l.*,
    CASE 
        WHEN l.sharpe_ratio >= 2.0 AND l.win_rate_pct >= 60 THEN 'Elite'
        WHEN l.sharpe_ratio >= 1.5 AND l.win_rate_pct >= 55 THEN 'Excellent'
        WHEN l.sharpe_ratio >= 1.0 AND l.win_rate_pct >= 50 THEN 'Good'
        ELSE 'Developing'
    END as rating
FROM v_algorithm_leaderboard l
WHERE l.sharpe_ratio >= 1.0
  AND l.total_trades >= 30
ORDER BY l.sharpe_ratio DESC, l.win_rate_pct DESC;

-- System Performance Summary
CREATE OR REPLACE VIEW v_system_performance AS
SELECT 
    system,
    COUNT(DISTINCT algorithm) as algorithms_count,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
    ROUND(SUM(pnl_pct), 2) as total_pnl_pct,
    ROUND(AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0), 4) as sharpe_ratio,
    MAX(entry_timestamp) as last_trade_date,
    DATEDIFF(NOW(), MAX(entry_timestamp)) as days_since_last_trade
FROM unified_predictions
WHERE outcome IS NOT NULL 
  AND is_backtest = 0
GROUP BY system
ORDER BY sharpe_ratio DESC;

-- ═══════════════════════════════════════════════════════════════
-- SAMPLE QUERIES
-- ═══════════════════════════════════════════════════════════════

-- Top 10 Algorithms by Sharpe Ratio
-- SELECT * FROM v_algorithm_leaderboard LIMIT 10;

-- Hidden Winners (Elite Performers)
-- SELECT * FROM v_hidden_winners WHERE rating IN ('Elite', 'Excellent');

-- System Comparison
-- SELECT * FROM v_system_performance;

-- Recent Trades (Last 24 Hours)
-- SELECT * FROM unified_predictions 
-- WHERE entry_timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
-- ORDER BY entry_timestamp DESC;

-- Backtest vs Live Performance Comparison
-- SELECT 
--     algorithm,
--     is_backtest,
--     COUNT(*) as trades,
--     ROUND(AVG(pnl_pct), 4) as avg_pnl,
--     ROUND(AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0), 4) as sharpe
-- FROM unified_predictions
-- WHERE outcome IS NOT NULL
-- GROUP BY algorithm, is_backtest
-- ORDER BY algorithm, is_backtest;
