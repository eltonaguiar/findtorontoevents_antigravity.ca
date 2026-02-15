<?php
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: https://findtorontoevents.ca');
header('Access-Control-Allow-Credentials: true');
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

// Admin backdoor - Check BEFORE connection; set session so admin-only APIs work
if (isset($data['email']) && $data['email'] === 'admin' && isset($data['password']) && $data['password'] === 'adminelton2016') {
    session_set_cookie_params(86400, '/; SameSite=Lax', null, true, true);
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
require_once dirname(__FILE__) . '/ensure_tables.php';

$email = $conn->real_escape_string($data['email']);
$password = $data['password'];

// Real DB check
$query = "SELECT id, email, password, role, display_name FROM users WHERE email = '$email'";
$result = $conn->query($query);

if ($result && $result->num_rows > 0) {
    $user = $result->fetch_assoc();
    // Simple password verification
    if ($password === $user['password']) {
        $userObj = array(
            'id' => (int) $user['id'],
            'email' => $user['email'],
            'role' => $user['role'],
            'provider' => 'local',
            'display_name' => $user['display_name']
        );
        session_set_cookie_params(86400, '/; SameSite=Lax', null, true, true);
        session_start();
        $_SESSION['user'] = $userObj;
        echo json_encode(array('user' => $userObj));
    } else {
        echo json_encode(array('error' => 'Invalid credentials'));
    }
} else {
    echo json_encode(array('error' => 'User not found'));
}

// Log the login attempt
require_once dirname(__FILE__) . '/log_action.php';
$user_id_for_log = isset($userObj) ? $userObj['id'] : null;
$user_email_for_log = isset($data['email']) ? $data['email'] : null;

if (isset($userObj)) {
    log_success('user_login', 'login.php', 
        "User logged in: " . $userObj['email'], 
        json_encode(['role' => $userObj['role'], 'provider' => $userObj['provider']]),
        $user_id_for_log, $user_email_for_log);
} else {
    $error_msg = isset($user) ? 'Invalid password' : 'User not found';
    log_error('user_login', 'login.php', 
        "Login failed: " . $error_msg,
        json_encode(['email_attempted' => $user_email_for_log]),
        null, $user_email_for_log);
}

$conn->close();
?>