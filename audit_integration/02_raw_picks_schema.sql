
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
