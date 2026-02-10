<?php
/**
 * GOLDMINE_CURSOR — Setup / Ensure Tables
 * Creates all goldmine_cursor_* tables if they don't exist.
 * Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
 * PHP 5.2 compatible.
 *
 * Usage: GET /goldmine_cursor/api/setup_tables.php?key=goldmine2026
 */
require_once dirname(__FILE__) . '/db_connect.php';

$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'goldmine2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    $conn->close();
    exit;
}

$tables_created = array();
$errors = array();

// ═══════════════════════════════════════════════════════════
// TABLE 1: goldmine_cursor_predictions
// Master ledger — INSERT-ONLY for new predictions.
// Only status/exit fields updated when resolved.
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id VARCHAR(64) NOT NULL,
    asset_class VARCHAR(20) NOT NULL COMMENT 'stocks|crypto|forex|sports|mutualfunds|etf|meme|penny',
    ticker VARCHAR(30) NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'long' COMMENT 'long|short|over|under',
    entry_price DECIMAL(16,6) NOT NULL DEFAULT 0,
    target_price DECIMAL(16,6) NOT NULL DEFAULT 0,
    stop_loss DECIMAL(16,6) NOT NULL DEFAULT 0,
    confidence_score INT NOT NULL DEFAULT 0 COMMENT '0-100',
    source_system VARCHAR(50) NOT NULL COMMENT 'findstocks|findcryptopairs|findforex2|live-monitor|findmutualfunds',
    logged_at DATETIME NOT NULL COMMENT 'Timestamp when prediction was recorded (immutable)',
    market_regime VARCHAR(20) NOT NULL DEFAULT 'unknown' COMMENT 'bull|bear|sideways|high_vol',
    status VARCHAR(20) NOT NULL DEFAULT 'open' COMMENT 'open|won|lost|expired|cancelled',
    exit_price DECIMAL(16,6) DEFAULT NULL,
    exit_date DATETIME DEFAULT NULL,
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    benchmark_return_pct DECIMAL(8,4) DEFAULT NULL COMMENT 'benchmark return over same holding period',
    hold_days INT DEFAULT NULL,
    resolved_at DATETIME DEFAULT NULL,
    UNIQUE KEY idx_pred_id (prediction_id),
    KEY idx_asset (asset_class),
    KEY idx_algo (algorithm),
    KEY idx_status (status),
    KEY idx_logged (logged_at),
    KEY idx_source (source_system),
    KEY idx_regime (market_regime)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_predictions';
} else {
    $errors[] = 'goldmine_cursor_predictions: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 2: goldmine_cursor_algo_scorecard
// Weekly algorithm performance snapshots
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_algo_scorecard (
    id INT AUTO_INCREMENT PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    total_picks INT NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
    avg_gain_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    expectancy DECIMAL(8,4) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) DEFAULT NULL,
    sortino_ratio DECIMAL(8,4) DEFAULT NULL,
    max_drawdown_pct DECIMAL(8,4) DEFAULT NULL,
    benchmark_return_pct DECIMAL(8,4) DEFAULT NULL,
    alpha_pct DECIMAL(8,4) DEFAULT NULL COMMENT 'algo return - benchmark return',
    deflated_sharpe DECIMAL(8,4) DEFAULT NULL,
    regime VARCHAR(20) NOT NULL DEFAULT 'unknown',
    verdict VARCHAR(20) NOT NULL DEFAULT 'neutral' COMMENT 'hidden_winner|strong|neutral|underperform|needs_review',
    snapshot_at DATETIME NOT NULL,
    UNIQUE KEY idx_week_algo (week_start, algorithm, asset_class),
    KEY idx_verdict (verdict),
    KEY idx_week (week_start)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_algo_scorecard';
} else {
    $errors[] = 'goldmine_cursor_algo_scorecard: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 3: goldmine_cursor_benchmarks
// Daily benchmark prices for comparison
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    benchmark VARCHAR(20) NOT NULL COMMENT 'SPY|BTC|EURUSD|VFINX',
    trade_date DATE NOT NULL,
    close_price DECIMAL(16,6) NOT NULL,
    UNIQUE KEY idx_bench_date (benchmark, trade_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_benchmarks';
} else {
    $errors[] = 'goldmine_cursor_benchmarks: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 4: goldmine_cursor_regime_log
// Market regime detection log
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_regime_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    detected_date DATE NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    regime VARCHAR(20) NOT NULL COMMENT 'bull|bear|sideways|high_vol',
    vix_level DECIMAL(8,2) DEFAULT NULL,
    sma50_trend VARCHAR(10) DEFAULT NULL COMMENT 'above|below',
    sma200_trend VARCHAR(10) DEFAULT NULL COMMENT 'above|below',
    notes TEXT,
    UNIQUE KEY idx_date_class (detected_date, asset_class)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_regime_log';
} else {
    $errors[] = 'goldmine_cursor_regime_log: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 5: goldmine_cursor_correlation_matrix
// Algorithm correlation snapshots
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_correlation_matrix (
    id INT AUTO_INCREMENT PRIMARY KEY,
    computed_date DATE NOT NULL,
    algo_a VARCHAR(80) NOT NULL,
    algo_b VARCHAR(80) NOT NULL,
    overlap_pct DECIMAL(6,2) NOT NULL DEFAULT 0 COMMENT 'pct of picks that are identical tickers',
    return_correlation DECIMAL(6,4) DEFAULT NULL COMMENT 'Pearson correlation of returns',
    KEY idx_date (computed_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_correlation_matrix';
} else {
    $errors[] = 'goldmine_cursor_correlation_matrix: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 6: goldmine_cursor_circuit_breaker
// Max-drawdown circuit breaker events
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_circuit_breaker (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm VARCHAR(80) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    triggered_at DATETIME NOT NULL,
    drawdown_pct DECIMAL(8,4) NOT NULL,
    threshold_pct DECIMAL(8,4) NOT NULL DEFAULT 15.00,
    status VARCHAR(20) NOT NULL DEFAULT 'triggered' COMMENT 'triggered|acknowledged|resumed',
    notes TEXT,
    KEY idx_algo (algorithm),
    KEY idx_status (status)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_circuit_breaker';
} else {
    $errors[] = 'goldmine_cursor_circuit_breaker: ' . $conn->error;
}

// ═══════════════════════════════════════════════════════════
// TABLE 7: goldmine_cursor_data_health
// Data freshness and health monitoring
// ═══════════════════════════════════════════════════════════
$sql = "CREATE TABLE IF NOT EXISTS goldmine_cursor_data_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checked_at DATETIME NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    last_data_time DATETIME DEFAULT NULL,
    hours_stale DECIMAL(8,2) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ok' COMMENT 'ok|warning|stale|dead',
    details TEXT,
    KEY idx_source (source_system),
    KEY idx_status (status)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql)) {
    $tables_created[] = 'goldmine_cursor_data_health';
} else {
    $errors[] = 'goldmine_cursor_data_health: ' . $conn->error;
}

$conn->close();

$response = array(
    'ok' => count($errors) === 0,
    'tables_created' => $tables_created,
    'total' => count($tables_created)
);
if (count($errors) > 0) {
    $response['errors'] = $errors;
}

echo json_encode($response);
?>
