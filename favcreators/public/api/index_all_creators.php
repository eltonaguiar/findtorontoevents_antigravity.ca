<?php
/**
 * Index content for ALL creators in the database into creator_mentions.
 * This is the key endpoint that populates the Streamer Updates feed.
 *
 * Called by GitHub Actions daily to keep the updates feed fresh for all users.
 *
 * For each creator in user_lists (user_id 0 and 2), this script:
 *   1. Ensures the creator exists in the creators table (with follower_count >= 50000)
 *   2. Fetches latest content from each platform account (YouTube, Twitch, Kick, TikTok, etc.)
 *   3. Inserts new content into creator_mentions (what the updates page reads from)
 *
 * GET /api/index_all_creators.php
 * GET /api/index_all_creators.php?dry_run=1        (test mode, report what would be indexed)
 * GET /api/index_all_creators.php?limit=5           (limit to N creators for testing)
 * GET /api/index_all_creators.php?offset=10         (skip first N creators, for batching)
 * GET /api/index_all_creators.php?user_id=2         (only process a specific user's creators)
 *
 * PHP 5.2 compatible.
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(300); // Allow up to 5 minutes

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

$dry_run = isset($_GET['dry_run']) && $_GET['dry_run'] == '1';
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 0;
$offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
$only_user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : null;

$start_time = microtime(true);
$results = array();
$total_creators = 0;
$total_accounts = 0;
$content_added = 0;
$content_exists = 0;
$error_count = 0;
$creators_ensured = 0;

// Ensure creator_mentions table exists
$conn->query("CREATE TABLE IF NOT EXISTS creator_mentions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    content_type VARCHAR(32) DEFAULT 'post',
    content_url VARCHAR(1024) NOT NULL,
    title VARCHAR(512) DEFAULT '',
    description TEXT,
    thumbnail_url VARCHAR(1024) DEFAULT '',
    author VARCHAR(255) DEFAULT '',
    engagement_count INT DEFAULT 0,
    posted_at INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_creator_id (creator_id),
    INDEX idx_platform (platform),
    INDEX idx_posted_at (posted_at),
    INDEX idx_content_url (content_url(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

// Collect all unique creators from user_lists
$user_ids = array(0, 2);
if ($only_user_id !== null) {
    $user_ids = array(intval($only_user_id));
}

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

        // Skip creators without accounts
        if (!isset($creator['accounts']) || !is_array($creator['accounts']) || count($creator['accounts']) === 0) {
            continue;
        }

        $seen_creator_ids[] = $creator['id'];
        $all_creators[] = $creator;
    }
}

$total_creators = count($all_creators);

// Apply offset and limit for batching
if ($offset > 0) {
    $all_creators = array_slice($all_creators, $offset);
}
if ($limit > 0 && $limit < count($all_creators)) {
    $all_creators = array_slice($all_creators, 0, $limit);
}

// Process each creator
foreach ($all_creators as $creator) {
    $creator_id = isset($creator['id']) ? $creator['id'] : '';
    $creator_name = isset($creator['name']) ? $creator['name'] : '';
    $accounts = isset($creator['accounts']) && is_array($creator['accounts']) ? $creator['accounts'] : array();
    $avatar_url = isset($creator['avatarUrl']) ? $creator['avatarUrl'] : '';
    if ($avatar_url === '' && isset($creator['avatar_url'])) {
        $avatar_url = $creator['avatar_url'];
    }

    if (empty($creator_id) || empty($accounts)) {
        continue;
    }

    // Step 1: Ensure creator exists in creators table with adequate follower_count
    $cid_safe = $conn->real_escape_string($creator_id);
    $check_sql = "SELECT id, follower_count FROM creators WHERE id = '$cid_safe'";
    $check_result = $conn->query($check_sql);

    if ($check_result && $check_result->num_rows > 0) {
        $cr = $check_result->fetch_assoc();
        // If follower_count is below threshold, bump it up so the feed query includes them
        if (intval($cr['follower_count']) < 50000) {
            $conn->query("UPDATE creators SET follower_count = 100000 WHERE id = '$cid_safe'");
            $creators_ensured++;
        }
    } else {
        // Insert the creator into creators table
        $name_safe = $conn->real_escape_string($creator_name);
        $avatar_safe = $conn->real_escape_string($avatar_url);
        $insert_sql = "INSERT INTO creators (id, name, avatar_url, follower_count, in_guest_list) VALUES ('$cid_safe', '$name_safe', '$avatar_safe', 100000, 0)";
        $conn->query($insert_sql);
        $creators_ensured++;
    }

    $creator_result = array(
        'creator_id' => $creator_id,
        'creator_name' => $creator_name,
        'accounts_checked' => 0,
        'content_added' => 0,
        'content_exists' => 0,
        'errors' => 0,
        'platforms' => array()
    );

    // Step 2: For each platform account, fetch content and store in creator_mentions
    foreach ($accounts as $account) {
        $platform = isset($account['platform']) ? strtolower(trim($account['platform'])) : '';
        $username = isset($account['username']) ? trim($account['username']) : '';

        if (empty($platform) || empty($username)) {
            continue;
        }

        // Skip unsupported platforms
        $supported = array('youtube', 'tiktok', 'twitter', 'instagram', 'kick', 'twitch', 'reddit');
        if (!in_array($platform, $supported)) {
            continue;
        }

        $creator_result['accounts_checked']++;
        $total_accounts++;

        if ($dry_run) {
            $creator_result['platforms'][] = array(
                'platform' => $platform,
                'username' => $username,
                'dry_run' => true
            );
            continue;
        }

        // Fetch content via HTTP call to fetch_platform_status.php
        $fetch_url = "https://findtorontoevents.ca/fc/api/fetch_platform_status.php?platform=" . urlencode($platform) . "&user=" . urlencode($username);

        $ch = curl_init($fetch_url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        $data = json_decode($response, true);

        $platform_result = array(
            'platform' => $platform,
            'username' => $username,
            'fetched' => false,
            'added' => 0,
            'exists' => 0,
            'error' => null
        );

        if ($data && isset($data['ok']) && $data['ok'] && isset($data['updates']) && is_array($data['updates'])) {
            $platform_result['fetched'] = true;

            foreach ($data['updates'] as $update) {
                // Skip profile-only updates (no real content)
                $update_type = isset($update['update_type']) ? $update['update_type'] : '';
                if ($update_type === 'profile') {
                    continue;
                }

                $content_url = isset($update['content_url']) ? $update['content_url'] : '';
                $title = isset($update['content_title']) ? $update['content_title'] : '';
                $thumbnail = isset($update['content_thumbnail']) ? $update['content_thumbnail'] : '';
                $content_type = ($update_type !== '') ? $update_type : 'post';
                $preview = isset($update['content_preview']) ? $update['content_preview'] : '';
                $published_at = 0;
                if (isset($update['content_published_at']) && $update['content_published_at'] !== null) {
                    $published_at = strtotime($update['content_published_at']);
                    if ($published_at === false || $published_at === -1) {
                        $published_at = time();
                    }
                } else {
                    $published_at = time();
                }

                if (empty($content_url) || empty($title)) {
                    continue;
                }

                // Check if this content URL already exists in creator_mentions
                $url_safe = $conn->real_escape_string($content_url);
                $exists_sql = "SELECT id FROM creator_mentions WHERE content_url = '$url_safe'";
                $exists_result = $conn->query($exists_sql);

                if ($exists_result && $exists_result->num_rows > 0) {
                    $platform_result['exists']++;
                    $creator_result['content_exists']++;
                    $content_exists++;
                    continue;
                }

                // Insert into creator_mentions
                $title_safe = $conn->real_escape_string(substr($title, 0, 500));
                $desc_safe = $conn->real_escape_string(substr($preview, 0, 1000));
                $thumb_safe = $conn->real_escape_string($thumbnail);
                $platform_safe = $conn->real_escape_string($platform);
                $type_safe = $conn->real_escape_string($content_type);

                $insert_sql = "INSERT INTO creator_mentions (creator_id, platform, content_type, content_url, title, description, thumbnail_url, author, engagement_count, posted_at)
                               VALUES ('$cid_safe', '$platform_safe', '$type_safe', '$url_safe', '$title_safe', '$desc_safe', '$thumb_safe', '$platform_safe', 0, $published_at)";

                if ($conn->query($insert_sql)) {
                    $platform_result['added']++;
                    $creator_result['content_added']++;
                    $content_added++;
                } else {
                    $platform_result['error'] = $conn->error;
                    $creator_result['errors']++;
                    $error_count++;
                }
            }
        } else {
            $err_msg = 'No data returned';
            if ($data && isset($data['error'])) {
                $err_msg = $data['error'];
            } elseif ($http_code >= 400) {
                $err_msg = 'HTTP ' . $http_code;
            }
            $platform_result['error'] = $err_msg;
            $creator_result['errors']++;
            $error_count++;
        }

        $creator_result['platforms'][] = $platform_result;

        // Small delay between API calls to avoid rate limiting
        usleep(500000); // 0.5 seconds
    }

    $results[] = $creator_result;
}

$execution_time = round(microtime(true) - $start_time, 2);

echo json_encode(array(
    'ok' => true,
    'dry_run' => $dry_run,
    'total_creators_in_db' => $total_creators,
    'creators_processed' => count($results),
    'creators_ensured_in_table' => $creators_ensured,
    'total_accounts_checked' => $total_accounts,
    'content_added' => $content_added,
    'content_already_exists' => $content_exists,
    'errors' => $error_count,
    'offset' => $offset,
    'limit' => $limit,
    'execution_time_seconds' => $execution_time,
    'timestamp' => date('Y-m-d H:i:s'),
    'results' => $results
));

$conn->close();
?>
