<?php
/**
 * Diagnostic: Check user 2's raw database content and properly add Brunitarte. Admin only.
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
$creators_json = $row['creators'];
$creators = json_decode($creators_json, true);

// Check current state
$has_brunitarte = false;
$creator_names = array();
if (is_array($creators)) {
    foreach ($creators as $c) {
        if (isset($c['name'])) {
            $creator_names[] = $c['name'];
        }
        if (isset($c['id']) && strpos($c['id'], 'brunitarte') !== false) {
            $has_brunitarte = true;
        }
    }
}

$result = array(
    'current_count' => count($creators),
    'has_brunitarte' => $has_brunitarte,
    'creator_names' => $creator_names
);

// If brunitarte is missing, add it
if (!$has_brunitarte) {
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

    // Save with error checking
    $new_json = json_encode($creators);
    $escaped = $conn->real_escape_string($new_json);
    $update_result = $conn->query("UPDATE user_lists SET creators = '$escaped' WHERE user_id = 2");

    if ($update_result) {
        $result['action'] = 'added';
        $result['new_count'] = count($creators);
        $result['update_success'] = true;

        // Verify it was saved
        $verify = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
        if ($verify && $verify->num_rows > 0) {
            $verify_row = $verify->fetch_assoc();
            $verify_data = json_decode($verify_row['creators'], true);
            $result['verified_count'] = is_array($verify_data) ? count($verify_data) : 0;
        }
    } else {
        $result['action'] = 'failed';
        $result['error'] = $conn->error;
        $result['update_success'] = false;
    }
} else {
    $result['action'] = 'already_exists';
}

echo json_encode($result);
$conn->close();
?>