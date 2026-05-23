-- NEW STRATEGY AUDIT INTEGRATION

-- Generated: 2026-03-08T01:07:14.586593

-- Run these SQL statements in order


-- Strategy Registry Insert/Update Statements
-- Generated: 2026-03-08T01:07:14.580954


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'KC_SCALP_v1',
    'PROP_FIRM',
    'SCALPING',
    'Keltner Channel compression breakout scalper',
    0.75,
    2.0,
    0.05,
    '1h',
    4,
    0.1,
    1.5,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]',
    'Keltner band compression + volume expansion',
    'ATR-based TP/SL + 4h time stop',
    'APPROVED_FOR_FORWARD',
    0.15,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.75,
    target_profit_factor = 2.0,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.15,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'VWAP_ELITE_v1',
    'PROP_FIRM',
    'MEAN_REVERSION',
    'VWAP mean reversion with RSI and volatility filters',
    0.7,
    1.8,
    0.06,
    '1h',
    6,
    0.08,
    1.5,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT"]',
    'Price >2std from VWAP + RSI extreme + vol filter',
    'Return to VWAP or 6h time stop',
    'APPROVED_FOR_FORWARD',
    0.12,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.7,
    target_profit_factor = 1.8,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.12,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'MTF_RSI_v1',
    'PROP_FIRM',
    'MOMENTUM',
    'Multi-timeframe RSI confluence for high-confidence entries',
    0.72,
    1.9,
    0.05,
    '1h',
    12,
    0.1,
    1.67,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]',
    'RSI(1h,4h,1d) all aligned oversold/overbought',
    'RSI reversion to 50 or TP/SL',
    'APPROVED_FOR_FORWARD',
    0.13,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.72,
    target_profit_factor = 1.9,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.13,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'FLASH_REV_v1',
    'GENERAL',
    'CRISIS_ALPHA',
    'Flash crash reversal hunter - extreme drop capture',
    0.78,
    2.5,
    0.08,
    '1h',
    12,
    0.05,
    2.0,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"]',
    '>5% drop in 4h + RSI <25 + volume spike',
    'RSI recovery or 12h time stop',
    'APPROVED_FOR_FORWARD',
    0.08,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.78,
    target_profit_factor = 2.5,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.08,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'FUNDING_PRO_v1',
    'GENERAL',
    'FUNDING_ARB',
    'Funding rate momentum with RSI confirmation',
    0.7,
    2.0,
    0.06,
    '1h',
    8,
    0.08,
    1.67,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]',
    'Extreme funding rate + RSI confirmation',
    'Funding normalization or TP/SL',
    'APPROVED_FOR_FORWARD',
    0.1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.7,
    target_profit_factor = 2.0,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.1,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'HMA_TREND_v1',
    'GENERAL',
    'TREND_FOLLOWING',
    'HMA trend following with ADX confirmation',
    0.65,
    1.8,
    0.08,
    '1h',
    24,
    0.08,
    2.0,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "LINKUSDT"]',
    'HMA slope + ADX>25 + pullback to HMA',
    'HMA reversal or trailing stop',
    'APPROVED_FOR_FORWARD',
    0.08,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.65,
    target_profit_factor = 1.8,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.08,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'BB_SQUEEZE_v1',
    'GENERAL',
    'BREAKOUT',
    'Bollinger Band squeeze breakout with volume',
    0.68,
    1.8,
    0.06,
    '1h',
    8,
    0.08,
    1.67,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "MATICUSDT"]',
    'BB width compression + breakout + volume',
    'Opposite band touch or TP/SL',
    'APPROVED_FOR_FORWARD',
    0.08,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.68,
    target_profit_factor = 1.8,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.08,
    updated_at = NOW();


INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    'MULTI_FACTOR_v1',
    'GENERAL',
    'ENSEMBLE',
    'Adaptive multi-factor scoring ensemble',
    0.65,
    1.7,
    0.07,
    '1h',
    12,
    0.06,
    1.67,
    'CRYPTO',
    '["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]',
    'Composite score >0.6 from trend/momentum/vol/volume',
    'Score reversal or 12h time stop',
    'APPROVED_FOR_FORWARD',
    0.06,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = 0.65,
    target_profit_factor = 1.7,
    status = 'APPROVED_FOR_FORWARD',
    forward_test_allocation = 0.06,
    updated_at = NOW();



--
-- Schema Updates
--



-- Update at_raw_picks schema for new strategies
-- Adds columns if they don't exist

ALTER TABLE at_raw_picks 
ADD COLUMN IF NOT EXISTS strategy_category VARCHAR(50) AFTER strategy_name,
ADD COLUMN IF NOT EXISTS risk_reward DECIMAL(5,2) AFTER confidence,
ADD COLUMN IF NOT EXISTS hold_time_hours INT AFTER risk_reward,
ADD COLUMN IF NOT EXISTS pnl_pct_current DECIMAL(8,4) AFTER exit_price,
ADD COLUMN IF NOT EXISTS rsi_1h DECIMAL(5,2) AFTER pnl_pct_current,
ADD COLUMN IF NOT EXISTS hma_slope TINYINT AFTER rsi_1h,
ADD COLUMN IF NOT EXISTS volume_ratio DECIMAL(5,2) AFTER hma_slope;

-- Add index for new strategy lookups
CREATE INDEX IF NOT EXISTS idx_strategy_category ON at_raw_picks(strategy_category);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON at_raw_picks(status, strategy_name);



-- Ensure at_signal_outcomes has strategy tracking
ALTER TABLE at_signal_outcomes
ADD COLUMN IF NOT EXISTS strategy_category VARCHAR(50) AFTER strategy_name,
ADD COLUMN IF NOT EXISTS exit_reason VARCHAR(50) AFTER pnl_pct,
ADD COLUMN IF NOT EXISTS max_drawdown_pct DECIMAL(8,4) AFTER exit_reason,
ADD COLUMN IF NOT EXISTS hold_time_hours DECIMAL(8,2) AFTER max_drawdown_pct;

-- Index for performance analysis
CREATE INDEX IF NOT EXISTS idx_outcomes_category ON at_signal_outcomes(strategy_category, exit_time);



-- Create/update strategy_symbol_performance table
CREATE TABLE IF NOT EXISTS at_strategy_symbol_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    total_trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    avg_win_pct DECIMAL(10,6) DEFAULT 0,
    avg_loss_pct DECIMAL(10,6) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    total_pnl_pct DECIMAL(10,6) DEFAULT 0,
    max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
    last_trade_time TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_strat_sym (strategy_name, symbol),
    INDEX idx_performance (win_rate, total_trades)
) ENGINE=InnoDB;

-- Insert placeholder rows for new strategies
