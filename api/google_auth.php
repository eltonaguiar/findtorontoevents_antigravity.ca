<?php
// google_auth.php — main site (findtorontoevents.ca)
// Initiates Google OAuth; redirect_uri = https://findtorontoevents.ca/api/google_callback.php
// Add that exact URL to Google Cloud Console → Credentials → Authorized redirect URIs.

$client_id = getenv('GOOGLE_CLIENT_ID') ?: '975574174292-n332bled0ud1bc51v1hcqpnmp8dass12.apps.googleusercontent.com';
$redirect_uri = 'https://findtorontoevents.ca/api/google_callback.php';

$return_to = isset($_GET['return_to']) ? $_GET['return_to'] : '/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || $return_to[0] !== '/') {
    $return_to = '/';
}

$params = array(
    'client_id'     => $client_id,
    'redirect_uri'  => $redirect_uri,
    'response_type' => 'code',
    'scope'         => 'email profile',
    'access_type'   => 'online',
    'state'         => $return_to
);

$url = 'https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query($params);
if (!headers_sent()) {
    header("Location: $url");
    exit;
}
echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=' . htmlspecialchars($url) . '"></head><body>Redirecting to Google sign-in… <a href="' . htmlspecialchars($url) . '">Continue</a></body></html>';
exit;
