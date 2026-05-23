-- Portfolio Challenge Audit Tables
-- Database: ejaguiar1_stocks
-- Created: 2026-03-11

-- Portfolio state snapshots (every update cycle)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL,
    portfolio_name VARCHAR(100) NOT NULL,
    methodology VARCHAR(50) NOT NULL,
    category ENUM('signal', 'deep_value', 'hoffman_htf', 'prop_firm') NOT NULL DEFAULT 'signal',
    status ENUM('ACTIVE', 'PASSED', 'BLOWN', 'WAITING') NOT NULL DEFAULT 'ACTIVE',
    equity DECIMAL(15,2) NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    pnl_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    open_positions INT NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    total_commission DECIMAL(10,2) NOT NULL DEFAULT 0,
    resets INT NOT NULL DEFAULT 0,
    snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_port_time (portfolio_id, snapshot_at),
    INDEX idx_snapshot_at (snapshot_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Individual position tracking
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL,
    position_id VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction ENUM('LONG', 'SHORT') NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    source_system VARCHAR(50),
    entry_price DECIMAL(20,8) NOT NULL,
    take_profit DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    size_usd DECIMAL(12,2) NOT NULL,
    pnl_pct DECIMAL(8,4) DEFAULT 0,
    pnl_usd DECIMAL(12,2) DEFAULT 0,
    net_pnl_usd DECIMAL(12,2) DEFAULT 0,
    commission_entry DECIMAL(8,2) DEFAULT 0,
    commission_exit DECIMAL(8,2) DEFAULT 0,
    exit_reason VARCHAR(20),
    status ENUM('OPEN', 'TP_HIT', 'SL_HIT', 'TRAIL', 'TIME_EXIT', 'MAX_HOLD', 'FORCE_CLOSED') NOT NULL DEFAULT 'OPEN',
    opened_at DATETIME NOT NULL,
    closed_at DATETIME,
    rr_ratio DECIMAL(6,2),
    sys_wr DECIMAL(5,2),
    sys_pf DECIMAL(6,2),
    confidence DECIMAL(4,2),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_port_pos (portfolio_id, position_id),
    INDEX idx_symbol (symbol),
    INDEX idx_strategy (strategy),
    INDEX idx_status (status),
    INDEX idx_opened (opened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Reset history for prop firm and any blown portfolios
CREATE TABLE IF NOT EXISTS portfolio_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL,
    reset_num INT NOT NULL,
    equity_at_reset DECIMAL(15,2) NOT NULL,
    pnl_usd DECIMAL(12,2) NOT NULL,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    reason TEXT,
    reset_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_port_reset (portfolio_id, reset_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Strategy performance aggregation
CREATE TABLE IF NOT EXISTS portfolio_strategy_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy VARCHAR(100) NOT NULL,
    total_picks INT NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    total_pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    avg_pnl_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    best_pnl_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    worst_pnl_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    avg_hold_hours DECIMAL(8,2) NOT NULL DEFAULT 0,
    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_strategy (strategy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
