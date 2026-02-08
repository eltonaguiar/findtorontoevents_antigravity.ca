<?php
/**
 * Refresh content updates for all creators in the database.
 * Called by GitHub Actions daily to keep creator content fresh.
 * 
 * GET /api/refresh_all_creators.php
 * GET /api/refresh_all_creators.php?dry_run=1 (test mode, no API calls)
 * GET /api/refresh_all_creators.php?limit=5 (limit to N creators for testing)
 * 
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/fetch_platform_status.php';

$dry_run = isset($_GET['dry_run']) && $_GET['dry_run'] == '1';
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 0;

$start_time = microtime(true);
$results = array();
$total_creators = 0;
$total_accounts = 0;
$refreshed_count = 0;
$error_count = 0;

// Get all creators from user_lists (user_id=0 is the guest/default list)
// We'll also check other users to get all unique creators
$user_ids = array(0, 2); // Guest list and user 2
$all_creators = array();
$seen_creator_ids = array();

foreach ($user_ids as $uid) {
    $query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $uid");
    if (!$query) {
        continue;
    }
    
    $row = $query->fetch_assoc();
    if (!$row || !$row['creators']) {
        continue;
    }
    
    $creators_json = $row['creators'];
    $creators = json_decode($creators_json, true);
    
    if (!is_array($creators)) {
        continue;
    }
    
    foreach ($creators as $creator) {
        if (!isset($creator['id']) || in_array($creator['id'], $seen_creator_ids)) {
            continue;
        }
        
        $seen_creator_ids[] = $creator['id'];
        $all_creators[] = $creator;
    }
}

$total_creators = count($all_creators);

// Apply limit if specified (for testing)
if ($limit > 0 && $limit < $total_creators) {
    $all_creators = array_slice($all_creators, 0, $limit);
}

// Process each creator
foreach ($all_creators as $creator) {
    $creator_id = isset($creator['id']) ? $creator['id'] : '';
    $creator_name = isset($creator['name']) ? $creator['name'] : '';
    $accounts = isset($creator['accounts']) && is_array($creator['accounts']) ? $creator['accounts'] : array();
    
    if (empty($creator_id) || empty($accounts)) {
        continue;
    }
    
    $creator_result = array(
        'creator_id' => $creator_id,
        'creator_name' => $creator_name,
        'accounts_checked' => 0,
        'accounts_updated' => 0,
        'accounts_failed' => 0,
        'platforms' => array()
    );
    
    // Process each account for this creator
    foreach ($accounts as $account) {
        $platform = isset($account['platform']) ? strtolower(trim($account['platform'])) : '';
        $username = isset($account['username']) ? trim($account['username']) : '';
        
        if (empty($platform) || empty($username)) {
            continue;
        }
        
        $total_accounts++;
        $creator_result['accounts_checked']++;
        
        if ($dry_run) {
            // Dry run mode - just report what would be checked
            $creator_result['platforms'][] = array(
                'platform' => $platform,
                'username' => $username,
                'dry_run' => true
            );
            continue;
        }
        
        // Fetch fresh status for this platform
        $fetch_result = null;
        switch ($platform) {
            case 'youtube':
                $fetch_result = fetch_youtube_status($username);
                break;
            case 'twitch':
                $fetch_result = fetch_twitch_status($username);
                break;
            case 'kick':
                $fetch_result = fetch_kick_status($username);
                break;
            case 'tiktok':
                $fetch_result = fetch_tiktok_status($username);
                break;
            case 'instagram':
                $fetch_result = fetch_instagram_status($username);
                break;
            case 'twitter':
                $fetch_result = fetch_twitter_status($username);
                break;
        }
        
        if ($fetch_result && isset($fetch_result['updates']) && !empty($fetch_result['updates'])) {
            // Save updates to database
            foreach ($fetch_result['updates'] as $update) {
                save_status_update_direct($conn, $creator_id, $creator_name, $platform, $username, $update);
            }
            
            $creator_result['accounts_updated']++;
            $refreshed_count++;
            
            $creator_result['platforms'][] = array(
                'platform' => $platform,
                'username' => $username,
                'ok' => true,
                'updates_count' => count($fetch_result['updates'])
            );
        } else {
            $creator_result['accounts_failed']++;
            $error_count++;
            
            $creator_result['platforms'][] = array(
                'platform' => $platform,
                'username' => $username,
                'ok' => false,
                'error' => isset($fetch_result['error']) ? $fetch_result['error'] : 'No updates found'
            );
        }
        
        // Small delay to avoid rate limiting
        usleep(500000); // 0.5 seconds
    }
    
    $results[] = $creator_result;
}

$execution_time = round(microtime(true) - $start_time, 2);

echo json_encode(array(
    'ok' => true,
    'dry_run' => $dry_run,
    'total_creators' => $total_creators,
    'total_accounts' => $total_accounts,
    'refreshed' => $refreshed_count,
    'errors' => $error_count,
    'execution_time_seconds' => $execution_time,
    'timestamp' => date('Y-m-d H:i:s'),
    'results' => $results
));

$conn->close();
?>
