<?php
// google_verify.php — Google Identity Services (GIS) token verification
// Receives JWT credential from Google Sign-In popup (no redirect_uri, no WAF issue)
// Frontend sends: POST { credential: "eyJhbG..." }
// We verify with Google, create/find user, start session, return JSON.

header('Content-Type: application/json');

// CORS for same-site + allowed origins
$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
$allowed_origins = array(
    'https://findtorontoevents.ca',
    'https://www.findtorontoevents.ca',
    'https://torontoevent.net',
    'https://www.torontoevent.net',
    'https://tdotevent.ca',
    'https://www.tdotevent.ca'
);
if (in_array($origin, $allowed_origins)) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
}
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('ok' => false, 'error' => 'POST only'));
    exit;
}

// Load config
$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}

// DB
require_once dirname(__FILE__) . '/db_config.php';
$sync_log_file = dirname(__FILE__) . '/sync_log.php';
if (file_exists($sync_log_file)) {
    require_once $sync_log_file;
}

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}

// Get credential from POST body (JSON or form-encoded)
$input = json_decode(file_get_contents('php://input'), true);
$credential = null;
if ($input && isset($input['credential'])) {
    $credential = $input['credential'];
} else if (isset($_POST['credential'])) {
    $credential = $_POST['credential'];
}

if (!$credential) {
    echo json_encode(array('ok' => false, 'error' => 'No credential'));
    exit;
}

// Verify JWT with Google's tokeninfo endpoint
$ch = curl_init('https://oauth2.googleapis.com/tokeninfo?id_token=' . urlencode($credential));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200) {
    echo json_encode(array('ok' => false, 'error' => 'Token verification failed'));
    exit;
}

$payload = json_decode($response, true);
if (!$payload || !isset($payload['email'])) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid token payload'));
    exit;
}

// Verify audience matches our client ID
$client_id = getenv('GOOGLE_CLIENT_ID');
if (($client_id === false || $client_id === null || $client_id === '') && defined('GOOGLE_CLIENT_ID')) {
    $client_id = GOOGLE_CLIENT_ID;
}
if ($client_id && isset($payload['aud']) && $payload['aud'] !== $client_id) {
    echo json_encode(array('ok' => false, 'error' => 'Token audience mismatch'));
    exit;
}

// Extract user info
$email = $conn->real_escape_string($payload['email']);
$name = isset($payload['name']) ? $conn->real_escape_string($payload['name']) : $email;
$avatar = isset($payload['picture']) ? $payload['picture'] : '';

// Find or create user (same logic as google_callback.php)
$check = $conn->query("SELECT * FROM users WHERE email='$email'");

if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
} else {
    // Register new user
    $pass = substr(md5(uniqid(rand(), true)), 0, 16);
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('$email', '$pass', 'user', '$name')");
    $user_id = $conn->insert_id;
    $user = array('id' => $user_id, 'email' => $email, 'role' => 'user', 'display_name' => $name);

    if (function_exists('sync_log_write')) {
        $row_data = array('id' => $user_id, 'email' => $payload['email'], 'role' => 'user', 'display_name' => $name, 'sync_version' => 1);
        sync_log_write($conn, 'users', 'INSERT', array('id' => $user_id), $row_data, $payload['email'], null);
    }

    // Auto-copy guest list
    $guest_list_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($guest_list_query && $guest_list_query->num_rows > 0) {
        $guest_row = $guest_list_query->fetch_assoc();
        $guest_creators_esc = $conn->real_escape_string($guest_row['creators']);
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$guest_creators_esc')");
    }

    // Auto-copy default notes
    $defaults = $conn->query("SELECT creator_id, note FROM creator_defaults");
    if ($defaults) {
        while ($row = $defaults->fetch_assoc()) {
            $cid = $row['creator_id'];
            $note = $conn->real_escape_string($row['note']);
            $conn->query("INSERT INTO user_notes (user_id, creator_id, note) VALUES ($user_id, '$cid', '$note')");
        }
    }
}

// Create session
session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION['user'] = array(
    'id' => $user['id'],
    'email' => $user['email'],
    'role' => $user['role'],
    'provider' => 'google',
    'display_name' => $user['display_name'],
    'avatar_url' => $avatar
);
$_SESSION['user_email'] = $user['email'];

echo json_encode(array(
    'ok' => true,
    'user_id' => intval($user['id']),
    'email' => $user['email'],
    'display_name' => $user['display_name'],
    'avatar_url' => $avatar
));
$conn->close();
?>
