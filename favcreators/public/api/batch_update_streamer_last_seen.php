<?php
/**
 * API endpoint for batch updating streamer last seen status.
 * More efficient for syncing multiple streamers at once.
 * 
 * POST /api/batch_update_streamer_last_seen.php
 * 
 * Request body (JSON):
 * {
 *   "updates": [
 *     {
 *       "creator_id": "creator123",
 *       "creator_name": "StreamerName",
 *       "platform": "twitch",
 *       "username": "streamer_username",
 *       "account_url": "https://twitch.tv/streamer",
 *       "is_live": true,
 *       "stream_title": "Stream Title",
 *       "viewer_count": 1234
 *     }
 *   ],
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

if (!$input || !isset($input['updates']) || !is_array($input['updates'])) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON input. Expected { updates: [...] }']);
    exit;
}

$updates = $input['updates'];
$checked_by = isset($input['checked_by']) ? $conn->real_escape_string($input['checked_by']) : 'anonymous';

if (count($updates) === 0) {
    echo json_encode(['ok' => true, 'processed' => 0, 'results' => []]);
    exit;
}

// Limit batch size to prevent abuse
if (count($updates) > 100) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(['ok' => false, 'error' => 'Batch size exceeds maximum of 100']);
    exit;
}

$start_time = microtime(true);
$results = [];
$processed = 0;
$now = date('Y-m-d H:i:s');

$conn->begin_transaction();

try {
    // Prepare statements for reuse
    $check_stmt = $conn->prepare("SELECT id, check_count FROM streamer_last_seen WHERE creator_id = ? AND platform = ?");
    $update_stmt = $conn->prepare("UPDATE streamer_last_seen SET 
        creator_name = ?, username = ?, account_url = ?, is_live = ?, 
        last_checked = ?, last_seen_online = ?, stream_title = ?, viewer_count = ?, 
        check_count = check_count + 1 WHERE id = ?");
    $insert_stmt = $conn->prepare("INSERT INTO streamer_last_seen 
        (creator_id, creator_name, platform, username, account_url, is_live, last_seen_online, last_checked, stream_title, viewer_count, check_count, first_seen_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)");
    $log_stmt = $conn->prepare("INSERT INTO streamer_check_log 
        (creator_id, creator_name, platform, was_live, checked_by, checked_at, response_time_ms) 
        VALUES (?, ?, ?, ?, ?, ?, 0)");
    
    foreach ($updates as $update) {
        // Validate required fields
        if (!isset($update['creator_id'], $update['creator_name'], $update['platform'], $update['username'])) {
            $results[] = ['error' => 'Missing required fields', 'skipped' => true];
            continue;
        }
        
        $creator_id = $update['creator_id'];
        $creator_name = $update['creator_name'];
        $platform = $update['platform'];
        $username = $update['username'];
        $account_url = $update['account_url'] ?? '';
        $is_live = !empty($update['is_live']) ? 1 : 0;
        $stream_title = $update['stream_title'] ?? '';
        $viewer_count = intval($update['viewer_count'] ?? 0);
        
        // Check if exists
        $check_stmt->bind_param("ss", $creator_id, $platform);
        $check_stmt->execute();
        $check_result = $check_stmt->get_result();
        $existing = $check_result->fetch_assoc();
        
        if ($existing) {
            // Update
            $last_seen = $is_live ? $now : null;
            $update_stmt->bind_param("sssissssii", 
                $creator_name, $username, $account_url, $is_live, 
                $now, $last_seen, $stream_title, $viewer_count, $existing['id']
            );
            $update_stmt->execute();
            $action = 'updated';
            $record_id = $existing['id'];
        } else {
            // Insert
            $last_seen = $is_live ? $now : null;
            $insert_stmt->bind_param("sssssisssis", 
                $creator_id, $creator_name, $platform, $username, $account_url,
                $is_live, $last_seen, $now, $stream_title, $viewer_count, $checked_by
            );
            $insert_stmt->execute();
            $action = 'created';
            $record_id = $conn->insert_id;
        }
        
        // Log
        $log_stmt->bind_param("sssis", $creator_id, $creator_name, $platform, $is_live, $checked_by, $now);
        $log_stmt->execute();
        
        $results[] = [
            'creator_id' => $creator_id,
            'platform' => $platform,
            'action' => $action,
            'is_live' => $is_live == 1
        ];
        $processed++;
    }
    
    $check_stmt->close();
    $update_stmt->close();
    $insert_stmt->close();
    $log_stmt->close();
    
    $conn->commit();
    
    $response_time = intval((microtime(true) - $start_time) * 1000);
    
    echo json_encode([
        'ok' => true,
        'processed' => $processed,
        'total_received' => count($updates),
        'response_time_ms' => $response_time,
        'checked_by' => $checked_by,
        'results' => $results
    ]);
    
} catch (Exception $e) {
    $conn->rollback();
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(['ok' => false, 'error' => 'Batch update failed: ' . $e->getMessage()]);
}

$conn->close();
?>