<?php
/**
 * youtube_latest.php - Fetch latest videos from a YouTube channel via RSS.
 *
 * Usage:
 *   GET ?handle=adinross          (YouTube handle without @)
 *   GET ?url=https://www.youtube.com/@adinross
 *   GET ?limit=5                  (max 10, default 5)
 *
 * Returns JSON: { ok: true, channel_id, handle, videos: [{id, title, published, thumbnail, embed_url, watch_url}] }
 * Results are cached in /tmp for 15 minutes.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=900');

$handle = isset($_GET['handle']) ? trim($_GET['handle']) : '';
$url    = isset($_GET['url'])    ? trim($_GET['url'])    : '';
$limit  = min(10, max(1, intval(isset($_GET['limit']) ? $_GET['limit'] : 5)));

// Extract handle from URL if not given directly
if (!$handle && $url) {
    if (preg_match('#youtube\.com/@?([^/\?#]+)#i', $url, $m)) {
        $handle = ltrim($m[1], '@');
    }
}

if (!$handle) {
    echo json_encode(array('ok' => false, 'error' => 'No handle provided. Use ?handle=username or ?url=...'));
    exit;
}

$handle = preg_replace('/[^a-zA-Z0-9_\-.]/', '', $handle);

// -- Cache --
$cacheDir  = sys_get_temp_dir() . '/yt_latest_cache';
if (!is_dir($cacheDir)) @mkdir($cacheDir, 0777, true);
$cacheFile = $cacheDir . '/' . md5($handle) . '.json';
$cacheTTL  = 900; // 15 min

if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheTTL) {
    $cached = @file_get_contents($cacheFile);
    if ($cached) { echo $cached; exit; }
}

// -- Resolve channel ID from handle page --
$ctxOpts = array(
    'http' => array(
        'timeout'         => 8,
        'follow_location' => 1,
        'header'          => "User-Agent: Mozilla/5.0 (compatible; FavCreators/1.0)\r\n",
    ),
);
$ctx = stream_context_create($ctxOpts);

$channelUrl = "https://www.youtube.com/@" . $handle;
$html = @file_get_contents($channelUrl, false, $ctx);
if (!$html) {
    $channelUrl = "https://www.youtube.com/c/" . $handle;
    $html = @file_get_contents($channelUrl, false, $ctx);
}
if (!$html) {
    echo json_encode(array('ok' => false, 'error' => 'Could not fetch channel page'));
    exit;
}

// Look for channel ID
if (!preg_match('/"channelId"\s*:\s*"(UC[a-zA-Z0-9_\-]+)"/', $html, $cidMatch)) {
    if (!preg_match('/channel_id=(UC[a-zA-Z0-9_\-]+)/', $html, $cidMatch)) {
        echo json_encode(array('ok' => false, 'error' => 'Could not extract channel ID', 'handle' => $handle));
        exit;
    }
}
$channelId = $cidMatch[1];

// -- Fetch RSS feed --
$feedUrl = "https://www.youtube.com/feeds/videos.xml?channel_id=" . $channelId;
$feedXml = @file_get_contents($feedUrl, false, $ctx);
if (!$feedXml) {
    echo json_encode(array('ok' => false, 'error' => 'Could not fetch RSS feed', 'channel_id' => $channelId));
    exit;
}

// -- Parse XML --
$xml = @simplexml_load_string($feedXml);
if (!$xml) {
    echo json_encode(array('ok' => false, 'error' => 'Could not parse RSS feed'));
    exit;
}

$videos = array();
$ns = $xml->getNamespaces(true);
$ytNs    = isset($ns['yt'])    ? $ns['yt']    : 'http://www.youtube.com/xml/schemas/2015';
$mediaNs = isset($ns['media']) ? $ns['media'] : 'http://search.yahoo.com/mrss/';

foreach ($xml->entry as $entry) {
    if (count($videos) >= $limit) break;
    $yt    = $entry->children($ytNs);
    $media = $entry->children($mediaNs);

    $videoId   = isset($yt->videoId)      ? (string)$yt->videoId      : '';
    $title     = isset($entry->title)     ? (string)$entry->title     : '';
    $published = isset($entry->published) ? (string)$entry->published : '';

    $views = '';
    if (isset($media->group) && isset($media->group->community) && isset($media->group->community->statistics)) {
        $attrs = $media->group->community->statistics->attributes();
        $views = isset($attrs['views']) ? (string)$attrs['views'] : '';
    }

    if ($videoId) {
        $videos[] = array(
            'id'        => $videoId,
            'title'     => $title,
            'published' => $published,
            'thumbnail' => "https://i.ytimg.com/vi/" . $videoId . "/hqdefault.jpg",
            'views'     => $views,
            'embed_url' => "https://www.youtube.com/embed/" . $videoId,
            'watch_url' => "https://www.youtube.com/watch?v=" . $videoId,
        );
    }
}

$result = json_encode(array(
    'ok'         => true,
    'channel_id' => $channelId,
    'handle'     => $handle,
    'videos'     => $videos,
));

@file_put_contents($cacheFile, $result);

echo $result;
