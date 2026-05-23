<?php
/**
 * API endpoint to get creator status updates across platforms.
 * Returns the latest content updates (posts, stories, streams, tweets, etc.)
 * for tracked creators.
 *
 * GET /api/status_updates.php
 * GET /api/status_updates.php?platform=twitch&user=nevsrealm
 * GET /api/status_updates.php?creator_id=xxx
 * GET /api/status_updates.php?platform=tiktok
 * GET /api/status_updates.php?type=story
 * GET /api/status_updates.php?since_hours=24
 * GET /api/status_updates.php?live_only=1
 *
 * Supported platforms: twitch, kick, tiktok, instagram, twitter, reddit, youtube
 * Supported types: post, story, stream, vod, tweet, comment, video, short, reel
 *
 * PHP 5.2 compatible: uses $conn->query() with real_escape_string, no prepared statements.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 200 OK');
    exit;
}

require_once 'db_connect.php';
require_once 'creator_status_updates_schema.php';

// Allowed platforms (no adult/illegal content platforms)
$allowed_platforms = array('twitch', 'kick', 'tiktok', 'instagram', 'twitter', 'reddit', 'youtube', 'spotify');

// Parse query parameters
$creator_id = isset($_GET['creator_id']) ? trim($_GET['creator_id']) : null;
$platform = isset($_GET['platform']) ? strtolower(trim($_GET['platform'])) : null;
$username = isset($_GET['user']) ? trim($_GET['user']) : null;
$update_type = isset($_GET['type']) ? strtolower(trim($_GET['type'])) : null;
$live_only = isset($_GET['live_only']) && $_GET['live_only'] == '1';
$since_hours = isset($_GET['since_hours']) ? intval($_GET['since_hours']) : 0;
$limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 100) : 50;

// Normalize twitter/x BEFORE validation
if ($platform === 'x') {
    $platform = 'twitter';
}

// Validate platform if provided
if ($platform !== null && !in_array($platform, $allowed_platforms)) {
    header('HTTP/1.0 400 Bad Request'); header('Status: 400 Bad Request');
    echo json_encode(array(
        'ok' => false,
        'error' => 'Invalid platform. Allowed: ' . implode(', ', $allowed_platforms)
    ));
    exit;
}

// Build query using real_escape_string (PHP 5.2 compatible, no prepared statements)
$sql = "SELECT * FROM creator_status_updates WHERE 1=1";

if ($creator_id) {
    $sql .= " AND creator_id = '" . $conn->real_escape_string($creator_id) . "'";
}

if ($platform) {
    $sql .= " AND platform = '" . $conn->real_escape_string($platform) . "'";
}

if ($username) {
    $sql .= " AND username = '" . $conn->real_escape_string($username) . "'";
}

if ($update_type) {
    $sql .= " AND update_type = '" . $conn->real_escape_string($update_type) . "'";
}

if ($live_only) {
    $sql .= " AND is_live = 1";
}

if ($since_hours > 0) {
    $safe_hours = intval($since_hours);
    $sql .= " AND (content_published_at >= DATE_SUB(NOW(), INTERVAL " . $safe_hours . " HOUR) OR last_checked >= DATE_SUB(NOW(), INTERVAL " . $safe_hours . " HOUR))";
}

$safe_limit = intval($limit);
$sql .= " ORDER BY content_published_at DESC, last_checked DESC LIMIT " . $safe_limit;

$result_set = $conn->query($sql);
if (!$result_set) {
    header('HTTP/1.0 500 Internal Server Error'); header('Status: 500 Internal Server Error');
    echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
    exit;
}

$updates = array();

while ($row = $result_set->fetch_assoc()) {
    $updates[] = array(
        'id' => intval($row['id']),
        'creator_id' => $row['creator_id'],
        'creator_name' => $row['creator_name'],
        'platform' => $row['platform'],
        'username' => $row['username'],
        'account_url' => $row['account_url'],
        'update_type' => $row['update_type'],
        'content_title' => $row['content_title'],
        'content_url' => $row['content_url'],
        'content_preview' => $row['content_preview'],
        'content_thumbnail' => $row['content_thumbnail'],
        'content_id' => $row['content_id'],
        'is_live' => $row['is_live'] == 1,
        'viewer_count' => intval($row['viewer_count']),
        'like_count' => intval($row['like_count']),
        'comment_count' => intval($row['comment_count']),
        'content_published_at' => $row['content_published_at'],
        'last_checked' => $row['last_checked'],
        'last_updated' => $row['last_updated'],
        'check_count' => intval($row['check_count']),
        'error_message' => $row['error_message']
    );
}

// Get aggregate stats
$stats_sql = "SELECT
    COUNT(*) as total_tracked,
    COUNT(DISTINCT creator_id) as unique_creators,
    COUNT(DISTINCT platform) as platforms_tracked,
    SUM(CASE WHEN is_live = 1 THEN 1 ELSE 0 END) as currently_live,
    MAX(last_checked) as last_check_time
FROM creator_status_updates";
$stats_result = $conn->query($stats_sql);
$stats = $stats_result ? $stats_result->fetch_assoc() : array(
    'total_tracked' => 0,
    'unique_creators' => 0,
    'platforms_tracked' => 0,
    'currently_live' => 0,
    'last_check_time' => null
);

// Get per-platform breakdown
$platform_stats_sql = "SELECT platform, COUNT(*) as count, SUM(CASE WHEN is_live = 1 THEN 1 ELSE 0 END) as live_count FROM creator_status_updates GROUP BY platform";
$platform_stats_result = $conn->query($platform_stats_sql);
$platform_breakdown = array();
if ($platform_stats_result) {
    while ($prow = $platform_stats_result->fetch_assoc()) {
        $platform_breakdown[$prow['platform']] = array(
            'tracked' => intval($prow['count']),
            'live' => intval($prow['live_count'])
        );
    }
}

echo json_encode(array(
    'ok' => true,
    'updates' => $updates,
    'count' => count($updates),
    'stats' => array(
        'total_tracked' => intval($stats['total_tracked']),
        'unique_creators' => intval($stats['unique_creators']),
        'platforms_tracked' => intval($stats['platforms_tracked']),
        'currently_live' => intval($stats['currently_live']),
        'last_check_time' => $stats['last_check_time']
    ),
    'platform_breakdown' => $platform_breakdown,
    'query' => array(
        'creator_id' => $creator_id,
        'platform' => $platform,
        'user' => $username,
        'type' => $update_type,
        'live_only' => $live_only,
        'since_hours' => $since_hours,
        'limit' => $limit
    ),
    'supported_platforms' => $allowed_platforms
));

$conn->close();
?>
