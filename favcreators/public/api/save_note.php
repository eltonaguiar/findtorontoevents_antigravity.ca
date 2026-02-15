<?php
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
    echo json_encode(array('error' => 'Use POST to save a note', 'status' => 'ok'));
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
$session_id = get_session_user_id();
if ($session_id === null) {
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

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['creator_id'])) {
    ob_end_clean();
    echo json_encode(array('error' => 'Invalid JSON input'));
    exit;
}

$creator_id = $conn->real_escape_string($data['creator_id']);
$note = $conn->real_escape_string(isset($data['note']) ? $data['note'] : '');
$requested_id = isset($data['user_id']) ? intval($data['user_id']) : $session_id;

// Only allow saving to own user_id, or to 0 (global default) if admin.
if ($requested_id !== $session_id && $requested_id !== 0) {
    header('HTTP/1.1 403 Forbidden');
    ob_end_clean();
    echo json_encode(array('error' => 'Access denied'));
    exit;
}
if ($requested_id === 0 && !is_session_admin()) {
    header('HTTP/1.1 403 Forbidden');
    ob_end_clean();
    echo json_encode(array('error' => 'Only admin can update global defaults'));
    exit;
}
$user_id = $requested_id;

// If admin saving to 0, we update the GLOBAL default for this creator
if ($user_id === 0) {
    // Check if record exists
    $check_query = "SELECT id FROM creator_defaults WHERE creator_id = '$creator_id'";
    $check = $conn->query($check_query);

    if ($check && $check->num_rows > 0) {
        $query = "UPDATE creator_defaults SET note = '$note' WHERE creator_id = '$creator_id'";
    } else {
        $query = "INSERT INTO creator_defaults (creator_id, note) VALUES ('$creator_id', '$note')";
    }
} else {
    // User specific note
    $check_query = "SELECT id FROM user_notes WHERE user_id = $user_id AND creator_id = '$creator_id'";
    $check = $conn->query($check_query);

    if ($check && $check->num_rows > 0) {
        $query = "UPDATE user_notes SET note = '$note' WHERE user_id = $user_id AND creator_id = '$creator_id'";
    } else {
        $query = "INSERT INTO user_notes (user_id, creator_id, note) VALUES ($user_id, '$creator_id', '$note')";
    }
}

ob_end_clean();
if ($conn->query($query) === TRUE) {
    // Log the note save
    require_once dirname(__FILE__) . '/log_action.php';
    $user_email = null;
    if (function_exists('get_session_user')) {
        $session_user = get_session_user();
        if ($session_user) {
            $user_email = isset($session_user['email']) ? $session_user['email'] : null;
        }
    }
    $note_type = ($user_id === 0) ? 'global_default' : 'user_note';
    log_success('save_note', 'save_note.php',
        "Note saved for creator: $creator_id ($note_type)",
        json_encode(['creator_id' => $creator_id, 'user_id' => $user_id, 'note_type' => $note_type, 'note_length' => strlen($note)]),
        $session_id, $user_email);
    
    echo json_encode(array('status' => 'success', 'message' => 'Note saved'));
} else {
    echo json_encode(array('error' => 'Failed to save note: ' . $conn->error));
}
$conn->close();
?>