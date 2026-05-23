<?php
/**
 * FriendTracker: Register new user (insert into users table)
 * Returns user id, email, display_name on success.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['email']) || !isset($data['password']) || !isset($data['displayName'])) {
    echo json_encode(array('error' => 'Email, password, and display name required'));
    exit;
}

$email = $conn->real_escape_string($data['email']);
$password = $data['password'];
$display_name = $conn->real_escape_string($data['displayName']);
$password_hash = md5($password); // same as login_email.php

// Check if email already exists
$check = $conn->query("SELECT id FROM users WHERE email = '$email'");
if ($check && $check->num_rows > 0) {
    echo json_encode(array('error' => 'Email already registered'));
    $conn->close();
    exit;
}

// Insert new user
$sql = "INSERT INTO users (email, password, display_name, role, created_at) 
        VALUES ('$email', '$password_hash', '$display_name', 'user', NOW())";
if ($conn->query($sql)) {
    $user_id = $conn->insert_id;
    echo json_encode(array(
        'id' => intval($user_id),
        'email' => $email,
        'displayName' => $display_name,
        'provider' => 'email'
    ));
} else {
    echo json_encode(array('error' => 'Registration failed: ' . $conn->error));
}

$conn->close();
?>