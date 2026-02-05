<?php
/**
 * Add one creator to the guest list (admin / user_id=0).
 * POST { "creator": { id, name, bio, avatarUrl, category, reason, tags, accounts, isFavorite, isPinned } }
 * Inserts/updates creators table and appends to user_lists(0).
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('error' => 'Use POST with { "creator": { ... } }'));
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/db_schema.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);
if (!$data || !isset($data['creator']) || !is_array($data['creator'])) {
    echo json_encode(array('error' => 'POST body must be { "creator": { id, name, ... } }'));
    exit;
}

$c = $data['creator'];
$id = isset($c['id']) ? trim($c['id']) : '';
if ($id === '') {
    $id = 'creator-' . uniqid();
    $c['id'] = $id;
}
$name = isset($c['name']) ? $conn->real_escape_string($c['name']) : 'Unknown';
$bio = isset($c['bio']) ? $conn->real_escape_string($c['bio']) : '';
$avatar_url = isset($c['avatarUrl']) ? $conn->real_escape_string($c['avatarUrl']) : '';
$category = isset($c['category']) ? $conn->real_escape_string($c['category']) : 'Other';
$reason = isset($c['reason']) ? $conn->real_escape_string($c['reason']) : '';
$tags = isset($c['tags']) ? $conn->real_escape_string(is_string($c['tags']) ? $c['tags'] : json_encode($c['tags'])) : '[]';
$accounts = isset($c['accounts']) ? $conn->real_escape_string(is_string($c['accounts']) ? $c['accounts'] : json_encode($c['accounts'])) : '[]';
$is_fav = isset($c['isFavorite']) ? (int) (bool) $c['isFavorite'] : 0;
$is_pinned = isset($c['isPinned']) ? (int) (bool) $c['isPinned'] : 0;
$id_esc = $conn->real_escape_string($id);

$next_order = 0;
$r = $conn->query("SELECT COALESCE(MAX(guest_sort_order), -1) + 1 AS n FROM creators WHERE in_guest_list = 1");
if ($r && $row = $r->fetch_assoc())
    $next_order = (int) $row['n'];

$sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
        VALUES ('$id_esc','$name','$bio','$avatar_url','$category','$reason','$tags','$accounts',$is_fav,$is_pinned,1,$next_order) 
        ON DUPLICATE KEY UPDATE name=VALUES(name), bio=VALUES(bio), avatar_url=VALUES(avatar_url), category=VALUES(category), reason=VALUES(reason), tags=VALUES(tags), accounts=VALUES(accounts), is_favorite=VALUES(is_favorite), is_pinned=VALUES(is_pinned), in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
if (!$conn->query($sql)) {
    $error_msg = $conn->error;
    echo json_encode(array('error' => 'Failed to upsert creator: ' . $error_msg));
    exit;
}

$c['addedAt'] = isset($c['addedAt']) ? $c['addedAt'] : (time() * 1000);
$c['lastChecked'] = isset($c['lastChecked']) ? $c['lastChecked'] : $c['addedAt'];

$current = array();
$r2 = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
if ($r2 && $r2->num_rows > 0) {
    $row = $r2->fetch_assoc();
    $dec = json_decode($row['creators'], true);
    if (is_array($dec))
        $current = $dec;
}
$found = false;
foreach ($current as $i => $existing) {
    if (isset($existing['id']) && $existing['id'] === $id) {
        $current[$i] = $c;
        $found = true;
        break;
    }
}
if (!$found)
    $current[] = $c;
$list_esc = $conn->real_escape_string(json_encode($current));
$conn->query("INSERT INTO user_lists (user_id, creators) VALUES (0, '$list_esc') ON DUPLICATE KEY UPDATE creators = '$list_esc'");

echo json_encode(array('status' => 'success', 'creator' => $c));
$conn->close();
