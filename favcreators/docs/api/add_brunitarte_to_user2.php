<?php
/**
 * Add Brunitarte to user 2's creator list. Admin only.
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

// Get user 2's current list
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$query || $query->num_rows === 0) {
    echo json_encode(array('error' => 'User 2 has no creator list'));
    exit;
}

$row = $query->fetch_assoc();
$creators = json_decode($row['creators'], true);
if (!is_array($creators))
    $creators = array();

// Check if brunitarte already exists
$has_brunitarte = false;
foreach ($creators as $c) {
    if (isset($c['id']) && strpos($c['id'], 'brunitarte') !== false) {
        $has_brunitarte = true;
        break;
    }
}

if ($has_brunitarte) {
    echo json_encode(array('status' => 'already_exists', 'message' => 'Brunitarte already in list', 'count' => count($creators)));
    exit;
}

// Add Brunitarte
$brunitarte = array(
    'id' => 'brunitarte-tiktok',
    'name' => 'Brunitarte',
    'bio' => '',
    'avatarUrl' => '',
    'category' => 'other',
    'reason' => '',
    'tags' => array(),
    'accounts' => array(
        array('platform' => 'tiktok', 'username' => 'brunitarte', 'url' => 'https://www.tiktok.com/@brunitarte')
    ),
    'isFavorite' => false,
    'isPinned' => false
);

$creators[] = $brunitarte;

// Save back to database
$creators_json = json_encode($creators);
$creators_escaped = $conn->real_escape_string($creators_json);
$conn->query("UPDATE user_lists SET creators = '$creators_escaped' WHERE user_id = 2");

echo json_encode(array(
    'status' => 'added',
    'message' => 'Brunitarte added to user 2',
    'new_count' => count($creators),
    'brunitarte' => $brunitarte
));

$conn->close();
?>