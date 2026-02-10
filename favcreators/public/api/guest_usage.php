<?php
/**
 * Guest Usage Check/Record API
 *
 * Tracks guest (non-logged-in) usage by IP address for:
 * - AI bot message limits (1 free message)
 * - Site day limits (7 days free, then login required)
 *
 * Actions:
 *   GET  ?action=check_ai   — Check if guest IP can send an AI message
 *   POST { "action": "record_ai" } — Record that guest IP sent an AI message
 *   GET  ?action=check_site  — Check site day usage (auto-increments if new day)
 *
 * PHP 5.2 compatible: array(), $conn->query(), real_escape_string(), header('HTTP/1.0 ...')
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 200 OK');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/guest_usage_schema.php';

$AI_MESSAGE_LIMIT = 1;
$SITE_DAY_LIMIT   = 7;

// Get client IP
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '';
if ($ip === '') {
    echo json_encode(array('ok' => false, 'error' => 'Could not determine IP'));
    exit;
}

$esc_ip = $conn->real_escape_string($ip);
$ua     = isset($_SERVER['HTTP_USER_AGENT']) ? $conn->real_escape_string(substr($_SERVER['HTTP_USER_AGENT'], 0, 512)) : '';
$now    = date('Y-m-d H:i:s');
$today  = date('Y-m-d');

// Determine action
$action = '';
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $action = isset($_GET['action']) ? $_GET['action'] : '';
} else if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = file_get_contents('php://input');
    $input = json_decode($raw, true);
    $action = isset($input['action']) ? $input['action'] : '';
}

// ── Helper: ensure row exists for this IP ──
function ensure_guest_row($conn, $esc_ip, $now, $today, $ua) {
    $sql = "INSERT INTO guest_usage (ip_address, ai_message_count, first_seen_at, last_seen_at, distinct_days, last_day_counted, user_agent)
            VALUES ('$esc_ip', 0, '$now', '$now', 1, '$today', '$ua')
            ON DUPLICATE KEY UPDATE last_seen_at = '$now'";
    $conn->query($sql);
}

// ── Helper: get current row for this IP ──
function get_guest_row($conn, $esc_ip) {
    $sql = "SELECT ai_message_count, first_seen_at, last_seen_at, distinct_days, last_day_counted, registered_user_id, registered_at
            FROM guest_usage WHERE ip_address = '$esc_ip'";
    $result = $conn->query($sql);
    if ($result && $row = $result->fetch_assoc()) {
        return $row;
    }
    return null;
}


// ════════════════════════════════════════════════════════════════
// ACTION: check_ai — Is this guest IP allowed to send an AI message?
// ════════════════════════════════════════════════════════════════
if ($action === 'check_ai') {
    ensure_guest_row($conn, $esc_ip, $now, $today, $ua);
    $row = get_guest_row($conn, $esc_ip);
    $count = $row ? intval($row['ai_message_count']) : 0;

    echo json_encode(array(
        'ok'               => true,
        'allowed'          => ($count < $AI_MESSAGE_LIMIT),
        'ai_message_count' => $count,
        'limit'            => $AI_MESSAGE_LIMIT
    ));
    $conn->close();
    exit;
}


// ════════════════════════════════════════════════════════════════
// ACTION: record_ai — Record an AI message from this guest IP
// ════════════════════════════════════════════════════════════════
if ($action === 'record_ai') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        header('HTTP/1.0 405 Method Not Allowed');
        echo json_encode(array('ok' => false, 'error' => 'Use POST for record_ai'));
        $conn->close();
        exit;
    }

    // Upsert: insert or increment
    $sql = "INSERT INTO guest_usage (ip_address, ai_message_count, first_seen_at, last_seen_at, distinct_days, last_day_counted, user_agent)
            VALUES ('$esc_ip', 1, '$now', '$now', 1, '$today', '$ua')
            ON DUPLICATE KEY UPDATE ai_message_count = ai_message_count + 1, last_seen_at = '$now'";

    $success = $conn->query($sql);
    if (!$success) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Failed to record usage'));
        $conn->close();
        exit;
    }

    $row = get_guest_row($conn, $esc_ip);
    $new_count = $row ? intval($row['ai_message_count']) : 1;

    echo json_encode(array(
        'ok'               => true,
        'recorded'         => true,
        'ai_message_count' => $new_count,
        'limit'            => $AI_MESSAGE_LIMIT,
        'allowed'          => ($new_count < $AI_MESSAGE_LIMIT)
    ));
    $conn->close();
    exit;
}


// ════════════════════════════════════════════════════════════════
// ACTION: check_site — Check site day usage (auto-increments on new calendar day)
//   Optional: &user_id=N — if provided, marks this IP as registered
// ════════════════════════════════════════════════════════════════
if ($action === 'check_site') {
    ensure_guest_row($conn, $esc_ip, $now, $today, $ua);

    // Count event clicks for this IP
    $EVENT_CLICK_LIMIT = 2;
    $event_click_count = 0;
    $ec_result = $conn->query("SELECT COUNT(*) as cnt FROM click_log WHERE ip_address = '$esc_ip' AND click_type = 'event_click'");
    if ($ec_result && $ec_row = $ec_result->fetch_assoc()) {
        $event_click_count = intval($ec_row['cnt']);
    }

    // If a logged-in user_id is provided, mark this IP as registered + track user visit days
    $user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;
    if ($user_id > 0) {
        // Mark IP row as registered
        $sql = "UPDATE guest_usage
                SET registered_user_id = $user_id, registered_at = COALESCE(registered_at, '$now'), last_seen_at = '$now'
                WHERE ip_address = '$esc_ip' AND (registered_user_id IS NULL OR registered_user_id = 0)";
        $conn->query($sql);

        // Track per-user distinct visit days (separate from IP-based tracking)
        $sql = "INSERT INTO user_visit_days (user_id, distinct_days, last_day_counted, first_visit_at, last_visit_at)
                VALUES ($user_id, 1, '$today', '$now', '$now')
                ON DUPLICATE KEY UPDATE last_visit_at = '$now',
                    distinct_days = IF(last_day_counted != '$today', distinct_days + 1, distinct_days),
                    last_day_counted = '$today'";
        $conn->query($sql);
    }

    $row = get_guest_row($conn, $esc_ip);

    if ($row) {
        $distinct_days    = intval($row['distinct_days']);
        $last_day_counted = $row['last_day_counted'];

        // If today is a new calendar day, increment distinct_days
        if ($last_day_counted !== $today) {
            $distinct_days = $distinct_days + 1;
            $esc_today = $conn->real_escape_string($today);
            $sql = "UPDATE guest_usage
                    SET distinct_days = $distinct_days, last_day_counted = '$esc_today', last_seen_at = '$now'
                    WHERE ip_address = '$esc_ip'";
            $conn->query($sql);
        }

        // Only check day limit — no restriction on number of events viewed
        $guest_allowed = ($distinct_days <= $SITE_DAY_LIMIT);

        echo json_encode(array(
            'ok'                 => true,
            'allowed'            => ($user_id > 0) ? true : $guest_allowed,
            'distinct_days'      => $distinct_days,
            'day_limit'          => $SITE_DAY_LIMIT,
            'event_click_count'  => $event_click_count,
            'event_click_limit'  => $EVENT_CLICK_LIMIT,
            'first_seen_at'      => $row['first_seen_at'],
            'registered'         => ($row['registered_user_id'] !== null && intval($row['registered_user_id']) > 0)
        ));
    } else {
        // Freshly inserted — day 1, allowed
        echo json_encode(array(
            'ok'                 => true,
            'allowed'            => true,
            'distinct_days'      => 1,
            'day_limit'          => $SITE_DAY_LIMIT,
            'event_click_count'  => $event_click_count,
            'event_click_limit'  => $EVENT_CLICK_LIMIT,
            'first_seen_at'      => $now,
            'registered'         => ($user_id > 0)
        ));
    }
    $conn->close();
    exit;
}


// ════════════════════════════════════════════════════════════════
// Unknown action
// ════════════════════════════════════════════════════════════════
header('HTTP/1.0 400 Bad Request');
echo json_encode(array('ok' => false, 'error' => 'Invalid action. Use check_ai, record_ai, or check_site.'));
$conn->close();
?>
