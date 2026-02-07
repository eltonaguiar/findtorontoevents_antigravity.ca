<?php
/**
 * Returns total and recent (7-day) post/content counts per creator.
 * Aggregates from both creator_status_updates and creator_mentions tables.
 *
 * GET /fc/api/get_creator_post_counts.php?user_id=2
 *
 * Response: { "ok": true, "counts": { "creator-id-1": { "total": 5, "recent": 2 }, ... } }
 *
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

// Get user_id parameter
$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

// Look up creator IDs from user_lists table
$user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$user_list_result = $conn->query($user_list_sql);

$creator_ids = array();

if ($user_list_result && $user_list_result->num_rows > 0) {
    $row = $user_list_result->fetch_assoc();
    $creators_data = json_decode($row['creators'], true);
    if (is_array($creators_data)) {
        foreach ($creators_data as $creator) {
            if (isset($creator['id'])) {
                $creator_ids[] = $conn->real_escape_string($creator['id']);
            }
        }
    }
}

if (count($creator_ids) === 0) {
    echo json_encode(array('ok' => true, 'counts' => new stdClass()));
    $conn->close();
    exit;
}

$ids_str = "'" . implode("','", $creator_ids) . "'";
$seven_days_ago = date('Y-m-d H:i:s', time() - 7 * 24 * 3600);
$counts = array();

// Query creator_status_updates table (total and recent)
$tables_exist = array('creator_status_updates' => false, 'creator_mentions' => false);

// Check if tables exist
$check = $conn->query("SHOW TABLES LIKE 'creator_status_updates'");
if ($check && $check->num_rows > 0) {
    $tables_exist['creator_status_updates'] = true;
}
$check2 = $conn->query("SHOW TABLES LIKE 'creator_mentions'");
if ($check2 && $check2->num_rows > 0) {
    $tables_exist['creator_mentions'] = true;
}

// Aggregate from creator_status_updates
if ($tables_exist['creator_status_updates']) {
    // Total counts
    $sql = "SELECT creator_id, COUNT(*) as cnt FROM creator_status_updates WHERE creator_id IN ($ids_str) GROUP BY creator_id";
    $result = $conn->query($sql);
    if ($result) {
        while ($r = $result->fetch_assoc()) {
            $cid = $r['creator_id'];
            if (!isset($counts[$cid])) {
                $counts[$cid] = array('total' => 0, 'recent' => 0);
            }
            $counts[$cid]['total'] += intval($r['cnt']);
        }
    }

    // Recent counts (last 7 days)
    $sql_recent = "SELECT creator_id, COUNT(*) as cnt FROM creator_status_updates WHERE creator_id IN ($ids_str) AND checked_at >= '$seven_days_ago' GROUP BY creator_id";
    $result_recent = $conn->query($sql_recent);
    if ($result_recent) {
        while ($r = $result_recent->fetch_assoc()) {
            $cid = $r['creator_id'];
            if (!isset($counts[$cid])) {
                $counts[$cid] = array('total' => 0, 'recent' => 0);
            }
            $counts[$cid]['recent'] += intval($r['cnt']);
        }
    }
}

// Aggregate from creator_mentions
if ($tables_exist['creator_mentions']) {
    // Total counts
    $sql = "SELECT creator_id, COUNT(*) as cnt FROM creator_mentions WHERE creator_id IN ($ids_str) GROUP BY creator_id";
    $result = $conn->query($sql);
    if ($result) {
        while ($r = $result->fetch_assoc()) {
            $cid = (string)$r['creator_id'];
            if (!isset($counts[$cid])) {
                $counts[$cid] = array('total' => 0, 'recent' => 0);
            }
            $counts[$cid]['total'] += intval($r['cnt']);
        }
    }

    // Recent counts (last 7 days) — creator_mentions uses posted_at (unix timestamp)
    $seven_days_unix = time() - 7 * 24 * 3600;
    $sql_recent = "SELECT creator_id, COUNT(*) as cnt FROM creator_mentions WHERE creator_id IN ($ids_str) AND posted_at >= $seven_days_unix GROUP BY creator_id";
    $result_recent = $conn->query($sql_recent);
    if ($result_recent) {
        while ($r = $result_recent->fetch_assoc()) {
            $cid = (string)$r['creator_id'];
            if (!isset($counts[$cid])) {
                $counts[$cid] = array('total' => 0, 'recent' => 0);
            }
            $counts[$cid]['recent'] += intval($r['cnt']);
        }
    }
}

// Return as object (empty creators omitted — frontend interprets missing = 0)
echo json_encode(array(
    'ok' => true,
    'counts' => count($counts) > 0 ? $counts : new stdClass()
));

$conn->close();
?>
