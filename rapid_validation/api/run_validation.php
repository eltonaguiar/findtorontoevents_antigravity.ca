<?php
/**
 * Rapid Validation Runner - PHP Implementation
 * CLAUDECODE_Feb152026
 *
 * Runs on server with database access, triggered by GitHub Actions
 * Pure PHP implementation - no Python dependencies needed
 * PHP 5.2 Compatible Version
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$key = isset($_GET['key']) ? $_GET['key'] : '';

// Simple authentication
if ($key !== 'livetrader2026') {
    http_response_code(401);
    echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
    exit;
}

// Database credentials
$DB_HOST = 'mysql.50webs.com';
$DB_USER = 'ejaguiar1_stocks';
$DB_PASS = 'stocks';
$DB_NAME = 'ejaguiar1_stocks';

// Connect to database
$conn = @mysqli_connect($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME);

if (!$conn) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Database connection failed',
        'details' => mysqli_connect_error()
    ));
    exit;
}

// Quality thresholds
$MIN_TRADES = 50;
$MIN_WIN_RATE = 55.0;

// 1. Create tables if they don't exist
$create_signals = "CREATE TABLE IF NOT EXISTS rapid_signals (
    signal_id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    pair VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL,
    strength DECIMAL(5,2) NOT NULL,
    entry_price DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'open',
    outcome VARCHAR(20) DEFAULT NULL,
    closed_at TIMESTAMP NULL,
    pnl DECIMAL(10,2) DEFAULT NULL,
    INDEX idx_strategy (strategy_name),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
)";
mysqli_query($conn, $create_signals);

$create_stats = "CREATE TABLE IF NOT EXISTS rapid_strategy_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) UNIQUE NOT NULL,
    total_trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    avg_pnl DECIMAL(10,2) DEFAULT 0,
    total_pnl DECIMAL(10,2) DEFAULT 0,
    rank VARCHAR(20) DEFAULT 'testing',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rank (rank)
)";
mysqli_query($conn, $create_stats);

// 2. Update strategy stats from closed signals
$update_stats = "INSERT INTO rapid_strategy_stats 
    (strategy_name, total_trades, wins, losses, win_rate, avg_pnl, total_pnl)
    SELECT
        strategy_name,
        COUNT(*) as total_trades,
        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
        ROUND(100.0 * SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
        ROUND(AVG(COALESCE(pnl, 0)), 2) as avg_pnl,
        ROUND(SUM(COALESCE(pnl, 0)), 2) as total_pnl
    FROM rapid_signals
    WHERE status = 'closed' AND outcome IS NOT NULL
    GROUP BY strategy_name
    ON DUPLICATE KEY UPDATE
        total_trades = VALUES(total_trades),
        wins = VALUES(wins),
        losses = VALUES(losses),
        win_rate = VALUES(win_rate),
        avg_pnl = VALUES(avg_pnl),
        total_pnl = VALUES(total_pnl)";
mysqli_query($conn, $update_stats);
$updated_stats = mysqli_affected_rows($conn);

// 3. Reset all ranks to testing
mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank = 'testing'");

// 4. Promote strategies with enough trades and good win rate
$promote_sql = "UPDATE rapid_strategy_stats 
    SET rank = 'promoted' 
    WHERE total_trades >= $MIN_TRADES AND win_rate >= $MIN_WIN_RATE";
mysqli_query($conn, $promote_sql);
$promoted = mysqli_affected_rows($conn);

// 5. Eliminate strategies with enough trades but poor win rate
$eliminate_sql = "UPDATE rapid_strategy_stats 
    SET rank = 'eliminated' 
    WHERE total_trades >= $MIN_TRADES AND win_rate < $MIN_WIN_RATE";
mysqli_query($conn, $eliminate_sql);
$eliminated = mysqli_affected_rows($conn);

// 6. Get final rankings
$result = mysqli_query($conn, "SELECT rank, COUNT(*) as count FROM rapid_strategy_stats GROUP BY rank");
$rankings = array('promoted' => 0, 'testing' => 0, 'eliminated' => 0);
if ($result) {
    while ($row = mysqli_fetch_assoc($result)) {
        $rankings[$row['rank']] = (int)$row['count'];
    }
}

// 7. Get signal counts
$total_result = mysqli_query($conn, "SELECT COUNT(*) as total FROM rapid_signals");
$total_signals = 0;
if ($total_result) {
    $total_row = mysqli_fetch_assoc($total_result);
    $total_signals = (int)$total_row['total'];
}

$closed_result = mysqli_query($conn, "SELECT COUNT(*) as closed FROM rapid_signals WHERE status = 'closed'");
$closed_signals = 0;
if ($closed_result) {
    $closed_row = mysqli_fetch_assoc($closed_result);
    $closed_signals = (int)$closed_row['closed'];
}

mysqli_close($conn);

echo json_encode(array(
    'ok' => true,
    'action' => 'validation_complete',
    'rankings' => $rankings,
    'changes' => array(
        'updated_stats' => $updated_stats,
        'promoted' => $promoted,
        'eliminated' => $eliminated
    ),
    'signals' => array(
        'total' => $total_signals,
        'closed' => $closed_signals
    ),
    'thresholds' => array(
        'min_trades' => $MIN_TRADES,
        'min_win_rate' => $MIN_WIN_RATE
    ),
    'timestamp' => date('Y-m-d H:i:s')
));
?>
