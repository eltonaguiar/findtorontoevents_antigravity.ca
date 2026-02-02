<?php
// google_callback.php — main site (findtorontoevents.ca)
// Callback URL: https://findtorontoevents.ca/api/google_callback.php
// Uses same users DB as FavCreators so one login works site-wide.

$fc_db = __DIR__ . '/../favcreators/public/api/db_config.php';
if (file_exists($fc_db) && is_readable($fc_db)) {
    require_once $fc_db;
} else {
    require_once __DIR__ . '/auth_db_config.php';
}

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

$client_id     = getenv('GOOGLE_CLIENT_ID')     ?: '';
$client_secret = getenv('GOOGLE_CLIENT_SECRET') ?: '';

if (empty($client_id) || empty($client_secret)) {
    die("Error: Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.");
}
$redirect_uri  = 'https://findtorontoevents.ca/api/google_callback.php';

if (!isset($_GET['code'])) {
    die("Error: No code returned.");
}

$code = $_GET['code'];
$return_to = isset($_GET['state']) ? $_GET['state'] : '/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || $return_to[0] !== '/') {
    $return_to = '/';
}

// 1. Exchange code for token
$ch = curl_init('https://oauth2.googleapis.com/token');
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query(array(
    'code'          => $code,
    'client_id'     => $client_id,
    'client_secret' => $client_secret,
    'redirect_uri'  => $redirect_uri,
    'grant_type'    => 'authorization_code'
)));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
$response = curl_exec($ch);
curl_close($ch);

$token_data = json_decode($response, true);
if (!isset($token_data['access_token'])) {
    die("Token exchange failed: " . htmlspecialchars(substr($response, 0, 200)));
}

// 2. Get profile
$ch = curl_init('https://www.googleapis.com/oauth2/v2/userinfo?access_token=' . $token_data['access_token']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
$response = curl_exec($ch);
curl_close($ch);

$google_user = json_decode($response, true);
if (!isset($google_user['email'])) {
    die("Profile fetch failed.");
}

// 3. Find or create user (same table as FavCreators)
$email = $conn->real_escape_string($google_user['email']);
$name  = $conn->real_escape_string(isset($google_user['name']) ? $google_user['name'] : '');
$avatar = isset($google_user['picture']) ? $google_user['picture'] : '';

$check = $conn->query("SELECT * FROM users WHERE email='$email'");
if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
} else {
    $pass = substr(md5(uniqid(rand(), true)), 0, 16);
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('$email', '$pass', 'user', '$name')");
    $user_id = $conn->insert_id;
    $user = array('id' => $user_id, 'email' => $email, 'role' => 'user', 'display_name' => $name);

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
    'id'           => $user['id'],
    'email'        => $user['email'],
    'role'         => $user['role'],
    'provider'     => 'google',
    'display_name' => $user['display_name'],
    'avatar_url'   => $avatar
);

// 4. Session (path / so valid for whole site) and redirect to main page
session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION['user'] = $userObj;

$base = 'https://findtorontoevents.ca';
$redirect_url = $base . $return_to;

header("Location: " . $redirect_url);
echo "<html><head><meta http-equiv='refresh' content='0;url=" . htmlspecialchars($redirect_url) . "'></head><body>Redirecting to <a href='" . htmlspecialchars($redirect_url) . "'>findtorontoevents.ca</a>...</body></html>";
exit;
