<?php
/**
 * Delete a link list. Session-protected: only own lists (user_id from session).
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
    echo json_encode(array('error' => 'Use POST to delete a link list'));
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

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    ob_end_clean();
    echo json_encode(array('error' => 'Invalid input'));
    exit;
}

if (isset($data['id'])) {
    $id = intval($data['id']);
    $query = "DELETE FROM user_link_lists WHERE id = $id AND user_id = $user_id";
} elseif (isset($data['list_name'])) {
    $list_name = $conn->real_escape_string($data['list_name']);
    $query = "DELETE FROM user_link_lists WHERE user_id = $user_id AND list_name = '$list_name'";
} else {
    ob_end_clean();
    echo json_encode(array('error' => 'id or list_name required'));
    exit;
}

ob_end_clean();
if ($conn->query($query) === TRUE) {
    echo json_encode(array('status' => 'success'));
} else {
    echo json_encode(array('error' => 'Failed to delete: ' . $conn->error));
}
$conn->close();
?>
