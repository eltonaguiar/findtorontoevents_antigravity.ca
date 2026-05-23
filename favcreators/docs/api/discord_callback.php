<?php
/**
 * Discord OAuth - Callback handler
 * Receives authorization code from Discord, exchanges for token, gets user info
 * 
 * Usage: GET /fc/api/discord_callback.php?code=...&state=...
 * Returns: Redirect back to app with success/error
 */

session_start();

require_once dirname(__FILE__) . '/discord_config.php';
require_once dirname(__FILE__) . '/db_connect.php';

$config = get_discord_config();
$app_url = 'https://findtorontoevents.ca/fc/';

// Check for errors from Discord
if (isset($_GET['error'])) {
    $error = isset($_GET['error_description']) ? $_GET['error_description'] : $_GET['error'];
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode($error));
    exit;
}

// Verify state to prevent CSRF
$state = isset($_GET['state']) ? $_GET['state'] : '';
$expected_state = isset($_SESSION['discord_oauth_state']) ? $_SESSION['discord_oauth_state'] : '';

if (empty($state) || $state !== $expected_state) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Invalid state - please try again'));
    exit;
}

// Get code
$code = isset($_GET['code']) ? $_GET['code'] : '';
if (empty($code)) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('No authorization code received'));
    exit;
}

// Get user_id from session
$user_id = isset($_SESSION['discord_oauth_user_id']) ? $_SESSION['discord_oauth_user_id'] : null;
if ($user_id === null) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Session expired - please try again'));
    exit;
}

// Exchange code for access token
$token_url = 'https://discord.com/api/oauth2/token';
$token_data = array(
    'client_id' => $config['client_id'],
    'client_secret' => $config['client_secret'],
    'grant_type' => 'authorization_code',
    'code' => $code,
    'redirect_uri' => $config['redirect_uri']
);

$ch = curl_init($token_url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($token_data));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/x-www-form-urlencoded'));
$token_response = curl_exec($ch);
$token_error = curl_error($ch);
curl_close($ch);

if ($token_error) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Failed to connect to Discord'));
    exit;
}

$token_json = json_decode($token_response, true);
if (!isset($token_json['access_token'])) {
    $error = isset($token_json['error_description']) ? $token_json['error_description'] : 'Failed to get access token';
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode($error));
    exit;
}

$access_token = $token_json['access_token'];

// Get user info from Discord
$user_url = 'https://discord.com/api/users/@me';
$ch = curl_init($user_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, array('Authorization: Bearer ' . $access_token));
$user_response = curl_exec($ch);
$user_error = curl_error($ch);
curl_close($ch);

if ($user_error) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Failed to get Discord user info'));
    exit;
}

$user_json = json_decode($user_response, true);
if (!isset($user_json['id'])) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Invalid Discord user data'));
    exit;
}

$discord_id = $user_json['id'];
$discord_username = isset($user_json['username']) ? $user_json['username'] : '';
if (isset($user_json['discriminator']) && $user_json['discriminator'] !== '0') {
    $discord_username .= '#' . $user_json['discriminator'];
}

// Save to database
if (!isset($conn) || !$conn) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Database not available'));
    exit;
}

$discord_id_esc = $conn->real_escape_string($discord_id);
$discord_username_esc = $conn->real_escape_string($discord_username);
$user_id_int = intval($user_id);

$sql = "UPDATE users SET discord_id = '$discord_id_esc', discord_username = '$discord_username_esc' WHERE id = $user_id_int";
$result = $conn->query($sql);

if (!$result) {
    header('Location: ' . $app_url . '#/settings?discord_error=' . urlencode('Failed to save Discord link'));
    exit;
}

// Clear session state
unset($_SESSION['discord_oauth_state']);
unset($_SESSION['discord_oauth_user_id']);

// Success - redirect back to app
header('Location: ' . $app_url . '#/settings?discord_linked=1&discord_user=' . urlencode($discord_username));
exit;
