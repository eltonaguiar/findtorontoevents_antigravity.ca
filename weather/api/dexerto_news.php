<?php
/**
 * dexerto_news.php — serves real Dexerto articles as JSON for the weather
 * page right panel. Fetches once per day (24h cache TTL). Falls back to
 * Google News RSS (site:dexerto.com) then broad gaming/esports when Dexerto's
 * own feed is unreachable.
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

define('CACHE_FILE', __DIR__ . '/.dexerto_cache.json');
define('CACHE_TTL', 86400); // 24 hours

$DEXERTO_FEEDS = array(
    'https://www.dexerto.com/feed/',
    'https://www.dexerto.com/category/gaming/feed/',
    'https://www.dexerto.com/category/esports/feed/',
    'https://www.dexerto.com/category/entertainment/feed/'
);
$GOOGLE_SITE_QUERY = 'https://news.google.com/rss/search?q=site:dexerto.com&hl=en-US&gl=US&ceid=US:en';
$GOOGLE_BROAD_QUERY = 'https://news.google.com/rss/search?q=esports+OR+competitive+gaming+OR+video+game+news&hl=en-US&gl=US&ceid=US:en';

function http_get($url) {
    $ch = curl_init($url);
    curl_setopt_array($ch, array(
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 12,
        CURLOPT_CONNECTTIMEOUT => 6,
        CURLOPT_USERAGENT => 'Mozilla/5.0 (compatible; findtorontoevents-weather/1.0)',
    ));
    $body = curl_exec($ch);
    $err = curl_error($ch);
    curl_close($ch);
    return ($body === false || $err !== '') ? '' : $body;
}

function parse_dexerto_rss($xml) {
    $feed = @simplexml_load_string($xml);
    if (!$feed || !isset($feed->channel->item)) return array();
    $items = array();
    foreach ($feed->channel->item as $it) {
        $t = trim((string)$it->title);
        $u = trim((string)$it->link);
        if ($t === '' || $u === '' || strlen($t) < 15) continue;
        $date = '';
        if (isset($it->pubDate)) {
            $ts = strtotime((string)$it->pubDate);
            if ($ts !== false) $date = date('Y-m-d', $ts);
        }
        $items[] = array('title' => $t, 'url' => $u, 'date' => $date);
    }
    return $items;
}

function parse_google_news_rss($xml) {
    $items = array();
    preg_match_all('/<item>(.*?)<\/item>/s', $xml, $matches);
    if (empty($matches[1])) return $items;
    foreach ($matches[1] as $item_xml) {
        $title = '';
        if (preg_match('/<title>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?<\/title>/', $item_xml, $tm)) {
            $title = html_entity_decode(trim($tm[1]), ENT_QUOTES, 'UTF-8');
            $dash = strrpos($title, ' - ');
            if ($dash !== false && $dash > 20) $title = trim(substr($title, 0, $dash));
        }
        $url = '';
        if (preg_match('/<link>(.+?)<\/link>/', $item_xml, $lm)) $url = trim($lm[1]);
        $date = '';
        if (preg_match('/<pubDate>(.+?)<\/pubDate>/', $item_xml, $pm)) {
            $ts = strtotime(trim($pm[1]));
            if ($ts !== false) $date = date('Y-m-d', $ts);
        }
        if ($title === '' || strlen($title) < 15) continue;
        $items[] = array('title' => $title, 'url' => $url, 'date' => $date);
    }
    return $items;
}

function dedupe_items($items) {
    $seen = array();
    $out = array();
    foreach ($items as $it) {
        $key = strtolower(substr($it['title'], 0, 50));
        if (isset($seen[$key])) continue;
        $seen[$key] = true;
        $out[] = $it;
    }
    return $out;
}

function read_cache() {
    if (!file_exists(CACHE_FILE)) return null;
    $raw = @file_get_contents(CACHE_FILE);
    $data = $raw ? json_decode($raw, true) : null;
    if (!is_array($data) || !isset($data['fetched_at'])) return null;
    if ((time() - (int)$data['fetched_at']) < CACHE_TTL) return $data;
    return $data; // stale but returnable as a fallback
}

function write_cache($items) {
    $data = array('ok' => true, 'fetched_at' => time(), 'items' => $items);
    @file_put_contents(CACHE_FILE, json_encode($data));
    return $data;
}

// ---- main logic ----
$cache = read_cache();

$items = array();
foreach ($DEXERTO_FEEDS as $feed_url) {
    $xml = http_get($feed_url);
    if ($xml === '') continue;
    $items = array_merge($items, parse_dexerto_rss($xml));
    if (count($items) > 0) break; // first working feed wins
}

if (count($items) === 0) {
    $xml = http_get($GOOGLE_SITE_QUERY);
    if ($xml !== '') $items = parse_google_news_rss($xml);
}
if (count($items) === 0) {
    $xml = http_get($GOOGLE_BROAD_QUERY);
    if ($xml !== '') $items = parse_google_news_rss($xml);
}

$items = dedupe_items($items);
$items = array_slice($items, 0, 6);

// Tag source (legacy PHP compat — no closures/anon functions).
foreach ($items as &$it) {
    $it['source'] = 'dexerto';
}
unset($it);

if ($items) {
    $out = write_cache($items);
    echo json_encode($out);
    exit;
}

// No fresh data: serve stale cache if present, else hard-fail.
if ($cache) {
    $cache_items = array_slice($cache['items'], 0, 6);
    foreach ($cache_items as &$cit) {
        $cit['source'] = 'dexerto';
    }
    unset($cit);
    $cache['items'] = $cache_items;
    echo json_encode($cache);
    exit;
}

echo json_encode(array('ok' => false, 'fetched_at' => time(), 'items' => array()));
?>