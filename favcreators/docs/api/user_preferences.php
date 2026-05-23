<?php
// user_preferences.php — GET: load prefs | POST: save prefs (session required)
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: ' . (isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '*'));
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    header('HTTP/1.1 204 No Content');
    exit;
}

session_set_cookie_params(86400, '/', null, true, true);
session_start();

if (!isset($_SESSION['user']) || !$_SESSION['user']) {
    echo json_encode(array('ok' => false, 'error' => 'Not authenticated'));
    exit;
}

$user_id = (int) $_SESSION['user']['id'];

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/sync_log.php';

// Ensure table exists
$conn->query("CREATE TABLE IF NOT EXISTS `user_preferences` (
  `user_id` int NOT NULL,
  `default_live_platforms` text,
  `default_follow_platforms` text,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) { echo json_encode(array('ok' => false, 'error' => 'Invalid JSON')); exit; }

    $live = isset($input['default_live_platforms']) ? json_encode($input['default_live_platforms']) : null;
    $follow = isset($input['default_follow_platforms']) ? json_encode($input['default_follow_platforms']) : null;
    $live_s = $live !== null ? "'" . $conn->real_escape_string($live) . "'" : 'NULL';
    $follow_s = $follow !== null ? "'" . $conn->real_escape_string($follow) . "'" : 'NULL';

    $conn->query("INSERT INTO user_preferences (user_id, default_live_platforms, default_follow_platforms)
        VALUES ($user_id, $live_s, $follow_s)
        ON DUPLICATE KEY UPDATE
            default_live_platforms = $live_s,
            default_follow_platforms = $follow_s");

    $email = isset($_SESSION['user']['email']) ? $_SESSION['user']['email'] : '';
    $sv_q = $conn->query("SELECT sync_version FROM user_preferences WHERE user_id = $user_id LIMIT 1");
    $sv = 1;
    if ($sv_q && $sv_q->num_rows > 0) {
        $sv_row = $sv_q->fetch_assoc();
        $sv = isset($sv_row['sync_version']) ? (int)$sv_row['sync_version'] + 1 : 1;
        $conn->query("UPDATE user_preferences SET sync_version = $sv WHERE user_id = $user_id");
    }
    $row_data = array('user_id' => $user_id, 'default_live_platforms' => $live, 'default_follow_platforms' => $follow, 'sync_version' => $sv);
    sync_log_write($conn, 'user_preferences', 'UPDATE', array('user_id' => $user_id), $row_data, $email, null);

    echo json_encode(array('ok' => true));
} else {
    $r = $conn->query("SELECT default_live_platforms, default_follow_platforms FROM user_preferences WHERE user_id = $user_id");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $prefs = array();
        if ($row['default_live_platforms']) $prefs['default_live_platforms'] = json_decode($row['default_live_platforms'], true);
        if ($row['default_follow_platforms']) $prefs['default_follow_platforms'] = json_decode($row['default_follow_platforms'], true);
        echo json_encode(array('ok' => true, 'preferences' => $prefs));
    } else {
        echo json_encode(array('ok' => true, 'preferences' => array()));
    }
}

$conn->close();
