<?php
/**
 * register.php — email/password registration for FavCreators.
 *
 * The SPA (assets/main-*.js) calls:
 *   POST /fc/api/register.php  { email, password, displayName }
 *   credentials:"include"
 * and expects HTTP 2xx on success, JSON { error } on failure.
 *
 * Contract notes:
 *  - Production runs PHP 5.2 (see ping.php): NO short array syntax, NO closures,
 *    NO ??, NO [] dereferencing of function calls. Use array() everywhere.
 *  - Stores the credential in the format login.php compares against (plain
 *    comparison), so a freshly registered account can log in immediately.
 *  - Establishes the same $_SESSION['user'] shape session_auth.php consumes.
 *  - Never returns or logs the password.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    echo json_encode(array('error' => 'POST required'));
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);
if (!$data || !is_array($data)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Invalid JSON input'));
    exit;
}

$email = isset($data['email']) ? trim((string) $data['email']) : '';
$password_value = isset($data['password']) ? (string) $data['password'] : '';
$display_name_value = isset($data['displayName']) ? trim((string) $data['displayName']) : '';
if ($display_name_value === '' && $email !== '') {
    // Fallback: derive a display name from the email local part.
    $at_pos = strpos($email, '@');
    $display_name_value = $at_pos > 0 ? substr($email, 0, $at_pos) : $email;
}

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Valid email required'));
    exit;
}
if ($display_name_value === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Display name required'));
    exit;
}
if (strlen($password_value) < 12
    || !preg_match('/[A-Z]/', $password_value)
    || !preg_match('/[a-z]/', $password_value)
    || !preg_match('/[0-9]/', $password_value)
    || !preg_match('/[^A-Za-z0-9]/', $password_value)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Password does not meet requirements (12+ chars, upper, lower, digit, symbol)'));
    exit;
}

$email_esc = $conn->real_escape_string($email);
$display_esc = $conn->real_escape_string($display_name_value);
// Same storage format login.php compares against (plain string compare).
$password_esc = $conn->real_escape_string($password_value);

$check = $conn->query("SELECT id FROM users WHERE email = '$email_esc' LIMIT 1");
if ($check && $check->num_rows > 0) {
    header('HTTP/1.1 409 Conflict');
    echo json_encode(array('error' => 'Email already registered'));
    $conn->close();
    exit;
}

// created_at must be supplied: production users.created_at has no default.
$sql = "INSERT INTO users (email, password, role, display_name, created_at)
        VALUES ('$email_esc', '$password_esc', 'user', '$display_esc', NOW())";
if (!$conn->query($sql)) {
    $err = $conn->error;
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => 'Registration failed: ' . $err));
    $conn->close();
    exit;
}

$user_id = (int) $conn->insert_id;
$user_obj = array(
    'id' => $user_id,
    'email' => $email,
    'role' => 'user',
    'provider' => 'local',
    'display_name' => $display_name_value
);

// Same session contract as login.php / google_callback.php.
if (!session_id()) {
    session_set_cookie_params(86400, '/', null, true, true);
    session_start();
}
$_SESSION['user'] = $user_obj;
$_SESSION['user_email'] = $email;

// Copy the default (guest) creator list so the account starts populated and
// its own user_lists row exists for subsequent saves.
$default_row = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0 LIMIT 1");
if ($default_row && $default_row->num_rows > 0) {
    $dr = $default_row->fetch_assoc();
    $default_esc = $conn->real_escape_string($dr['creators']);
    $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$default_esc') ON DUPLICATE KEY UPDATE creators = '$default_esc'");
}

echo json_encode(array('user' => $user_obj));
$conn->close();
?>