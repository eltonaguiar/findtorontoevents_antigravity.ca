<?php
/**
 * Email/password login endpoint
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

if (!$data || !isset($data['email']) || !isset($data['password'])) {
    echo json_encode(array('error' => 'Email and password required'));
    exit;
}

$email = $conn->real_escape_string($data['email']);
$password = $data['password'];
$password_hash = md5($password); // PHP 5.2 compatible

// Find user
$query = $conn->query("SELECT id, email, display_name FROM users WHERE email = '$email' AND password = '$password_hash'");

if (!$query || $query->num_rows === 0) {
    echo json_encode(array('error' => 'Invalid credentials'));
    $conn->close();
    exit;
}

$user = $query->fetch_assoc();

echo json_encode(array(
    'id' => intval($user['id']),
    'email' => $user['email'],
    'displayName' => $user['display_name'],
    'provider' => 'email'
));

$conn->close();
?>