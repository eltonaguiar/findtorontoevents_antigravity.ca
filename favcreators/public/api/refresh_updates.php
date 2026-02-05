<?php
/**
 * Refresh updates for specific platform/username pairs.
 * Called by frontend after showing cached data to get fresh updates.
 * 
 * POST /api/refresh_updates.php
 * Body: {"accounts": [{"platform": "twitch", "username": "adinross", "creator_id": "123", "creator_name": "Adin Ross"}, ...]}
 * 
 * Or for single account:
 * GET /api/refresh_updates.php?platform=twitch&user=adinross&creator_id=123&creator_name=Adin
 * 
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/creator_status_updates_schema.php';

// Include the fetcher functions from fetch_platform_status.php
// We'll extract just the functions we need
require_once dirname(__FILE__) . '/fetch_platform_status.php';

$accounts = array();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    if (isset($data['accounts']) && is_array($data['accounts'])) {
        $accounts = $data['accounts'];
    }
} else {
    // Single account from GET params
    $platform = isset($_GET['platform']) ? strtolower(trim($_GET['platform'])) : '';
    $username = isset($_GET['user']) ? trim($_GET['user']) : '';
    $creator_id = isset($_GET['creator_id']) ? trim($_GET['creator_id']) : '';
    $creator_name = isset($_GET['creator_name']) ? trim($_GET['creator_name']) : $username;
    
    if ($platform !== '' && $username !== '') {
        $accounts[] = array(
            'platform' => $platform,
            'username' => $username,
            'creator_id' => $creator_id,
            'creator_name' => $creator_name
        );
    }
}

if (empty($accounts)) {
    echo json_encode(array('ok' => false, 'error' => 'No accounts provided'));
    exit;
}

// Limit to prevent abuse
$max_accounts = 20;
if (count($accounts) > $max_accounts) {
    $accounts = array_slice($accounts, 0, $max_accounts);
}

$supported_platforms = array('twitch', 'kick', 'youtube', 'tiktok', 'instagram', 'twitter', 'reddit');
$results = array();
$updated_count = 0;
$error_count = 0;

foreach ($accounts as $account) {
    $platform = isset($account['platform']) ? strtolower(trim($account['platform'])) : '';
    $username = isset($account['username']) ? trim($account['username']) : '';
    $creator_id = isset($account['creator_id']) ? trim($account['creator_id']) : '';
    $creator_name = isset($account['creator_name']) ? trim($account['creator_name']) : $username;
    
    if ($platform === '' || $username === '' || !in_array($platform, $supported_platforms)) {
        continue;
    }
    
    // Fetch fresh status using the existing fetcher
    $fetch_result = null;
    switch ($platform) {
        case 'twitch':
            $fetch_result = fetch_twitch_status($username);
            break;
        case 'kick':
            $fetch_result = fetch_kick_status($username);
            break;
        case 'youtube':
            $fetch_result = fetch_youtube_status($username);
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
        case 'reddit':
            $fetch_result = fetch_reddit_status($username);
            break;
    }
    
    if ($fetch_result && isset($fetch_result['updates']) && !empty($fetch_result['updates'])) {
        // Save to database
        foreach ($fetch_result['updates'] as $update) {
            save_status_update_direct($conn, $creator_id, $creator_name, $platform, $username, $update);
        }
        $updated_count++;
        
        $results[] = array(
            'platform' => $platform,
            'username' => $username,
            'creator_id' => $creator_id,
            'ok' => true,
            'is_live' => isset($fetch_result['is_live']) ? $fetch_result['is_live'] : false,
            'updates_count' => count($fetch_result['updates']),
            'updates' => $fetch_result['updates']
        );
    } else {
        $error_count++;
        $results[] = array(
            'platform' => $platform,
            'username' => $username,
            'creator_id' => $creator_id,
            'ok' => false,
            'error' => isset($fetch_result['error']) ? $fetch_result['error'] : 'No updates found'
        );
    }
}

echo json_encode(array(
    'ok' => true,
    'refreshed' => $updated_count,
    'errors' => $error_count,
    'total' => count($accounts),
    'results' => $results
));

$conn->close();
?>
