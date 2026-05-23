
-- Ensure at_signal_outcomes has strategy tracking
ALTER TABLE at_signal_outcomes
ADD COLUMN IF NOT EXISTS strategy_category VARCHAR(50) AFTER strategy_name,
ADD COLUMN IF NOT EXISTS exit_reason VARCHAR(50) AFTER pnl_pct,
ADD COLUMN IF NOT EXISTS max_drawdown_pct DECIMAL(8,4) AFTER exit_reason,
ADD COLUMN IF NOT EXISTS hold_time_hours DECIMAL(8,2) AFTER max_drawdown_pct;

-- Index for performance analysis
CREATE INDEX IF NOT EXISTS idx_outcomes_category ON at_signal_outcomes(strategy_category, exit_time);
