-- =============================================================================
-- UNIFIED PREDICTION LEDGER SCHEMA
-- =============================================================================
-- Add this table to ejaguiar1_memecoin database
-- This provides single source of truth for all predictions across all 11 systems
-- =============================================================================

-- Main ledger table
CREATE TABLE IF NOT EXISTS unified_prediction_ledger (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Identification
    prediction_id VARCHAR(100) NOT NULL UNIQUE,
    system VARCHAR(50) NOT NULL,
    system_version VARCHAR(20),
    
    -- Asset & Direction
    asset_class VARCHAR(20) NOT NULL,  -- stock, crypto, forex, mutual_fund
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,    -- buy, sell, hold
    
    -- Price Levels
    entry_price DECIMAL(18, 8) NOT NULL,
    target_price DECIMAL(18, 8),
    stop_price DECIMAL(18, 8),
    
    -- Confidence & Metadata
    confidence DECIMAL(5, 4) NOT NULL,  -- 0-1
    score DECIMAL(8, 4),
    factors_json JSON,
    
    -- Timing
    prediction_time DATETIME NOT NULL,
    expected_duration_hours INT,
    expiry_time DATETIME,
    
    -- Status & Results
    status VARCHAR(20) DEFAULT 'pending',
    exit_price DECIMAL(18, 8),
    exit_time DATETIME,
    pnl_percent DECIMAL(8, 4),
    
    -- Audit & Integrity
    input_hash VARCHAR(64),  -- SHA-256 of inputs
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_system (system),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_prediction_time (prediction_time),
    INDEX idx_asset_class (asset_class),
    INDEX idx_system_symbol (system, symbol),
    INDEX idx_system_status (system, status),
    INDEX idx_system_time (system, prediction_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Performance summary view (materialized via scheduled update)
CREATE TABLE IF NOT EXISTS system_performance_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    system VARCHAR(50) NOT NULL,
    period_days INT NOT NULL,
    total_predictions INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(5, 2),
    avg_pnl DECIMAL(8, 4),
    avg_win DECIMAL(8, 4),
    avg_loss DECIMAL(8, 4),
    best_trade DECIMAL(8, 4),
    worst_trade DECIMAL(8, 4),
    sharpe DECIMAL(6, 4),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_system_period (system, period_days),
    INDEX idx_win_rate (win_rate)
) ENGINE=InnoDB;

-- Meta-learning table (which system works best in which conditions)
CREATE TABLE IF NOT EXISTS meta_learning_insights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    system VARCHAR(50) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    market_regime VARCHAR(20),  -- bull, bear, chop
    win_rate DECIMAL(5, 2),
    sample_size INT,
    avg_pnl DECIMAL(8, 4),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_condition (system, asset_class, direction, market_regime),
    INDEX idx_best_performers (win_rate, sample_size)
) ENGINE=InnoDB;

-- Early warning log
CREATE TABLE IF NOT EXISTS early_warning_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    system VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL,  -- HIGH, MEDIUM, LOW
    warning_type VARCHAR(50) NOT NULL,
    message TEXT,
    metrics_json JSON,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    INDEX idx_unresolved (resolved, severity),
    INDEX idx_system_time (system, alert_time)
) ENGINE=InnoDB;

-- =============================================================================
-- INITIAL DATA MIGRATION (from existing tables)
-- =============================================================================

-- Migrate existing crypto_signals to unified ledger
INSERT INTO unified_prediction_ledger (
    prediction_id, system, system_version, asset_class, symbol,
    direction, entry_price, target_price, stop_price, confidence,
    score, factors_json, prediction_time, expected_duration_hours,
    status, exit_price, pnl_percent, notes
)
SELECT 
    signal_id,
    'cryptoalpha_pro',
    '1.0',
    'crypto',
    symbol,
    signal_type,
    entry_price,
    target_price_1,
    stop_loss,
    COALESCE(confidence, 0.5),
    confidence * 100,
    indicators_triggered,
    created_at,
    48,
    status,
    exit_price,
    pnl_percent,
    strategy
FROM crypto_signals
WHERE signal_id NOT IN (SELECT prediction_id FROM unified_prediction_ledger)
ON DUPLICATE KEY UPDATE
    status = VALUES(status),
    exit_price = VALUES(exit_price),
    pnl_percent = VALUES(pnl_percent);

-- Migrate meme coin winners
INSERT INTO unified_prediction_ledger (
    prediction_id, system, asset_class, symbol,
    direction, entry_price, target_price, stop_price, confidence,
    score, factors_json, prediction_time, status, exit_price, pnl_percent
)
SELECT 
    CONCAT('meme_v1_', scan_id, '_', pair),
    'meme_coin_v1',
    'crypto',
    pair,
    'buy',
    price_at_signal,
    price_at_signal * (1 + target_pct/100),
    price_at_signal * (1 - risk_pct/100),
    score / 100,
    score,
    factors_json,
    created_at,
    CASE outcome
        WHEN 'win' THEN 'target_hit'
        WHEN 'partial_win' THEN 'target_hit'
        WHEN 'loss' THEN 'stop_hit'
        WHEN 'partial_loss' THEN 'stop_hit'
        ELSE 'expired'
    END,
    price_at_resolve,
    pnl_pct
FROM mc_winners
WHERE CONCAT('meme_v1_', scan_id, '_', pair) NOT IN (SELECT prediction_id FROM unified_prediction_ledger)
ON DUPLICATE KEY UPDATE
    status = VALUES(status),
    exit_price = VALUES(exit_price),
    pnl_percent = VALUES(pnl_percent);

-- =============================================================================
-- STORED PROCEDURES
-- =============================================================================

DELIMITER //

-- Calculate performance for a system
CREATE PROCEDURE IF NOT EXISTS CalculateSystemPerformance(
    IN p_system VARCHAR(50),
    IN p_days INT
)
BEGIN
    INSERT INTO system_performance_summary (
        system, period_days, total_predictions, wins, losses,
        win_rate, avg_pnl, avg_win, avg_loss, best_trade, worst_trade, sharpe
    )
    SELECT 
        p_system,
        p_days,
        COUNT(*),
        SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN pnl_percent <= 0 THEN 1 ELSE 0 END),
        AVG(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) * 100,
        AVG(pnl_percent),
        AVG(CASE WHEN pnl_percent > 0 THEN pnl_percent END),
        AVG(CASE WHEN pnl_percent <= 0 THEN pnl_percent END),
        MAX(pnl_percent),
        MIN(pnl_percent),
        CASE 
            WHEN STDDEV(pnl_percent) > 0 THEN 
                (AVG(pnl_percent) / STDDEV(pnl_percent)) * SQRT(252)
            ELSE 0
        END
    FROM unified_prediction_ledger
    WHERE system = p_system
    AND prediction_time >= DATE_SUB(NOW(), INTERVAL p_days DAY)
    AND status IN ('target_hit', 'stop_hit', 'expired')
    ON DUPLICATE KEY UPDATE
        total_predictions = VALUES(total_predictions),
        wins = VALUES(wins),
        losses = VALUES(losses),
        win_rate = VALUES(win_rate),
        avg_pnl = VALUES(avg_pnl),
        avg_win = VALUES(avg_win),
        avg_loss = VALUES(avg_loss),
        best_trade = VALUES(best_trade),
        worst_trade = VALUES(worst_trade),
        sharpe = VALUES(sharpe),
        calculated_at = NOW();
END //

-- Check for early warnings
CREATE PROCEDURE IF NOT EXISTS CheckEarlyWarnings()
BEGIN
    INSERT INTO early_warning_log (system, severity, warning_type, message, metrics_json)
    SELECT 
        system,
        CASE 
            WHEN win_rate < 25 THEN 'HIGH'
            WHEN win_rate < 35 THEN 'MEDIUM'
            ELSE 'LOW'
        END,
        'LOW_WIN_RATE',
        CONCAT('Win rate ', CAST(win_rate AS CHAR), '% below threshold'),
        JSON_OBJECT('win_rate', win_rate, 'sample_size', total_predictions, 'avg_pnl', avg_pnl)
    FROM system_performance_summary
    WHERE period_days = 14
    AND win_rate < 35
    AND total_predictions >= 5
    AND NOT EXISTS (
        SELECT 1 FROM early_warning_log 
        WHERE system = system_performance_summary.system 
        AND warning_type = 'LOW_WIN_RATE'
        AND resolved = FALSE
        AND alert_time > DATE_SUB(NOW(), INTERVAL 24 HOUR)
    );
END //

DELIMITER ;

-- =============================================================================
-- SCHEDULED EVENTS (enable event scheduler)
-- =============================================================================

SET GLOBAL event_scheduler = ON;

-- Update performance summaries every 6 hours
CREATE EVENT IF NOT EXISTS update_performance_summaries
ON SCHEDULE EVERY 6 HOUR
DO
BEGIN
    CALL CalculateSystemPerformance('v2_scientific_ledger', 7);
    CALL CalculateSystemPerformance('v2_scientific_ledger', 30);
    CALL CalculateSystemPerformance('cryptoalpha_pro', 7);
    CALL CalculateSystemPerformance('cryptoalpha_pro', 30);
    CALL CalculateSystemPerformance('meme_coin_v1', 7);
    CALL CalculateSystemPerformance('meme_coin_v1', 30);
    CALL CalculateSystemPerformance('meme_coin_v2', 7);
    CALL CalculateSystemPerformance('meme_coin_v2', 30);
END;

-- Check warnings every 4 hours
CREATE EVENT IF NOT EXISTS check_warnings
ON SCHEDULE EVERY 4 HOUR
DO
BEGIN
    CALL CheckEarlyWarnings();
END;
