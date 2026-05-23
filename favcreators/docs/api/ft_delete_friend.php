<?php
/**
 * FriendTracker: Delete a friend and their hangouts.
 * Requires friend ID in POST JSON.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once dirname(__FILE__) . '/session_auth.php';
$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['id']) || trim($data['id']) === '') {
    echo json_encode(array('error' => 'Invalid input: friend ID is required'));
    exit;
}

$friend_id = $conn->real_escape_string(trim($data['id']));

// Verify the friend belongs to this user
$check = $conn->query("SELECT id FROM friendt_friends WHERE id = '$friend_id' AND user_id = $user_id");
if (!$check || $check->num_rows === 0) {
    echo json_encode(array('error' => 'Friend not found or access denied'));
    $conn->close();
    exit;
}

// Delete hangouts first (cascade)
$conn->query("DELETE FROM friendt_hangouts WHERE friend_id = '$friend_id' AND user_id = $user_id");
// Delete friend
$delete_result = $conn->query("DELETE FROM friendt_friends WHERE id = '$friend_id' AND user_id = $user_id");

if ($delete_result) {
    echo json_encode(array(
        'status' => 'success',
        'message' => 'Friend and associated hangouts deleted',
        'friendId' => $friend_id
    ));
} else {
    echo json_encode(array('error' => 'Delete failed: ' . $conn->error));
}

$conn->close();
?>