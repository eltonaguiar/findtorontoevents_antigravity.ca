<?php
/**
 * Analyze user_id=2's creator list and add briannasumba if missing
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    die(json_encode(array('error' => 'Database not available')));
}

$result = array(
    'timestamp' => date('Y-m-d H:i:s'),
    'action' => 'analyze'
);

// Get user_id=2's data
$q = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$q || $q->num_rows === 0) {
    $result['error'] = 'No record for user_id=2';
    echo json_encode($result, JSON_PRETTY_PRINT);
    exit;
}

$row = $q->fetch_assoc();
$creators = json_decode($row['creators'], true);

if (!is_array($creators)) {
    $result['error'] = 'Failed to decode JSON';
    echo json_encode($result, JSON_PRETTY_PRINT);
    exit;
}

$result['total_creators'] = count($creators);
$result['creator_names'] = array();

// Find briannasumba
$has_briannasumba = false;
$briannasumba_index = -1;

foreach ($creators as $i => $c) {
    $name = isset($c['name']) ? $c['name'] : '(no name)';
    $result['creator_names'][] = $name;
    
    $nameLower = strtolower($name);
    if (strpos($nameLower, 'brianna') !== false || strpos($nameLower, 'sumba') !== false) {
        $has_briannasumba = true;
        $briannasumba_index = $i;
    }
}

$result['has_briannasumba'] = $has_briannasumba;

// Check if we should add briannasumba
$should_add = isset($_GET['add_briannasumba']) && $_GET['add_briannasumba'] === '1';

if (!$has_briannasumba && $should_add) {
    // Add briannasumba to the list
    $briannasumba = array(
        'id' => 'briannasumba-tiktok-' . time(),
        'name' => 'Briannasumba',
        'bio' => 'TikTok creator',
        'avatarUrl' => '',
        'category' => 'Other',
        'reason' => '',
        'tags' => array(),
        'accounts' => array(
            array(
                'id' => 'briannasumba-tiktok-acc',
                'platform' => 'tiktok',
                'username' => 'briannasumba',
                'url' => 'https://www.tiktok.com/@briannasumba',
                'isLive' => false,
                'checkLive' => true
            )
        ),
        'isFavorite' => false,
        'isPinned' => false,
        'note' => '',
        'addedAt' => time() * 1000,
        'lastChecked' => 0
    );
    
    $creators[] = $briannasumba;
    
    // Save back to database
    $creators_json = json_encode($creators);
    $creators_escaped = $conn->real_escape_string($creators_json);
    $update_q = $conn->query("UPDATE user_lists SET creators = '$creators_escaped' WHERE user_id = 2");
    
    if ($update_q) {
        $result['action'] = 'added_briannasumba';
        $result['new_total'] = count($creators);
        $result['success'] = true;
    } else {
        $result['error'] = 'Failed to update: ' . $conn->error;
    }
}

$conn->close();
echo json_encode($result, JSON_PRETTY_PRINT);
?>
