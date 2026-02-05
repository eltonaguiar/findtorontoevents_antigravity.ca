<?php
/**
 * Diagnostic: Check user_id=2's creator list and database state
 * One-time debug tool - remove after investigation
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    die(json_encode(array('error' => 'Database not available')));
}

$result = array(
    'timestamp' => date('Y-m-d H:i:s'),
    'tables' => array(),
    'user2_data' => null,
    'user_lists_summary' => array(),
    'briannasumba_check' => null
);

// Check table row counts
$tables_to_check = array(
    'user_lists',
    'users',
    'creators',
    'favcreatorslogs',
    'streamer_check_log',
    'streamer_content',
    'streamer_last_seen',
    'streamer_live_cache',
    'user_content_preferences',
    'user_link_lists'
);

foreach ($tables_to_check as $table) {
    $count_q = $conn->query("SELECT COUNT(*) as cnt FROM $table");
    if ($count_q && $row = $count_q->fetch_assoc()) {
        $result['tables'][$table] = array('count' => (int)$row['cnt']);
    } else {
        $result['tables'][$table] = array('count' => 0, 'error' => $conn->error);
    }
}

// Get all user_lists entries summary
$ul_q = $conn->query("SELECT user_id, LENGTH(creators) as json_length FROM user_lists ORDER BY user_id");
if ($ul_q) {
    while ($row = $ul_q->fetch_assoc()) {
        $uid = (int)$row['user_id'];
        // Get creator count from JSON
        $detail_q = $conn->query("SELECT creators FROM user_lists WHERE user_id = $uid");
        $creator_count = 0;
        $creator_names = array();
        if ($detail_q && $dr = $detail_q->fetch_assoc()) {
            $creators = json_decode($dr['creators'], true);
            if (is_array($creators)) {
                $creator_count = count($creators);
                // Get first 5 names for reference
                $i = 0;
                foreach ($creators as $c) {
                    if ($i >= 5) break;
                    $creator_names[] = isset($c['name']) ? $c['name'] : '(no name)';
                    $i++;
                }
            }
        }
        $result['user_lists_summary'][] = array(
            'user_id' => $uid,
            'json_bytes' => (int)$row['json_length'],
            'creator_count' => $creator_count,
            'sample_names' => $creator_names
        );
    }
}

// Get user_id=2's full data
$u2_q = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if ($u2_q && $row = $u2_q->fetch_assoc()) {
    $creators = json_decode($row['creators'], true);
    if (is_array($creators)) {
        $result['user2_data'] = array(
            'total_creators' => count($creators),
            'all_names' => array()
        );
        foreach ($creators as $c) {
            $name = isset($c['name']) ? $c['name'] : '(no name)';
            $result['user2_data']['all_names'][] = $name;
        }
        
        // Check for briannasumba
        $has_briannasumba = false;
        foreach ($creators as $c) {
            $name = isset($c['name']) ? strtolower($c['name']) : '';
            if (strpos($name, 'brianna') !== false || strpos($name, 'sumba') !== false) {
                $has_briannasumba = true;
                $result['briannasumba_check'] = array(
                    'found' => true,
                    'name' => $c['name'],
                    'accounts' => isset($c['accounts']) ? $c['accounts'] : array()
                );
                break;
            }
        }
        if (!$has_briannasumba) {
            $result['briannasumba_check'] = array('found' => false);
        }
    } else {
        $result['user2_data'] = array('error' => 'JSON decode failed');
    }
} else {
    $result['user2_data'] = array('error' => 'No record for user_id=2');
}

// Check users table for user_id=2
$u2_user = $conn->query("SELECT id, email, created_at FROM users WHERE id = 2");
if ($u2_user && $row = $u2_user->fetch_assoc()) {
    $result['user2_info'] = array(
        'id' => $row['id'],
        'email' => $row['email'],
        'created_at' => $row['created_at']
    );
}

$conn->close();
echo json_encode($result, JSON_PRETTY_PRINT);
?>
