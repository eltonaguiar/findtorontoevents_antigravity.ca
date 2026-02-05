<?php
/**
 * One-time script to add briannasumba to user_id=2's list
 * DELETE THIS FILE AFTER USE
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    die(json_encode(array('error' => 'Database not available')));
}

// Get current list
$q = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$q || $q->num_rows === 0) {
    die(json_encode(array('error' => 'No user_id=2 record')));
}

$row = $q->fetch_assoc();
$creators = json_decode($row['creators'], true);

if (!is_array($creators)) {
    die(json_encode(array('error' => 'JSON decode failed')));
}

// Check if already exists
foreach ($creators as $c) {
    $name = isset($c['name']) ? strtolower($c['name']) : '';
    if (strpos($name, 'brianna') !== false || strpos($name, 'sumba') !== false) {
        echo json_encode(array('status' => 'already_exists', 'total' => count($creators)));
        exit;
    }
}

// Add briannasumba
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
            'checkLive' => true,
            'lastChecked' => time() * 1000
        )
    ),
    'isFavorite' => false,
    'isPinned' => false,
    'note' => '',
    'addedAt' => time() * 1000,
    'lastChecked' => 0
);

$creators[] = $briannasumba;

// Save
$json = json_encode($creators);
$escaped = $conn->real_escape_string($json);
$update = $conn->query("UPDATE user_lists SET creators = '$escaped', updated_at = NOW() WHERE user_id = 2");

if ($update) {
    echo json_encode(array(
        'status' => 'added',
        'total' => count($creators),
        'added' => 'Briannasumba'
    ));
} else {
    echo json_encode(array('error' => 'Update failed: ' . $conn->error));
}

$conn->close();
?>
