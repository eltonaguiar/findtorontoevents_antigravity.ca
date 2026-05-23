<?php
/**
 * Get all link lists for a user. Session-protected: only own lists unless admin.
 */
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    ob_end_clean();
    echo json_encode(array('lists' => array()));
    exit;
}
require_once dirname(__FILE__) . '/db_schema.php';

$session_id = get_session_user_id();
if ($session_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    ob_end_clean();
    echo json_encode(array('lists' => array()));
    exit;
}
// Admin can view any user_id. Non-admin can ONLY view their own (no guest/0, no others).
$requested_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : $session_id;
if (is_session_admin()) {
    $user_id = (int) $requested_id;
} else {
    if ($requested_id !== $session_id) {
        header('HTTP/1.1 403 Forbidden');
        ob_end_clean();
        echo json_encode(array('lists' => array()));
        exit;
    }
    $user_id = (int) $session_id;
}

$query = "SELECT id, list_name, links, created_at, updated_at FROM user_link_lists WHERE user_id = $user_id ORDER BY updated_at DESC";
$result = $conn->query($query);

$lists = array();
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $lists[] = array(
            'id' => (int)$row['id'],
            'list_name' => $row['list_name'],
            'links' => isset($row['links']) ? $row['links'] : '',
            'created_at' => $row['created_at'],
            'updated_at' => $row['updated_at'],
        );
    }
}

ob_end_clean();
echo json_encode(array('lists' => $lists));
$conn->close();
?>
