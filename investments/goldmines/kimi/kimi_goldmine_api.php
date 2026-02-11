<?php
/**
 * KIMI Goldmine API
 * Main API endpoint for the Goldmine dashboard
 * 
 * Endpoints:
 *   ?action=dashboard - Main dashboard data
 *   ?action=picks&source=X&status=Y&limit=Z - List picks
 *   ?action=winners&category=X - List winners
 *   ?action=performance&period=X - Performance metrics
 *   ?action=sources - List all sources
 *   ?action=alerts - List alerts
 *   ?action=goldmines - List goldmine-worthy sources
 *   ?action=pick_detail&uuid=X - Single pick details
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Error handler to always return JSON
set_error_handler(function($errno, $errstr) {
    echo json_encode(['ok' => false, 'error' => $errstr]);
    exit;
});

try {
    require_once dirname(__FILE__) . '/../../../findstocks/portfolio2/api/db_connect.php';
} catch (Exception $e) {
    echo json_encode(['ok' => false, 'error' => 'Database connection failed: ' . $e->getMessage()]);
    exit;
}

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';

switch ($action) {
    case 'dashboard':
        get_dashboard($conn);
        break;
    case 'picks':
        get_picks($conn);
        break;
    case 'winners':
        get_winners($conn);
        break;
    case 'performance':
        get_performance($conn);
        break;
    case 'sources':
        get_sources($conn);
        break;
    case 'alerts':
        get_alerts($conn);
        break;
    case 'goldmines':
        get_goldmines($conn);
        break;
    case 'pick_detail':
        get_pick_detail($conn);
        break;
    case 'source_detail':
        get_source_detail($conn);
        break;
    case 'mark_alert_read':
        mark_alert_read($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();

// ─────────────────────────────────────────────────────────────────────────────
// Main dashboard data
// ─────────────────────────────────────────────────────────────────────────────
function get_dashboard($conn) {
    $dashboard = array();
    
    // Header stats
    $stats = array();
    
    // Total picks tracked
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_PICKS");
    $stats['total_picks_tracked'] = (int)$res->fetch_assoc()['c'];
    
    // Active picks
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_PICKS WHERE status = 'active'");
    $stats['active_picks'] = (int)$res->fetch_assoc()['c'];
    
    // Total winners
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_WINNERS");
    $stats['total_winners'] = (int)$res->fetch_assoc()['c'];
    
    // Active goldmines
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_SOURCES WHERE current_goldmine_status = 1");
    $stats['active_goldmines'] = (int)$res->fetch_assoc()['c'];
    
    // Today's new picks
    $res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_PICKS WHERE DATE(pick_date) = CURDATE()");
    $stats['new_picks_today'] = (int)$res->fetch_assoc()['c'];
    
    $dashboard['stats'] = $stats;
    
    // Performance by source type (last 30 days)
    $res = $conn->query("SELECT 
                            source_type,
                            COUNT(*) as picks,
                            AVG(exit_return_pct) as avg_return,
                            SUM(CASE WHEN exit_return_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as win_rate
                         FROM KIMI_GOLDMINE_PICKS
                         WHERE pick_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
                         AND status IN ('target_hit', 'stop_hit', 'closed')
                         GROUP BY source_type");
    $by_type = array();
    while ($row = $res->fetch_assoc()) {
        $by_type[$row['source_type']] = array(
            'picks' => (int)$row['picks'],
            'avg_return' => round((float)$row['avg_return'], 2),
            'win_rate' => round((float)$row['win_rate'], 1)
        );
    }
    $dashboard['performance_by_type'] = $by_type;
    
    // Top performing sources
    $res = $conn->query("SELECT 
                            source_name, algorithm_name, source_type,
                            COUNT(*) as total_picks,
                            AVG(exit_return_pct) as avg_return,
                            SUM(CASE WHEN exit_return_pct > 0 THEN 1 ELSE 0 END) as wins
                         FROM KIMI_GOLDMINE_PICKS
                         WHERE pick_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
                         AND status IN ('target_hit', 'stop_hit', 'closed')
                         GROUP BY source_name, algorithm_name
                         HAVING COUNT(*) >= 5
                         ORDER BY avg_return DESC
                         LIMIT 5");
    $top_sources = array();
    while ($row = $res->fetch_assoc()) {
        $total = (int)$row['total_picks'];
        $wins = (int)$row['wins'];
        $top_sources[] = array(
            'name' => $row['algorithm_name'],
            'source' => $row['source_name'],
            'type' => $row['source_type'],
            'picks' => $total,
            'win_rate' => round(($wins / $total) * 100, 1),
            'avg_return' => round((float)$row['avg_return'], 2)
        );
    }
    $dashboard['top_sources'] = $top_sources;
    
    // Recent winners
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_WINNERS 
                         ORDER BY exit_return_pct DESC 
                         LIMIT 10");
    $winners = array();
    while ($row = $res->fetch_assoc()) {
        $winners[] = array(
            'symbol' => $row['asset_symbol'],
            'name' => $row['asset_name'],
            'source' => $row['source_name'],
            'algorithm' => $row['algorithm_name'],
            'return' => round((float)$row['exit_return_pct'], 2),
            'category' => $row['winner_category'],
            'date' => $row['exit_date']
        );
    }
    $dashboard['recent_winners'] = $winners;
    
    // Recent picks needing attention
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_PICKS 
                         WHERE status = 'active'
                         AND pick_date > DATE_SUB(NOW(), INTERVAL 7 DAY)
                         ORDER BY confidence_score DESC, pick_date DESC
                         LIMIT 10");
    $recent = array();
    while ($row = $res->fetch_assoc()) {
        $recent[] = array(
            'uuid' => $row['pick_uuid'],
            'symbol' => $row['asset_symbol'],
            'source' => $row['source_name'],
            'algorithm' => $row['algorithm_name'],
            'confidence' => (int)$row['confidence_score'],
            'date' => $row['pick_date'],
            'status' => $row['status']
        );
    }
    $dashboard['recent_picks'] = $recent;
    
    // Unread alerts
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_ALERTS 
                         WHERE is_read = 0
                         ORDER BY created_at DESC
                         LIMIT 5");
    $alerts = array();
    while ($row = $res->fetch_assoc()) {
        $alerts[] = array(
            'id' => $row['id'],
            'type' => $row['alert_type'],
            'severity' => $row['severity'],
            'title' => $row['title'],
            'message' => $row['message'],
            'created' => $row['created_at']
        );
    }
    $dashboard['unread_alerts'] = $alerts;
    
    // Goldmine-worthy sources
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_SOURCES 
                         WHERE current_goldmine_status = 1
                         ORDER BY total_picks_all_time DESC");
    $goldmines = array();
    while ($row = $res->fetch_assoc()) {
        $goldmines[] = array(
            'name' => $row['display_name'],
            'type' => $row['source_type'],
            'algorithm' => $row['algorithm_name'],
            'win_rate' => round((float)$row['avg_return_all_time'], 2),
            'total_picks' => (int)$row['total_picks_all_time']
        );
    }
    $dashboard['goldmines'] = $goldmines;
    
    echo json_encode(array('ok' => true, 'dashboard' => $dashboard));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get picks with filtering
// ─────────────────────────────────────────────────────────────────────────────
function get_picks($conn) {
    $source = isset($_GET['source']) ? $conn->real_escape_string($_GET['source']) : '';
    $status = isset($_GET['status']) ? $conn->real_escape_string($_GET['status']) : '';
    $type = isset($_GET['type']) ? $conn->real_escape_string($_GET['type']) : '';
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    $offset = isset($_GET['offset']) ? (int)$_GET['offset'] : 0;
    
    $where = array('1=1');
    if ($source) $where[] = "source_name = '$source'";
    if ($status) $where[] = "status = '$status'";
    if ($type) $where[] = "source_type = '$type'";
    
    $where_clause = implode(' AND ', $where);
    
    // Get total count
    $count_res = $conn->query("SELECT COUNT(*) as c FROM KIMI_GOLDMINE_PICKS WHERE $where_clause");
    $total = (int)$count_res->fetch_assoc()['c'];
    
    // Get picks
    $sql = "SELECT * FROM KIMI_GOLDMINE_PICKS 
            WHERE $where_clause
            ORDER BY pick_date DESC
            LIMIT $limit OFFSET $offset";
    
    $res = $conn->query($sql);
    $picks = array();
    while ($row = $res->fetch_assoc()) {
        $picks[] = array(
            'uuid' => $row['pick_uuid'],
            'symbol' => $row['asset_symbol'],
            'name' => $row['asset_name'],
            'type' => $row['source_type'],
            'source' => $row['source_name'],
            'algorithm' => $row['algorithm_name'],
            'direction' => $row['pick_direction'],
            'entry' => (float)$row['entry_price'],
            'current' => $row['current_price'] ? (float)$row['current_price'] : null,
            'return' => $row['current_return_pct'] ? round((float)$row['current_return_pct'], 2) : null,
            'target' => $row['target_pct'] ? (float)$row['target_pct'] : null,
            'stop' => $row['stop_pct'] ? (float)$row['stop_pct'] : null,
            'confidence' => (int)$row['confidence_score'],
            'status' => $row['status'],
            'date' => $row['pick_date']
        );
    }
    
    echo json_encode(array(
        'ok' => true,
        'total' => $total,
        'limit' => $limit,
        'offset' => $offset,
        'picks' => $picks
    ));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get winners
// ─────────────────────────────────────────────────────────────────────────────
function get_winners($conn) {
    $category = isset($_GET['category']) ? $conn->real_escape_string($_GET['category']) : '';
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 20;
    
    $where = '1=1';
    if ($category) $where .= " AND winner_category = '$category'";
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_WINNERS 
                         WHERE $where
                         ORDER BY exit_return_pct DESC
                         LIMIT $limit");
    
    $winners = array();
    while ($row = $res->fetch_assoc()) {
        $winners[] = array(
            'uuid' => $row['pick_uuid'],
            'symbol' => $row['asset_symbol'],
            'name' => $row['asset_name'],
            'type' => $row['source_type'],
            'algorithm' => $row['algorithm_name'],
            'entry' => (float)$row['entry_price'],
            'exit' => (float)$row['exit_price'],
            'return' => round((float)$row['exit_return_pct'], 2),
            'category' => $row['winner_category'],
            'reason' => $row['winner_reason'],
            'days_held' => (int)$row['days_held'],
            'date' => $row['exit_date']
        );
    }
    
    echo json_encode(array('ok' => true, 'winners' => $winners));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get performance metrics
// ─────────────────────────────────────────────────────────────────────────────
function get_performance($conn) {
    $period = isset($_GET['period']) ? $conn->real_escape_string($_GET['period']) : 'monthly';
    $source = isset($_GET['source']) ? $conn->real_escape_string($_GET['source']) : '';
    
    $where = "period = '$period'";
    if ($source) $where .= " AND source_name = '$source'";
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_PERFORMANCE 
                         WHERE $where
                         ORDER BY overall_score DESC, avg_return_pct DESC");
    
    $performance = array();
    while ($row = $res->fetch_assoc()) {
        $performance[] = array(
            'source' => $row['source_name'],
            'algorithm' => $row['algorithm_name'],
            'type' => $row['source_type'],
            'period' => $row['period'],
            'total_picks' => (int)$row['total_picks'],
            'win_rate' => round((float)$row['win_rate_pct'], 1),
            'avg_return' => round((float)$row['avg_return_pct'], 2),
            'sharpe' => $row['sharpe_ratio'] ? round((float)$row['sharpe_ratio'], 2) : null,
            'profit_factor' => $row['profit_factor'] ? round((float)$row['profit_factor'], 2) : null,
            'is_goldmine' => (bool)$row['is_goldmine_worthy'],
            'score' => $row['overall_score'] ? round((float)$row['overall_score'], 1) : null
        );
    }
    
    echo json_encode(array('ok' => true, 'performance' => $performance));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get all sources
// ─────────────────────────────────────────────────────────────────────────────
function get_sources($conn) {
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_SOURCES ORDER BY source_type, display_name");
    
    $sources = array();
    while ($row = $res->fetch_assoc()) {
        $sources[] = array(
            'id' => $row['id'],
            'name' => $row['display_name'],
            'slug' => $row['source_slug'],
            'algorithm' => $row['algorithm_name'],
            'type' => $row['source_type'],
            'strategy' => $row['strategy_type'],
            'timeframe' => $row['ideal_timeframe'],
            'risk' => $row['risk_level'],
            'is_active' => (bool)$row['is_active'],
            'is_goldmine' => (bool)$row['current_goldmine_status'],
            'total_picks' => (int)$row['total_picks_all_time'],
            'win_rate' => round((float)$row['avg_return_all_time'], 2),
            'description' => $row['description']
        );
    }
    
    echo json_encode(array('ok' => true, 'sources' => $sources));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get alerts
// ─────────────────────────────────────────────────────────────────────────────
function get_alerts($conn) {
    $unread_only = isset($_GET['unread']) && $_GET['unread'] == '1';
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 20;
    
    $where = $unread_only ? 'is_read = 0' : '1=1';
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_ALERTS 
                         WHERE $where
                         ORDER BY created_at DESC
                         LIMIT $limit");
    
    $alerts = array();
    while ($row = $res->fetch_assoc()) {
        $alerts[] = array(
            'id' => $row['id'],
            'type' => $row['alert_type'],
            'severity' => $row['severity'],
            'title' => $row['title'],
            'message' => $row['message'],
            'source' => $row['source_name'],
            'symbol' => $row['asset_symbol'],
            'is_read' => (bool)$row['is_read'],
            'created' => $row['created_at']
        );
    }
    
    echo json_encode(array('ok' => true, 'alerts' => $alerts));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get goldmine-worthy sources
// ─────────────────────────────────────────────────────────────────────────────
function get_goldmines($conn) {
    $res = $conn->query("SELECT 
                            s.*,
                            COUNT(p.id) as recent_picks,
                            AVG(p.exit_return_pct) as recent_return
                         FROM KIMI_GOLDMINE_SOURCES s
                         LEFT JOIN KIMI_GOLDMINE_PICKS p ON 
                            s.source_name = p.source_name 
                            AND s.algorithm_name = p.algorithm_name
                            AND p.pick_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
                         WHERE s.current_goldmine_status = 1
                         GROUP BY s.id
                         ORDER BY recent_return DESC");
    
    $goldmines = array();
    while ($row = $res->fetch_assoc()) {
        $goldmines[] = array(
            'name' => $row['display_name'],
            'algorithm' => $row['algorithm_name'],
            'type' => $row['source_type'],
            'strategy' => $row['strategy_type'],
            'risk' => $row['risk_level'],
            'achieved_date' => $row['goldmine_achieved_date'],
            'total_picks' => (int)$row['total_picks_all_time'],
            'recent_picks' => (int)$row['recent_picks'],
            'recent_return' => round((float)$row['recent_return'], 2),
            'win_rate' => round((float)$row['avg_return_all_time'], 2),
            'reason' => $row['goldmine_reason']
        );
    }
    
    echo json_encode(array('ok' => true, 'goldmines' => $goldmines));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get single pick detail
// ─────────────────────────────────────────────────────────────────────────────
function get_pick_detail($conn) {
    $uuid = isset($_GET['uuid']) ? $conn->real_escape_string($_GET['uuid']) : '';
    
    if (!$uuid) {
        echo json_encode(array('ok' => false, 'error' => 'UUID required'));
        return;
    }
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_PICKS WHERE pick_uuid = '$uuid'");
    
    if ($res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Pick not found'));
        return;
    }
    
    $pick = $res->fetch_assoc();
    
    echo json_encode(array(
        'ok' => true,
        'pick' => array(
            'uuid' => $pick['pick_uuid'],
            'symbol' => $pick['asset_symbol'],
            'name' => $pick['asset_name'],
            'type' => $pick['source_type'],
            'source' => $pick['source_name'],
            'algorithm' => $pick['algorithm_name'],
            'direction' => $pick['pick_direction'],
            'entry_price' => (float)$pick['entry_price'],
            'current_price' => $pick['current_price'] ? (float)$pick['current_price'] : null,
            'exit_price' => $pick['exit_price'] ? (float)$pick['exit_price'] : null,
            'target_pct' => $pick['target_pct'] ? (float)$pick['target_pct'] : null,
            'stop_pct' => $pick['stop_pct'] ? (float)$pick['stop_pct'] : null,
            'confidence' => (int)$pick['confidence_score'],
            'kelly' => $pick['kelly_fraction'] ? (float)$pick['kelly_fraction'] : null,
            'timeframe' => (int)$pick['timeframe_days'],
            'status' => $pick['status'],
            'pick_date' => $pick['pick_date'],
            'exit_date' => $pick['exit_date'],
            'return_pct' => $pick['current_return_pct'] ? round((float)$pick['current_return_pct'], 2) : null,
            'exit_return' => $pick['exit_return_pct'] ? round((float)$pick['exit_return_pct'], 2) : null,
            'factors' => $pick['factors_json'] ? json_decode($pick['factors_json'], true) : null,
            'raw_data' => $pick['raw_data'] ? json_decode($pick['raw_data'], true) : null
        )
    ));
}

// ─────────────────────────────────────────────────────────────────────────────
// Get source detail with performance
// ─────────────────────────────────────────────────────────────────────────────
function get_source_detail($conn) {
    $slug = isset($_GET['slug']) ? $conn->real_escape_string($_GET['slug']) : '';
    
    if (!$slug) {
        echo json_encode(array('ok' => false, 'error' => 'Slug required'));
        return;
    }
    
    $res = $conn->query("SELECT * FROM KIMI_GOLDMINE_SOURCES WHERE source_slug = '$slug'");
    
    if ($res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Source not found'));
        return;
    }
    
    $source = $res->fetch_assoc();
    
    // Get recent picks
    $picks_res = $conn->query("SELECT * FROM KIMI_GOLDMINE_PICKS 
                               WHERE source_name = '{$source['source_name']}'
                               AND algorithm_name = '{$source['algorithm_name']}'
                               ORDER BY pick_date DESC
                               LIMIT 20");
    
    $recent_picks = array();
    while ($row = $picks_res->fetch_assoc()) {
        $recent_picks[] = array(
            'symbol' => $row['asset_symbol'],
            'return' => $row['exit_return_pct'] ? round((float)$row['exit_return_pct'], 2) : null,
            'status' => $row['status'],
            'date' => $row['pick_date']
        );
    }
    
    // Get performance history
    $perf_res = $conn->query("SELECT * FROM KIMI_GOLDMINE_PERFORMANCE
                              WHERE source_name = '{$source['source_name']}'
                              AND algorithm_name = '{$source['algorithm_name']}'
                              ORDER BY period, period_start DESC");
    
    $performance = array();
    while ($row = $perf_res->fetch_assoc()) {
        $performance[] = array(
            'period' => $row['period'],
            'picks' => (int)$row['total_picks'],
            'win_rate' => round((float)$row['win_rate_pct'], 1),
            'avg_return' => round((float)$row['avg_return_pct'], 2),
            'sharpe' => $row['sharpe_ratio'] ? round((float)$row['sharpe_ratio'], 2) : null
        );
    }
    
    echo json_encode(array(
        'ok' => true,
        'source' => array(
            'name' => $source['display_name'],
            'algorithm' => $source['algorithm_name'],
            'type' => $source['source_type'],
            'description' => $source['description'],
            'strategy' => $source['strategy_type'],
            'timeframe' => $source['ideal_timeframe'],
            'risk' => $source['risk_level'],
            'is_goldmine' => (bool)$source['current_goldmine_status'],
            'total_picks' => (int)$source['total_picks_all_time'],
            'total_wins' => (int)$source['total_wins_all_time'],
            'avg_return' => round((float)$source['avg_return_all_time'], 2),
            'recent_picks' => $recent_picks,
            'performance_history' => $performance
        )
    ));
}

// ─────────────────────────────────────────────────────────────────────────────
// Mark alert as read
// ─────────────────────────────────────────────────────────────────────────────
function mark_alert_read($conn) {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    
    if (!$id) {
        echo json_encode(array('ok' => false, 'error' => 'ID required'));
        return;
    }
    
    $stmt = $conn->prepare("UPDATE KIMI_GOLDMINE_ALERTS SET is_read = 1, read_at = NOW() WHERE id = ?");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    
    echo json_encode(array('ok' => true, 'updated' => $stmt->affected_rows > 0));
}
