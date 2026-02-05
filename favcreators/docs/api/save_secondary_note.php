<?php
/**
 * Save secondary note for a creator. Session-protected: only own notes.
 * POST: { creator_id, secondary_note } (user_id from session)
 */
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    header('HTTP/1.1 204 No Content');
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    ob_end_clean();
    echo json_encode(array('error' => 'Use POST to save a secondary note'));
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    ob_end_clean();
    echo json_encode(array('error' => 'Unauthorized'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    ob_end_clean();
    echo json_encode(array('error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/db_schema.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['creator_id'])) {
    ob_end_clean();
    echo json_encode(array('error' => 'Invalid JSON input'));
    exit;
}

$creator_id = $conn->real_escape_string($data['creator_id']);
$secondary_note = $conn->real_escape_string(isset($data['secondary_note']) ? $data['secondary_note'] : '');

// Upsert into user_secondary_notes
$check_query = "SELECT id FROM user_secondary_notes WHERE user_id = $user_id AND creator_id = '$creator_id'";
$check = $conn->query($check_query);

if ($check && $check->num_rows > 0) {
    $query = "UPDATE user_secondary_notes SET secondary_note = '$secondary_note' WHERE user_id = $user_id AND creator_id = '$creator_id'";
} else {
    $query = "INSERT INTO user_secondary_notes (user_id, creator_id, secondary_note) VALUES ($user_id, '$creator_id', '$secondary_note')";
}

ob_end_clean();
if ($conn->query($query) === TRUE) {
    echo json_encode(array('status' => 'success', 'message' => 'Secondary note saved'));
} else {
    echo json_encode(array('error' => 'Failed to save secondary note: ' . $conn->error));
}
$conn->close();
?>
