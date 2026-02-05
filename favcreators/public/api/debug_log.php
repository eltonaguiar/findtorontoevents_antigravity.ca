<?php
/**
 * Debug logging API: write a log entry to ejaguiar1_debuglog.debug_log.
 * Only accepts entries when session user is admin AND debug_log_enabled is on.
 * POST body: { "event_type": string, "payload": object }
 * Event types: event_clicked, heart_click, save_event_success, save_event_failure, login_success, login_failure, etc.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('error' => 'Use POST'));
    exit;
}

session_set_cookie_params(86400, '/', null, true, true);
session_start();

$user = isset($_SESSION['user']) ? $_SESSION['user'] : null;
$is_admin = $user && isset($user['role']) && $user['role'] === 'admin';
$debug_enabled = isset($_SESSION['debug_log_enabled']) && $_SESSION['debug_log_enabled'];

if (!$is_admin || !$debug_enabled) {
    echo json_encode(array('error' => 'Debug logging not enabled', 'status' => 'ignored'));
    exit;
}

require_once dirname(__FILE__) . '/debuglog_db_config.php';
$debuglog_conn = new mysqli($debuglog_host, $debuglog_user, $debuglog_password, $debuglog_database);
if ($debuglog_conn->connect_error) {
    echo json_encode(array('error' => 'Debug log DB connection failed'));
    exit;
}

require_once dirname(__FILE__) . '/debuglog_ensure_table.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);
$event_type = isset($data['event_type']) ? $data['event_type'] : 'unknown';
$payload = isset($data['payload']) ? $data['payload'] : array();
if (!is_array($payload)) $payload = array('raw' => $payload);

$user_id = $user && isset($user['id']) ? intval($user['id']) : null;
$session_id = session_id();
$payload_json = $debuglog_conn->real_escape_string(json_encode($payload));
$event_type_esc = $debuglog_conn->real_escape_string($event_type);
$ip = isset($_SERVER['REMOTE_ADDR']) ? $debuglog_conn->real_escape_string($_SERVER['REMOTE_ADDR']) : '';
$ua = isset($_SERVER['HTTP_USER_AGENT']) ? $debuglog_conn->real_escape_string(substr($_SERVER['HTTP_USER_AGENT'], 0, 512)) : '';

$q = "INSERT INTO debug_log (event_type, user_id, session_id, payload, ip, user_agent) VALUES ('$event_type_esc', " . ($user_id === null ? 'NULL' : $user_id) . ", '" . $debuglog_conn->real_escape_string($session_id) . "', '$payload_json', '$ip', '$ua')";
if ($debuglog_conn->query($q)) {
    echo json_encode(array('status' => 'ok'));
} else {
    echo json_encode(array('error' => $debuglog_conn->error));
}
$debuglog_conn->close();
