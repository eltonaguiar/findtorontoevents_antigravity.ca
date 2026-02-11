<?php
/**
 * KIMI Goldmine Data Collector
 * Imports picks from all prediction sources across the platform
 */

// Suppress all errors - we'll handle them manually
error_reporting(0);
ini_set('display_errors', '0');

// Ensure JSON output even on fatal errors
register_shutdown_function(function() {
    $error = error_get_last();
    if ($error && ($error['type'] === E_ERROR || $error['type'] === E_PARSE)) {
        ob_clean();
        echo json_encode(['ok' => false, 'error' => 'Fatal error: ' . $error['message']]);
    }
});

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Capture any output
ob_start();

try {
    require_once dirname(__FILE__) . '/../../../findstocks/portfolio2/api/db_connect.php';
} catch (Exception $e) {
    ob_clean();
    echo json_encode(['ok' => false, 'error' => 'Database connection failed: ' . $e->getMessage()]);
    exit;
}

// Clean any output from db_connect.php
ob_clean();

$ADMIN_KEY = 'goldmine2026';
$action = isset($_GET['action']) ? trim($_GET['action']) : 'status';
$key = isset($_GET['key']) ? trim($_GET['key']) : '';

if ($action !== 'status' && $key !== $ADMIN_KEY) {
    echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
    exit;
}

switch ($action) {
    case 'status':
        get_status($conn);
        break;
    case 'collect':
        $source = isset($_GET['source']) ? trim($_GET['source']) : 'all';
        collect_data($conn, $source);
        break;
    case 'update_prices':
        update_prices($conn);
        break;
    case 'resolve':
        resolve_picks($conn);
        break;
    case 'calculate_performance':
        calculate_performance($conn);
        break;
    case 'find_winners':
        find_winners($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();

// ─────────────────────────────────────────────────────────────────────────────
// Get current status
// ─────────────────────────────────────────────────────────────────────────────
function get_status($conn) {
    $stats = array();
    
    // Total picks
    $res = $conn->query("SELECT COUNT(*) as c, status FROM KIMI_GOLDMINE_PICKS GROUP BY status");
    $stats['picks_by_status'] = array();
    while ($row = $res->fetch_assoc()) {
        $stats['picks_by_status'][$row['status']] = (int)$row['c'];
    }
    
    // By source
    $res = $conn->query("SELECT source_type, COUNT(*) as c FROM KIMI_GOLDMINE_PICKS GROUP BY source_type");
    $stats['picks_by_source'] = array();
    while ($row = $res->fetch_assoc()) {
        $stats['picks_by_source'][$row['source_type']] = (int)$row['c'];
    }
    
    // Active goldmines
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_SOURCES WHERE current_goldmine_status = 1");
    $row = $res->fetch_assoc();
    $stats['active_goldmines'] = (int)$row['c'];
    
    // Recent winners
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_WINNERS WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)");
    $row = $res->fetch_assoc();
    $stats['winners_this_week'] = (int)$row['c'];
    
    // Unread alerts
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_ALERTS WHERE is_read = 0");
    $row = $res->fetch_assoc();
    $stats['unread_alerts'] = (int)$row['c'];
    
    echo json_encode(array('ok' => true, 'status' => $stats));
}

// ─────────────────────────────────────────────────────────────────────────────
// Collect data from all sources
// ─────────────────────────────────────────────────────────────────────────────
function collect_data($conn, $source_filter) {
    $collected = array();
    $total_new = 0;
    $errors = array();
    
    // Get active sources
    $where = "is_active = 1 AND auto_import = 1";
    if ($source_filter !== 'all') {
        $safe = $conn->real_escape_string($source_filter);
        $where .= " AND source_type = '$safe'";
    }
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_SOURCES WHERE $where");
    
    if (!$res) {
        echo json_encode(array(
            'ok' => false, 
            'error' => 'Failed to query sources: ' . $conn->error
        ));
        return;
    }
    
    while ($source = $res->fetch_assoc()) {
        $new_picks = 0;
        
        try {
            switch ($source['source_type']) {
                case 'stock':
                case 'penny_stock':
                    $new_picks = collect_stock_picks($conn, $source);
                    break;
                case 'meme_coin':
                    $new_picks = collect_meme_picks($conn, $source);
                    break;
                case 'crypto':
                    $new_picks = collect_crypto_picks($conn, $source);
                    break;
                case 'sports':
                    $new_picks = collect_sports_picks($conn, $source);
                    break;
                case 'forex':
                    $new_picks = collect_forex_picks($conn, $source);
                    break;
                case 'mutual_fund':
                    $new_picks = collect_fund_picks($conn, $source);
                    break;
            }
        } catch (Exception $e) {
            $errors[] = $source['display_name'] . ': ' . $e->getMessage();
        }
        
        $collected[] = array(
            'source' => $source['display_name'],
            'new_picks' => $new_picks
        );
        $total_new += $new_picks;
    }
    
    echo json_encode(array(
        'ok' => true,
        'total_new' => $total_new,
        'by_source' => $collected,
        'errors' => $errors
    ));
}

// ─────────────────────────────────────────────────────────────────────────────
// Collect stock picks
// ─────────────────────────────────────────────────────────────────────────────
function collect_stock_picks($conn, $source) {
    // Check if stock_picks table exists
    $check = $conn->query("SHOW TABLES LIKE 'stock_picks'");
    if ($check->num_rows === 0) {
        throw new Exception('stock_picks table does not exist in this database');
    }
    
    // Get picks from stock_picks table not yet in goldmine
    $sql = "SELECT sp.*, s.company_name 
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            LEFT JOIN KIMI_GOLDMINE_PICKS kgp ON 
                CONCAT('stock_', sp.id) = kgp.pick_uuid
            WHERE kgp.id IS NULL 
            AND sp.pick_date > DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND sp.algorithm_name = '" . $conn->real_escape_string($source['algorithm_name']) . "'
            LIMIT 100";
    
    $res = $conn->query($sql);
    if (!$res) {
        throw new Exception('Query failed: ' . $conn->error);
    }
    
    $count = 0;
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_PICKS 
        (pick_uuid, source_type, source_name, algorithm_name, asset_symbol, asset_name,
         pick_direction, entry_price, confidence_score, timeframe_days, pick_date, 
         pick_timestamp, expected_exit_date, status, raw_data) 
        VALUES (?, 'stock', ?, ?, ?, ?, 'long', ?, ?, ?, ?, ?, DATE_ADD(?, INTERVAL ? DAY), 'active', ?)");
    
    while ($row = $res->fetch_assoc()) {
        $uuid = 'stock_' . $row['id'];
        $symbol = $row['ticker'];
        $name = $row['company_name'];
        $price = $row['entry_price'];
        $score = $row['score'];
        $hold = 7; // default
        $pdate = $row['pick_date'];
        $pts = strtotime($pdate);
        $raw = json_encode($row);
        
        $stmt->bind_param('ssssdisiisss', 
            $uuid, $source['source_name'], $source['algorithm_name'],
            $symbol, $name, $price, $score, $hold, $pdate, $pts, $pdate, $hold, $raw
        );
        $stmt->execute();
        $count++;
    }
    $stmt->close();
    
    return $count;
}

// ─────────────────────────────────────────────────────────────────────────────
// Collect meme coin picks
// ─────────────────────────────────────────────────────────────────────────────
function collect_meme_picks($conn, $source) {
    // Check if mc_winners table exists
    $check = $conn->query("SHOW TABLES LIKE 'mc_winners'");
    if ($check->num_rows === 0) {
        throw new Exception('mc_winners table does not exist in this database');
    }
    
    $sql = "SELECT mw.* 
            FROM mc_winners mw
            LEFT JOIN KIMI_GOLDMINE_PICKS kgp ON 
                CONCAT('meme_', mw.id) = kgp.pick_uuid
            WHERE kgp.id IS NULL 
            AND mw.created_at > DATE_SUB(NOW(), INTERVAL 2 DAY)
            LIMIT 100";
    
    $res = $conn->query($sql);
    if (!$res) return 0;
    
    $count = 0;
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_PICKS 
        (pick_uuid, source_type, source_name, algorithm_name, asset_symbol,
         entry_price, confidence_score, target_pct, risk_pct, pick_date,
         pick_timestamp, expected_exit_date, status, factors_json, raw_data) 
        VALUES (?, 'meme_coin', ?, 'meme_scanner', ?, ?, ?, ?, ?, ?, ?, DATE_ADD(?, INTERVAL 1 DAY), 'active', ?, ?)");
    
    while ($row = $res->fetch_assoc()) {
        $uuid = 'meme_' . $row['id'];
        $symbol = str_replace('_USDT', '', $row['pair']);
        $price = $row['price_at_signal'];
        $score = $row['score'];
        $target = $row['target_pct'];
        $risk = $row['risk_pct'];
        $pdate = $row['created_at'];
        $pts = strtotime($pdate);
        $factors = $row['factors_json'];
        $raw = json_encode($row);
        
        $stmt->bind_param('sssddiisssss', 
            $uuid, $source['source_name'], $symbol, $price, $score,
            $target, $risk, $pdate, $pts, $pdate, $factors, $raw
        );
        $stmt->execute();
        $count++;
    }
    $stmt->close();
    
    return $count;
}

// ─────────────────────────────────────────────────────────────────────────────
// Collect sports picks
// ─────────────────────────────────────────────────────────────────────────────
function collect_sports_picks($conn, $source) {
    // Check if lm_sports_value_bets table exists
    $check = $conn->query("SHOW TABLES LIKE 'lm_sports_value_bets'");
    if ($check->num_rows === 0) {
        throw new Exception('lm_sports_value_bets table does not exist in this database');
    }
    
    $sql = "SELECT * FROM lm_sports_value_bets 
            WHERE status = 'active' 
            AND detected_at > DATE_SUB(NOW(), INTERVAL 1 DAY)
            AND ev_pct >= 3.0
            LIMIT 100";
    
    $res = $conn->query($sql);
    if (!$res) return 0;
    
    $count = 0;
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_PICKS 
        (pick_uuid, source_type, source_name, algorithm_name, asset_symbol, asset_name,
         pick_direction, entry_price, confidence_score, target_pct, pick_date,
         pick_timestamp, expected_exit_date, status, raw_data) 
        VALUES (?, 'sports', ?, 'value_bet', ?, ?, 'over', 1.0, ?, ?, ?, ?, DATE_ADD(?, INTERVAL 1 DAY), 'active', ?)
        ON DUPLICATE KEY UPDATE current_price = VALUES(current_price)");
    
    while ($row = $res->fetch_assoc()) {
        $uuid = 'sports_' . $row['event_id'] . '_' . $row['outcome_name'];
        $asset = $row['home_team'] . ' vs ' . $row['away_team'];
        $name = $row['bet_type'];
        $conf = min(100, (float)$row['ev_pct'] * 10); // Scale EV to confidence
        $target = $row['ev_pct'];
        $pdate = $row['detected_at'];
        $pts = strtotime($pdate);
        $raw = json_encode($row);
        
        $stmt->bind_param('ssssdississs', 
            $uuid, $source['source_name'], $asset, $name,
            $conf, $target, $pdate, $pts, $pdate, $raw
        );
        $stmt->execute();
        if ($stmt->affected_rows > 0) $count++;
    }
    $stmt->close();
    
    return $count;
}

// ─────────────────────────────────────────────────────────────────────────────
// Placeholder collectors
// ─────────────────────────────────────────────────────────────────────────────
function collect_crypto_picks($conn, $source) { return 0; }
function collect_forex_picks($conn, $source) { return 0; }
function collect_fund_picks($conn, $source) { return 0; }

// ─────────────────────────────────────────────────────────────────────────────
// Update current prices for active picks
// ─────────────────────────────────────────────────────────────────────────────
function update_prices($conn) {
    // This would integrate with price APIs
    // For now, placeholder
    
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_PICKS WHERE status = 'active'");
    $row = $res->fetch_assoc();
    $active = (int)$row['c'];
    
    echo json_encode(array(
        'ok' => true,
        'message' => 'Price update placeholder - integrate with price APIs',
        'active_picks' => $active
    ));
}

// ─────────────────────────────────────────────────────────────────────────────
// Resolve completed picks
// ─────────────────────────────────────────────────────────────────────────────
function resolve_picks($conn) {
    // Check for exits based on target/stop/time
    $sql = "SELECT * FROM KIMI_GOLDMINE_PICKS 
            WHERE status = 'active'
            AND (expected_exit_date < CURDATE() OR current_price IS NOT NULL)";
    
    $res = $conn->query($sql);
    $resolved = 0;
    
    while ($pick = $res->fetch_assoc()) {
        $return_pct = null;
        $exit_reason = null;
        $new_status = 'active';
        
        if ($pick['current_price'] && $pick['entry_price']) {
            $return_pct = (($pick['current_price'] - $pick['entry_price']) / $pick['entry_price']) * 100;
            
            // Check target hit
            if ($pick['target_pct'] && $return_pct >= $pick['target_pct']) {
                $new_status = 'target_hit';
                $exit_reason = 'target_hit';
            }
            // Check stop hit
            elseif ($pick['stop_pct'] && $return_pct <= -$pick['stop_pct']) {
                $new_status = 'stop_hit';
                $exit_reason = 'stop_hit';
            }
            // Time exit
            elseif ($pick['expected_exit_date'] && strtotime($pick['expected_exit_date']) < time()) {
                $new_status = 'time_exit';
                $exit_reason = 'time_exit';
            }
        }
        
        if ($new_status !== 'active') {
            $stmt = $conn->prepare("UPDATE KIMI_GOLDMINE_PICKS 
                SET status = ?, exit_return_pct = ?, exit_reason = ?, resolved_at = NOW()
                WHERE id = ?");
            $stmt->bind_param('sdii', $new_status, $return_pct, $exit_reason, $pick['id']);
            $stmt->execute();
            $stmt->close();
            $resolved++;
        }
    }
    
    echo json_encode(array('ok' => true, 'resolved' => $resolved));
}

// ─────────────────────────────────────────────────────────────────────────────
// Calculate performance metrics
// ─────────────────────────────────────────────────────────────────────────────
function calculate_performance($conn) {
    // Aggregate by source/algorithm for different periods
    $periods = array('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'all_time');
    
    foreach ($periods as $period) {
        calculate_period_performance($conn, $period);
    }
    
    echo json_encode(array('ok' => true, 'message' => 'Performance calculated for all periods'));
}

function calculate_period_performance($conn, $period) {
    $date_clause = '';
    switch ($period) {
        case 'daily':
            $date_clause = "pick_date >= CURDATE()";
            break;
        case 'weekly':
            $date_clause = "pick_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
            break;
        case 'monthly':
            $date_clause = "pick_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
            break;
        case 'quarterly':
            $date_clause = "pick_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)";
            break;
        case 'yearly':
            $date_clause = "pick_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)";
            break;
        case 'all_time':
            $date_clause = "1=1";
            break;
    }
    
    $sql = "SELECT 
                source_type, source_name, algorithm_name,
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('target_hit', 'closed') AND exit_return_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status IN ('stop_hit', 'closed') AND exit_return_pct <= 0 THEN 1 ELSE 0 END) as losses,
                AVG(exit_return_pct) as avg_return,
                MAX(exit_return_pct) as best_return,
                MIN(exit_return_pct) as worst_return
            FROM KIMI_GOLDMINE_PICKS
            WHERE $date_clause AND status != 'pending'
            GROUP BY source_type, source_name, algorithm_name";
    
    $res = $conn->query($sql);
    
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_PERFORMANCE 
        (period, period_start, period_end, source_type, source_name, algorithm_name,
         total_picks, resolved_picks, winning_picks, losing_picks,
         win_rate_pct, avg_return_pct, best_pick_return, worst_pick_return)
        VALUES (?, CURDATE(), CURDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
        total_picks = VALUES(total_picks),
        winning_picks = VALUES(winning_picks),
        losing_picks = VALUES(losing_picks),
        win_rate_pct = VALUES(win_rate_pct),
        avg_return_pct = VALUES(avg_return_pct),
        updated_at = NOW()");
    
    while ($row = $res->fetch_assoc()) {
        $total = (int)$row['total'];
        $wins = (int)$row['wins'];
        $losses = (int)$row['losses'];
        $resolved = $wins + $losses;
        $win_rate = $resolved > 0 ? round(($wins / $resolved) * 100, 2) : 0;
        
        $stmt->bind_param('ssssiiiidddd',
            $period,
            $row['source_type'],
            $row['source_name'],
            $row['algorithm_name'],
            $total,
            $resolved,
            $wins,
            $losses,
            $win_rate,
            $row['avg_return'],
            $row['best_return'],
            $row['worst_return']
        );
        $stmt->execute();
    }
    $stmt->close();
}

// ─────────────────────────────────────────────────────────────────────────────
// Find and surface winners
// ─────────────────────────────────────────────────────────────────────────────
function find_winners($conn) {
    // Criteria for goldmine-worthy performance
    $sql = "SELECT * FROM KIMI_GOLDMINE_PICKS 
            WHERE status IN ('target_hit', 'closed')
            AND exit_return_pct >= 10
            AND pick_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
            AND pick_uuid NOT IN (SELECT pick_uuid FROM KIMI_GOLDMINE_WINNERS)";
    
    $res = $conn->query($sql);
    $found = 0;
    
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_WINNERS 
        (pick_uuid, source_type, source_name, algorithm_name, asset_symbol, asset_name,
         entry_price, pick_date, exit_price, exit_return_pct, exit_date, days_held,
         winner_category, winner_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    while ($pick = $res->fetch_assoc()) {
        $category = 'hidden_gem';
        $reason = 'Exceptional return of ' . round($pick['exit_return_pct'], 2) . '%';
        
        if ($pick['exit_return_pct'] >= 50) {
            $category = 'mega_winner';
            $reason = 'Mega winner with ' . round($pick['exit_return_pct'], 2) . '% return!';
        } elseif ($pick['exit_return_pct'] >= 20) {
            $category = 'quick_hit';
        }
        
        $days = (strtotime($pick['exit_date']) - strtotime($pick['pick_date'])) / 86400;
        
        $stmt->bind_param('sssssssdssdisss',
            $pick['pick_uuid'],
            $pick['source_type'],
            $pick['source_name'],
            $pick['algorithm_name'],
            $pick['asset_symbol'],
            $pick['asset_name'],
            $pick['entry_price'],
            $pick['pick_date'],
            $pick['exit_price'],
            $pick['exit_return_pct'],
            $pick['exit_date'],
            $days,
            $category,
            $reason
        );
        $stmt->execute();
        
        // Create alert
        create_alert($conn, 'mega_winner', 'info', $pick);
        $found++;
    }
    $stmt->close();
    
    echo json_encode(array('ok' => true, 'new_winners' => $found));
}

function create_alert($conn, $type, $severity, $pick) {
    $title = "New Winner: " . $pick['asset_symbol'];
    $message = $pick['algorithm_name'] . " generated a " . round($pick['exit_return_pct'], 2) . "% return on " . $pick['asset_symbol'];
    
    $stmt = $conn->prepare("INSERT INTO KIMI_GOLDMINE_ALERTS 
        (alert_type, severity, source_type, source_name, algorithm_name, asset_symbol, pick_uuid, title, message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->bind_param('sssssssss', $type, $severity, $pick['source_type'], $pick['source_name'], $pick['algorithm_name'], $pick['asset_symbol'], $pick['pick_uuid'], $title, $message);
    $stmt->execute();
    $stmt->close();
}
