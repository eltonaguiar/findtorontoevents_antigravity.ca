<?php
// google_callback.php - Compatible Version (PHP 5.x/7.x)
// Simplified without logging to avoid errors

// Load config file if it exists (for local credentials)
$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}

// DB Init
require_once dirname(__FILE__) . '/db_config.php';

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Load credentials from environment or config file
$client_id = getenv('GOOGLE_CLIENT_ID');
if (($client_id === false || $client_id === null || $client_id === '') && defined('GOOGLE_CLIENT_ID')) {
    $client_id = GOOGLE_CLIENT_ID;
}
if ($client_id === false || $client_id === null) {
    $client_id = '';
}

$client_secret = getenv('GOOGLE_CLIENT_SECRET');
if (($client_secret === false || $client_secret === null || $client_secret === '') && defined('GOOGLE_CLIENT_SECRET')) {
    $client_secret = GOOGLE_CLIENT_SECRET;
}
if ($client_secret === false || $client_secret === null) {
    $client_secret = '';
}
$redirect_uri = 'https://findtorontoevents.ca/fc/api/google_callback.php';

if (!isset($_GET['code'])) {
    die("Error: No code returned.");
}

$code = $_GET['code'];
$return_to = isset($_GET['state']) ? $_GET['state'] : '/fc/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || $return_to[0] !== '/') {
    $return_to = '/fc/';
}

// 1. Exchange Code
$ch = curl_init('https://oauth2.googleapis.com/token');
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query(array(
    'code' => $code,
    'client_id' => $client_id,
    'client_secret' => $client_secret,
    'redirect_uri' => $redirect_uri,
    'grant_type' => 'authorization_code'
)));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
$response = curl_exec($ch);
curl_close($ch);

$token_data = json_decode($response, true);
if (!isset($token_data['access_token'])) {
    $retry_url = 'https://findtorontoevents.ca/fc/api/google_auth.php?return_to=' . urlencode($return_to);
    echo '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sign In - Retry</title>';
    echo '<style>body{font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0f0f23;color:#fff;}';
    echo '.box{text-align:center;max-width:400px;padding:2.5rem;background:rgba(30,30,60,0.95);border-radius:1.5rem;border:1px solid rgba(99,102,241,0.3);}';
    echo 'h2{color:#a5b4fc;margin:0 0 1rem;}p{color:#94a3b8;line-height:1.6;margin:0 0 1.5rem;}';
    echo 'a.btn{display:inline-block;padding:0.85rem 2rem;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;text-decoration:none;border-radius:0.75rem;font-weight:700;}</style></head>';
    echo '<body><div class="box"><h2>Sign-in hiccup</h2>';
    echo '<p>The sign-in link expired. This can happen if the page sat open too long or was refreshed. No worries — just try again!</p>';
    echo '<a class="btn" href="' . htmlspecialchars($retry_url) . '">Try Again</a>';
    echo '<p style="margin-top:1rem;font-size:0.75rem;color:#64748b;">If this keeps happening, try clearing your browser cookies for this site.</p>';
    echo '</div></body></html>';
    exit;
}

// 2. Profile
$ch = curl_init('https://www.googleapis.com/oauth2/v2/userinfo?access_token=' . $token_data['access_token']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
$response = curl_exec($ch);
curl_close($ch);

$google_user = json_decode($response, true);
if (!isset($google_user['email'])) {
    die("Profile Fetch Failed.");
}

// 3. Logic
$email = $conn->real_escape_string($google_user['email']);
$name = $conn->real_escape_string($google_user['name']);
$avatar = isset($google_user['picture']) ? $google_user['picture'] : '';

$check = $conn->query("SELECT * FROM users WHERE email='$email'");

if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
} else {
    // Register
    $pass = substr(md5(uniqid(rand(), true)), 0, 16);

    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('$email', '$pass', 'user', '$name')");
    $user_id = $conn->insert_id;
    $user = array('id' => $user_id, 'email' => $email, 'role' => 'user', 'display_name' => $name);

    // Auto-Copy Guest List (user_id=0) to new user
    $guest_list_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($guest_list_query && $guest_list_query->num_rows > 0) {
        $guest_row = $guest_list_query->fetch_assoc();
        $guest_creators = $guest_row['creators'];
        $guest_creators_esc = $conn->real_escape_string($guest_creators);
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$guest_creators_esc')");
    }

    // Auto-Copy Defaults (notes)
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

// 4. Session & Redirect
session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION['user'] = $userObj;
$_SESSION['user_email'] = $user['email'];

$redirect_url = "https://findtorontoevents.ca" . $return_to;

// Robust Redirect
header("Location: " . $redirect_url);
echo "<html><head><meta http-equiv='refresh' content='0;url=$redirect_url'></head><body>Redirecting to <a href='$redirect_url'>App</a>...</body></html>";
exit;
?>