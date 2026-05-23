<?php
/**
 * API endpoint to update/insert creator status updates.
 * Called by the frontend or by fetch_platform_status.php when new content is detected.
 *
 * POST /api/update_creator_status.php
 *
 * Request body (JSON):
 * {
 *   "creator_id": "nevsrealm",
 *   "creator_name": "NevsRealm",
 *   "platform": "twitch",
 *   "username": "nevsrealm",
 *   "account_url": "https://twitch.tv/nevsrealm",
 *   "update_type": "stream",
 *   "content_title": "Playing Elden Ring",
 *   "content_url": "https://twitch.tv/nevsrealm",
 *   "content_preview": "Come hang out!",
 *   "content_thumbnail": "",
 *   "content_id": "stream_12345",
 *   "is_live": true,
 *   "viewer_count": 500,
 *   "like_count": 0,
 *   "comment_count": 0,
 *   "content_published_at": "2026-02-05 14:30:00",
 *   "checked_by": "system"
 * }
 *
 * Also supports batch updates:
 * POST with { "updates": [ {...}, {...} ] }
 *
 * PHP 5.2 compatible: uses $conn->query() with real_escape_string, no prepared statements.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 200 OK');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.0 405 Method Not Allowed'); header('Status: 405 Method Not Allowed');
    echo json_encode(array('ok' => false, 'error' => 'Method not allowed. Use POST.'));
    exit;
}

require_once 'db_connect.php';
require_once 'creator_status_updates_schema.php';

$allowed_platforms = array('twitch', 'kick', 'tiktok', 'instagram', 'twitter', 'reddit', 'youtube', 'spotify');
$allowed_types = array('post', 'story', 'stream', 'vod', 'tweet', 'comment', 'video', 'short', 'reel');

$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    header('HTTP/1.0 400 Bad Request'); header('Status: 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Invalid JSON input'));
    exit;
}

// Support batch updates
$items = isset($input['updates']) ? $input['updates'] : array($input);
$results = array();
$errors = array();

foreach ($items as $idx => $item) {
    $result = process_status_update($conn, $item, $allowed_platforms, $allowed_types);
    if ($result['ok']) {
        $results[] = $result;
    } else {
        $result['index'] = $idx;
        $errors[] = $result;
    }
}

echo json_encode(array(
    'ok' => empty($errors),
    'processed' => count($results),
    'errors' => $errors,
    'results' => $results
));

$conn->close();

function process_status_update($conn, $item, $allowed_platforms, $allowed_types) {
    // Validate required fields
    $required = array('creator_id', 'creator_name', 'platform', 'username');
    foreach ($required as $field) {
        if (!isset($item[$field]) || trim($item[$field]) === '') {
            return array('ok' => false, 'error' => "Missing required field: $field");
        }
    }

    $platform = strtolower(trim($item['platform']));
    if ($platform === 'x') $platform = 'twitter';

    if (!in_array($platform, $allowed_platforms)) {
        return array('ok' => false, 'error' => 'Invalid platform: ' . $platform);
    }

    $update_type = isset($item['update_type']) ? strtolower(trim($item['update_type'])) : 'post';
    if (!in_array($update_type, $allowed_types)) {
        return array('ok' => false, 'error' => 'Invalid update_type: ' . $update_type);
    }

    $creator_id = trim($item['creator_id']);
    $creator_name = trim($item['creator_name']);
    $username = trim($item['username']);
    $account_url = isset($item['account_url']) ? trim($item['account_url']) : '';
    $content_title = isset($item['content_title']) ? trim($item['content_title']) : '';
    $content_url = isset($item['content_url']) ? trim($item['content_url']) : '';
    $content_preview = isset($item['content_preview']) ? trim($item['content_preview']) : '';
    $content_thumbnail = isset($item['content_thumbnail']) ? trim($item['content_thumbnail']) : '';
    $content_id = isset($item['content_id']) ? trim($item['content_id']) : '';
    $is_live = isset($item['is_live']) ? ($item['is_live'] ? 1 : 0) : 0;
    $viewer_count = isset($item['viewer_count']) ? intval($item['viewer_count']) : 0;
    $like_count = isset($item['like_count']) ? intval($item['like_count']) : 0;
    $comment_count = isset($item['comment_count']) ? intval($item['comment_count']) : 0;
    $content_published_at = isset($item['content_published_at']) ? trim($item['content_published_at']) : null;
    $checked_by = isset($item['checked_by']) ? trim($item['checked_by']) : 'system';
    $error_message = isset($item['error_message']) ? trim($item['error_message']) : '';

    $start_time = microtime(true);
    $now = date('Y-m-d H:i:s');

    // Escape all values for safe SQL
    $esc_creator_id = $conn->real_escape_string($creator_id);
    $esc_creator_name = $conn->real_escape_string($creator_name);
    $esc_platform = $conn->real_escape_string($platform);
    $esc_username = $conn->real_escape_string($username);
    $esc_account_url = $conn->real_escape_string($account_url);
    $esc_update_type = $conn->real_escape_string($update_type);
    $esc_content_title = $conn->real_escape_string($content_title);
    $esc_content_url = $conn->real_escape_string($content_url);
    $esc_content_preview = $conn->real_escape_string($content_preview);
    $esc_content_thumbnail = $conn->real_escape_string($content_thumbnail);
    $esc_content_id = $conn->real_escape_string($content_id);
    $esc_checked_by = $conn->real_escape_string($checked_by);
    $esc_error_message = $conn->real_escape_string($error_message);
    $esc_now = $conn->real_escape_string($now);
    $esc_content_published_at = ($content_published_at !== null) ? "'" . $conn->real_escape_string($content_published_at) . "'" : 'NULL';

    // Check if record exists (unique on creator_id + platform + update_type)
    $check_sql = "SELECT id, check_count FROM creator_status_updates WHERE creator_id = '$esc_creator_id' AND platform = '$esc_platform' AND update_type = '$esc_update_type'";
    $check_result = $conn->query($check_sql);
    if (!$check_result) {
        return array('ok' => false, 'error' => 'Check query failed: ' . $conn->error);
    }
    $existing = $check_result->fetch_assoc();

    if ($existing) {
        // Update existing record
        $update_sql = "UPDATE creator_status_updates SET
            creator_name = '$esc_creator_name',
            username = '$esc_username',
            account_url = '$esc_account_url',
            content_title = '$esc_content_title',
            content_url = '$esc_content_url',
            content_preview = '$esc_content_preview',
            content_thumbnail = '$esc_content_thumbnail',
            content_id = '$esc_content_id',
            is_live = " . intval($is_live) . ",
            viewer_count = " . intval($viewer_count) . ",
            like_count = " . intval($like_count) . ",
            comment_count = " . intval($comment_count) . ",
            last_checked = '$esc_now',
            last_updated = '$esc_now',
            check_count = check_count + 1,
            checked_by = '$esc_checked_by',
            error_message = '$esc_error_message'";

        if ($content_published_at !== null) {
            $update_sql .= ", content_published_at = $esc_content_published_at";
        }

        $update_sql .= " WHERE id = " . intval($existing['id']);

        $success = $conn->query($update_sql);
        if (!$success) {
            return array('ok' => false, 'error' => 'Update failed: ' . $conn->error);
        }

        $action = 'updated';
        $record_id = $existing['id'];
    } else {
        // Insert new record
        $insert_sql = "INSERT INTO creator_status_updates
            (creator_id, creator_name, platform, username, account_url,
             update_type, content_title, content_url, content_preview, content_thumbnail, content_id,
             is_live, viewer_count, like_count, comment_count,
             content_published_at, last_checked, last_updated,
             check_count, checked_by, error_message)
            VALUES (
                '$esc_creator_id', '$esc_creator_name', '$esc_platform', '$esc_username', '$esc_account_url',
                '$esc_update_type', '$esc_content_title', '$esc_content_url', '$esc_content_preview', '$esc_content_thumbnail', '$esc_content_id',
                " . intval($is_live) . ", " . intval($viewer_count) . ", " . intval($like_count) . ", " . intval($comment_count) . ",
                $esc_content_published_at, '$esc_now', '$esc_now',
                1, '$esc_checked_by', '$esc_error_message'
            )";

        $success = $conn->query($insert_sql);
        if (!$success) {
            return array('ok' => false, 'error' => 'Insert failed: ' . $conn->error);
        }

        $action = 'created';
        $record_id = $conn->insert_id;
    }

    // Log the check
    $response_time = intval((microtime(true) - $start_time) * 1000);
    $found_update = ($content_title !== '' || $content_url !== '' || $is_live) ? 1 : 0;
    $log_sql = "INSERT INTO creator_status_check_log
        (creator_id, creator_name, platform, update_type, found_update, checked_by, checked_at, response_time_ms, error_message)
        VALUES (
            '$esc_creator_id', '$esc_creator_name', '$esc_platform', '$esc_update_type',
            " . intval($found_update) . ", '$esc_checked_by', '$esc_now',
            " . intval($response_time) . ", '$esc_error_message'
        )";
    $conn->query($log_sql);

    return array(
        'ok' => true,
        'action' => $action,
        'record_id' => $record_id,
        'creator_id' => $creator_id,
        'platform' => $platform,
        'update_type' => $update_type,
        'last_checked' => $now
    );
}
?>
