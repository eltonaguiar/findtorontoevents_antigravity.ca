<?php
/**
 * FriendTracker: Create or update an event.
 * Accepts POST with event data, saves to friendt_events.
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

if (!$data || !isset($data['name']) || trim($data['name']) === '' || !isset($data['date'])) {
    echo json_encode(array('error' => 'Invalid input: name and date are required'));
    exit;
}

// Extract and validate event data
$event_id = isset($data['id']) ? $conn->real_escape_string($data['id']) : '';
if ($event_id === '') {
    // Generate new ID if not provided
    $event_id = 'event_' . time() . '_' . rand(1000, 9999);
}

// Map JS camelCase to DB snake_case
$name = $conn->real_escape_string(trim($data['name']));
$type = isset($data['type']) ? $conn->real_escape_string(trim($data['type'])) : 'hangout';
$date = $conn->real_escape_string($data['date']);
$time = isset($data['time']) && $data['time'] ? $conn->real_escape_string($data['time']) : null;
$location = isset($data['location']) ? $conn->real_escape_string(trim($data['location'])) : '';
$description = isset($data['description']) ? $conn->real_escape_string(trim($data['description'])) : '';

// JSON fields
$invite_by_tags = isset($data['inviteByTags']) && is_array($data['inviteByTags']) ? $conn->real_escape_string(json_encode($data['inviteByTags'])) : '[]';
$invited_friends = isset($data['invitedFriends']) && is_array($data['invitedFriends']) ? $conn->real_escape_string(json_encode($data['invitedFriends'])) : '[]';

// Determine if this is an update or insert
$existing_check = $conn->query("SELECT id FROM friendt_events WHERE id = '$event_id' AND user_id = $user_id");
$is_update = ($existing_check && $existing_check->num_rows > 0);

if ($is_update) {
    // Update existing event
    $sql = "UPDATE friendt_events SET
        name = '$name',
        type = '$type',
        date = '$date',
        time = " . ($time ? "'$time'" : "NULL") . ",
        location = '$location',
        description = '$description',
        invite_by_tags = '$invite_by_tags',
        invited_friends = '$invited_friends',
        updated_at = CURRENT_TIMESTAMP
        WHERE id = '$event_id' AND user_id = $user_id";
} else {
    // Insert new event
    $sql = "INSERT INTO friendt_events (
        id, user_id, name, type, date, time, location, description,
        invite_by_tags, invited_friends, created_at, updated_at
    ) VALUES (
        '$event_id',
        $user_id,
        '$name',
        '$type',
        '$date',
        " . ($time ? "'$time'" : "NULL") . ",
        '$location',
        '$description',
        '$invite_by_tags',
        '$invited_friends',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )";
}

if (!$conn->query($sql)) {
    $error_msg = $conn->error;
    echo json_encode(array('error' => 'Database error: ' . $error_msg, 'sql' => $sql));
    $conn->close();
    exit;
}

// Retrieve the saved event to return
$result = $conn->query("SELECT * FROM friendt_events WHERE id = '$event_id' AND user_id = $user_id");
if (!$result || $result->num_rows === 0) {
    echo json_encode(array('error' => 'Event saved but could not retrieve'));
    $conn->close();
    exit;
}

$row = $result->fetch_assoc();
$event = array(
    'id' => $row['id'],
    'name' => $row['name'],
    'type' => $row['type'],
    'date' => $row['date'],
    'time' => $row['time'],
    'location' => $row['location'],
    'description' => $row['description'],
    'inviteByTags' => json_decode($row['invite_by_tags'], true) ?: array(),
    'invitedFriends' => json_decode($row['invited_friends'], true) ?: array(),
    'createdAt' => $row['created_at'],
    'updatedAt' => $row['updated_at']
);

echo json_encode(array(
    'status' => 'success',
    'event' => $event,
    'isUpdate' => $is_update,
    'message' => $is_update ? 'Event updated successfully' : 'Event created successfully'
));

$conn->close();
?>