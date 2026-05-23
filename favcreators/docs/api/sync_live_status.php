<?php
/**
 * API endpoint to sync live status from frontend to database cache.
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

// Get JSON input
$input = json_decode(file_get_contents('php://input'), true);

if (!$input || !isset($input['creators']) || !is_array($input['creators'])) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid JSON input or missing creators array'));
    exit;
}

$now = date('Y-m-d H:i:s');
$updated = 0;
$errors = array();

// Ensure table exists
$conn->query("CREATE TABLE IF NOT EXISTS live_status_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    creator_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(1024) DEFAULT '',
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(255) NOT NULL,
    is_live TINYINT(1) DEFAULT 0,
    stream_title VARCHAR(512) DEFAULT '',
    viewer_count INT DEFAULT 0,
    started_at VARCHAR(64) DEFAULT '',
    check_method VARCHAR(64) DEFAULT '',
    next_check_date BIGINT DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_creator_platform (creator_id, platform),
    INDEX idx_is_live (is_live),
    INDEX idx_last_updated (last_updated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

// Process each creator
foreach ($input['creators'] as $creator) {
    if (!isset($creator['id']) || !isset($creator['accounts']) || !is_array($creator['accounts'])) {
        continue;
    }
    
    $creator_id = $conn->real_escape_string($creator['id']);
    $creator_name = isset($creator['name']) ? $conn->real_escape_string($creator['name']) : '';
    $avatar_url = isset($creator['avatarUrl']) ? $conn->real_escape_string($creator['avatarUrl']) : '';
    
    foreach ($creator['accounts'] as $account) {
        if (!isset($account['platform']) || !isset($account['username'])) {
            continue;
        }
        
        $platform = $conn->real_escape_string($account['platform']);
        $username = $conn->real_escape_string($account['username']);
        $is_live = !empty($account['isLive']) ? 1 : 0;
        $stream_title = isset($account['streamTitle']) ? $conn->real_escape_string($account['streamTitle']) : '';
        $viewer_count = isset($account['viewerCount']) ? intval($account['viewerCount']) : 0;
        $started_at = isset($account['startedAt']) ? $conn->real_escape_string($account['startedAt']) : '';
        $check_method = isset($account['checkMethod']) ? $conn->real_escape_string($account['checkMethod']) : '';
        $next_check_date = isset($account['nextCheckDate']) ? intval($account['nextCheckDate']) : 0;
        
        // Check if record exists using bind_result
        $existing_id = null;
        $check_sql = "SELECT id FROM live_status_cache WHERE creator_id = ? AND platform = ?";
        $check_stmt = $conn->prepare($check_sql);
        $check_stmt->bind_param("ss", $creator_id, $platform);
        $check_stmt->execute();
        $check_stmt->bind_result($existing_id);
        if (!$check_stmt->fetch()) {
            $existing_id = null;
        }
        $check_stmt->close();
        
        if ($existing_id) {
            // Update existing record
            $update_sql = "UPDATE live_status_cache SET 
                creator_name = ?,
                avatar_url = ?,
                username = ?,
                is_live = ?,
                stream_title = ?,
                viewer_count = ?,
                started_at = ?,
                check_method = ?,
                next_check_date = ?,
                last_updated = ?
                WHERE creator_id = ? AND platform = ?";
            
            $update_stmt = $conn->prepare($update_sql);
            $update_stmt->bind_param("sssisississs", 
                $creator_name, $avatar_url, $username, $is_live, 
                $stream_title, $viewer_count, $started_at, $check_method, 
                $next_check_date, $now, $creator_id, $platform
            );
            
            if ($update_stmt->execute()) {
                $updated++;
            } else {
                $errors[] = "Update failed for $creator_id/$platform: " . $conn->error;
            }
            $update_stmt->close();
        } else {
            // Insert new record
            $insert_sql = "INSERT INTO live_status_cache 
                (creator_id, creator_name, avatar_url, platform, username, is_live, 
                 stream_title, viewer_count, started_at, check_method, next_check_date, last_updated) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            $insert_stmt = $conn->prepare($insert_sql);
            $insert_stmt->bind_param("sssssisissis", 
                $creator_id, $creator_name, $avatar_url, $platform, $username, $is_live,
                $stream_title, $viewer_count, $started_at, $check_method, $next_check_date, $now
            );
            
            if ($insert_stmt->execute()) {
                $updated++;
            } else {
                $errors[] = "Insert failed for $creator_id/$platform: " . $conn->error;
            }
            $insert_stmt->close();
        }
    }
}

// Clean up old records
$conn->query("DELETE FROM live_status_cache WHERE last_updated < DATE_SUB(NOW(), INTERVAL 24 HOUR)");

$response = array(
    'ok' => true,
    'updated' => $updated,
    'timestamp' => $now
);

if (!empty($errors)) {
    $response['errors'] = $errors;
}

echo json_encode($response);
$conn->close();
?>
