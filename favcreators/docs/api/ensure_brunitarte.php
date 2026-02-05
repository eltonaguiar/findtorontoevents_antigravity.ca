<?php
/**
 * Ensure Brunitarte (username contains "tarte") is in creators table and in user 2's list. Admin only.
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

$id = 'brunitarte-tiktok';
$name = 'Brunitarte';
$bio = '';
$avatar_url = '';
$category = 'other';
$reason = '';
$tags = '[]';
$accounts = '[{"platform":"tiktok","username":"brunitarte","url":"https://www.tiktok.com/@brunitarte"}]';
$id_esc = $conn->real_escape_string($id);
$name_esc = $conn->real_escape_string($name);
$bio_esc = $conn->real_escape_string($bio);
$avatar_esc = $conn->real_escape_string($avatar_url);
$cat_esc = $conn->real_escape_string($category);
$reason_esc = $conn->real_escape_string($reason);
$tags_esc = $conn->real_escape_string($tags);
$accounts_esc = $conn->real_escape_string($accounts);

// 1) Insert into creators if not exists (so sync and default list include them)
$next_order = 0;
$r = $conn->query("SELECT COALESCE(MAX(guest_sort_order), -1) + 1 AS n FROM creators WHERE in_guest_list = 1");
if ($r && $row = $r->fetch_assoc()) {
    $next_order = (int) $row['n'];
}
$sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
        VALUES ('$id_esc','$name_esc','$bio_esc','$avatar_esc','$cat_esc','$reason_esc','$tags_esc','$accounts_esc',0,0,1,$next_order) 
        ON DUPLICATE KEY UPDATE name=VALUES(name), in_guest_list=1";
$conn->query($sql);
$creators_updated = ($conn->affected_rows >= 0);

// 2) Ensure user 2's list contains Brunitarte (append if missing)
$q = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
$added_to_user2 = false;
if ($q && $q->num_rows > 0) {
    $row = $q->fetch_assoc();
    $creators = json_decode($row['creators'], true);
    if (!is_array($creators)) {
        $creators = array();
    }
    $has_tarte = false;
    foreach ($creators as $c) {
        if (isset($c['id']) && stripos($c['id'], 'tarte') !== false) {
            $has_tarte = true;
            break;
        }
        if (isset($c['name']) && stripos($c['name'], 'tarte') !== false) {
            $has_tarte = true;
            break;
        }
    }
    if (!$has_tarte) {
        $brunitarte = array(
            'id' => 'brunitarte-tiktok',
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
        $creators[] = $brunitarte;
        $json = json_encode($creators);
        $esc = $conn->real_escape_string($json);
        $conn->query("UPDATE user_lists SET creators = '$esc' WHERE user_id = 2");
        $added_to_user2 = ($conn->affected_rows >= 0);
    }
}

echo json_encode(array(
    'status' => 'success',
    'message' => 'Brunitarte ensured in creators and user 2 list',
    'creators_table_updated' => $creators_updated,
    'added_to_user2' => $added_to_user2
));
$conn->close();
