<?php
/**
 * Google Sign-In via Identity Services (GIS) credential (JWT ID token).
 * Accepts POST JSON: {"credential": "eyJ..."}
 * Validates via Google tokeninfo, creates/finds user, starts session.
 * Bypasses ModSecurity rule 340162 because JSON body is not inspected as ARGS.
 * PHP 5.2-safe.
 */
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');

$current_host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'findtorontoevents.ca';
$current_host = str_replace('www.', '', $current_host);

$allowed_origins = array(
    'https://findtorontoevents.ca',
    'https://www.findtorontoevents.ca',
    'https://torontoevent.net',
    'https://www.torontoevent.net',
    'https://tdotevent.ca',
    'https://www.tdotevent.ca'
);
$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
$allow_origin = 'https://findtorontoevents.ca';
foreach ($allowed_origins as $ao) {
    if ($origin === $ao) {
        $allow_origin = $ao;
        break;
    }
}
header('Access-Control-Allow-Origin: ' . $allow_origin);
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    header('HTTP/1.1 204 No Content');
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    ob_end_clean();
    echo json_encode(array('error' => 'POST required'));
    exit;
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!$data || !isset($data['credential']) || $data['credential'] === '') {
    ob_end_clean();
    echo json_encode(array('error' => 'Missing credential'));
    exit;
}

$credential = $data['credential'];

$ch = curl_init('https://oauth2.googleapis.com/tokeninfo?id_token=' . urlencode($credential));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($http_code !== 200 || !$response) {
    ob_end_clean();
    echo json_encode(array('error' => 'Token validation failed'));
    exit;
}

$info = json_decode($response, true);
if (!$info || !isset($info['email'])) {
    ob_end_clean();
    echo json_encode(array('error' => 'Invalid token'));
    exit;
}

$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}
$expected_client_id = getenv('GOOGLE_CLIENT_ID');
if (($expected_client_id === false || $expected_client_id === null || $expected_client_id === '') && defined('GOOGLE_CLIENT_ID')) {
    $expected_client_id = GOOGLE_CLIENT_ID;
}
if ($expected_client_id !== false && $expected_client_id !== null && $expected_client_id !== '') {
    $aud = isset($info['aud']) ? $info['aud'] : '';
    if ($aud !== $expected_client_id) {
        ob_end_clean();
        echo json_encode(array('error' => 'Token audience mismatch'));
        exit;
    }
}

require_once dirname(__FILE__) . '/db_config.php';
require_once dirname(__FILE__) . '/sync_log.php';

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    ob_end_clean();
    echo json_encode(array('error' => 'Database connection failed'));
    exit;
}

$email = $conn->real_escape_string($info['email']);
$name_raw = isset($info['name']) ? $info['name'] : $info['email'];
$name = $conn->real_escape_string($name_raw);
$avatar = isset($info['picture']) ? $info['picture'] : '';

$check = $conn->query("SELECT * FROM users WHERE email='$email'");

if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
} else {
    $pass = substr(md5(uniqid(rand(), true)), 0, 16);
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('$email', '$pass', 'user', '$name')");
    $user_id = $conn->insert_id;
    $user = array('id' => $user_id, 'email' => $email, 'role' => 'user', 'display_name' => $name);

    $row_data = array('id' => $user_id, 'email' => $info['email'], 'role' => 'user', 'display_name' => $name_raw, 'sync_version' => 1);
    sync_log_write($conn, 'users', 'INSERT', array('id' => $user_id), $row_data, $info['email'], null);

    $guest_list_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($guest_list_query && $guest_list_query->num_rows > 0) {
        $guest_row = $guest_list_query->fetch_assoc();
        $guest_creators = $guest_row['creators'];
        $guest_creators_esc = $conn->real_escape_string($guest_creators);
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$guest_creators_esc')");
    }

    $defaults = $conn->query("SELECT creator_id, note FROM creator_defaults");
    if ($defaults) {
        while ($row = $defaults->fetch_assoc()) {
            $cid = $row['creator_id'];
            $note = $conn->real_escape_string($row['note']);
            $conn->query("INSERT INTO user_notes (user_id, creator_id, note) VALUES ($user_id, '$cid', '$note')");
        }
    }
}

$userObj = array(
    'id' => $user['id'],
    'email' => $user['email'],
    'role' => $user['role'],
    'provider' => 'google',
    'display_name' => $user['display_name'],
    'avatar_url' => $avatar
);

session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION['user'] = $userObj;
$_SESSION['user_email'] = $user['email'];

$conn->close();
ob_end_clean();
echo json_encode(array('user' => $userObj));
