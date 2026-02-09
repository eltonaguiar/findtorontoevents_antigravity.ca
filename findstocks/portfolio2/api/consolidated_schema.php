<?php
/**
 * Consolidated Picks — Schema
 * Creates cache + consensus history tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../consolidated_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$response = array('ok' => true, 'tables_created' => array());

// ── consolidated_cache: key/value store for API response caching ──
$sql = "CREATE TABLE IF NOT EXISTS consolidated_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(64) NOT NULL,
    cache_data LONGTEXT,
    generated_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    UNIQUE KEY idx_key (cache_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'consolidated_cache';
} else {
    $response['errors'][] = 'consolidated_cache: ' . $conn->error;
}

// ── consensus_history: daily snapshots of consensus picks ──
$sql = "CREATE TABLE IF NOT EXISTS consensus_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    consensus_date DATE NOT NULL,
    consensus_count INT NOT NULL DEFAULT 0,
    consensus_score DECIMAL(10,4) NOT NULL DEFAULT 0,
    source_algos TEXT,
    source_tables TEXT,
    avg_entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    latest_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_date (ticker, consensus_date),
    KEY idx_date (consensus_date),
    KEY idx_score (consensus_score),
    KEY idx_count (consensus_count)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'consensus_history';
} else {
    $response['errors'][] = 'consensus_history: ' . $conn->error;
}

// ── stock_analyst_recs: Yahoo Finance analyst recommendations ──
$sql = "CREATE TABLE IF NOT EXISTS stock_analyst_recs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL DEFAULT '0m',
    strong_buy INT NOT NULL DEFAULT 0,
    buy INT NOT NULL DEFAULT 0,
    hold_count INT NOT NULL DEFAULT 0,
    sell INT NOT NULL DEFAULT 0,
    strong_sell INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'stock_analyst_recs';
} else {
    $response['errors'][] = 'stock_analyst_recs: ' . $conn->error;
}

// ── daytrader_sim_days: daily $500 simulation results ──
$sql = "CREATE TABLE IF NOT EXISTS daytrader_sim_days (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sim_date DATE NOT NULL,
    budget DECIMAL(12,2) NOT NULL DEFAULT 500.00,
    picks_used INT NOT NULL DEFAULT 0,
    total_invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    best_pick_ticker VARCHAR(10) NOT NULL DEFAULT '',
    best_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_pick_ticker VARCHAR(10) NOT NULL DEFAULT '',
    worst_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    algo_version VARCHAR(20) NOT NULL DEFAULT 'original',
    cumulative_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_date_version (sim_date, algo_version),
    KEY idx_date (sim_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'daytrader_sim_days';
} else {
    $response['errors'][] = 'daytrader_sim_days: ' . $conn->error;
}

// ── daytrader_sim_trades: individual trades within each sim day ──
$sql = "CREATE TABLE IF NOT EXISTS daytrader_sim_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sim_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL DEFAULT '',
    source_table VARCHAR(30) NOT NULL DEFAULT '',
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares INT NOT NULL DEFAULT 0,
    invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    algo_version VARCHAR(20) NOT NULL DEFAULT 'original',
    created_at DATETIME NOT NULL,
    KEY idx_date (sim_date),
    KEY idx_ticker (ticker),
    KEY idx_version (algo_version)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'daytrader_sim_trades';
} else {
    $response['errors'][] = 'daytrader_sim_trades: ' . $conn->error;
}

echo json_encode($response);
$conn->close();
?>
