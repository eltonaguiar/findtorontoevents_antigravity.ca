<?php
/**
 * FriendTracker: Get all events for the logged-in user.
 * Returns events array with parsed JSON fields.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Pragma: no-cache");

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
    exit;
}

// Ensure tables exist
require_once dirname(__FILE__) . '/ensure_tables.php';

$response = array('events' => array());

// Get all events for this user, ordered by date ascending (upcoming first)
$events_query = $conn->query("
    SELECT 
        id, name, type, date, time, location, description,
        invite_by_tags, invited_friends, created_at, updated_at
    FROM friendt_events 
    WHERE user_id = $user_id 
    ORDER BY date ASC, time ASC
");

if ($events_query) {
    while ($row = $events_query->fetch_assoc()) {
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
        $response['events'][] = $event;
    }
}

echo json_encode($response, JSON_PRETTY_PRINT);
$conn->close();
?>