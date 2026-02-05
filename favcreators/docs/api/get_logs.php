<?php
/**
 * Admin-only endpoint to view FavCreators logs.
 * GET /api/get_logs.php?limit=50&offset=0&status=error&action=save_creators
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

// Get query parameters
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
$offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
$status = isset($_GET['status']) ? $conn->real_escape_string($_GET['status']) : '';
$action = isset($_GET['action']) ? $conn->real_escape_string($_GET['action']) : '';

// Build query
$where = array();
if ($status !== '') {
    $where[] = "status = '$status'";
}
if ($action !== '') {
    $where[] = "action = '$action'";
}
$where_clause = count($where) > 0 ? 'WHERE ' . implode(' AND ', $where) : '';

$query = "SELECT * FROM favcreatorslogs $where_clause ORDER BY created_at DESC LIMIT $limit OFFSET $offset";
$result = $conn->query($query);

$logs = array();
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $logs[] = $row;
    }
}

// Get total count
$count_query = "SELECT COUNT(*) as total FROM favcreatorslogs $where_clause";
$count_result = $conn->query($count_query);
$total = 0;
if ($count_result) {
    $count_row = $count_result->fetch_assoc();
    $total = (int) $count_row['total'];
}

echo json_encode(array(
    'logs' => $logs,
    'total' => $total,
    'limit' => $limit,
    'offset' => $offset
));

$conn->close();
?>