<?php
// kick_status.php — PHP 5.2 compatible (array(), no closures, no short array syntax).
// Same-origin proxy for Kick's public channel API (kick.com sends no CORS header,
// so the browser cannot fetch it directly from findtorontoevents.ca).
// Usage: GET /fc/api/kick_status.php?slug=moxie
// Degrades gracefully: always answers JSON, never fatals the caller.
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store');

$slug = isset($_GET['slug']) ? $_GET['slug'] : '';
$slug = preg_replace('/[^a-zA-Z0-9_\-]/', '', $slug);
if ($slug === '') {
    echo json_encode(array('error' => 'slug required'));
    exit;
}

$url = 'https://kick.com/api/v2/channels/' . $slug;
$raw = false;

// 1) try file_get_contents (allow_url_fopen)
$ctx = stream_context_create(array('http' => array('timeout' => 8, 'user_agent' => 'Mozilla/5.0 (compatible; findtorontoevents.ca status)')));
$raw = @file_get_contents($url, false, $ctx);

// 2) fallback: curl
if ($raw === false && function_exists('curl_init')) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (compatible; findtorontoevents.ca status)');
    $raw = curl_exec($ch);
    curl_close($ch);
}

if ($raw === false || $raw === '') {
    echo json_encode(array('slug' => $slug, 'live' => null, 'error' => 'upstream unavailable'));
    exit;
}

$d = json_decode($raw, true);
if (!is_array($d)) {
    echo json_encode(array('slug' => $slug, 'live' => null, 'error' => 'bad upstream json'));
    exit;
}

$is_live = (isset($d['livestream']) && $d['livestream']);
$out = array('slug' => $slug, 'live' => $is_live ? 1 : 0);

if ($is_live && is_array($d['livestream'])) {
    $ls = $d['livestream'];
    $out['title'] = isset($ls['session_title']) ? strval($ls['session_title']) : '';
    $out['viewers'] = isset($ls['viewer_count']) ? intval($ls['viewer_count']) : 0;
    $out['language'] = isset($ls['language']) ? strval($ls['language']) : '';
}

if (isset($d['followers_count'])) {
    $out['followers'] = intval($d['followers_count']);
}

echo json_encode($out);
// No closing PHP tag — intentional (PHP-only file best practice)
