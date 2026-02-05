<?php
/**
 * Save or update a link list. Session-protected: only own lists.
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
    echo json_encode(array('error' => 'Use POST to save a link list'));
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

if (!$data || !isset($data['list_name'])) {
    ob_end_clean();
    echo json_encode(array('error' => 'Invalid input: list_name required'));
    exit;
}
$list_name = $conn->real_escape_string(trim($data['list_name']));
$links = $conn->real_escape_string(isset($data['links']) ? $data['links'] : '');

if ($list_name === '') {
    ob_end_clean();
    echo json_encode(array('error' => 'list_name cannot be empty'));
    exit;
}

// Upsert
$check = $conn->query("SELECT id FROM user_link_lists WHERE user_id = $user_id AND list_name = '$list_name'");
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $id = (int)$row['id'];
    $query = "UPDATE user_link_lists SET links = '$links' WHERE id = $id";
} else {
    $query = "INSERT INTO user_link_lists (user_id, list_name, links) VALUES ($user_id, '$list_name', '$links')";
}

ob_end_clean();
if ($conn->query($query) === TRUE) {
    $id = isset($id) ? $id : $conn->insert_id;
    echo json_encode(array('status' => 'success', 'id' => $id));
} else {
    echo json_encode(array('error' => 'Failed to save: ' . $conn->error));
}
$conn->close();
?>
