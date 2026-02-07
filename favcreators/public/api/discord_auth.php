<?php
/**
 * Discord OAuth - Initiate authorization
 * Redirects user to Discord to authorize the app
 * 
 * Usage: GET /fc/api/discord_auth.php
 * Returns: Redirect to Discord OAuth
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

session_set_cookie_params(86400, '/', null, true, true);
session_start();

require_once dirname(__FILE__) . '/discord_config.php';

// Check session manually (session_auth.php might have issues)
$user_id = null;
if (isset($_SESSION['user']['id'])) {
    $user_id = (int)$_SESSION['user']['id'];
}

// Must be logged in to link Discord
if ($user_id === null) {
    header('Content-Type: text/html; charset=utf-8');
    echo '<h2>Not Logged In</h2>';
    echo '<p>You must be logged in to FavCreators before linking Discord.</p>';
    echo '<p><a href="https://findtorontoevents.ca/fc/">Go to FavCreators and log in first</a></p>';
    exit;
}

$config = get_discord_config();

if (empty($config['client_id'])) {
    header('Content-Type: text/html; charset=utf-8');
    echo '<h2>Discord Not Configured</h2>';
    echo '<p>Discord Client ID is missing from server configuration.</p>';
    echo '<p>Client ID from config: ' . htmlspecialchars(var_export($config['client_id'], true)) . '</p>';
    exit;
}

// Generate state for CSRF protection - use mt_rand for PHP 5.2 compatibility
$state = md5(uniqid(mt_rand(), true));
$_SESSION['discord_oauth_state'] = $state;
$_SESSION['discord_oauth_user_id'] = $user_id;

// Build Discord OAuth URL
$params = array(
    'client_id' => $config['client_id'],
    'redirect_uri' => $config['redirect_uri'],
    'response_type' => 'code',
    'scope' => 'identify',
    'state' => $state
);

$auth_url = 'https://discord.com/api/oauth2/authorize?' . http_build_query($params);

// Redirect to Discord
header('Location: ' . $auth_url);
exit;
