#!/usr/bin/env python3
"""
Fix google_callback.php:
1. Add mysqli_report(MYSQLI_REPORT_OFF) before connection
2. Use @ suppressor on new mysqli()
3. Load Google credentials from config.php properly
"""
import ftplib
from io import BytesIO
import urllib.request, ssl, time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

NEW_CALLBACK = r'''<?php
// google_callback.php - Handles Google OAuth callback

// Load config (Google credentials, DB defaults)
$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}

// DB Init — suppress mysqli exceptions for PHP 8.x compatibility
if (function_exists('mysqli_report')) {
    mysqli_report(MYSQLI_REPORT_OFF);
}
require_once dirname(__FILE__) . '/db_config.php';

$conn = @new mysqli($servername, $username, $password, $dbname);
if (!$conn || $conn->connect_error) {
    http_response_code(503);
    die('<html><body style="font-family:sans-serif;text-align:center;padding:3rem;background:#0f0f23;color:#fff"><h2 style="color:#f87171">Database temporarily unavailable</h2><p>Please try again in a moment.</p><a href="/fc/" style="color:#a5b4fc">Back to app</a></body></html>');
}

// Load Google credentials
$client_id = '';
$client_secret = '';
if (defined('GOOGLE_CLIENT_ID') && GOOGLE_CLIENT_ID !== '') {
    $client_id = GOOGLE_CLIENT_ID;
}
if (defined('GOOGLE_CLIENT_SECRET') && GOOGLE_CLIENT_SECRET !== '') {
    $client_secret = GOOGLE_CLIENT_SECRET;
}
// Also try getenv as fallback
if ($client_id === '') $client_id = (string)@getenv('GOOGLE_CLIENT_ID');
if ($client_secret === '') $client_secret = (string)@getenv('GOOGLE_CLIENT_SECRET');

$redirect_uri = 'https://torontoevent.net/fc/api/google_callback.php';

if (!isset($_GET['code'])) {
    die("Error: No code returned.");
}

$code = $_GET['code'];
$return_to = isset($_GET['state']) ? $_GET['state'] : '/fc/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || $return_to[0] !== '/') {
    $return_to = '/fc/';
}

// 1. Exchange Code for Token
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
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$response = curl_exec($ch);
curl_close($ch);

$token_data = json_decode($response, true);
if (!isset($token_data['access_token'])) {
    $retry_url = 'https://torontoevent.net/fc/api/google_auth.php?return_to=' . urlencode($return_to);
    echo '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sign In - Retry</title>';
    echo '<style>body{font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0f0f23;color:#fff;}';
    echo '.box{text-align:center;max-width:400px;padding:2.5rem;background:rgba(30,30,60,0.95);border-radius:1.5rem;border:1px solid rgba(99,102,241,0.3);}';
    echo 'h2{color:#a5b4fc;margin:0 0 1rem;}p{color:#94a3b8;line-height:1.6;margin:0 0 1.5rem;}';
    echo 'a.btn{display:inline-block;padding:0.85rem 2rem;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;text-decoration:none;border-radius:0.75rem;font-weight:700;}</style></head>';
    echo '<body><div class="box"><h2>Sign-in hiccup</h2>';
    echo '<p>The authorization code expired — this happens if the browser tab was left open too long. Click below to try again.</p>';
    echo '<a class="btn" href="' . htmlspecialchars($retry_url) . '">Try Again</a>';
    echo '<p style="margin-top:1rem;font-size:0.75rem;color:#64748b;">If this keeps happening, try clearing your browser cookies for this site.</p>';
    echo '</div></body></html>';
    exit;
}

// 2. Get Google Profile
$ch = curl_init('https://www.googleapis.com/oauth2/v2/userinfo?access_token=' . urlencode($token_data['access_token']));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$response = curl_exec($ch);
curl_close($ch);

$google_user = json_decode($response, true);
if (!isset($google_user['email'])) {
    die('<html><body style="font-family:sans-serif;text-align:center;padding:3rem;background:#0f0f23;color:#fff"><h2 style="color:#f87171">Could not fetch Google profile</h2><a href="/fc/" style="color:#a5b4fc">Back to app</a></body></html>');
}

// 3. Find or Create User
$email = $conn->real_escape_string($google_user['email']);
$name = $conn->real_escape_string(isset($google_user['name']) ? $google_user['name'] : $google_user['email']);
$avatar = isset($google_user['picture']) ? $google_user['picture'] : '';

$check = $conn->query("SELECT id, email, role, display_name FROM users WHERE email='$email'");

if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
} else {
    // New user — register
    $pass = substr(md5(uniqid(rand(), true)), 0, 16);
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('$email', '$pass', 'user', '$name')");
    $user_id = $conn->insert_id;
    $user = array('id' => $user_id, 'email' => $email, 'role' => 'user', 'display_name' => $name);

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
            $cid = intval($row['creator_id']);
            $note = $conn->real_escape_string($row['note']);
            $conn->query("INSERT INTO user_notes (user_id, creator_id, note) VALUES ($user_id, $cid, '$note')");
        }
    }
}

$conn->close();

$userObj = array(
    'id' => $user['id'],
    'email' => $user['email'],
    'role' => $user['role'],
    'provider' => 'google',
    'display_name' => $user['display_name'],
    'avatar_url' => $avatar
);

// 4. Set Session & Redirect
if (!session_id()) {
    session_set_cookie_params(86400, '/', null, true, true);
    session_start();
}
$_SESSION['user'] = $userObj;
$_SESSION['user_email'] = $user['email'];

$redirect_url = 'https://torontoevent.net' . $return_to;
header('Location: ' . $redirect_url);
echo '<html><head><meta http-equiv="refresh" content="0;url=' . htmlspecialchars($redirect_url) . '"></head><body>Redirecting... <a href="' . htmlspecialchars($redirect_url) . '">click here</a></body></html>';
exit;
?>
'''

def ftp_write(ftp, path, content):
    if isinstance(content, str):
        content = content.encode('utf-8')
    ftp.storbinary(f'STOR {path}', BytesIO(content))
    print(f'  [OK] {path}')

def ftp_read(ftp, path):
    buf = BytesIO()
    ftp.retrbinary(f'RETR {path}', buf.write)
    return buf.getvalue().decode('utf-8')

ftp = ftplib.FTP(FTP_HOST, timeout=30)
ftp.login(FTP_USER, FTP_PASS)

# Backup + deploy
old = ftp_read(ftp, '/fc/api/google_callback.php')
ftp_write(ftp, '/fc/api/google_callback.php.bak', old)
ftp_write(ftp, '/fc/api/google_callback.php', NEW_CALLBACK)

# Clean up diagnostic
try:
    ftp.delete('/fc/api/_gcbtest.php')
    print('  [OK] Cleaned up _gcbtest.php')
except:
    pass
try:
    ftp.delete('/fc/api/dbstatus.php')
    print('  [OK] Cleaned up dbstatus.php')
except:
    pass

ftp.quit()

# Quick smoke test (no code → should say "Error: No code returned.")
time.sleep(1)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    req = urllib.request.Request(
        'https://torontoevent.net/fc/api/google_callback.php',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    body = resp.read().decode('utf-8')
    print(f'\nSmoke test (no code): HTTP 200, body: {body[:100]}')
except urllib.error.HTTPError as e:
    print(f'\nSmoke test: HTTP {e.code} — ', end='')
    try: print(e.read().decode('utf-8')[:200])
    except: print(e.reason)
except Exception as e:
    print(f'\nSmoke test error: {type(e).__name__}: {e}')
