<?php
/**
 * Portfolio Schema - Creates tables for saved portfolios & daily tracking.
 * PHP 5.2 compatible.
 *
 * Usage: GET portfolio_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(

// 1. Saved portfolios (user-created from horizon picks)
"CREATE TABLE IF NOT EXISTS saved_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_name VARCHAR(200) NOT NULL,
    portfolio_key VARCHAR(64) NOT NULL DEFAULT '',
    horizon VARCHAR(20) NOT NULL DEFAULT 'swing',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    current_equity DECIMAL(12,2) NOT NULL DEFAULT 0,
    take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    max_hold_days INT NOT NULL DEFAULT 30,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    KEY idx_status (status),
    KEY idx_ip (ip_address),
    KEY idx_key (portfolio_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Portfolio positions (individual stock holdings)
"CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL DEFAULT '',
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    entry_date DATE NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares DECIMAL(12,4) NOT NULL DEFAULT 0,
    allocated_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    current_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    realized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    KEY idx_portfolio (portfolio_id),
    KEY idx_status (status),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Daily equity snapshots (for equity curve chart)
"CREATE TABLE IF NOT EXISTS portfolio_daily_equity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    snapshot_date DATE NOT NULL,
    equity_value DECIMAL(12,2) NOT NULL DEFAULT 0,
    cash_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    open_positions INT NOT NULL DEFAULT 0,
    daily_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    cumulative_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    spy_close DECIMAL(10,2) NOT NULL DEFAULT 0,
    UNIQUE KEY idx_portfolio_date (portfolio_id, snapshot_date),
    KEY idx_date (snapshot_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8"

);

foreach ($tables as $sql) {
    if ($conn->query($sql)) {
        $matches = array();
        preg_match('/CREATE TABLE IF NOT EXISTS (\w+)/', $sql, $matches);
        $tname = isset($matches[1]) ? $matches[1] : 'unknown';
        $results['actions'][] = 'OK: ' . $tname;
    } else {
        $results['ok'] = false;
        $results['actions'][] = 'FAIL: ' . $conn->error;
    }
}

echo json_encode($results);
$conn->close();
?>
