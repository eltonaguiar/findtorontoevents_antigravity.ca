<?php
/**
 * One-off fix for zerounderscore@gmail.com (user_id=2): Admin only.
 * 1) Ensure Brunitarte is in creators table and in user 2's list.
 * 2) Deduplicate user 2's list by creator id (removes duplicate Tony Robbins etc).
 * GET: run fix, return JSON.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$USER_ID = 2;
$BRUNITARTE_ID = 'brunitarte-tiktok';

// 1) Ensure Brunitarte in creators table
$name_esc = $conn->real_escape_string('Brunitarte');
$accounts_esc = $conn->real_escape_string('[{"platform":"tiktok","username":"brunitarte","url":"https://www.tiktok.com/@brunitarte"}]');
$r = $conn->query("SELECT COALESCE(MAX(guest_sort_order), -1) + 1 AS n FROM creators WHERE in_guest_list = 1");
$next_order = ($r && $row = $r->fetch_assoc()) ? (int) $row['n'] : 0;
$sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
        VALUES ('$BRUNITARTE_ID','$name_esc','','','other','','[]','$accounts_esc',0,0,1,$next_order) 
        ON DUPLICATE KEY UPDATE name=VALUES(name), in_guest_list=1";
$conn->query($sql);

// 2) Get user 2's list, dedupe by id, add Brunitarte if missing, save back
$q = $conn->query("SELECT creators FROM user_lists WHERE user_id = $USER_ID");
$deduped_count = 0;
$added_brunitarte = false;
$creator_count_now = 0;

if ($q && $q->num_rows > 0) {
    $row = $q->fetch_assoc();
    $creators = json_decode($row['creators'], true);
    if (!is_array($creators)) {
        $creators = array();
    }
    $original_count = count($creators);

    // Deduplicate by id then by name (keep first of each) - PHP 5.x safe
    $seen = array();
    $deduped = array();
    foreach ($creators as $c) {
        $id = isset($c['id']) ? $c['id'] : '';
        if ($id === '' || isset($seen[$id])) continue;
        $seen[$id] = true;
        $deduped[] = $c;
    }
    $seen_names = array();
    $by_name = array();
    foreach ($deduped as $c) {
        $name = isset($c['name']) ? trim($c['name']) : '';
        if ($name === '') { $by_name[] = $c; continue; }
        $key = strtolower($name);
        if (isset($seen_names[$key])) continue;
        $seen_names[$key] = true;
        $by_name[] = $c;
    }
    $creators = $by_name;
    $deduped_count = $original_count - count($creators);

    // Add Brunitarte if missing
    $has_tarte = false;
    foreach ($creators as $c) {
        if (isset($c['id']) && (stripos($c['id'], 'tarte') !== false || (isset($c['name']) && stripos($c['name'], 'tarte') !== false))) {
            $has_tarte = true;
            break;
        }
    }
    if (!$has_tarte) {
        $creators[] = array(
            'id' => $BRUNITARTE_ID,
            'name' => 'Brunitarte',
            'bio' => '',
            'avatarUrl' => '',
            'category' => 'other',
            'reason' => '',
            'tags' => array(),
            'accounts' => array(array('platform' => 'tiktok', 'username' => 'brunitarte', 'url' => 'https://www.tiktok.com/@brunitarte')),
            'isFavorite' => false,
            'isPinned' => false,
            'note' => '',
            'addedAt' => 0,
            'lastChecked' => 0
        );
        $added_brunitarte = true;
    }

    $json = json_encode($creators);
    $esc = $conn->real_escape_string($json);
    $conn->query("UPDATE user_lists SET creators = '$esc' WHERE user_id = $USER_ID");
    $creator_count_now = count($creators);
}

$conn->close();

echo json_encode(array(
    'status' => 'success',
    'message' => 'User 2 list fixed: deduped and Brunitarte ensured',
    'duplicates_removed' => $deduped_count,
    'brunitarte_added' => $added_brunitarte,
    'creator_count_now' => $creator_count_now
));
