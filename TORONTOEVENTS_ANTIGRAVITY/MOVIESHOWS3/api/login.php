<?php
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    header('HTTP/1.0 204 No Content');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    ob_end_clean();
    echo json_encode(array('error' => 'Use POST to login'));
    exit;
}

// Get POST data
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    echo json_encode(array('error' => 'Invalid JSON input'));
    exit;
}

// Admin backdoor - Check BEFORE connection
if (isset($data['email']) && $data['email'] === 'admin' && isset($data['password']) && $data['password'] === 'admin') {
    session_set_cookie_params(86400, '/', null, true, true);
    session_start();
    $_SESSION['user'] = array(
        'id' => 0,
        'email' => 'admin',
        'role' => 'admin',
        'provider' => 'admin',
        'display_name' => 'Admin'
    );
    echo json_encode(array('user' => $_SESSION['user']));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

$email = $conn->real_escape_string($data['email']);
$password = $data['password'];

// Check if users table exists, if not create it
$conn->query("CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)");

// Real DB check
$query = "SELECT id, email, password, role, display_name FROM users WHERE email = '$email'";
$result = $conn->query($query);

if ($result && $result->num_rows > 0) {
    $user = $result->fetch_assoc();
    // Simple password verification (in production, use password_hash/password_verify)
    if ($password === $user['password']) {
        $userObj = array(
            'id' => (int) $user['id'],
            'email' => $user['email'],
            'role' => $user['role'],
            'provider' => 'local',
            'display_name' => $user['display_name']
        );
        session_set_cookie_params(86400, '/', null, true, true);
        session_start();
        $_SESSION['user'] = $userObj;
        echo json_encode(array('user' => $userObj));
    } else {
        echo json_encode(array('error' => 'Invalid credentials'));
    }
} else {
    echo json_encode(array('error' => 'User not found'));
}

$conn->close();
?>