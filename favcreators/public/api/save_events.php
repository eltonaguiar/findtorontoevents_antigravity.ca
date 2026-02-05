<?php
/**
 * Save a Toronto event to "My Events" for the logged-in user.
 * Session-only: user_id is taken from session, not from the request body.
 * POST body: { "action": "add"|"remove", "event": { "id": string, "title": string, ... } }
 * Returns: { "status": "success" } or { "error": "..." } or 401 if not logged in.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Allow-Credentials: true');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('error' => 'Use POST'));
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized'));
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

if (!$data || !isset($data['event'])) {
    echo json_encode(array('error' => 'Invalid input: need event'));
    exit;
}

$action = isset($data['action']) ? $data['action'] : 'add';
$event = $data['event'];
if (!is_array($event) || empty($event['id'])) {
    echo json_encode(array('error' => 'event must be object with id'));
    exit;
}

$event_id = $conn->real_escape_string($event['id']);
$event_json = $conn->real_escape_string(json_encode($event));

if ($action === 'remove') {
    $q = "DELETE FROM user_saved_events WHERE user_id = $user_id AND event_id = '$event_id'";
    if (!$conn->query($q)) {
        echo json_encode(array('error' => $conn->error));
        $conn->close();
        exit;
    }
    echo json_encode(array('status' => 'success'));
    $conn->close();
    exit;
}

// add (default)
$q = "INSERT INTO user_saved_events (user_id, event_id, event_data) VALUES ($user_id, '$event_id', '$event_json') ON DUPLICATE KEY UPDATE event_data = '$event_json'";
if (!$conn->query($q)) {
    echo json_encode(array('error' => $conn->error));
    $conn->close();
    exit;
}

echo json_encode(array('status' => 'success'));
$conn->close();
