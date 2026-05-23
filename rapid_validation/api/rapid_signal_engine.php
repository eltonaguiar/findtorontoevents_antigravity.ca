<?php
/**
 * Rapid Validation Signal Engine API
 * CLAUDECODE_Feb152026
 * 
 * Provides API endpoints for the rapid validation system
 * Uses PHP/mysqli instead of Python (server lacks mysql-connector)
 * PHP 5.2 Compatible Version
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$key = isset($_GET['key']) ? $_GET['key'] : '';

// Auth required for non-status actions
if ($action !== 'status' && $key !== 'livetrader2026') {
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

if (!$conn && $action !== 'status') {
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

switch ($action) {
    case 'status':
        // Get current rankings
        $rankings = array('promoted' => 0, 'testing' => 0, 'eliminated' => 0);
        $total_signals = 0;
        $closed_signals = 0;
        
        if ($conn) {
            $result = mysqli_query($conn, "SELECT rank, COUNT(*) as count FROM rapid_strategy_stats GROUP BY rank");
            if ($result) {
                while ($row = mysqli_fetch_assoc($result)) {
                    $rankings[$row['rank']] = (int)$row['count'];
                }
            }
            
            // Get total signals
            $total_result = mysqli_query($conn, "SELECT COUNT(*) as total FROM rapid_signals");
            if ($total_result) {
                $total_row = mysqli_fetch_assoc($total_result);
                $total_signals = (int)$total_row['total'];
            }
            
            // Get closed signals
            $closed_result = mysqli_query($conn, "SELECT COUNT(*) as closed FROM rapid_signals WHERE status = 'closed'");
            if ($closed_result) {
                $closed_row = mysqli_fetch_assoc($closed_result);
                $closed_signals = (int)$closed_row['closed'];
            }
        }
        
        echo json_encode(array(
            'ok' => true,
            'initialized' => true,
            'rankings' => $rankings,
            'signals' => array(
                'total' => $total_signals,
                'closed' => $closed_signals
            ),
            'timestamp' => date('Y-m-d H:i:s')
        ));
        break;
        
    case 'validate':
        // Create tables if they don't exist
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
        
        // Update strategy stats from closed signals
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
        
        $updated = mysqli_affected_rows($conn);
        
        echo json_encode(array(
            'ok' => true,
            'action' => 'validation_complete',
            'updated_strategies' => $updated,
            'timestamp' => date('Y-m-d H:i:s')
        ));
        break;
        
    case 'rank':
        // Re-rank all strategies based on performance
        // First, mark all as testing
        mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank = 'testing'");
        
        // Promote strategies with enough trades and good win rate
        $promote_sql = "UPDATE rapid_strategy_stats 
            SET rank = 'promoted' 
            WHERE total_trades >= $MIN_TRADES AND win_rate >= $MIN_WIN_RATE";
        mysqli_query($conn, $promote_sql);
        $promoted = mysqli_affected_rows($conn);
        
        // Eliminate strategies with enough trades but poor win rate
        $eliminate_sql = "UPDATE rapid_strategy_stats 
            SET rank = 'eliminated' 
            WHERE total_trades >= $MIN_TRADES AND win_rate < $MIN_WIN_RATE";
        mysqli_query($conn, $eliminate_sql);
        $eliminated = mysqli_affected_rows($conn);
        
        // Get current counts
        $result = mysqli_query($conn, "SELECT rank, COUNT(*) as count FROM rapid_strategy_stats GROUP BY rank");
        $rankings = array('promoted' => 0, 'testing' => 0, 'eliminated' => 0);
        if ($result) {
            while ($row = mysqli_fetch_assoc($result)) {
                $rankings[$row['rank']] = (int)$row['count'];
            }
        }
        
        echo json_encode(array(
            'ok' => true,
            'action' => 'ranking_complete',
            'changes' => array(
                'promoted' => $promoted,
                'eliminated' => $eliminated
            ),
            'rankings' => $rankings,
            'timestamp' => date('Y-m-d H:i:s')
        ));
        break;
        
    case 'cycle':
        // Run full cycle: validate then rank
        // Step 1: Validate (update stats)
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
        
        // Step 2: Rank
        mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank = 'testing'");
        
        mysqli_query($conn, "UPDATE rapid_strategy_stats 
            SET rank = 'promoted' 
            WHERE total_trades >= $MIN_TRADES AND win_rate >= $MIN_WIN_RATE");
        $promoted = mysqli_affected_rows($conn);
        
        mysqli_query($conn, "UPDATE rapid_strategy_stats 
            SET rank = 'eliminated' 
            WHERE total_trades >= $MIN_TRADES AND win_rate < $MIN_WIN_RATE");
        $eliminated = mysqli_affected_rows($conn);
        
        // Get final counts
        $result = mysqli_query($conn, "SELECT rank, COUNT(*) as count FROM rapid_strategy_stats GROUP BY rank");
        $rankings = array('promoted' => 0, 'testing' => 0, 'eliminated' => 0);
        if ($result) {
            while ($row = mysqli_fetch_assoc($result)) {
                $rankings[$row['rank']] = (int)$row['count'];
            }
        }
        
        echo json_encode(array(
            'ok' => true,
            'action' => 'cycle_complete',
            'results' => array(
                'validate' => 'ok',
                'rank' => array(
                    'promoted' => $promoted,
                    'eliminated' => $eliminated
                )
            ),
            'rankings' => $rankings,
            'timestamp' => date('Y-m-d H:i:s')
        ));
        break;
        
    case 'ingest':
        // Accept POST JSON body with closed picks from Rise of the Claw live competition
        $raw = file_get_contents('php://input');
        $payload = json_decode($raw, true);

        if (!$payload || !isset($payload['picks']) || !is_array($payload['picks'])) {
            echo json_encode(array('ok' => false, 'error' => 'Expected JSON body: {"picks": [...]}'));
            break;
        }

        // Ensure tables exist
        $create_signals_i = "CREATE TABLE IF NOT EXISTS rapid_signals (
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
            pnl DECIMAL(10,4) DEFAULT NULL,
            INDEX idx_strategy (strategy_name),
            INDEX idx_status (status),
            INDEX idx_created (created_at)
        )";
        mysqli_query($conn, $create_signals_i);

        $create_stats_i = "CREATE TABLE IF NOT EXISTS rapid_strategy_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            strategy_name VARCHAR(100) UNIQUE NOT NULL,
            total_trades INT DEFAULT 0,
            wins INT DEFAULT 0,
            losses INT DEFAULT 0,
            win_rate DECIMAL(5,2) DEFAULT 0,
            avg_pnl DECIMAL(10,4) DEFAULT 0,
            total_pnl DECIMAL(10,4) DEFAULT 0,
            rank VARCHAR(20) DEFAULT 'testing',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_rank (rank)
        )";
        mysqli_query($conn, $create_stats_i);

        $ingested = 0;
        $skipped  = 0;
        $err_msgs = array();

        foreach ($payload['picks'] as $pick) {
            $strategy   = isset($pick['algorithm']) ? $pick['algorithm'] : '';
            $pair       = isset($pick['symbol'])    ? $pick['symbol']    : '';
            if (!$strategy || !$pair) { $skipped++; continue; }

            $strategy   = mysqli_real_escape_string($conn, substr($strategy, 0, 100));
            $pair       = mysqli_real_escape_string($conn, substr($pair, 0, 20));
            $entry_price = isset($pick['entry_price']) ? (float)$pick['entry_price'] : 0.0;
            $exit_price  = isset($pick['exit_price'])  ? (float)$pick['exit_price']  : 0.0;
            // pnl stored as decimal fraction (e.g. -0.08 = -8%)
            $pnl_raw    = isset($pick['pnl']) ? (float)$pick['pnl'] : 0.0;
            $outcome    = (isset($pick['outcome']) && $pick['outcome'] === 'win') ? 'win' : 'loss';
            // Dates: accept ISO string, fallback to NOW()
            $created_at = isset($pick['entry_date']) ? mysqli_real_escape_string($conn, substr($pick['entry_date'], 0, 19)) : null;
            $closed_at  = isset($pick['exit_date'])  ? mysqli_real_escape_string($conn, substr($pick['exit_date'],  0, 19)) : null;

            // strength: 50 base + (pnl% * 5), clamped 0-100
            $strength = min(100.0, max(0.0, 50.0 + ($pnl_raw * 100 * 5)));

            $ca_sql = $created_at ? "'$created_at'" : 'NOW()';
            $cl_sql = $closed_at  ? "'$closed_at'"  : 'NOW()';
            $ep_sql = $entry_price > 0 ? $entry_price : 'NULL';
            $tp_sql = $exit_price  > 0 ? $exit_price  : 'NULL';

            $ins = "INSERT INTO rapid_signals
                (strategy_name, pair, signal_type, strength, entry_price, take_profit, stop_loss,
                 created_at, status, outcome, closed_at, pnl)
                VALUES (
                    '$strategy', '$pair', 'long', $strength, $ep_sql, $tp_sql, NULL,
                    $ca_sql, 'closed', '$outcome', $cl_sql, $pnl_raw
                )";

            if (mysqli_query($conn, $ins)) {
                $ingested++;
            } else {
                $err_msgs[] = mysqli_error($conn);
                $skipped++;
            }
        }

        // Mini validate+rank cycle after ingestion
        $upd = "INSERT INTO rapid_strategy_stats
            (strategy_name, total_trades, wins, losses, win_rate, avg_pnl, total_pnl)
            SELECT strategy_name,
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) as losses,
                ROUND(100.0*SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END)/COUNT(*),2) as win_rate,
                ROUND(AVG(COALESCE(pnl,0)),4) as avg_pnl,
                ROUND(SUM(COALESCE(pnl,0)),4) as total_pnl
            FROM rapid_signals WHERE status='closed' AND outcome IS NOT NULL
            GROUP BY strategy_name
            ON DUPLICATE KEY UPDATE
                total_trades=VALUES(total_trades), wins=VALUES(wins), losses=VALUES(losses),
                win_rate=VALUES(win_rate), avg_pnl=VALUES(avg_pnl), total_pnl=VALUES(total_pnl)";
        mysqli_query($conn, $upd);

        mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank='testing'");
        mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank='promoted'
            WHERE total_trades >= $MIN_TRADES AND win_rate >= $MIN_WIN_RATE");
        $ingest_promoted = mysqli_affected_rows($conn);
        mysqli_query($conn, "UPDATE rapid_strategy_stats SET rank='eliminated'
            WHERE total_trades >= $MIN_TRADES AND win_rate < $MIN_WIN_RATE");
        $ingest_elim = mysqli_affected_rows($conn);

        $res_i = mysqli_query($conn, "SELECT rank, COUNT(*) as cnt FROM rapid_strategy_stats GROUP BY rank");
        $ingest_rankings = array('promoted' => 0, 'testing' => 0, 'eliminated' => 0);
        if ($res_i) {
            while ($row = mysqli_fetch_assoc($res_i)) {
                $ingest_rankings[$row['rank']] = (int)$row['cnt'];
            }
        }

        echo json_encode(array(
            'ok'       => true,
            'action'   => 'ingest_complete',
            'ingested' => $ingested,
            'skipped'  => $skipped,
            'errors'   => array_unique($err_msgs),
            'cycle'    => array('promoted' => $ingest_promoted, 'eliminated' => $ingest_elim),
            'rankings' => $ingest_rankings,
            'timestamp' => date('Y-m-d H:i:s')
        ));
        break;

    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action. Use: status, validate, rank, cycle, ingest'
        ));
}

if ($conn) {
    mysqli_close($conn);
}
?>
