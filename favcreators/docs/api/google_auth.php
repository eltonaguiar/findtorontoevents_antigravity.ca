<?php
// google_auth.php
// Initiates Google OAuth Flow (redirect to Google). No DB needed here.

// Load credentials from environment or config file
$client_id = getenv('GOOGLE_CLIENT_ID') ?: '';

// Must match exactly what you entered in Google Console
$redirect_uri = 'https://findtorontoevents.ca/fc/api/google_callback.php';
$return_to = isset($_GET['return_to']) ? $_GET['return_to'] : '/fc/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || $return_to[0] !== '/') {
    $return_to = '/fc/';
}

$params = array(
    'client_id' => $client_id,
    'redirect_uri' => $redirect_uri,
    'response_type' => 'code',
    'scope' => 'email profile',
    'access_type' => 'online',
    'state' => $return_to
);

// Redirect to Google
$url = 'https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query($params);
if (!headers_sent()) {
    header("Location: $url");
    exit;
}
// Fallback if headers already sent (e.g. server sent something)
echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=' . htmlspecialchars($url) . '"></head><body>Redirecting to Google sign-in… <a href="' . htmlspecialchars($url) . '">Continue</a></body></html>';
exit;
?>