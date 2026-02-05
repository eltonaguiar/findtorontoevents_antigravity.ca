<?php
/**
 * API endpoint to get streamer last seen status.
 * PHP 5 compatible version
 */

header('Content-Type: application/json');

// Simple error handler
function send_error($message) {
    echo json_encode(array('ok' => false, 'error' => $message));
    exit;
}

require_once 'db_connect.php';
require_once 'streamer_last_seen_schema.php';

$creator_id = isset($_GET['creator_id']) ? $conn->real_escape_string($_GET['creator_id']) : null;
$platform = isset($_GET['platform']) ? $conn->real_escape_string($_GET['platform']) : null;
$live_only = isset($_GET['live_only']) && $_GET['live_only'] == '1';
$since_minutes = isset($_GET['since_minutes']) ? intval($_GET['since_minutes']) : 60;

// Build query - PHP 5 compatible string concatenation
$sql = "SELECT * FROM streamer_last_seen WHERE 1=1";
$params = array();
$types = "";

if ($creator_id) {
    $sql .= " AND creator_id = ?";
    $params[] = $creator_id;
    $types .= "s";
}

if ($platform) {
    $sql .= " AND platform = ?";
    $params[] = $platform;
    $types .= "s";
}

if ($live_only) {
    $sql .= " AND is_live = 1";
}

if ($since_minutes > 0) {
    $sql .= " AND (last_seen_online >= DATE_SUB(NOW(), INTERVAL ? MINUTE) OR last_checked >= DATE_SUB(NOW(), INTERVAL ? MINUTE))";
    $params[] = $since_minutes;
    $params[] = $since_minutes;
    $types .= "ii";
}

$sql .= " ORDER BY last_seen_online DESC, last_checked DESC";

$stmt = $conn->prepare($sql);
if (!$stmt) {
    send_error('Prepare failed: ' . $conn->error);
}

// Bind params if any
if (!empty($params)) {
    // PHP 5 compatible binding
    $bind_params = array_merge(array($types), $params);
    call_user_func_array(array($stmt, 'bind_param'), $bind_params);
}

$result = $stmt->execute();
if (!$result) {
    send_error('Execute failed: ' . $stmt->error);
}

$result_set = $stmt->get_result();
$streamers = array();

while ($row = $result_set->fetch_assoc()) {
    $streamers[] = array(
        'id' => $row['id'],
        'creator_id' => $row['creator_id'],
        'creator_name' => $row['creator_name'],
        'platform' => $row['platform'],
        'username' => $row['username'],
        'account_url' => $row['account_url'],
        'is_live' => $row['is_live'] == 1,
        'last_seen_online' => $row['last_seen_online'],
        'last_checked' => $row['last_checked'],
        'stream_title' => $row['stream_title'],
        'viewer_count' => intval($row['viewer_count']),
        'check_count' => intval($row['check_count']),
        'first_seen_by' => $row['first_seen_by']
    );
}

$stmt->close();

// Get stats
$stats_sql = "SELECT COUNT(*) as total_tracked FROM streamer_last_seen";
$stats_result = $conn->query($stats_sql);
$total_tracked = 0;
if ($stats_result && $row = $stats_result->fetch_assoc()) {
    $total_tracked = intval($row['total_tracked']);
}

// Build response
$response = array(
    'ok' => true,
    'streamers' => $streamers,
    'stats' => array(
        'total_tracked' => $total_tracked,
        'currently_live' => 0,
        'unique_creators' => 0,
        'last_check_time' => null
    ),
    'query' => array(
        'creator_id' => $creator_id,
        'platform' => $platform,
        'live_only' => $live_only,
        'since_minutes' => $since_minutes
    )
);

echo json_encode($response);
$conn->close();
?>