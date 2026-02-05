<?php
/**
 * Get cached creator updates for a user's followed creators.
 * Returns instantly from database cache - no live API calls.
 * 
 * GET /api/get_cached_updates.php?user_id=0 (guest list)
 * GET /api/get_cached_updates.php?user_id=2 (specific user)
 * GET /api/get_cached_updates.php (auto-detect from session)
 * 
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/creator_status_updates_schema.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

// Determine user_id (same logic as get_my_creators.php)
$requested_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : null;
$session_id = get_session_user_id();

if ($requested_id === null) {
    // Auto-detect: use session user or guest
    $user_id = $session_id !== null ? $session_id : 0;
} else {
    // Validate access
    if ($session_id === null) {
        // Not logged in - can only access guest list
        if ($requested_id !== 0) {
            header('HTTP/1.0 403 Forbidden');
            echo json_encode(array('ok' => false, 'error' => 'Access denied'));
            exit;
        }
        $user_id = 0;
    } else {
        // Logged in - can access own list or guest list (admin can access any)
        if (is_session_admin()) {
            $user_id = $requested_id;
        } else {
            if ($requested_id !== $session_id && $requested_id !== 0) {
                header('HTTP/1.0 403 Forbidden');
                echo json_encode(array('ok' => false, 'error' => 'Access denied'));
                exit;
            }
            $user_id = $requested_id;
        }
    }
}

// Get user's creator list (from user_lists table)
$creators_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
$creators = array();

if ($creators_query && $creators_query->num_rows > 0) {
    $row = $creators_query->fetch_assoc();
    $decoded = json_decode($row['creators'], true);
    if (is_array($decoded)) {
        $creators = $decoded;
    }
}

// If no creators found for logged-in user, try guest list
if (empty($creators) && $user_id > 0) {
    $guest_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($guest_query && $guest_query->num_rows > 0) {
        $row = $guest_query->fetch_assoc();
        $decoded = json_decode($row['creators'], true);
        if (is_array($decoded)) {
            $creators = $decoded;
        }
    }
}

// Collect all platform/username pairs from creators
$account_keys = array();
$creator_map = array(); // Map creator_id -> creator data

foreach ($creators as $creator) {
    $cid = isset($creator['id']) ? $creator['id'] : '';
    if ($cid !== '') {
        $creator_map[$cid] = $creator;
    }
    
    if (isset($creator['accounts']) && is_array($creator['accounts'])) {
        foreach ($creator['accounts'] as $account) {
            $platform = isset($account['platform']) ? strtolower($account['platform']) : '';
            $username = isset($account['username']) ? $account['username'] : '';
            if ($platform !== '' && $username !== '' && $platform !== 'other') {
                $account_keys[] = array(
                    'creator_id' => $cid,
                    'platform' => $platform,
                    'username' => $username
                );
            }
        }
    }
}

// Build query to get cached updates for these accounts
$updates = array();
$cache_stats = array(
    'total_cached' => 0,
    'live_count' => 0,
    'oldest_check' => null,
    'newest_check' => null
);

// Collect creator IDs for querying creator_mentions
$creator_ids = array();
foreach ($creators as $c) {
    if (isset($c['id']) && $c['id'] !== '') {
        $creator_ids[] = $conn->real_escape_string($c['id']);
    }
}

// PART 1: Get real-time status from creator_status_updates table
if (!empty($account_keys)) {
    // Build OR conditions for each account
    $conditions = array();
    foreach ($account_keys as $ak) {
        $esc_platform = $conn->real_escape_string($ak['platform']);
        $esc_username = $conn->real_escape_string($ak['username']);
        $conditions[] = "(platform = '$esc_platform' AND username = '$esc_username')";
    }
    
    $where_clause = implode(' OR ', $conditions);
    $sql = "SELECT * FROM creator_status_updates WHERE ($where_clause) ORDER BY is_live DESC, content_published_at DESC, last_checked DESC LIMIT 500";
    
    $result = $conn->query($sql);
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            // Find the creator for this update
            $creator_data = null;
            foreach ($creators as $c) {
                if (isset($c['accounts']) && is_array($c['accounts'])) {
                    foreach ($c['accounts'] as $acc) {
                        if (strtolower($acc['platform']) === $row['platform'] && 
                            strtolower($acc['username']) === strtolower($row['username'])) {
                            $creator_data = $c;
                            break 2;
                        }
                    }
                }
            }
            
            $updates[] = array(
                'id' => intval($row['id']),
                'creator_id' => $row['creator_id'],
                'creator_name' => $row['creator_name'],
                'creator' => $creator_data,
                'platform' => $row['platform'],
                'username' => $row['username'],
                'account_url' => $row['account_url'],
                'accountUrl' => $row['account_url'],
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
                'cached' => true,
                'source' => 'status_updates'
            );
            
            if ($row['is_live'] == 1) {
                $cache_stats['live_count']++;
            }
            
            // Track oldest/newest check times
            if ($cache_stats['oldest_check'] === null || $row['last_checked'] < $cache_stats['oldest_check']) {
                $cache_stats['oldest_check'] = $row['last_checked'];
            }
            if ($cache_stats['newest_check'] === null || $row['last_checked'] > $cache_stats['newest_check']) {
                $cache_stats['newest_check'] = $row['last_checked'];
            }
        }
    }
}

// PART 2: Also fetch indexed content from creator_mentions table
// This includes YouTube videos, news articles, etc. that were indexed
if (!empty($creator_ids)) {
    // Build ID list with both full IDs and numeric prefixes (for IDs like 44280078-uuid...)
    $all_ids = array();
    $id_to_creator = array(); // Map both full IDs and prefixes back to creator data
    
    foreach ($creator_ids as $cid) {
        $all_ids[] = $conn->real_escape_string($cid);
        $id_to_creator[$cid] = $cid;
        
        // If ID is UUID format, also try the numeric prefix (e.g., "44280078" from "44280078-02e3-...")
        if (preg_match('/^(\d+)-/', $cid, $matches)) {
            $prefix = $matches[1];
            $all_ids[] = $conn->real_escape_string($prefix);
            $id_to_creator[$prefix] = $cid; // Map prefix back to full ID
        }
    }
    
    $ids_in = "'" . implode("','", array_unique($all_ids)) . "'";
    $mentions_sql = "SELECT cm.*, c.name as creator_name, c.avatar_url as creator_avatar 
                     FROM creator_mentions cm 
                     LEFT JOIN creators c ON cm.creator_id = c.id 
                     WHERE cm.creator_id IN ($ids_in) 
                     ORDER BY cm.posted_at DESC 
                     LIMIT 100";
    
    $mentions_result = $conn->query($mentions_sql);
    if ($mentions_result) {
        // Track existing content URLs to avoid duplicates
        $existing_urls = array();
        foreach ($updates as $u) {
            if (isset($u['content_url'])) {
                $existing_urls[$u['content_url']] = true;
            }
        }
        
        while ($row = $mentions_result->fetch_assoc()) {
            // Skip if we already have this URL from status_updates
            if (isset($existing_urls[$row['content_url']])) {
                continue;
            }
            
            // Find the creator data from our list (check both full ID and mapped prefix)
            $creator_data = null;
            $mention_cid = $row['creator_id'];
            
            // First try direct match
            foreach ($creators as $c) {
                if (isset($c['id']) && $c['id'] == $mention_cid) {
                    $creator_data = $c;
                    break;
                }
            }
            
            // If not found, try using the ID mapping (for prefix matches)
            if (!$creator_data && isset($id_to_creator[$mention_cid])) {
                $full_id = $id_to_creator[$mention_cid];
                foreach ($creators as $c) {
                    if (isset($c['id']) && $c['id'] == $full_id) {
                        $creator_data = $c;
                        break;
                    }
                }
            }
            
            // Map platform names
            $platform = strtolower($row['platform']);
            if ($platform === 'googlenews' || $platform === 'google_news') {
                $platform = 'news';
            }
            
            $updates[] = array(
                'id' => intval($row['id']) + 100000, // Offset to avoid ID conflicts
                'creator_id' => $row['creator_id'],
                'creator_name' => $row['creator_name'] ? $row['creator_name'] : (isset($creator_data['name']) ? $creator_data['name'] : 'Unknown'),
                'creator' => $creator_data ? $creator_data : array(
                    'id' => $row['creator_id'],
                    'name' => $row['creator_name'],
                    'avatarUrl' => $row['creator_avatar']
                ),
                'platform' => $platform,
                'username' => '',
                'account_url' => $row['content_url'],
                'accountUrl' => $row['content_url'],
                'update_type' => $row['content_type'] ? $row['content_type'] : 'post',
                'content_title' => $row['title'],
                'content_url' => $row['content_url'],
                'content_preview' => $row['description'] ? $row['description'] : '',
                'content_thumbnail' => $row['thumbnail_url'] ? $row['thumbnail_url'] : '',
                'content_id' => 'mention_' . $row['id'],
                'is_live' => false,
                'viewer_count' => 0,
                'like_count' => intval($row['engagement_count']),
                'comment_count' => 0,
                'content_published_at' => $row['posted_at'] ? date('Y-m-d H:i:s', $row['posted_at']) : null,
                'last_checked' => date('Y-m-d H:i:s'),
                'last_updated' => date('Y-m-d H:i:s'),
                'cached' => true,
                'source' => 'mentions'
            );
            
            $existing_urls[$row['content_url']] = true;
        }
    }
}

// Sort all updates by publish date (live first, then by date)
// PHP 5.2 compatible sort function
function _compare_updates($a, $b) {
    // Live content first
    $a_live = isset($a['is_live']) && $a['is_live'];
    $b_live = isset($b['is_live']) && $b['is_live'];
    if ($a_live && !$b_live) return -1;
    if (!$a_live && $b_live) return 1;
    
    // Then by publish date
    $date_a = isset($a['content_published_at']) ? strtotime($a['content_published_at']) : 0;
    $date_b = isset($b['content_published_at']) ? strtotime($b['content_published_at']) : 0;
    return $date_b - $date_a;
}
usort($updates, '_compare_updates');

$cache_stats['total_cached'] = count($updates);

echo json_encode(array(
    'ok' => true,
    'user_id' => $user_id,
    'is_guest' => $user_id === 0,
    'creators_count' => count($creators),
    'accounts_count' => count($account_keys),
    'updates' => $updates,
    'cache_stats' => $cache_stats,
    'from_cache' => true
));

$conn->close();
?>
