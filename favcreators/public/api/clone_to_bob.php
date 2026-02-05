<?php
/**
 * Clone user 2's creator list to bob (email='bob', password='bob'). Admin only.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/ensure_tables.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

// Get bob's user ID
$bob_query = $conn->query("SELECT id FROM users WHERE email = 'bob'");
if (!$bob_query || $bob_query->num_rows === 0) {
    echo json_encode(array('error' => 'User bob not found. Run ensure_tables.php first.'));
    exit;
}
$bob_row = $bob_query->fetch_assoc();
$bob_id = $bob_row['id'];

// Get user 2's creator list
$user2_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$user2_query || $user2_query->num_rows === 0) {
    echo json_encode(array('error' => 'User 2 has no creator list'));
    exit;
}

$user2_row = $user2_query->fetch_assoc();
$creators_json = $user2_row['creators'];
$creators_escaped = $conn->real_escape_string($creators_json);

// Clone to bob (insert or update)
$conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($bob_id, '$creators_escaped') ON DUPLICATE KEY UPDATE creators = '$creators_escaped'");

// Parse and count
$creators = json_decode($creators_json, true);
$count = is_array($creators) ? count($creators) : 0;

// List all creator names
$creator_names = array();
if (is_array($creators)) {
    foreach ($creators as $c) {
        if (isset($c['name'])) {
            $creator_names[] = $c['name'];
        }
    }
}

echo json_encode(array(
    'status' => 'success',
    'bob_user_id' => $bob_id,
    'email' => 'bob',
    'password' => 'bob',
    'creators_cloned' => $count,
    'creator_names' => $creator_names,
    'message' => "Cloned $count creators from user 2 to bob (user_id $bob_id)"
));

$conn->close();
?>