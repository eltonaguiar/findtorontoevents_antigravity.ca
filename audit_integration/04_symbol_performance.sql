
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
