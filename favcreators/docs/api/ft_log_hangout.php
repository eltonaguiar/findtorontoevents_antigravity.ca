<?php
/**
 * FriendTracker: Log a hangout with a friend.
 * Accepts POST with friendId, date, activity, notes.
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

if (!$data || !isset($data['friendId']) || !isset($data['date'])) {
    echo json_encode(array('error' => 'Invalid input: friendId and date are required'));
    exit;
}

$friend_id = $conn->real_escape_string($data['friendId']);
$date = $conn->real_escape_string($data['date']);
$activity = isset($data['activity']) ? $conn->real_escape_string(trim($data['activity'])) : '';
$notes = isset($data['notes']) ? $conn->real_escape_string(trim($data['notes'])) : '';

// Verify that the friend belongs to the current user
$friend_check = $conn->query("SELECT id, name FROM friendt_friends WHERE id = '$friend_id' AND user_id = $user_id");
if (!$friend_check || $friend_check->num_rows === 0) {
    echo json_encode(array('error' => 'Friend not found or access denied'));
    exit;
}
$friend_row = $friend_check->fetch_assoc();
$friend_name = $friend_row['name'];

// Generate hangout ID
$hangout_id = 'hang_' . time() . '_' . rand(1000, 9999);

// Insert hangout
$sql = "INSERT INTO friendt_hangouts (id, friend_id, user_id, date, activity, notes, created_at)
        VALUES ('$hangout_id', '$friend_id', $user_id, '$date', '$activity', '$notes', CURRENT_TIMESTAMP)";

if (!$conn->query($sql)) {
    $error_msg = $conn->error;
    echo json_encode(array('error' => 'Database error: ' . $error_msg, 'sql' => $sql));
    $conn->close();
    exit;
}

// Retrieve the created hangout
$result = $conn->query("SELECT * FROM friendt_hangouts WHERE id = '$hangout_id' AND user_id = $user_id");
if (!$result || $result->num_rows === 0) {
    echo json_encode(array('error' => 'Hangout logged but could not retrieve'));
    $conn->close();
    exit;
}

$row = $result->fetch_assoc();
$hangout = array(
    'id' => $row['id'],
    'friendId' => $row['friend_id'],
    'date' => $row['date'],
    'activity' => $row['activity'],
    'notes' => $row['notes'],
    'createdAt' => $row['created_at']
);

// Update friend's last updated timestamp (optional)
$conn->query("UPDATE friendt_friends SET updated_at = CURRENT_TIMESTAMP WHERE id = '$friend_id' AND user_id = $user_id");

echo json_encode(array(
    'status' => 'success',
    'hangout' => $hangout,
    'friendName' => $friend_name,
    'message' => 'Hangout logged with ' . $friend_name
));

$conn->close();
?>