-- ============================================================================
-- PERFORMANCE TRACKING & ALERT SYSTEM
-- For Multi-Dimensional Consensus Engine
-- ============================================================================

-- ============================================================================
-- PART 1: PERFORMANCE TRACKING TABLES
-- ============================================================================

-- Track conviction scores over time with price snapshots
CREATE TABLE IF NOT EXISTS conviction_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    calculation_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    conviction_score INT NOT NULL,
    label VARCHAR(20) NOT NULL, -- 'STRONG BUY', 'BUY', 'NEUTRAL', etc.
    
    -- Dimension scores at time of calculation
    whale_score INT DEFAULT 0,
    insider_score INT DEFAULT 0,
    analyst_score INT DEFAULT 0,
    crowd_score INT DEFAULT 0,
    fear_greed_score INT DEFAULT 0,
    value_score INT DEFAULT 0,
    growth_score INT DEFAULT 0,
    momentum_score INT DEFAULT 0,
    regime_score INT DEFAULT 0,
    
    -- Price at calculation time
    entry_price DECIMAL(10,2),
    entry_volume BIGINT,
    
    -- Metadata
    calculation_detail TEXT,
    
    INDEX idx_ticker_date (ticker, calculation_date),
    INDEX idx_date (calculation_date),
    INDEX idx_score (conviction_score),
    INDEX idx_label (label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Track actual performance outcomes
CREATE TABLE IF NOT EXISTS conviction_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    conviction_date DATE NOT NULL,
    conviction_score INT NOT NULL,
    label VARCHAR(20) NOT NULL,
    
    -- Entry price
    entry_price DECIMAL(10,2) NOT NULL,
    
    -- Future prices (updated by cron job)
    price_3d DECIMAL(10,2),
    price_7d DECIMAL(10,2),
    price_14d DECIMAL(10,2),
    price_30d DECIMAL(10,2),
    price_60d DECIMAL(10,2),
    price_90d DECIMAL(10,2),
    
    -- Returns (calculated)
    return_3d DECIMAL(6,2),
    return_7d DECIMAL(6,2),
    return_14d DECIMAL(6,2),
    return_30d DECIMAL(6,2),
    return_60d DECIMAL(6,2),
    return_90d DECIMAL(6,2),
    
    -- Performance classification
    outcome_30d ENUM('win', 'loss', 'pending') DEFAULT 'pending',
    
    -- Max drawdown during period
    max_drawdown_30d DECIMAL(6,2),
    
    -- Benchmark comparison (SPY)
    spy_return_30d DECIMAL(6,2),
    alpha_30d DECIMAL(6,2),
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_ticker_date (ticker, conviction_date),
    INDEX idx_conviction (conviction_score),
    INDEX idx_outcome (outcome_30d),
    INDEX idx_date (conviction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Aggregate performance by conviction level
CREATE TABLE IF NOT EXISTS conviction_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_period VARCHAR(20) NOT NULL, -- '7d', '30d', '90d'
    conviction_bucket VARCHAR(20) NOT NULL, -- '80-100', '70-79', '60-69', etc.
    
    -- Counts
    total_signals INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    pending INT DEFAULT 0,
    
    -- Performance metrics
    win_rate DECIMAL(5,2),
    avg_return DECIMAL(6,2),
    median_return DECIMAL(6,2),
    max_return DECIMAL(6,2),
    min_return DECIMAL(6,2),
    avg_max_drawdown DECIMAL(6,2),
    
    -- Benchmark comparison
    avg_spy_return DECIMAL(6,2),
    avg_alpha DECIMAL(6,2),
    
    -- Dimension performance (which factors worked best)
    avg_whale_score DECIMAL(5,2),
    avg_insider_score DECIMAL(5,2),
    avg_analyst_score DECIMAL(5,2),
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_period_bucket (stat_period, conviction_bucket),
    INDEX idx_period (stat_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- PART 2: ALERT SYSTEM TABLES
-- ============================================================================

-- Alert configurations
CREATE TABLE IF NOT EXISTS alert_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL, -- 'conviction_spike', 'insider_cluster', 'fear_extreme', etc.
    alert_name VARCHAR(100) NOT NULL,
    
    -- Threshold conditions
    threshold_value INT,
    threshold_direction ENUM('above', 'below', 'change_by'),
    comparison_period VARCHAR(20), -- '7d', '30d', etc.
    
    -- Ticker filters
    ticker_whitelist TEXT, -- comma-separated or NULL for all
    ticker_blacklist TEXT, -- comma-separated
    min_market_cap BIGINT, -- e.g., 1000000000 for $1B+
    
    -- Notification settings
    is_active BOOLEAN DEFAULT TRUE,
    notify_email VARCHAR(255),
    notify_webhook VARCHAR(500),
    cooldown_hours INT DEFAULT 24, -- don't alert same ticker within X hours
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_type (alert_type),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert history (what was triggered)
CREATE TABLE IF NOT EXISTS alert_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_config_id INT NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    
    -- Values at trigger time
    trigger_value DECIMAL(10,2),
    trigger_detail TEXT,
    
    -- Conviction snapshot
    conviction_score INT,
    whale_score INT,
    insider_score INT,
    analyst_score INT,
    crowd_score INT,
    fear_greed_score INT,
    
    -- Price snapshot
    trigger_price DECIMAL(10,2),
    
    -- Notification status
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP NULL,
    webhook_sent BOOLEAN DEFAULT FALSE,
    webhook_response TEXT,
    
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ticker (ticker),
    INDEX idx_type (alert_type),
    INDEX idx_triggered (triggered_at),
    INDEX idx_config (alert_config_id),
    FOREIGN KEY (alert_config_id) REFERENCES alert_configs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert cooldown tracking (prevent spam)
CREATE TABLE IF NOT EXISTS alert_cooldowns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    last_triggered TIMESTAMP NOT NULL,
    cooldown_until TIMESTAMP NOT NULL,
    
    UNIQUE KEY uk_type_ticker (alert_type, ticker),
    INDEX idx_cooldown (cooldown_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- PART 3: INSERT DEFAULT ALERT CONFIGURATIONS
-- ============================================================================

INSERT INTO alert_configs (alert_type, alert_name, threshold_value, threshold_direction, cooldown_hours) VALUES
-- Conviction-based alerts
('conviction_spike', 'Strong Bullish Signal (70+)', 70, 'above', 168), -- 7 days
('conviction_extreme', 'Extreme Conviction (80+)', 80, 'above', 168),
('conviction_jump', 'Conviction Jump (+10 in 7d)', 10, 'change_by', 72),
('conviction_drop', 'Conviction Drop (-10 in 7d)', -10, 'change_by', 24),

-- Insider-based alerts  
('insider_cluster', 'Insider Cluster (3+ buyers)', 3, 'above', 72),
('insider_massive', 'Massive Insider Buy ($5M+)', 5000000, 'above', 168),
('insider_ceo', 'CEO Purchase Detected', 1, 'above', 72),

-- Fear & Greed alerts
('fear_extreme', 'Extreme Fear (F&G < 25)', 25, 'below', 168),
('greed_extreme', 'Extreme Greed (F&G > 85)', 85, 'above', 168),

-- Dimension-specific alerts
('whale_accumulation', 'Smart Money Accumulation (85+)', 85, 'above', 168),
('crowd_euphoria', 'Crowd Euphoria (80+)', 80, 'above', 72),
('analyst_upgrade', 'Analyst Consensus Upgrade (80+)', 80, 'above', 72)

ON DUPLICATE KEY UPDATE
threshold_value = VALUES(threshold_value),
cooldown_hours = VALUES(cooldown_hours);

-- ============================================================================
-- PART 4: STORED PROCEDURES FOR PERFORMANCE TRACKING
-- ============================================================================

DELIMITER //

-- Procedure: Record a new conviction calculation
CREATE PROCEDURE IF NOT EXISTS RecordConviction(
    IN p_ticker VARCHAR(10),
    IN p_conviction INT,
    IN p_label VARCHAR(20),
    IN p_whale INT,
    IN p_insider INT,
    IN p_analyst INT,
    IN p_crowd INT,
    IN p_fg INT,
    IN p_value INT,
    IN p_growth INT,
    IN p_momentum INT,
    IN p_regime INT,
    IN p_price DECIMAL(10,2),
    IN p_volume BIGINT,
    IN p_detail TEXT
)
BEGIN
    -- Insert into history
    INSERT INTO conviction_history (
        ticker, conviction_score, label,
        whale_score, insider_score, analyst_score, crowd_score,
        fear_greed_score, value_score, growth_score, momentum_score, regime_score,
        entry_price, entry_volume, calculation_detail
    ) VALUES (
        p_ticker, p_conviction, p_label,
        p_whale, p_insider, p_analyst, p_crowd,
        p_fg, p_value, p_growth, p_momentum, p_regime,
        p_price, p_volume, p_detail
    );
    
    -- Upsert into performance tracking
    INSERT INTO conviction_performance (
        ticker, conviction_date, conviction_score, label, entry_price
    ) VALUES (
        p_ticker, CURDATE(), p_conviction, p_label, p_price
    ) ON DUPLICATE KEY UPDATE
        conviction_score = p_conviction,
        label = p_label,
        entry_price = p_price;
END //

-- Procedure: Update performance returns (run daily via cron)
CREATE PROCEDURE IF NOT EXISTS UpdatePerformanceReturns()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_ticker VARCHAR(10);
    DECLARE v_date DATE;
    DECLARE v_entry DECIMAL(10,2);
    
    DECLARE cur CURSOR FOR 
        SELECT ticker, conviction_date, entry_price 
        FROM conviction_performance 
        WHERE return_30d IS NULL 
        AND conviction_date <= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        LIMIT 100;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_ticker, v_date, v_entry;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        -- Get current price
        SET @current_price = (
            SELECT close_price FROM daily_prices 
            WHERE ticker = v_ticker 
            ORDER BY trade_date DESC LIMIT 1
        );
        
        -- Get SPY price for same dates
        SET @spy_entry = (
            SELECT close_price FROM daily_prices 
            WHERE ticker = 'SPY' AND trade_date = v_date
        );
        SET @spy_current = (
            SELECT close_price FROM daily_prices 
            WHERE ticker = 'SPY' 
            ORDER BY trade_date DESC LIMIT 1
        );
        
        -- Calculate returns
        IF @current_price IS NOT NULL AND v_entry > 0 THEN
            SET @return_30d = ((@current_price - v_entry) / v_entry) * 100;
            SET @spy_return = ((@spy_current - @spy_entry) / @spy_entry) * 100;
            SET @alpha = @return_30d - @spy_return;
            
            UPDATE conviction_performance SET
                price_30d = @current_price,
                return_30d = @return_30d,
                spy_return_30d = @spy_return,
                alpha_30d = @alpha,
                outcome_30d = CASE 
                    WHEN @return_30d > 5 THEN 'win'
                    WHEN @return_30d < -5 THEN 'loss'
                    ELSE 'pending'
                END
            WHERE ticker = v_ticker AND conviction_date = v_date;
        END IF;
    END LOOP;
    
    CLOSE cur;
END //

-- Procedure: Calculate aggregate statistics
CREATE PROCEDURE IF NOT EXISTS CalculateConvictionStats(IN p_period VARCHAR(20))
BEGIN
    -- Clear old stats for this period
    DELETE FROM conviction_stats WHERE stat_period = p_period;
    
    -- Insert new stats by conviction bucket
    INSERT INTO conviction_stats (
        stat_period, conviction_bucket, total_signals, wins, losses, pending,
        win_rate, avg_return, median_return, max_return, min_return,
        avg_spy_return, avg_alpha
    )
    SELECT 
        p_period,
        CASE 
            WHEN conviction_score >= 80 THEN '80-100'
            WHEN conviction_score >= 70 THEN '70-79'
            WHEN conviction_score >= 60 THEN '60-69'
            WHEN conviction_score >= 50 THEN '50-59'
            ELSE '0-49'
        END as bucket,
        COUNT(*) as total,
        SUM(CASE WHEN outcome_30d = 'win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome_30d = 'loss' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN outcome_30d = 'pending' THEN 1 ELSE 0 END) as pending,
        ROUND(SUM(CASE WHEN outcome_30d = 'win' THEN 1 ELSE 0 END) / 
              NULLIF(SUM(CASE WHEN outcome_30d IN ('win', 'loss') THEN 1 ELSE 0 END), 0) * 100, 2) as win_rate,
        ROUND(AVG(return_30d), 2) as avg_return,
        ROUND(
            (SELECT AVG(return_30d) FROM (
                SELECT return_30d FROM conviction_performance 
                WHERE return_30d IS NOT NULL
                ORDER BY return_30d 
                LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM conviction_performance WHERE return_30d IS NOT NULL)
            ) sub), 2) as median_return,
        ROUND(MAX(return_30d), 2) as max_return,
        ROUND(MIN(return_30d), 2) as min_return,
        ROUND(AVG(spy_return_30d), 2) as avg_spy,
        ROUND(AVG(alpha_30d), 2) as avg_alpha
    FROM conviction_performance
    WHERE conviction_date >= DATE_SUB(CURDATE(), INTERVAL 
        CASE p_period
            WHEN '7d' THEN 7
            WHEN '30d' THEN 30
            WHEN '90d' THEN 90
            ELSE 30
        END DAY)
    GROUP BY bucket;
END //

-- Procedure: Check and trigger alerts
CREATE PROCEDURE IF NOT EXISTS CheckAlerts()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_config_id INT;
    DECLARE v_alert_type VARCHAR(50);
    DECLARE v_threshold INT;
    DECLARE v_direction VARCHAR(10);
    DECLARE v_cooldown INT;
    
    DECLARE cur CURSOR FOR 
        SELECT id, alert_type, threshold_value, threshold_direction, cooldown_hours
        FROM alert_configs WHERE is_active = TRUE;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    alert_loop: LOOP
        FETCH cur INTO v_config_id, v_alert_type, v_threshold, v_direction, v_cooldown;
        IF done THEN
            LEAVE alert_loop;
        END IF;
        
        -- Check each alert type
        CASE v_alert_type
            WHEN 'conviction_spike' THEN
                INSERT INTO alert_history (alert_config_id, ticker, alert_type, trigger_value, 
                    conviction_score, trigger_price, trigger_detail)
                SELECT v_config_id, ch.ticker, v_alert_type, ch.conviction_score,
                    ch.conviction_score, ch.entry_price,
                    CONCAT('Conviction jumped to ', ch.conviction_score, ' (', ch.label, ')')
                FROM conviction_history ch
                LEFT JOIN alert_cooldowns cd ON cd.alert_type = v_alert_type 
                    AND cd.ticker = ch.ticker AND cd.cooldown_until > NOW()
                WHERE ch.conviction_score >= v_threshold
                AND cd.ticker IS NULL
                AND ch.calculation_date >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                ORDER BY ch.conviction_score DESC
                LIMIT 5;
                
            WHEN 'insider_cluster' THEN
                INSERT INTO alert_history (alert_config_id, ticker, alert_type, trigger_value,
                    insider_score, trigger_detail)
                SELECT v_config_id, ticker, v_alert_type, cluster_count,
                    85, -- estimated
                    CONCAT(cluster_count, ' insiders bought in 7 days')
                FROM (
                    SELECT ticker, COUNT(DISTINCT filer_name) as cluster_count
                    FROM gm_sec_insider_trades
                    WHERE transaction_type = 'P'
                    AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    GROUP BY ticker
                    HAVING cluster_count >= v_threshold
                ) clusters
                LEFT JOIN alert_cooldowns cd ON cd.alert_type = v_alert_type 
                    AND cd.ticker = clusters.ticker AND cd.cooldown_until > NOW()
                WHERE cd.ticker IS NULL
                LIMIT 5;
                
            WHEN 'fear_extreme' THEN
                INSERT INTO alert_history (alert_config_id, ticker, alert_type, trigger_value,
                    fear_greed_score, trigger_detail)
                SELECT v_config_id, ch.ticker, v_alert_type, ch.fear_greed_score,
                    ch.fear_greed_score,
                    CONCAT('Extreme fear detected: ', ch.fear_greed_score, '/100')
                FROM conviction_history ch
                LEFT JOIN alert_cooldowns cd ON cd.alert_type = v_alert_type 
                    AND cd.ticker = ch.ticker AND cd.cooldown_until > NOW()
                WHERE ch.fear_greed_score <= v_threshold
                AND cd.ticker IS NULL
                AND ch.calculation_date >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                LIMIT 5;
        END CASE;
        
        -- Set cooldown for triggered alerts
        INSERT INTO alert_cooldowns (alert_type, ticker, last_triggered, cooldown_until)
        SELECT v_alert_type, ticker, NOW(), DATE_ADD(NOW(), INTERVAL v_cooldown HOUR)
        FROM alert_history
        WHERE alert_config_id = v_config_id
        AND triggered_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        ON DUPLICATE KEY UPDATE
            last_triggered = VALUES(last_triggered),
            cooldown_until = VALUES(cooldown_until);
        
    END LOOP;
    
    CLOSE cur;
END //

DELIMITER ;

-- ============================================================================
-- PART 5: VIEWS FOR EASY REPORTING
-- ============================================================================

-- Latest conviction scores for all tickers
CREATE OR REPLACE VIEW v_latest_conviction AS
SELECT 
    ch.*,
    DATEDIFF(NOW(), ch.calculation_date) as days_since_calculation
FROM conviction_history ch
INNER JOIN (
    SELECT ticker, MAX(calculation_date) as max_date
    FROM conviction_history
    GROUP BY ticker
) latest ON ch.ticker = latest.ticker AND ch.calculation_date = latest.max_date;

-- Performance summary by ticker
CREATE OR REPLACE VIEW v_ticker_performance AS
SELECT 
    ticker,
    COUNT(*) as total_signals,
    AVG(conviction_score) as avg_conviction,
    AVG(return_30d) as avg_return_30d,
    SUM(CASE WHEN outcome_30d = 'win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome_30d = 'loss' THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN outcome_30d = 'win' THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN outcome_30d IN ('win', 'loss') THEN 1 ELSE 0 END), 0) * 100, 2) as win_rate,
    AVG(alpha_30d) as avg_alpha
FROM conviction_performance
WHERE return_30d IS NOT NULL
GROUP BY ticker;

-- Recent alerts with conviction context
CREATE OR REPLACE VIEW v_recent_alerts AS
SELECT 
    ah.*,
    ch.conviction_score as current_conviction,
    ch.label as current_label
FROM alert_history ah
LEFT JOIN v_latest_conviction ch ON ah.ticker = ch.ticker
WHERE ah.triggered_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY ah.triggered_at DESC;

-- ============================================================================
-- PART 6: CRON JOB SETUP (Add to your crontab)
-- ============================================================================

/*
# Update performance returns daily at 6:30 AM
30 6 * * * mysql -u username -p'password' database_name -e "CALL UpdatePerformanceReturns();"

# Calculate stats weekly on Sundays at 7 AM
0 7 * * 0 mysql -u username -p'password' database_name -e "CALL CalculateConvictionStats('30d');"

# Check alerts every hour
0 * * * * mysql -u username -p'password' database_name -e "CALL CheckAlerts();"

# Clean up old cooldowns daily
0 3 * * * mysql -u username -p'password' database_name -e "DELETE FROM alert_cooldowns WHERE cooldown_until < NOW();"
*/

-- ============================================================================
-- PART 7: SAMPLE QUERIES FOR DASHBOARD
-- ============================================================================

-- 1. Get top performing conviction levels
-- SELECT * FROM conviction_stats WHERE stat_period = '30d' ORDER BY avg_alpha DESC;

-- 2. Get tickers with recent conviction spikes
-- SELECT * FROM v_latest_conviction WHERE days_since_calculation <= 1 ORDER BY conviction_score DESC;

-- 3. Get unresolved alerts
-- SELECT * FROM alert_history WHERE email_sent = FALSE LIMIT 10;

-- 4. Get tickers needing performance update
-- SELECT ticker, conviction_date FROM conviction_performance 
-- WHERE return_30d IS NULL AND conviction_date <= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
