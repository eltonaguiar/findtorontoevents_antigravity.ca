<?php
/**
 * Image proxy — fetches event thumbnails server-side to bypass CDN hotlink protection.
 * 
 * Usage: /api/image-proxy.php?url=https://img.evbuc.com/...
 * 
 * Only proxies from whitelisted image domains. Caches in memory via browser caching headers.
 * PHP 5.2 compatible.
 */

$allowed_domains = array(
    'img.evbuc.com',
    'cdn.evbuc.com',
    'cdn.evbstatic.com',
    'cdn2.fatsoma.com',
    'www.eventbrite.ca',
    'www.eventbrite.com',
    'secure.meetupstatic.com',
    'www.meetup.com',
    'nowtoronto.com',
    'www.nowtoronto.com',
    'torontobotanicalgarden.ca',
    'www.torontobotanicalgarden.ca',
    'www.rom.on.ca',
    'static1.squarespace.com',
    'cdn.cityswoon.com',
    'www.25dates.com',
    'www.evergreen.ca',
    'harbourfrontcentre.com'
);

$url = isset($_GET['url']) ? trim($_GET['url']) : '';

if ($url === '') {
    header('HTTP/1.1 400 Bad Request');
    echo 'Missing url parameter';
    exit;
}

$parts = parse_url($url);
$host = isset($parts['host']) ? strtolower($parts['host']) : '';

$domain_ok = false;
for ($i = 0; $i < count($allowed_domains); $i++) {
    if ($host === $allowed_domains[$i]) {
        $domain_ok = true;
        break;
    }
}

if (!$domain_ok) {
    header('HTTP/1.1 403 Forbidden');
    echo 'Domain not whitelisted';
    exit;
}

$scheme = isset($parts['scheme']) ? $parts['scheme'] : '';
if ($scheme !== 'http' && $scheme !== 'https') {
    header('HTTP/1.1 400 Bad Request');
    echo 'Invalid URL scheme';
    exit;
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
curl_setopt($ch, CURLOPT_TIMEOUT, 8);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
curl_setopt($ch, CURLOPT_HEADER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);

if ($response === false || $http_code >= 400) {
    header('HTTP/1.1 502 Bad Gateway');
    echo 'Upstream error: ' . $http_code;
    curl_close($ch);
    exit;
}

$headers = substr($response, 0, $header_size);
$body = substr($response, $header_size);
curl_close($ch);

$content_type = 'image/jpeg';
if (preg_match('/Content-Type:\s*([^\r\n]+)/i', $headers, $m)) {
    $ct = trim($m[1]);
    if (strpos($ct, 'image/') === 0) {
        $content_type = $ct;
    }
}

header('Content-Type: ' . $content_type);
header('Cache-Control: public, max-age=86400');
header('Access-Control-Allow-Origin: *');
header('X-Proxy: findtorontoevents');

echo $body;
