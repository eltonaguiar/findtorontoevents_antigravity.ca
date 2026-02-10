<?php
/**
 * Consensus Performance Tracking — Schema
 * Tables for tracking consensus pick outcomes, self-learning, and $200/day challenge.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$response = array('ok' => true, 'tables_created' => array(), 'errors' => array());

// ── consensus_tracked: each consensus pick as a virtual position ──
$sql = "CREATE TABLE IF NOT EXISTS consensus_tracked (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(100) NOT NULL DEFAULT '',
    entry_date DATE NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    consensus_count INT NOT NULL DEFAULT 0,
    consensus_score DECIMAL(10,4) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    source_algos TEXT,
    target_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 8.00,
    target_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 4.00,
    max_hold_days INT NOT NULL DEFAULT 14,
    current_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    current_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    peak_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    trough_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    exit_date DATE DEFAULT NULL,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(30) NOT NULL DEFAULT '',
    final_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    hold_days INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_date (ticker, entry_date),
    KEY idx_status (status),
    KEY idx_entry_date (entry_date),
    KEY idx_return (final_return_pct)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'consensus_tracked';
} else {
    $response['errors'][] = 'consensus_tracked: ' . $conn->error;
}

// ── consensus_performance_daily: daily snapshot of overall performance ──
$sql = "CREATE TABLE IF NOT EXISTS consensus_performance_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    track_date DATE NOT NULL,
    open_positions INT NOT NULL DEFAULT 0,
    total_closed INT NOT NULL DEFAULT 0,
    total_wins INT NOT NULL DEFAULT 0,
    total_losses INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
    total_pnl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    best_ticker VARCHAR(10) NOT NULL DEFAULT '',
    best_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_ticker VARCHAR(10) NOT NULL DEFAULT '',
    worst_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_hold_days DECIMAL(6,1) NOT NULL DEFAULT 0,
    current_streak INT NOT NULL DEFAULT 0,
    portfolio_value DECIMAL(12,2) NOT NULL DEFAULT 10000,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_date (track_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'consensus_performance_daily';
} else {
    $response['errors'][] = 'consensus_performance_daily: ' . $conn->error;
}

// ── consensus_lessons: auto-detected patterns and lessons ──
$sql = "CREATE TABLE IF NOT EXISTS consensus_lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lesson_date DATE NOT NULL,
    lesson_type VARCHAR(30) NOT NULL,
    lesson_title VARCHAR(200) NOT NULL DEFAULT '',
    lesson_text TEXT NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    supporting_data TEXT,
    applied INT NOT NULL DEFAULT 0,
    impact_score DECIMAL(6,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    KEY idx_date (lesson_date),
    KEY idx_type (lesson_type),
    KEY idx_confidence (confidence)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'consensus_lessons';
} else {
    $response['errors'][] = 'consensus_lessons: ' . $conn->error;
}

// ── challenge_200_days: $200/day challenge daily results ──
$sql = "CREATE TABLE IF NOT EXISTS challenge_200_days (
    id INT AUTO_INCREMENT PRIMARY KEY,
    challenge_date DATE NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'consensus',
    capital DECIMAL(12,2) NOT NULL DEFAULT 5000,
    picks_count INT NOT NULL DEFAULT 0,
    total_invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    daily_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    daily_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    target_amount DECIMAL(12,2) NOT NULL DEFAULT 200,
    target_hit INT NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    best_pick VARCHAR(10) NOT NULL DEFAULT '',
    best_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_pick VARCHAR(10) NOT NULL DEFAULT '',
    worst_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    cumulative_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    cumulative_days INT NOT NULL DEFAULT 0,
    win_streak INT NOT NULL DEFAULT 0,
    lessons_json TEXT,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_date_mode (challenge_date, mode),
    KEY idx_mode (mode),
    KEY idx_date (challenge_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'challenge_200_days';
} else {
    $response['errors'][] = 'challenge_200_days: ' . $conn->error;
}

// ── challenge_200_trades: individual trades within each challenge day ──
$sql = "CREATE TABLE IF NOT EXISTS challenge_200_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    challenge_date DATE NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'consensus',
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(100) NOT NULL DEFAULT '',
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares DECIMAL(12,4) NOT NULL DEFAULT 0,
    invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    consensus_count INT NOT NULL DEFAULT 0,
    consensus_score DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(30) NOT NULL DEFAULT '',
    algo_notes TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_date_mode (challenge_date, mode),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";
if ($conn->query($sql)) {
    $response['tables_created'][] = 'challenge_200_trades';
} else {
    $response['errors'][] = 'challenge_200_trades: ' . $conn->error;
}

// Only echo + close when called directly (not when included)
if (basename($_SERVER['SCRIPT_FILENAME']) === basename(__FILE__)) {
    echo json_encode($response);
    $conn->close();
}
?>
