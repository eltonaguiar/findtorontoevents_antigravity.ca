<?php
// Debug script to check user's creator list
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

// Get user's creator list
$sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$result = $conn->query($sql);

if (!$result || $result->num_rows === 0) {
    echo json_encode(array(
        'error' => 'No user_lists entry for user ' . $user_id,
        'user_id' => $user_id
    ));
    $conn->close();
    exit;
}

$row = $result->fetch_assoc();
$creators_json = $row['creators'];
$creators = json_decode($creators_json, true);

// Get creator IDs
$creator_ids = array();
$creator_names = array();
foreach ($creators as $c) {
    if (isset($c['id'])) {
        $creator_ids[] = $c['id'];
        $creator_names[$c['id']] = isset($c['name']) ? $c['name'] : 'Unknown';
    }
}

// Check which creators exist in the creators table
$existing = array();
$missing = array();

if (count($creator_ids) > 0) {
    $ids_escaped = array();
    foreach ($creator_ids as $id) {
        $ids_escaped[] = "'" . $conn->real_escape_string($id) . "'";
    }
    
    $check_sql = "SELECT id, name, follower_count FROM creators WHERE id IN (" . implode(',', $ids_escaped) . ")";
    $check_result = $conn->query($check_sql);
    
    if ($check_result) {
        while ($r = $check_result->fetch_assoc()) {
            $existing[$r['id']] = array(
                'name' => $r['name'],
                'follower_count' => intval($r['follower_count']),
                'meets_threshold' => intval($r['follower_count']) >= 50000
            );
        }
    }
    
    foreach ($creator_ids as $id) {
        if (!isset($existing[$id])) {
            $missing[] = array(
                'id' => $id,
                'name' => $creator_names[$id]
            );
        }
    }
}

// Check creator_mentions for existing creators
$content_counts = array();
foreach (array_keys($existing) as $cid) {
    $cid_safe = $conn->real_escape_string($cid);
    $count_sql = "SELECT COUNT(*) as cnt FROM creator_mentions WHERE creator_id = '$cid_safe'";
    $count_result = $conn->query($count_sql);
    if ($count_result) {
        $cr = $count_result->fetch_assoc();
        $content_counts[$cid] = intval($cr['cnt']);
    }
}

echo json_encode(array(
    'user_id' => $user_id,
    'total_in_list' => count($creators),
    'creators_in_db' => $existing,
    'creators_missing' => $missing,
    'content_counts' => $content_counts,
    'raw_creator_ids' => $creator_ids
));

$conn->close();
?>
