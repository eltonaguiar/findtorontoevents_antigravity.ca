<?php
/**
 * Server-side fetch proxy for live-status and avatar checks. Avoids CORS by fetching on the server.
 * Logged-in users only (prevents open proxy abuse).
 * GET ?url=https://example.com/page
 * Returns the response body; on failure returns 502 with empty or error body.
 */
header('Content-Type: text/html; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Cache-Control: no-store, max-age=0');

require_once dirname(__FILE__) . '/session_auth.php';
if (get_session_user_id() === null) {
    header('HTTP/1.1 401 Unauthorized');
    exit('Unauthorized');
}

$url = isset($_GET['url']) ? trim($_GET['url']) : '';
if ($url === '' || !preg_match('#^https?://#i', $url)) {
    header('HTTP/1.1 400 Bad Request');
    exit('Invalid url');
}

$body = false;

if (function_exists('curl_init')) {
    $ch = curl_init($url);
    if ($ch) {
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 12);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0');
        $body = curl_exec($ch);
        curl_close($ch);
    }
}

if ($body === false && ini_get('allow_url_fopen')) {
    $opts = array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0\r\n",
            'timeout' => 12,
            'ignore_errors' => true,
        )
    );
    $ctx = stream_context_create($opts);
    $body = @file_get_contents($url, false, $ctx);
}

if ($body === false) {
    header('HTTP/1.1 502 Bad Gateway');
    exit('');
}
echo $body;
