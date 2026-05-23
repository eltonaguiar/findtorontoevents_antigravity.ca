<?php
/**
 * API endpoint to update streamer last seen status.
 * PHP 5.2 compatible version (without get_result())
 */

error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

require_once 'db_connect.php';

// Ensure tables exist
$conn->query("CREATE TABLE IF NOT EXISTS streamer_last_seen (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    creator_name VARCHAR(255) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(255) NOT NULL,
    account_url VARCHAR(1024) DEFAULT '',
    is_live TINYINT(1) DEFAULT 0,
    last_seen_online DATETIME,
    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    stream_title VARCHAR(512) DEFAULT '',
    viewer_count INT DEFAULT 0,
    check_count INT DEFAULT 1,
    first_seen_by VARCHAR(255) DEFAULT '',
    UNIQUE KEY uq_creator_platform (creator_id, platform),
    INDEX idx_is_live (is_live),
    INDEX idx_last_seen_online (last_seen_online),
    INDEX idx_last_checked (last_checked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

$conn->query("CREATE TABLE IF NOT EXISTS streamer_check_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    creator_name VARCHAR(255) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    was_live TINYINT(1) DEFAULT 0,
    checked_by VARCHAR(255) DEFAULT '',
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INT DEFAULT 0,
    INDEX idx_creator_id (creator_id),
    INDEX idx_checked_at (checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

// Get JSON input
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid JSON input'));
    exit;
}

// Validate required fields
$required = array('creator_id', 'creator_name', 'platform', 'username', 'is_live');
foreach ($required as $field) {
    if (!isset($input[$field])) {
        echo json_encode(array('ok' => false, 'error' => 'Missing required field: ' . $field));
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
$now = date('Y-m-d H:i:s');

// Check if record exists using bind_result for PHP 5.2 compatibility
$existing_id = null;
$existing_check_count = 0;
$existing_first_seen_by = '';

$check_sql = "SELECT id, check_count, first_seen_by FROM streamer_last_seen WHERE creator_id = ? AND platform = ?";
$check_stmt = $conn->prepare($check_sql);
if ($check_stmt) {
    $check_stmt->bind_param("ss", $creator_id, $platform);
    $check_stmt->execute();
    $check_stmt->bind_result($existing_id, $existing_check_count, $existing_first_seen_by);
    if (!$check_stmt->fetch()) {
        $existing_id = null;
    }
    $check_stmt->close();
}

if ($existing_id) {
    // Update existing record
    if ($is_live) {
        $update_sql = "UPDATE streamer_last_seen SET 
            creator_name = ?,
            username = ?,
            account_url = ?,
            is_live = ?,
            last_checked = ?,
            stream_title = ?,
            viewer_count = ?,
            check_count = check_count + 1,
            last_seen_online = ?
            WHERE id = ?";
        
        $update_stmt = $conn->prepare($update_sql);
        $update_stmt->bind_param("sssissisi", 
            $creator_name, $username, $account_url, $is_live, $now, 
            $stream_title, $viewer_count, $now, $existing_id
        );
    } else {
        $update_sql = "UPDATE streamer_last_seen SET 
            creator_name = ?,
            username = ?,
            account_url = ?,
            is_live = ?,
            last_checked = ?,
            stream_title = ?,
            viewer_count = ?,
            check_count = check_count + 1
            WHERE id = ?";
        
        $update_stmt = $conn->prepare($update_sql);
        $update_stmt->bind_param("sssissii", 
            $creator_name, $username, $account_url, $is_live, $now, 
            $stream_title, $viewer_count, $existing_id
        );
    }
    
    $result = $update_stmt->execute();
    $update_stmt->close();
    
    if (!$result) {
        echo json_encode(array('ok' => false, 'error' => 'Update failed: ' . $conn->error));
        exit;
    }
    
    $action = 'updated';
    $record_id = $existing_id;
} else {
    // Insert new record
    $insert_sql = "INSERT INTO streamer_last_seen 
        (creator_id, creator_name, platform, username, account_url, is_live, last_seen_online, last_checked, stream_title, viewer_count, check_count, first_seen_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)";
    
    $insert_stmt = $conn->prepare($insert_sql);
    
    if ($is_live) {
        $insert_stmt->bind_param("sssssisssis", 
            $creator_id, $creator_name, $platform, $username, $account_url, 
            $is_live, $now, $now, $stream_title, $viewer_count, $checked_by
        );
    } else {
        $null_val = null;
        $insert_stmt->bind_param("sssssisssis", 
            $creator_id, $creator_name, $platform, $username, $account_url, 
            $is_live, $null_val, $now, $stream_title, $viewer_count, $checked_by
        );
    }
    
    $result = $insert_stmt->execute();
    $insert_stmt->close();
    
    if (!$result) {
        echo json_encode(array('ok' => false, 'error' => 'Insert failed: ' . $conn->error));
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

echo json_encode(array(
    'ok' => true,
    'action' => $action,
    'record_id' => $record_id,
    'creator_id' => $creator_id,
    'platform' => $platform,
    'is_live' => $is_live == 1,
    'last_checked' => $now,
    'checked_by' => $checked_by
));

$conn->close();
?>
