<?php
/**
 * Create bob1 user and clone user 2's data. Admin only.
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

// Create bob1 user
$email = 'bob1';
$password_hash = md5('bob1'); // PHP 5.2 compatible
$display_name = 'Bob Test User';

// Check if bob1 exists
$check = $conn->query("SELECT id FROM users WHERE email = 'bob1'");
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $bob_id = $row['id'];
    echo json_encode(array('status' => 'exists', 'message' => 'bob1 already exists', 'user_id' => $bob_id));
} else {
    // Insert bob1
    $stmt = $conn->prepare("INSERT INTO users (email, password, display_name, role) VALUES (?, ?, ?, 'user')");
    $stmt->bind_param('sss', $email, $password_hash, $display_name);

    if (!$stmt->execute()) {
        echo json_encode(array('error' => 'Failed to create bob1: ' . $conn->error));
        $conn->close();
        exit;
    }

    $bob_id = $conn->insert_id;
    $stmt->close();
}

// Clone user 2's creator list to bob1
$user2_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$user2_query || $user2_query->num_rows === 0) {
    echo json_encode(array('error' => 'User 2 has no creator list to clone'));
    $conn->close();
    exit;
}

$user2_row = $user2_query->fetch_assoc();
$user2_creators = $user2_row['creators'];
$escaped = $conn->real_escape_string($user2_creators);

// Insert/update bob1's creator list
$conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($bob_id, '$escaped') ON DUPLICATE KEY UPDATE creators = '$escaped'");

// Verify
$verify_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $bob_id");
$verify_row = $verify_query->fetch_assoc();
$bob_creators = json_decode($verify_row['creators'], true);

$has_brunitarte = false;
foreach ($bob_creators as $c) {
    if (isset($c['name']) && $c['name'] === 'Brunitarte') {
        $has_brunitarte = true;
        break;
    }
}

echo json_encode(array(
    'status' => 'success',
    'user_id' => $bob_id,
    'email' => 'bob1',
    'password' => 'bob1',
    'creator_count' => count($bob_creators),
    'has_brunitarte' => $has_brunitarte,
    'message' => 'bob1 user created and user 2 data cloned'
));

$conn->close();
?>