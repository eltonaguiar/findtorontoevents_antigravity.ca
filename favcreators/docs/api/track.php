<?php
/**
 * User Activity Tracking API
 *
 * Logs clicks and page views for both guests and logged-in users.
 * All tracking is fire-and-forget (non-blocking from frontend).
 *
 * Actions (all POST):
 *   { "action": "click", "click_type": "event_click", "page": "events", "target_url": "...", "target_title": "...", "target_id": "..." }
 *   { "action": "pageview", "page": "events", "page_url": "/index.html" }
 *
 * Optional in all: "user_id": N (if logged in)
 *
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 200 OK');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.0 405 Method Not Allowed');
    echo json_encode(array('ok' => false, 'error' => 'POST only'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/guest_usage_schema.php';

$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '';
if ($ip === '') {
    echo json_encode(array('ok' => false, 'error' => 'No IP'));
    exit;
}

$esc_ip = $conn->real_escape_string($ip);
$now    = date('Y-m-d H:i:s');

$raw   = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!$input || !isset($input['action'])) {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Missing action'));
    exit;
}

$action  = $input['action'];
$user_id = isset($input['user_id']) ? intval($input['user_id']) : 0;
$esc_uid = ($user_id > 0) ? $user_id : 'NULL';


// ════════════════════════════════════════════════════════════════
// ACTION: click — Log a click event
// ════════════════════════════════════════════════════════════════
if ($action === 'click') {
    $click_type   = isset($input['click_type']) ? $conn->real_escape_string(substr($input['click_type'], 0, 32)) : 'link_click';
    $page         = isset($input['page']) ? $conn->real_escape_string(substr($input['page'], 0, 64)) : 'unknown';
    $target_url   = isset($input['target_url']) ? $conn->real_escape_string(substr($input['target_url'], 0, 1024)) : '';
    $target_title = isset($input['target_title']) ? $conn->real_escape_string(substr($input['target_title'], 0, 512)) : '';
    $target_id    = isset($input['target_id']) ? $conn->real_escape_string(substr($input['target_id'], 0, 255)) : '';

    $sql = "INSERT INTO click_log (ip_address, user_id, click_type, page, target_url, target_title, target_id, clicked_at)
            VALUES ('$esc_ip', $esc_uid, '$click_type', '$page', '$target_url', '$target_title', '$target_id', '$now')";

    $success = $conn->query($sql);
    echo json_encode(array('ok' => (bool)$success));
    $conn->close();
    exit;
}


// ════════════════════════════════════════════════════════════════
// ACTION: pageview — Log a page view (upsert: increment visit_count)
// ════════════════════════════════════════════════════════════════
if ($action === 'pageview') {
    $page     = isset($input['page']) ? $conn->real_escape_string(substr($input['page'], 0, 64)) : 'unknown';
    $page_url = isset($input['page_url']) ? $conn->real_escape_string(substr($input['page_url'], 0, 1024)) : '';

    // Upsert: insert or increment visit_count
    $sql = "INSERT INTO page_view_log (ip_address, user_id, page, page_url, visit_count, first_visit_at, last_visit_at)
            VALUES ('$esc_ip', $esc_uid, '$page', '$page_url', 1, '$now', '$now')
            ON DUPLICATE KEY UPDATE visit_count = visit_count + 1, last_visit_at = '$now',
                user_id = IF($esc_uid IS NOT NULL AND $esc_uid > 0, $esc_uid, user_id)";

    $success = $conn->query($sql);
    echo json_encode(array('ok' => (bool)$success));
    $conn->close();
    exit;
}


// Unknown action
header('HTTP/1.0 400 Bad Request');
echo json_encode(array('ok' => false, 'error' => 'Invalid action. Use click or pageview.'));
$conn->close();
?>
