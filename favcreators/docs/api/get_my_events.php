<?php
/**
 * Get "My Events" (saved Toronto events) for the logged-in user.
 * Session-only: user_id is taken from session, not from the request.
 * Returns: { "events": [ { "id", "title", ... }, ... ] } or 401 if not logged in.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Credentials: true');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/session_auth.php';
$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized', 'events' => array()));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available', 'events' => array()));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';

$user_id_esc = (int) $user_id;
$result = $conn->query("SELECT event_id, event_data FROM user_saved_events WHERE user_id = $user_id_esc ORDER BY created_at ASC");

$events = array();
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $data = json_decode($row['event_data'], true);
        if (is_array($data)) {
            $events[] = $data;
        } else {
            $events[] = array('id' => $row['event_id'], 'title' => $row['event_id']);
        }
    }
}

echo json_encode(array('events' => $events));
$conn->close();
