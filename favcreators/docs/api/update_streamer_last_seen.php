<?php
/**
 * API endpoint to update streamer last seen status.
 * Called by the frontend when a user checks live status and finds a streamer online.
 * 
 * POST /api/update_streamer_last_seen.php
 * 
 * Request body (JSON):
 * {
 *   "creator_id": "creator123",
 *   "creator_name": "StreamerName",
 *   "platform": "twitch",
 *   "username": "streamer_username",
 *   "account_url": "https://twitch.tv/streamer",
 *   "is_live": true,
 *   "stream_title": "Stream Title",
 *   "viewer_count": 1234,
 *   "checked_by": "user@example.com"
 * }
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

require_once 'db_connect.php';
require_once 'streamer_last_seen_schema.php';

// Get JSON input
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON input']);
    exit;
}

// Validate required fields
$required = ['creator_id', 'creator_name', 'platform', 'username', 'is_live'];
foreach ($required as $field) {
    if (!isset($input[$field])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(['ok' => false, 'error' => "Missing required field: $field"]);
        exit;
    }
}

$creator_id = $conn->real_escape_string($input['creator_id']);
$creator_name = $conn->real_escape_string($input['creator_name']);
$platform = $conn->real_escape_string($input['platform']);
$username = $conn->real_escape_string($input['username']);
$account_url = isset($input['account_url']) ? $conn->real_escape_string($input['account_url']) : '';
$is_live = $input['is_live'] ? 1 : 0;
$stream_title = isset($input['stream_title']) ? $conn->real_escape_string($input['stream_title']) : '';
$viewer_count = isset($input['viewer_count']) ? intval($input['viewer_count']) : 0;
$checked_by = isset($input['checked_by']) ? $conn->real_escape_string($input['checked_by']) : 'anonymous';

$start_time = microtime(true);

// Check if record exists
$check_sql = "SELECT id, check_count, first_seen_by FROM streamer_last_seen WHERE creator_id = ? AND platform = ?";
$check_stmt = $conn->prepare($check_sql);
$check_stmt->bind_param("ss", $creator_id, $platform);
$check_stmt->execute();
$check_result = $check_stmt->get_result();
$existing = $check_result->fetch_assoc();
$check_stmt->close();

$now = date('Y-m-d H:i:s');

if ($existing) {
    // Update existing record
    $update_sql = "UPDATE streamer_last_seen SET 
        creator_name = ?,
        username = ?,
        account_url = ?,
        is_live = ?,
        last_checked = ?,
        stream_title = ?,
        viewer_count = ?,
        check_count = check_count + 1";
    
    $params = [$creator_name, $username, $account_url, $is_live, $now, $stream_title, $viewer_count];
    $types = "sssissi";
    
    // Only update last_seen_online if currently live
    if ($is_live) {
        $update_sql .= ", last_seen_online = ?";
        $params[] = $now;
        $types .= "s";
    }
    
    $update_sql .= " WHERE id = ?";
    $params[] = $existing['id'];
    $types .= "i";
    
    $update_stmt = $conn->prepare($update_sql);
    // PHP 5 compatible: use call_user_func_array instead of spread operator
    $bind_params = array_merge(array($types), $params);
    call_user_func_array(array($update_stmt, 'bind_param'), $bind_params);
    $result = $update_stmt->execute();
    $update_stmt->close();
    
    if (!$result) {
        header('HTTP/1.1 500 Internal Server Error');
        echo json_encode(['ok' => false, 'error' => 'Update failed: ' . $conn->error]);
        exit;
    }
    
    $action = 'updated';
    $record_id = $existing['id'];
} else {
    // Insert new record
    $insert_sql = "INSERT INTO streamer_last_seen 
        (creator_id, creator_name, platform, username, account_url, is_live, last_seen_online, last_checked, stream_title, viewer_count, check_count, first_seen_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)";
    
    $last_seen_online = $is_live ? $now : null;
    
    $insert_stmt = $conn->prepare($insert_sql);
    $insert_stmt->bind_param("sssssisssis", 
        $creator_id, $creator_name, $platform, $username, $account_url, 
        $is_live, $last_seen_online, $now, $stream_title, $viewer_count, $checked_by
    );
    $result = $insert_stmt->execute();
    $insert_stmt->close();
    
    if (!$result) {
        header('HTTP/1.1 500 Internal Server Error');
        echo json_encode(['ok' => false, 'error' => 'Insert failed: ' . $conn->error]);
        exit;
    }
    
    $action = 'created';
    $record_id = $conn->insert_id;
}

// Log the check
$response_time = intval((microtime(true) - $start_time) * 1000);
$log_sql = "INSERT INTO streamer_check_log (creator_id, creator_name, platform, was_live, checked_by, checked_at, response_time_ms) 
            VALUES (?, ?, ?, ?, ?, ?, ?)";
$log_stmt = $conn->prepare($log_sql);
$log_stmt->bind_param("sssissi", $creator_id, $creator_name, $platform, $is_live, $checked_by, $now, $response_time);
$log_stmt->execute();
$log_stmt->close();

echo json_encode([
    'ok' => true,
    'action' => $action,
    'record_id' => $record_id,
    'creator_id' => $creator_id,
    'platform' => $platform,
    'is_live' => $is_live == 1,
    'last_checked' => $now,
    'checked_by' => $checked_by
]);

$conn->close();
?>