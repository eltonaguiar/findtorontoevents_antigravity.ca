-- =============================================================================
-- Shadow Mode Signal Collection Schema
-- For XGBoost Meme Coin Model Validation
-- 
-- Purpose: Collect 350+ resolved signals to validate ML model with 95% CI
--          at 40% target win rate
-- 
-- Run this SQL to initialize the shadow collection tables
-- =============================================================================

USE ejaguiar1_memecoin;

-- =============================================================================
-- Table: mc_shadow_signals
-- Stores individual shadow signals with both ML and rule-based predictions
-- =============================================================================

CREATE TABLE IF NOT EXISTS mc_shadow_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Signal identification
    symbol VARCHAR(20) NOT NULL COMMENT 'Coin symbol (e.g., DOGE)',
    timestamp INT NOT NULL COMMENT 'Unix timestamp when signal created',
    
    -- Entry information
    entry_price DECIMAL(18,8) NOT NULL COMMENT 'Price at signal time',
    
    -- ML prediction (from XGBoost model)
    ml_score DECIMAL(5,4) NOT NULL COMMENT 'XGBoost probability (0-1)',
    ml_prediction VARCHAR(10) NOT NULL COMMENT 'buy/hold/sell/avoid/lean_buy/strong_buy',
    ml_tier VARCHAR(20) NOT NULL COMMENT 'strong_buy/moderate_buy/lean_buy',
    
    -- Rule-based prediction (from meme_scanner.php)
    rule_based_score INT NOT NULL COMMENT 'Scanner score (0-100)',
    rule_based_tier VARCHAR(20) NOT NULL COMMENT 'Strong Buy/Buy/Lean Buy/Skip',
    
    -- Feature snapshot (for analysis)
    features JSON COMMENT 'All 16 features used at prediction time',
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'open' COMMENT 'open/closed/expired',
    
    -- Exit levels
    tp_price DECIMAL(18,8) NOT NULL COMMENT 'Take profit price (+8% default)',
    sl_price DECIMAL(18,8) NOT NULL COMMENT 'Stop loss price (-4% default)',
    
    -- Outcome tracking
    exit_price DECIMAL(18,8) COMMENT 'Price when signal closed',
    exit_time INT COMMENT 'Unix timestamp when signal closed',
    exit_reason VARCHAR(20) COMMENT 'tp_hit/sl_hit/max_hold/expiration',
    return_pct DECIMAL(8,4) COMMENT 'Actual return percentage',
    
    -- Accuracy tracking
    ml_was_correct BOOLEAN COMMENT 'Did ML prediction match outcome?',
    rule_based_was_correct BOOLEAN COMMENT 'Did rule-based prediction match outcome?',
    
    -- Indexes for performance
    INDEX idx_symbol_time (symbol, timestamp),
    INDEX idx_status (status),
    INDEX idx_ml_tier (ml_tier),
    INDEX idx_rule_tier (rule_based_tier),
    INDEX idx_created (timestamp)
    
) ENGINE=MyISAM DEFAULT CHARSET=utf8
COMMENT='Shadow mode signals - no actual trades, just tracking predictions';

-- =============================================================================
-- Table: mc_shadow_summary
-- Daily aggregated statistics for trend analysis
-- =============================================================================

CREATE TABLE IF NOT EXISTS mc_shadow_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Date
    date DATE NOT NULL COMMENT 'Summary date',
    
    -- Signal counts
    total_signals INT DEFAULT 0 COMMENT 'Total signals for the day',
    
    -- Overall win rates
    ml_win_rate DECIMAL(5,4) COMMENT 'ML model win rate (0-1)',
    rule_based_win_rate DECIMAL(5,4) COMMENT 'Rule-based win rate (0-1)',
    
    -- ML tier-specific win rates
    ml_strong_buy_wr DECIMAL(5,4) COMMENT 'Strong Buy tier win rate',
    ml_moderate_buy_wr DECIMAL(5,4) COMMENT 'Moderate Buy tier win rate',
    ml_lean_buy_wr DECIMAL(5,4) COMMENT 'Lean Buy tier win rate',
    
    -- Rule-based tier-specific win rates
    rule_based_strong_wr DECIMAL(5,4) COMMENT 'Strong Buy tier win rate',
    rule_based_moderate_wr DECIMAL(5,4) COMMENT 'Buy tier win rate',
    rule_based_lean_wr DECIMAL(5,4) COMMENT 'Lean Buy tier win rate',
    
    -- Statistical validity
    samples_sufficient BOOLEAN DEFAULT FALSE COMMENT 'Has 350+ closed signals?',
    
    -- Unique constraint
    UNIQUE KEY idx_date (date)
    
) ENGINE=MyISAM DEFAULT CHARSET=utf8
COMMENT='Daily shadow signal summary statistics';

-- =============================================================================
-- Sample Queries for Analysis
-- =============================================================================

-- Get overall comparison between ML and rule-based
-- SELECT 
--     'ML Model' as method,
--     SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
--     SUM(CASE WHEN ml_was_correct = 0 THEN 1 ELSE 0 END) as losses,
--     ROUND(SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate
-- FROM mc_shadow_signals WHERE status = 'closed'
-- UNION ALL
-- SELECT 
--     'Rule-Based' as method,
--     SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) as wins,
--     SUM(CASE WHEN rule_based_was_correct = 0 THEN 1 ELSE 0 END) as losses,
--     ROUND(SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate
-- FROM mc_shadow_signals WHERE status = 'closed';

-- Get win rate by ML tier
-- SELECT 
--     ml_tier,
--     COUNT(*) as signals,
--     SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
--     ROUND(SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate
-- FROM mc_shadow_signals 
-- WHERE status = 'closed' 
-- GROUP BY ml_tier;

-- Get current progress to 350 target
-- SELECT 
--     COUNT(*) as current_signals,
--     350 as target,
--     ROUND(COUNT(*) / 350 * 100, 1) as percent_complete,
--     CASE WHEN COUNT(*) >= 350 THEN 'YES' ELSE 'NO' END as is_valid
-- FROM mc_shadow_signals WHERE status = 'closed';

-- Get open signals that need monitoring
-- SELECT 
--     symbol,
--     FROM_UNIXTIME(timestamp) as entry_time,
--     entry_price,
--     ml_score,
--     ml_prediction,
--     tp_price,
--     sl_price,
--     ROUND((UNIX_TIMESTAMP() - timestamp) / 3600, 1) as hours_open
-- FROM mc_shadow_signals 
-- WHERE status = 'open' 
-- ORDER BY timestamp DESC;
