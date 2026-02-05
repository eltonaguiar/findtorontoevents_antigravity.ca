<?php
/**
 * One-time or on-demand: ensure creators + user_lists + creator_defaults + user_notes tables exist,
 * and optionally seed the creators table from the current guest list (user_lists user_id=0) or from POST body.
 * GET: create tables, then if user_lists has no row for user_id=0, seed from initial_creators.json if present.
 * POST: create tables, then upsert each creator from body into creators table and set in_guest_list=1; update user_lists(0).
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';
require_once dirname(__FILE__) . '/db_schema.php';

$out = array('ok' => true, 'tables_created' => true, 'creators_synced' => 0, 'guest_list_updated' => false);

// Helper: creator object from app to row for DB
function creator_to_row($c) {
    $id = isset($c['id']) ? $c['id'] : '';
    $name = isset($c['name']) ? $c['name'] : '';
    $bio = isset($c['bio']) ? $c['bio'] : '';
    $avatar_url = isset($c['avatarUrl']) ? $c['avatarUrl'] : '';
    $category = isset($c['category']) ? $c['category'] : '';
    $reason = isset($c['reason']) ? $c['reason'] : '';
    $tags = isset($c['tags']) ? (is_string($c['tags']) ? $c['tags'] : json_encode($c['tags'])) : '[]';
    $accounts = isset($c['accounts']) ? (is_string($c['accounts']) ? $c['accounts'] : json_encode($c['accounts'])) : '[]';
    $is_fav = isset($c['isFavorite']) ? (int)(bool)$c['isFavorite'] : 0;
    $is_pinned = isset($c['isPinned']) ? (int)(bool)$c['isPinned'] : 0;
    return array(
        'id' => $id,
        'name' => $name,
        'bio' => $bio,
        'avatar_url' => $avatar_url,
        'category' => $category,
        'reason' => $reason,
        'tags' => $tags,
        'accounts' => $accounts,
        'is_favorite' => $is_fav,
        'is_pinned' => $is_pinned
    );
}

// Helper: row from DB to creator object for API
function row_to_creator($row) {
    $accounts = json_decode($row['accounts'], true);
    if (!is_array($accounts)) $accounts = array();
    $tags = json_decode($row['tags'], true);
    if (!is_array($tags)) $tags = array();
    $addedAt = isset($row['addedAt']) ? (int)$row['addedAt'] : (isset($row['created_at']) ? strtotime($row['created_at']) * 1000 : 0);
    return array(
        'id' => $row['id'],
        'name' => $row['name'],
        'bio' => (string)$row['bio'],
        'avatarUrl' => (string)$row['avatar_url'],
        'category' => (string)$row['category'],
        'reason' => (string)$row['reason'],
        'tags' => $tags,
        'accounts' => $accounts,
        'isFavorite' => (bool)(int)$row['is_favorite'],
        'isPinned' => (bool)(int)$row['is_pinned'],
        'addedAt' => $addedAt,
        'lastChecked' => isset($row['lastChecked']) ? (int)$row['lastChecked'] : $addedAt,
        'note' => isset($row['note']) ? $row['note'] : ''
    );
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    if (!$data || !isset($data['creators']) || !is_array($data['creators'])) {
        echo json_encode(array('ok' => false, 'error' => 'POST body must be { "creators": [ ... ] }'));
        exit;
    }
    $creators = $data['creators'];
    $order = 0;
    foreach ($creators as $c) {
        $r = creator_to_row($c);
        if ($r['id'] === '') continue;
        $id_esc = $conn->real_escape_string($r['id']);
        $name_esc = $conn->real_escape_string($r['name']);
        $bio_esc = $conn->real_escape_string($r['bio']);
        $avatar_esc = $conn->real_escape_string($r['avatar_url']);
        $cat_esc = $conn->real_escape_string($r['category']);
        $reason_esc = $conn->real_escape_string($r['reason']);
        $tags_esc = $conn->real_escape_string($r['tags']);
        $acc_esc = $conn->real_escape_string($r['accounts']);
        $sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
                VALUES ('$id_esc','$name_esc','$bio_esc','$avatar_esc','$cat_esc','$reason_esc','$tags_esc','$acc_esc',{$r['is_favorite']},{$r['is_pinned']},1,$order) 
                ON DUPLICATE KEY UPDATE name=VALUES(name), bio=VALUES(bio), avatar_url=VALUES(avatar_url), category=VALUES(category), reason=VALUES(reason), tags=VALUES(tags), accounts=VALUES(accounts), is_favorite=VALUES(is_favorite), is_pinned=VALUES(is_pinned), in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
        if ($conn->query($sql)) $out['creators_synced']++;
        $order++;
    }
    $list_json = $conn->real_escape_string(json_encode($creators));
    $conn->query("INSERT INTO user_lists (user_id, creators) VALUES (0, '$list_json') ON DUPLICATE KEY UPDATE creators = '$list_json'");
    $out['guest_list_updated'] = true;
} else {
    // GET: ensure tables; if no guest list, try to seed from initial_creators.json
    $json_file = dirname(__FILE__) . '/initial_creators.json';
    $seed = array();
    if (file_exists($json_file)) {
        $raw = file_get_contents($json_file);
        $seed = json_decode($raw, true);
        if (!is_array($seed)) $seed = array();
    }
    $has_guest = false;
    $r = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($r && $r->num_rows > 0) $has_guest = true;
    if (!$has_guest && count($seed) > 0) {
        $order = 0;
        foreach ($seed as $c) {
            $r = creator_to_row($c);
            if ($r['id'] === '') continue;
            $id_esc = $conn->real_escape_string($r['id']);
            $name_esc = $conn->real_escape_string($r['name']);
            $bio_esc = $conn->real_escape_string($r['bio']);
            $avatar_esc = $conn->real_escape_string($r['avatar_url']);
            $cat_esc = $conn->real_escape_string($r['category']);
            $reason_esc = $conn->real_escape_string($r['reason']);
            $tags_esc = $conn->real_escape_string($r['tags']);
            $acc_esc = $conn->real_escape_string($r['accounts']);
            $sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
                    VALUES ('$id_esc','$name_esc','$bio_esc','$avatar_esc','$cat_esc','$reason_esc','$tags_esc','$acc_esc',{$r['is_favorite']},{$r['is_pinned']},1,$order) 
                    ON DUPLICATE KEY UPDATE in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
            $conn->query($sql);
            $out['creators_synced']++;
            $order++;
        }
        $list_json = $conn->real_escape_string(json_encode($seed));
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES (0, '$list_json') ON DUPLICATE KEY UPDATE creators = '$list_json'");
        $out['guest_list_updated'] = true;
    }
}

$conn->close();
echo json_encode($out);
