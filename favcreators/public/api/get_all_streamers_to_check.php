<?php
/**
 * API endpoint to get all streamers that need checking.
 * Prioritizes those not checked recently (oldest first).
 * Used by GitHub Actions background job.
 */

error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

// Parameters
$limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 500) : 100;
$min_age_minutes = isset($_GET['min_age_minutes']) ? intval($_GET['min_age_minutes']) : 60;

$streamers = array();

// Strategy 1: Get from streamer_last_seen table (already tracked accounts, prioritize old checks)
$last_seen_sql = "SELECT DISTINCT creator_id, creator_name, platform, username, account_url, 
                  is_live, last_seen_online, last_checked
                  FROM streamer_last_seen 
                  WHERE last_checked < DATE_SUB(NOW(), INTERVAL ? MINUTE)
                     OR last_checked IS NULL
                  ORDER BY last_checked ASC, last_seen_online DESC
                  LIMIT ?";

$stmt = $conn->prepare($last_seen_sql);
if ($stmt) {
    $stmt->bind_param("ii", $min_age_minutes, $limit);
    $stmt->execute();
    $stmt->bind_result($creator_id, $creator_name, $platform, $username, $account_url, 
                       $is_live, $last_seen_online, $last_checked);
    
    while ($stmt->fetch()) {
        // Only include checkable platforms
        $p = strtolower($platform);
        if (in_array($p, array('tiktok', 'twitch', 'kick', 'youtube'))) {
            $streamers[] = array(
                'creator_id' => $creator_id,
                'creator_name' => $creator_name,
                'platform' => $p,
                'username' => $username,
                'url' => $account_url,
                'last_checked' => $last_checked,
                'last_seen_online' => $last_seen_online,
                'source' => 'streamer_last_seen'
            );
        }
    }
    $stmt->close();
}

// Strategy 2: If we need more, get from user_lists (all users' creators)
$remaining = $limit - count($streamers);
if ($remaining > 0) {
    // Get all unique accounts from all user lists
    $user_lists_sql = "SELECT user_id, creators FROM user_lists";
    $ul_result = $conn->query($user_lists_sql);
    
    $seen_accounts = array();
    // Mark already-fetched accounts
    foreach ($streamers as $s) {
        $seen_accounts[$s['creator_id'] . '_' . $s['platform']] = true;
    }
    
    $new_accounts = array();
    
    if ($ul_result) {
        while ($row = $ul_result->fetch_assoc()) {
            $creators = json_decode($row['creators'], true);
            if (!is_array($creators)) continue;
            
            foreach ($creators as $creator) {
                $accounts = isset($creator['accounts']) ? $creator['accounts'] : array();
                if (!is_array($accounts)) continue;
                
                foreach ($accounts as $acc) {
                    $platform = isset($acc['platform']) ? strtolower($acc['platform']) : '';
                    if (!in_array($platform, array('tiktok', 'twitch', 'kick', 'youtube'))) continue;
                    
                    $creator_id = isset($creator['id']) ? $creator['id'] : '';
                    $key = $creator_id . '_' . $platform;
                    
                    if (isset($seen_accounts[$key])) continue;
                    $seen_accounts[$key] = true;
                    
                    $new_accounts[] = array(
                        'creator_id' => $creator_id,
                        'creator_name' => isset($creator['name']) ? $creator['name'] : '',
                        'platform' => $platform,
                        'username' => isset($acc['username']) ? $acc['username'] : '',
                        'url' => isset($acc['url']) ? $acc['url'] : '',
                        'last_checked' => null,
                        'last_seen_online' => null,
                        'source' => 'user_lists'
                    );
                }
            }
        }
        $ul_result->free();
    }
    
    // Add new accounts up to remaining limit
    $streamers = array_merge($streamers, array_slice($new_accounts, 0, $remaining));
}

// Get stats
$stats_sql = "SELECT 
    COUNT(*) as total_tracked,
    SUM(CASE WHEN last_checked >= DATE_SUB(NOW(), INTERVAL 60 MINUTE) THEN 1 ELSE 0 END) as checked_last_hour,
    SUM(CASE WHEN is_live = 1 THEN 1 ELSE 0 END) as currently_live
    FROM streamer_last_seen";
$stats_result = $conn->query($stats_sql);
$stats = array('total_tracked' => 0, 'checked_last_hour' => 0, 'currently_live' => 0);
if ($stats_result) {
    $row = $stats_result->fetch_assoc();
    if ($row) {
        $stats = array(
            'total_tracked' => intval($row['total_tracked']),
            'checked_last_hour' => intval($row['checked_last_hour']),
            'currently_live' => intval($row['currently_live'])
        );
    }
    $stats_result->free();
}

echo json_encode(array(
    'ok' => true,
    'streamers' => $streamers,
    'count' => count($streamers),
    'params' => array(
        'limit' => $limit,
        'min_age_minutes' => $min_age_minutes
    ),
    'stats' => $stats,
    'timestamp' => date('Y-m-d H:i:s')
));

$conn->close();
?>
