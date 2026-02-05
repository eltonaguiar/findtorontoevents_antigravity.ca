<?php
/**
 * Sync user_lists with the global creators table WITHOUT removing user-added creators. Admin only.
 *
 * DATA MODEL:
 * - creators table = global guest list only. New users get a mirror of this (or of user_id=0).
 * - user_lists = per-user override. Users can add creators not in the global list; we must never drop those.
 *
 * BEHAVIOUR:
 * 1. User ID 0 (guest): set list = creators WHERE in_guest_list=1 (the global default).
 * 2. User ID 2 and all others: MERGE. New list = default list + any creators they already have that are NOT in the default (by id). So we never remove user-added creators.
 *
 * GET: run sync and return JSON summary.
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

// Build one creator object for frontend from DB row + optional default note
function build_creator_for_list($row, $note = '') {
    $tags = $row['tags'];
    if (is_string($tags)) {
        $tags = json_decode($tags, true);
    }
    if (!is_array($tags)) {
        $tags = array();
    }
    $accounts = $row['accounts'];
    if (is_string($accounts)) {
        $accounts = json_decode($accounts, true);
    }
    if (!is_array($accounts)) {
        $accounts = array();
    }
    return array(
        'id' => $row['id'],
        'name' => $row['name'],
        'bio' => isset($row['bio']) ? $row['bio'] : '',
        'avatarUrl' => isset($row['avatar_url']) ? $row['avatar_url'] : '',
        'category' => isset($row['category']) ? $row['category'] : '',
        'reason' => isset($row['reason']) ? $row['reason'] : '',
        'tags' => $tags,
        'accounts' => $accounts,
        'isFavorite' => (bool) (isset($row['is_favorite']) ? $row['is_favorite'] : 0),
        'isPinned' => (bool) (isset($row['is_pinned']) ? $row['is_pinned'] : 0),
        'note' => $note,
        'addedAt' => 0,
        'lastChecked' => 0
    );
}

// Return merged list: default_list (from global) + any creators in current_list that are not in default (by id)
function merge_default_with_user_extras($default_list, $current_list) {
    if (!is_array($current_list)) {
        return $default_list;
    }
    $default_ids = array();
    foreach ($default_list as $c) {
        $id = isset($c['id']) ? $c['id'] : '';
        if ($id !== '') {
            $default_ids[$id] = true;
        }
    }
    $extras = array();
    foreach ($current_list as $c) {
        $id = isset($c['id']) ? $c['id'] : '';
        if ($id !== '' && !isset($default_ids[$id])) {
            $extras[] = $c;
            $default_ids[$id] = true;
        }
    }
    return array_merge($default_list, $extras);
}

// Load creator_defaults (creator_id => note) for merging into lists
$default_notes = array();
$dn_q = $conn->query("SELECT creator_id, note FROM creator_defaults");
if ($dn_q) {
    while ($r = $dn_q->fetch_assoc()) {
        $default_notes[$r['creator_id']] = isset($r['note']) ? $r['note'] : '';
    }
}

// 1) Build guest/default list: creators with in_guest_list=1, ordered (global list only)
$guest_query = $conn->query("SELECT id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned FROM creators WHERE in_guest_list = 1 ORDER BY guest_sort_order ASC");
$default_list = array();
if ($guest_query) {
    while ($row = $guest_query->fetch_assoc()) {
        $note = isset($default_notes[$row['id']]) ? $default_notes[$row['id']] : '';
        $default_list[] = build_creator_for_list($row, $note);
    }
}

// 2) Build full list from creators table (for merging with user 2's extras)
$all_query = $conn->query("SELECT id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned FROM creators ORDER BY id");
$all_list = array();
if ($all_query) {
    while ($row = $all_query->fetch_assoc()) {
        $note = isset($default_notes[$row['id']]) ? $default_notes[$row['id']] : '';
        $all_list[] = build_creator_for_list($row, $note);
    }
}

$default_json = json_encode($default_list);
$default_esc = $conn->real_escape_string($default_json);

// 3) Update user_id=0 (guest list) = global default only
$conn->query("INSERT INTO user_lists (user_id, creators) VALUES (0, '$default_esc') ON DUPLICATE KEY UPDATE creators = '$default_esc'");
$updated_guest = ($conn->affected_rows >= 0);

// 4) User 2: MERGE all from creators table + any they had that are not in the table (user-added)
$user2_row = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
$user2_current = array();
if ($user2_row && $user2_row->num_rows > 0) {
    $row = $user2_row->fetch_assoc();
    $dec = json_decode($row['creators'], true);
    if (is_array($dec)) {
        $user2_current = $dec;
    }
}
$user2_merged = merge_default_with_user_extras($all_list, $user2_current);
$user2_json = json_encode($user2_merged);
$user2_esc = $conn->real_escape_string($user2_json);
$conn->query("INSERT INTO user_lists (user_id, creators) VALUES (2, '$user2_esc') ON DUPLICATE KEY UPDATE creators = '$user2_esc'");
$updated_admin = ($conn->affected_rows >= 0);
$user2_extras = count($user2_merged) - count($all_list);

// 5) Other users: MERGE default list + their existing extras (so we never drop user-added creators)
$users_query = $conn->query("SELECT id FROM users WHERE id > 0 AND id != 2");
$other_updated = 0;
if ($users_query) {
    while ($u = $users_query->fetch_assoc()) {
        $uid = (int) $u['id'];
        $cur_row = $conn->query("SELECT creators FROM user_lists WHERE user_id = $uid");
        $cur_list = array();
        if ($cur_row && $cur_row->num_rows > 0) {
            $r = $cur_row->fetch_assoc();
            $dec = json_decode($r['creators'], true);
            if (is_array($dec)) {
                $cur_list = $dec;
            }
        }
        $merged = merge_default_with_user_extras($default_list, $cur_list);
        $merged_json = json_encode($merged);
        $merged_esc = $conn->real_escape_string($merged_json);
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($uid, '$merged_esc') ON DUPLICATE KEY UPDATE creators = '$merged_esc'");
        if ($conn->affected_rows >= 0) {
            $other_updated++;
        }
    }
}

echo json_encode(array(
    'status' => 'success',
    'message' => 'user_lists synced (merge: default + user extras kept)',
    'default_list_count' => count($default_list),
    'all_creators_count' => count($all_list),
    'user_0_updated' => $updated_guest,
    'user_2_updated' => $updated_admin,
    'user_2_extra_creators_kept' => max(0, $user2_extras),
    'other_users_merged' => $other_updated
));

$conn->close();
