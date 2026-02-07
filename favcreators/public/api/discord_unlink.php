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

// Also clear notification preferences
$conn->query("DELETE FROM notification_preferences WHERE user_id = $user_id_int");

echo json_encode(array('ok' => true, 'message' => 'Discord unlinked'));
$conn->close();
