<?php
/**
 * Discord OAuth - Unlink account
 * Removes Discord link from user account
 * 
 * Usage: POST /fc/api/discord_unlink.php
 * Returns: JSON { ok: true }
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://findtorontoevents.ca');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/sync_log.php';

// Must be logged in
$user_id = get_session_user_id();
if ($user_id === null) {
    http_response_code(401);
    echo json_encode(array('ok' => false, 'error' => 'Must be logged in'));
    exit;
}

if (!isset($conn) || !$conn) {
    http_response_code(500);
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

$user_id_int = intval($user_id);
$sql = "UPDATE users SET discord_id = NULL, discord_username = NULL WHERE id = $user_id_int";
$result = $conn->query($sql);

if (!$result) {
    http_response_code(500);
    echo json_encode(array('ok' => false, 'error' => 'Failed to unlink Discord'));
    exit;
}

// Log each notification_preference deletion before removing
$np_rows = $conn->query("SELECT * FROM notification_preferences WHERE user_id = $user_id_int");
$email = sync_get_user_email_local($conn, $user_id_int);
if ($np_rows) {
    while ($np_row = $np_rows->fetch_assoc()) {
        $pk = array('user_id' => $user_id_int, 'creator_id' => $np_row['creator_id']);
        $np_row['sync_version'] = isset($np_row['sync_version']) ? (int)$np_row['sync_version'] + 1 : 1;
        sync_log_write($conn, 'notification_preferences', 'DELETE', $pk, $np_row, $email, null);
    }
}
$conn->query("DELETE FROM notification_preferences WHERE user_id = $user_id_int");

echo json_encode(array('ok' => true, 'message' => 'Discord unlinked'));
$conn->close();
