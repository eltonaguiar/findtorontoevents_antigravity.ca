<?php
/**
 * API endpoint to get cached live status from database.
 * PHP 5.2 compatible version (without get_result())
 */

error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

$since_minutes = isset($_GET['since_minutes']) ? intval($_GET['since_minutes']) : 60;
if ($since_minutes < 1) $since_minutes = 60;
if ($since_minutes > 1440) $since_minutes = 1440;

$live_now = array();
$recently_live = array();

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

// Get currently live creators using bind_result
$live_sql = "SELECT creator_id, creator_name, avatar_url, platform, username, is_live, 
             stream_title, viewer_count, started_at, check_method, next_check_date, last_updated 
             FROM live_status_cache 
             WHERE is_live = 1 
             AND last_updated >= DATE_SUB(NOW(), INTERVAL ? MINUTE)
             ORDER BY last_updated DESC";

$live_stmt = $conn->prepare($live_sql);
$live_stmt->bind_param("i", $since_minutes);
$live_stmt->execute();
$live_stmt->bind_result($creator_id, $creator_name, $avatar_url, $platform, $username, 
                         $is_live, $stream_title, $viewer_count, $started_at, 
                         $check_method, $next_check_date, $last_updated);

$creators_by_id = array();

while ($live_stmt->fetch()) {
    if (!isset($creators_by_id[$creator_id])) {
        $creators_by_id[$creator_id] = array(
            'id' => $creator_id,
            'name' => $creator_name,
            'avatarUrl' => $avatar_url,
            'platforms' => array()
        );
    }
    
    $creators_by_id[$creator_id]['platforms'][] = array(
        'platform' => $platform,
        'username' => $username,
        'isLive' => $is_live == 1,
        'streamTitle' => $stream_title,
        'viewerCount' => intval($viewer_count),
        'startedAt' => $started_at,
        'checkMethod' => $check_method,
        'nextCheckDate' => intval($next_check_date),
        'lastUpdated' => $last_updated
    );
}

$live_stmt->close();

$live_now = array_values($creators_by_id);

// Get recently live creators (is_live = 0)
$recent_sql = "SELECT creator_id, creator_name, avatar_url, platform, username, is_live, 
               stream_title, viewer_count, started_at, check_method, next_check_date, last_updated 
               FROM live_status_cache 
               WHERE is_live = 0 
               AND last_updated >= DATE_SUB(NOW(), INTERVAL ? MINUTE)
               ORDER BY last_updated DESC
               LIMIT 50";

$recent_stmt = $conn->prepare($recent_sql);
$recent_stmt->bind_param("i", $since_minutes);
$recent_stmt->execute();
$recent_stmt->bind_result($creator_id, $creator_name, $avatar_url, $platform, $username, 
                           $is_live, $stream_title, $viewer_count, $started_at, 
                           $check_method, $next_check_date, $last_updated);

$recent_by_id = array();

while ($recent_stmt->fetch()) {
    if (!isset($recent_by_id[$creator_id])) {
        $recent_by_id[$creator_id] = array(
            'id' => $creator_id,
            'name' => $creator_name,
            'avatarUrl' => $avatar_url,
            'platforms' => array()
        );
    }
    
    $recent_by_id[$creator_id]['platforms'][] = array(
        'platform' => $platform,
        'username' => $username,
        'isLive' => false,
        'streamTitle' => $stream_title,
        'viewerCount' => intval($viewer_count),
        'startedAt' => $started_at,
        'checkMethod' => $check_method,
        'nextCheckDate' => intval($next_check_date),
        'lastUpdated' => $last_updated
    );
}

$recent_stmt->close();

$recently_live = array_values($recent_by_id);

// Get stats
$stats_sql = "SELECT 
    COUNT(DISTINCT creator_id) as total_creators,
    SUM(CASE WHEN is_live = 1 THEN 1 ELSE 0 END) as live_count
    FROM live_status_cache 
    WHERE last_updated >= DATE_SUB(NOW(), INTERVAL ? MINUTE)";

$stats_stmt = $conn->prepare($stats_sql);
$stats_stmt->bind_param("i", $since_minutes);
$stats_stmt->execute();
$stats_stmt->bind_result($total_creators, $live_count);
$stats_stmt->fetch();
$stats_stmt->close();

echo json_encode(array(
    'ok' => true,
    'liveNow' => $live_now,
    'recentlyLive' => $recently_live,
    'cached' => true,
    'stats' => array(
        'totalCached' => intval($total_creators),
        'liveCount' => intval($live_count),
        'sinceMinutes' => $since_minutes
    ),
    'timestamp' => date('Y-m-d H:i:s')
));

$conn->close();
?>
