<?php
/**
 * Create test user 'bob' with password 'bob'. Admin only. PHP 5.2 compatible.
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

// Create user 'bob' with password 'bob' (MD5 for PHP 5.2 compatibility)
$username = 'bob';
$password = md5('bob'); // PHP 5.2 compatible
$email = 'bob@test.com';

// Check if user exists
$check = $conn->query("SELECT id FROM users WHERE username = 'bob'");
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $bob_id = $row['id'];

    // Get bob's creator count
    $bob_creators_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $bob_id");
    $bob_count = 0;
    if ($bob_creators_query && $bob_creators_query->num_rows > 0) {
        $bob_row = $bob_creators_query->fetch_assoc();
        $bob_creators = json_decode($bob_row['creators'], true);
        $bob_count = is_array($bob_creators) ? count($bob_creators) : 0;
    }

    echo json_encode(array(
        'status' => 'exists',
        'user_id' => $bob_id,
        'username' => 'bob',
        'password' => 'bob',
        'creators_count' => $bob_count,
        'message' => "User bob already exists with $bob_count creators"
    ));
} else {
    // Insert new user
    $insert = $conn->query("INSERT INTO users (username, password, email, role) VALUES ('bob', '$password', 'bob@test.com', 'user')");
    if (!$insert) {
        echo json_encode(array('error' => 'Failed to create user: ' . $conn->error));
        exit;
    }
    $bob_id = $conn->insert_id;

    // Clone user 2's creator list
    $user2_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
    if ($user2_query && $user2_query->num_rows > 0) {
        $user2_row = $user2_query->fetch_assoc();
        $creators_json = $user2_row['creators'];
        $creators_escaped = $conn->real_escape_string($creators_json);

        // Insert for bob
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($bob_id, '$creators_escaped')");

        $creators = json_decode($creators_json, true);
        $count = is_array($creators) ? count($creators) : 0;

        // List all creators
        $creator_names = array();
        if (is_array($creators)) {
            foreach ($creators as $c) {
                if (isset($c['name'])) {
                    $creator_names[] = $c['name'];
                }
            }
        }

        echo json_encode(array(
            'status' => 'created',
            'user_id' => $bob_id,
            'username' => 'bob',
            'password' => 'bob',
            'creators_cloned' => $count,
            'creator_names' => $creator_names,
            'message' => "User bob created with $count creators from user 2"
        ));
    } else {
        echo json_encode(array(
            'status' => 'created_empty',
            'user_id' => $bob_id,
            'message' => 'User bob created but user 2 has no creators to clone'
        ));
    }
}

$conn->close();
?>