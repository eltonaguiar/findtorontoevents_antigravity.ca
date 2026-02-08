<?php
/**
 * Admin-only: returns all creators that appear in any user's list, with follower count
 * and whether the creator is in the guest list. Used to show impact of changes.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available', 'creators' => array()));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';
require_once dirname(__FILE__) . '/db_schema.php';

// Guest list creator IDs (from user_id = 0)
$guest_creator_ids = array();
$q_guest = "SELECT creators FROM user_lists WHERE user_id = 0";
$r_guest = $conn->query($q_guest);
if ($r_guest && $r_guest->num_rows > 0) {
    $row = $r_guest->fetch_assoc();
    $data = json_decode($row['creators'], true);
    if (is_array($data)) {
        foreach ($data as $c) {
            $id = isset($c['id']) ? $c['id'] : '';
            if ($id !== '') $guest_creator_ids[$id] = true;
        }
    }
}

// All user_lists (every user_id and their creators JSON)
$count_by_creator = array(); // creator_id => array('count' => N, 'name' => name)
$q = "SELECT user_id, creators FROM user_lists";
$r = $conn->query($q);
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $user_id = (int) $row['user_id'];
        $data = json_decode($row['creators'], true);
        if (!is_array($data)) continue;
        foreach ($data as $c) {
            $id = isset($c['id']) ? $c['id'] : '';
            $name = isset($c['name']) ? $c['name'] : $id;
            if ($id === '') continue;
            if (!isset($count_by_creator[$id])) {
                $count_by_creator[$id] = array('creator_id' => $id, 'name' => $name, 'follower_count' => 0);
            }
            $count_by_creator[$id]['follower_count']++;
        }
    }
}

$list = array();
foreach ($count_by_creator as $id => $info) {
    $list[] = array(
        'creator_id' => $info['creator_id'],
        'name' => $info['name'],
        'follower_count' => (int) $info['follower_count'],
        'in_guest_list' => isset($guest_creator_ids[$id]),
    );
}
// Sort by follower_count desc, then name (PHP 5.2 compatible - no anonymous functions)
// Build sortable keys: zero-padded inverted count + lowercase name
$sort_keys = array();
foreach ($list as $i => $item) {
    $sort_keys[$i] = str_pad(99999 - $item['follower_count'], 5, '0', STR_PAD_LEFT) . strtolower($item['name']);
}
array_multisort($sort_keys, SORT_ASC, SORT_STRING, $list);

echo json_encode(array('creators' => $list));
$conn->close();
