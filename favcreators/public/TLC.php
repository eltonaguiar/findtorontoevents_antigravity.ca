<?php
/**
 * TLC - Multi-Platform Live Check
 * 
 * Check if a streamer is live on TikTok, Twitch, Kick, or YouTube.
 * 
 * PHP 5 Compatibility: Define http_response_code() if not available
 */
if (!function_exists('http_response_code')) {
    function http_response_code($code = null) {
        if ($code !== null) {
            $text = '';
            switch ($code) {
                case 200: $text = 'OK'; break;
                case 400: $text = 'Bad Request'; break;
                case 401: $text = 'Unauthorized'; break;
                case 403: $text = 'Forbidden'; break;
                case 404: $text = 'Not Found'; break;
                case 500: $text = 'Internal Server Error'; break;
                case 502: $text = 'Bad Gateway'; break;
                case 503: $text = 'Service Unavailable'; break;
                case 204: $text = 'No Content'; break;
                default: $text = 'Unknown'; break;
            }
            header("HTTP/1.1 $code $text");
        }
        return 200;
    }
}

/**
 * TLC - Multi-Platform Live Check
 * 
 * Check if a streamer is live on TikTok, Twitch, Kick, or YouTube.
 * 
 * Usage:
 *   /fc/TLC.php?user=gabbyvn3&platform=tiktok
 *   /fc/TLC.php?user=jynxzi&platform=twitch
 *   /fc/TLC.php?user=amandasoliss&platform=kick
 *   /fc/TLC.php?user=wavemusic1809&platform=youtube
 * 
 * YouTube also supports video URLs:
 *   /fc/TLC.php?url=https://www.youtube.com/watch?v=2Q_MTz0ObVA
 * 
 * Legacy (defaults to TikTok):
 *   /fc/TLC.php?user=gabbyvn3
 * 
 * Response:
 *   {"user":"gabbyvn3","platform":"tiktok","live":true,"method":"sigi_user_status","checked_at":"..."}
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');

// ============ CONFIG ============
$NUM_VERIFICATION_CHECKS = 1; // Single check for speed - frontend handles retries if needed
$TIKTOK_MAX_RETRIES = 2; // Extra retries for TikTok (often rate-limited)
$TIKTOK_RETRY_DELAY_MS = 500; // Delay between retries in milliseconds

$USER_AGENTS = array(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
);

$PROXY_SERVICES = array(
    'allorigins' => 'https://api.allorigins.win/raw?url=',
    'corsproxy' => 'https://corsproxy.io/?',
    'codetabs' => 'https://api.codetabs.com/v1/proxy?quest=',
    'crossorigin' => 'https://api.crossorigin.io/proxy/?url=',
);

// Kick-specific API endpoints to try
$KICK_API_ENDPOINTS = array(
    'v2' => 'https://kick.com/api/v2/channels/',  // Newer endpoint
    'v1' => 'https://kick.com/api/v1/channels/',  // Original endpoint
);

$SUPPORTED_PLATFORMS = array('tiktok', 'twitch', 'kick', 'youtube', 'instagram', 'facebook');

// ============ HELPERS ============

function getRandomUserAgent()
{
    global $USER_AGENTS;
    return $USER_AGENTS[array_rand($USER_AGENTS)];
}

function fetchUrl($url, $timeout = 12, $extraHeaders = array())
{
    $html = false;
    $userAgent = getRandomUserAgent();
    $cacheBuster = $url . (strpos($url, '?') !== false ? '&' : '?') . '_cb=' . mt_rand(100000, 999999) . time();

    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $cacheBuster);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_USERAGENT, $userAgent);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FRESH_CONNECT, true);

        $headers = array_merge(array(
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language: en-US,en;q=0.5',
            'Cache-Control: no-cache',
        ), $extraHeaders);

        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_ENCODING, '');

        $html = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode >= 400 || $html === false) {
            return false;
        }
    }

    return $html;
}

function fetchViaProxy($targetUrl, $proxyBaseUrl)
{
    $proxyUrl = $proxyBaseUrl . urlencode($targetUrl);
    return fetchUrl($proxyUrl, 15);
}

// ============ TIKTOK DETECTION ============

/**
 * Detect TikTok story status (stories posted in last 24h)
 * Returns: array with has_story, story_count, story_posted_at
 */
function detectTikTokStory($html)
{
    if ($html === false || strlen($html) < 500) {
        return array('has_story' => false, 'story_count' => 0);
    }

    // METHOD 1: Check SIGI_STATE for story data
    if (preg_match('/<script id="SIGI_STATE"[^>]*>({.+?})<\/script>/s', $html, $matches)) {
        $sigiData = @json_decode($matches[1], true);
        if ($sigiData !== null) {
            // Look for story indicators in user data
            // TikTok stories are in the "ItemModule" or similar structure
            if (isset($sigiData['ItemModule'])) {
                $items = $sigiData['ItemModule'];
                $storyCount = 0;
                $latestTimestamp = 0;

                foreach ($items as $itemId => $item) {
                    // Check if item is a story (createTime within last 24h)
                    if (isset($item['createTime'])) {
                        $createTime = (int) $item['createTime'];
                        $age = time() - $createTime;

                        if ($age < 86400) { // 24 hours
                            $storyCount++;
                            if ($createTime > $latestTimestamp) {
                                $latestTimestamp = $createTime;
                            }
                        }
                    }
                }

                if ($storyCount > 0) {
                    return array(
                        'has_story' => true,
                        'story_count' => $storyCount,
                        'story_posted_at' => $latestTimestamp,
                        'method' => 'sigi_item_module'
                    );
                }
            }
        }
    }

    // METHOD 2: Check for story indicators in HTML text
    // Look for relative time patterns like "22h ago", "3h ago", etc.
    if (preg_match('/(\d+)h ago/', $html, $match)) {
        $hoursAgo = (int) $match[1];
        if ($hoursAgo < 24) {
            $postedAt = time() - ($hoursAgo * 3600);

            // Try to count story items (rough estimate)
            $storyCount = 1;
            if (preg_match_all('/(\d+)h ago/', $html, $matches)) {
                $storyCount = min(count($matches[0]), 10); // Cap at 10
            }

            return array(
                'has_story' => true,
                'story_count' => $storyCount,
                'story_posted_at' => $postedAt,
                'method' => 'html_time_pattern'
            );
        }
    }

    // METHOD 3: Check for story badge or indicator elements
    if (preg_match('/story|Story|STORY/', $html) && preg_match('/(\d+)\s*(video|clip)s?/', $html, $match)) {
        $count = (int) $match[1];
        if ($count > 0) {
            return array(
                'has_story' => true,
                'story_count' => $count,
                'story_posted_at' => time(), // Assume recent
                'method' => 'html_story_badge'
            );
        }
    }

    return array('has_story' => false, 'story_count' => 0);
}

function detectTikTokLive($html)
{
    if ($html === false || strlen($html) < 500) {
        return array('live' => null, 'method' => 'fetch_failed');
    }

    // SIGI_STATE JSON check (most reliable)
    if (preg_match('/<script id="SIGI_STATE"[^>]*>(\{.+?\})<\/script>/s', $html, $matches)) {
        $sigiData = @json_decode($matches[1], true);
        if ($sigiData !== null && isset($sigiData['LiveRoom'])) {
            $liveRoom = $sigiData['LiveRoom'];

            // user.status: 2 = live, 4 = offline
            if (isset($liveRoom['liveRoomUserInfo']['user']['status'])) {
                $status = (int) $liveRoom['liveRoomUserInfo']['user']['status'];
                if ($status === 2)
                    return array('live' => true, 'method' => 'sigi_user_status');
                if ($status === 4)
                    return array('live' => false, 'method' => 'sigi_user_status');
            }

            // liveRoom.status
            if (isset($liveRoom['liveRoomUserInfo']['liveRoom']['status'])) {
                $status = (int) $liveRoom['liveRoomUserInfo']['liveRoom']['status'];
                if ($status === 2)
                    return array('live' => true, 'method' => 'sigi_room_status');
                if ($status === 4)
                    return array('live' => false, 'method' => 'sigi_room_status');
            }

            // roomId check
            if (isset($liveRoom['liveRoomUserInfo']['user']['roomId'])) {
                $roomId = $liveRoom['liveRoomUserInfo']['user']['roomId'];
                if (!empty($roomId) && $roomId !== '0' && strlen($roomId) > 5) {
                    return array('live' => true, 'method' => 'sigi_roomId');
                }
            }
        }
    }

    // __UNIVERSAL_DATA check
    if (preg_match('/<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.+?\})<\/script>/s', $html, $matches)) {
        $jsonStr = $matches[1];
        if (preg_match('/"status"\s*:\s*2/', $jsonStr) && strpos($jsonStr, 'LiveRoom') !== false) {
            return array('live' => true, 'method' => 'universal_status');
        }
        if (preg_match('/"status"\s*:\s*4/', $jsonStr) && strpos($jsonStr, 'LiveRoom') !== false) {
            return array('live' => false, 'method' => 'universal_status');
        }
    }

    // Additional detection methods for edge cases
    // Method: Check for livestream page metadata
    if (preg_match('/"liveStreaming"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'live_streaming_meta');
    }

    // Method: Check for isLiveStreaming field
    if (preg_match('/"isLiveStreaming"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'isLiveStreaming_true');
    }

    // Method: Check for broadcast title indicators
    if (preg_match('/"broadcastTitle"\s*:/i', $html) && preg_match('/"roomId"\s*:\s*"\d+"/', $html)) {
        return array('live' => true, 'method' => 'broadcast_title_with_room');
    }

    // Method: Check for live stream URL patterns in webapp data
    if (preg_match('/webapp\.live-detail/i', $html) || preg_match('/live\.tiktok\.com/i', $html)) {
        if (preg_match('/"roomInfo"\s*:/i', $html)) {
            return array('live' => true, 'method' => 'webapp_live_detail');
        }
    }

    // Method: Check for flv or hls stream URLs
    if (preg_match('/\.flv|\.m3u8|stream-\d+\.tiktok/i', $html)) {
        return array('live' => true, 'method' => 'stream_url_pattern');
    }

    // Method: Check for live viewer count indicators
    if (preg_match('/"viewerCount"\s*:\s*\d+/i', $html) && preg_match('/"roomId"\s*:/i', $html)) {
        return array('live' => true, 'method' => 'viewer_count_with_room');
    }

    // roomId regex (improved to catch more patterns)
    if (preg_match('/"roomId"\s*:\s*"(\d{10,})"/', $html, $match) && $match[1] !== '0') {
        return array('live' => true, 'method' => 'regex_roomId');
    }

    // Stream URL check
    if (preg_match('/pull-[a-z0-9-]+\.tiktokcdn\.com\/stage\/stream-\d+/', $html)) {
        return array('live' => true, 'method' => 'stream_url');
    }

    // Default to offline if valid HTML
    if (strlen($html) > 10000 && strpos($html, 'tiktok') !== false) {
        return array('live' => false, 'method' => 'no_live_indicators');
    }

    return array('live' => null, 'method' => 'undetermined');
}

// ============ TWITCH DETECTION ============

function detectTwitchLive($html)
{
    if ($html === false || strlen($html) < 1000) {
        return array('live' => null, 'method' => 'fetch_failed');
    }

    // PRIMARY: Check for isLiveBroadcast in JSON-LD (most reliable from testing)
    if (preg_match('/"isLiveBroadcast"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'isLiveBroadcast_true');
    }

    // If isLiveBroadcast is explicitly false
    if (preg_match('/"isLiveBroadcast"\s*:\s*false/i', $html)) {
        return array('live' => false, 'method' => 'isLiveBroadcast_false');
    }

    // Check og:description for live indicators (stream title usually present when live)
    if (preg_match('/<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']/', $html, $match)) {
        $desc = $match[1];
        // If description looks like a stream title (not just bio), likely live
        if (preg_match('/\[\d+\/\d+\]/', $desc) || preg_match('/playing|streaming/i', $desc)) {
            return array('live' => true, 'method' => 'og_desc_stream_title');
        }
    }

    // Check for viewer count pattern (strong live indicator)
    if (preg_match('/(\d+[\d,]*)\s*(viewer|watching)/i', $html, $match)) {
        $viewers = (int) str_replace(',', '', $match[1]);
        if ($viewers > 0) {
            return array('live' => true, 'method' => 'viewer_count', 'viewers' => $viewers);
        }
    }

    // Check for offline message explicitly
    if (
        strpos($html, 'is offline') !== false ||
        preg_match('/channel.*offline/i', $html)
    ) {
        return array('live' => false, 'method' => 'offline_message');
    }

    // Large HTML but no live indicators = offline
    if (strlen($html) > 100000) {
        return array('live' => false, 'method' => 'no_live_indicators');
    }

    return array('live' => null, 'method' => 'undetermined');
}

// ============ KICK DETECTION ============

/**
 * Detect Kick live status using API via proxy (optimized for speed)
 * - Tries v2 API first with allorigins proxy (fastest combo)
 * - Falls back to v1 API if v2 fails
 * - Short timeouts to keep response time under 10s
 */
// Helper function to parse Kick API response
function parseKickApiResponse($data, $apiVersion, $proxyName) {
    if ($data === null || isset($data['error']) || isset($data['message'])) {
        return null;
    }
    
    // v2 API has is_live at top level
    if (isset($data['is_live'])) {
        if ($data['is_live'] === true) {
            return array(
                'live' => true,
                'method' => "kick_api_{$apiVersion}_is_live_{$proxyName}",
                'viewers' => isset($data['livestream']['viewer_count']) ? $data['livestream']['viewer_count'] : null,
                'title' => isset($data['livestream']['session_title']) ? $data['livestream']['session_title'] : null
            );
        } else {
            return array('live' => false, 'method' => "kick_api_{$apiVersion}_not_live_{$proxyName}");
        }
    }
    
    // Check livestream object
    if (array_key_exists('livestream', $data)) {
        if ($data['livestream'] !== null && !empty($data['livestream'])) {
            $livestream = $data['livestream'];
            return array(
                'live' => true,
                'method' => "kick_api_{$apiVersion}_livestream_{$proxyName}",
                'viewers' => isset($livestream['viewer_count']) ? $livestream['viewer_count'] : null,
                'title' => isset($livestream['session_title']) ? $livestream['session_title'] : null
            );
        }
        return array('live' => false, 'method' => "kick_api_{$apiVersion}_no_stream_{$proxyName}");
    }
    
    return null;
}

function detectKickLive($username)
{
    global $KICK_API_ENDPOINTS, $PROXY_SERVICES;

    // Try v2 API DIRECTLY first (PHP is server-side, no CORS needed)
    $apiUrl = "https://kick.com/api/v2/channels/{$username}";
    $response = fetchUrl($apiUrl, 10); // Direct call with 10s timeout
    
    if ($response !== false && strlen($response) > 100) {
        $data = @json_decode($response, true);
        $result = parseKickApiResponse($data, 'v2', 'direct');
        if ($result !== null) {
            return $result;
        }
    }
    
    // Try v1 API directly
    $apiUrl = "https://kick.com/api/v1/channels/{$username}";
    $response = fetchUrl($apiUrl, 10);
    
    if ($response !== false && strlen($response) > 100) {
        $data = @json_decode($response, true);
        $result = parseKickApiResponse($data, 'v1', 'direct');
        if ($result !== null) {
            return $result;
        }
    }
    
    // Fallback: Try v2 API with proxies (in case direct is blocked)
    $apiUrl = "https://kick.com/api/v2/channels/{$username}";
    
    foreach ($PROXY_SERVICES as $proxyName => $proxyBase) {
        $proxyUrl = $proxyBase . urlencode($apiUrl);
        $response = fetchUrl($proxyUrl, 6); // 6s timeout per proxy
        
        if ($response !== false && strlen($response) > 100) {
            $data = @json_decode($response, true);
            $result = parseKickApiResponse($data, 'v2', $proxyName);
            if ($result !== null) {
                return $result;
            }
        }
    }
    
    // All API attempts failed - return undetermined
    return array('live' => null, 'method' => 'kick_api_failed');
}

/**
 * Parse Kick HTML for live status indicators
 */
function detectKickLiveFromHtml($html, $username)
{
    // Check 1: __NEXT_DATA__ JSON (Next.js hydration data)
    if (preg_match('/<script\s+id="__NEXT_DATA__"[^>]*>(\{.+?\})<\/script>/s', $html, $match)) {
        $data = @json_decode($match[1], true);
        if ($data !== null) {
            // Navigate to channel data
            $channelData = null;
            if (isset($data['props']['pageProps']['channelData'])) {
                $channelData = $data['props']['pageProps']['channelData'];
            } else if (isset($data['props']['pageProps']['initialData'])) {
                $channelData = $data['props']['pageProps']['initialData'];
            }

            if ($channelData !== null) {
                // Check is_live field
                if (isset($channelData['is_live'])) {
                    if ($channelData['is_live'] === true) {
                        return array(
                            'live' => true,
                            'method' => 'kick_nextdata_is_live',
                            'viewers' => isset($channelData['livestream']['viewer_count']) ? $channelData['livestream']['viewer_count'] : null
                        );
                    } else {
                        return array('live' => false, 'method' => 'kick_nextdata_not_live');
                    }
                }

                // Check livestream field
                if (array_key_exists('livestream', $channelData)) {
                    if ($channelData['livestream'] !== null && !empty($channelData['livestream'])) {
                        return array('live' => true, 'method' => 'kick_nextdata_livestream_present');
                    } else {
                        return array('live' => false, 'method' => 'kick_nextdata_livestream_null');
                    }
                }
            }
        }
    }

    // Check 2: Raw JSON patterns in HTML
    // "livestream":null = offline
    if (preg_match('/"livestream"\s*:\s*null/', $html)) {
        return array('live' => false, 'method' => 'kick_html_livestream_null');
    }

    // "livestream":{"id": = live (has populated object)
    if (preg_match('/"livestream"\s*:\s*\{\s*"id"\s*:/', $html)) {
        return array('live' => true, 'method' => 'kick_html_livestream_object');
    }

    // "is_live":true/false patterns
    if (preg_match('/"is_live"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'kick_html_is_live_true');
    }
    if (preg_match('/"is_live"\s*:\s*false/i', $html)) {
        return array('live' => false, 'method' => 'kick_html_is_live_false');
    }

    // Check 3: Text indicators (less reliable but good fallback)
    $usernameLower = strtolower($username);

    // "OFFLINE" and "{username} is offline" pattern
    if (stripos($html, 'OFFLINE') !== false) {
        // Look for "{username} is offline" nearby
        if (preg_match('/' . preg_quote($username, '/') . '\s+is\s+offline/i', $html)) {
            return array('live' => false, 'method' => 'kick_html_offline_text');
        }
        // Just "OFFLINE" in prominent position
        if (preg_match('/>OFFLINE</', $html)) {
            return array('live' => false, 'method' => 'kick_html_offline_badge');
        }
    }

    // "LIVE" badge text (usually in a div/span)
    if (preg_match('/>LIVE</', $html) || preg_match('/class="[^"]*live[^"]*"[^>]*>LIVE/i', $html)) {
        return array('live' => true, 'method' => 'kick_html_live_badge');
    }

    // Check 4: Video player presence (live streams have player elements)
    if (preg_match('/<video[^>]+/', $html) || strpos($html, 'player.kick.com') !== false) {
        // If video element exists and no offline indicators, likely live
        if (stripos($html, 'offline') === false) {
            return array('live' => true, 'method' => 'kick_html_video_player');
        }
    }

    // Check 5: viewer_count in HTML (only present when live)
    if (preg_match('/"viewer_count"\s*:\s*(\d+)/', $html, $match)) {
        $viewers = (int) $match[1];
        if ($viewers > 0) {
            return array('live' => true, 'method' => 'kick_html_viewer_count', 'viewers' => $viewers);
        }
    }

    // If we have substantial HTML but couldn't determine, default to offline
    if (strlen($html) > 10000) {
        return array('live' => false, 'method' => 'kick_html_no_live_indicators');
    }

    return array('live' => null, 'method' => 'kick_html_undetermined');
}

// ============ INSTAGRAM DETECTION ============

function detectInstagramLive($html, $username)
{
    if ($html === false || strlen($html) < 500) {
        return array('live' => null, 'method' => 'fetch_failed');
    }

    // Check for login redirect (Instagram blocks unauthenticated access)
    if (strpos($html, 'login') !== false && strpos($html, 'Login') !== false && strlen($html) < 50000) {
        return array('live' => null, 'method' => 'login_required');
    }

    // METHOD 1: Check JSON-LD structured data for live broadcast
    if (preg_match('/<script type="application\/ld\+json"[^>]*>(.+?)<\/script>/s', $html, $matches)) {
        $jsonData = @json_decode($matches[1], true);
        if ($jsonData !== null) {
            // Check for VideoObject with BroadcastEvent
            if (isset($jsonData['@type']) && $jsonData['@type'] === 'VideoObject') {
                if (isset($jsonData['publication']['@type']) && $jsonData['publication']['@type'] === 'BroadcastEvent') {
                    return array('live' => true, 'method' => 'ig_jsonld_broadcast');
                }
            }
            // Check isLiveBroadcast field
            if (isset($jsonData['isLiveBroadcast']) && $jsonData['isLiveBroadcast'] === true) {
                return array('live' => true, 'method' => 'ig_jsonld_islive');
            }
        }
    }

    // METHOD 2: Check for "is_live" in embedded JSON data
    if (preg_match('/"is_live"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'ig_json_is_live');
    }

    // METHOD 3: Check for broadcast_status in page data
    if (preg_match('/"broadcast_status"\s*:\s*"(active|live)"/i', $html)) {
        return array('live' => true, 'method' => 'ig_broadcast_status');
    }

    // METHOD 4: Check window._sharedData for live indicators
    if (preg_match('/window\._sharedData\s*=\s*(\{.+?\});/s', $html, $match)) {
        $sharedData = @json_decode($match[1], true);
        if ($sharedData !== null) {
            // Navigate through the data structure
            if (isset($sharedData['entry_data']['ProfilePage'][0]['graphql']['user'])) {
                $user = $sharedData['entry_data']['ProfilePage'][0]['graphql']['user'];
                // Check for live video in edge_felix_video_timeline
                if (isset($user['edge_felix_video_timeline']['edges'])) {
                    foreach ($user['edge_felix_video_timeline']['edges'] as $edge) {
                        if (isset($edge['node']['is_video']) && $edge['node']['is_video']) {
                            if (isset($edge['node']['product_type']) && $edge['node']['product_type'] === 'igtv') {
                                // Check if it's a live broadcast
                                if (isset($edge['node']['dash_info']['is_dash_eligible']) && $edge['node']['dash_info']['is_dash_eligible']) {
                                    return array('live' => true, 'method' => 'ig_shareddata_live');
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // METHOD 5: Check meta tags
    if (preg_match('/<meta[^>]+property=["\']og:type["\'][^>]+content=["\']video\.(other|episode)["\']/', $html)) {
        // If og:type is video and title contains LIVE
        if (preg_match('/<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*LIVE[^"\']*)["\']/', $html)) {
            return array('live' => true, 'method' => 'ig_meta_live_title');
        }
    }

    // METHOD 6: Check for explicit offline indicators
    if (preg_match('/"is_live"\s*:\s*false/i', $html)) {
        return array('live' => false, 'method' => 'ig_json_not_live');
    }

    // If we have substantial HTML but no live indicators = likely offline
    if (strlen($html) > 20000 && strpos($html, 'instagram') !== false) {
        return array('live' => false, 'method' => 'ig_no_live_indicators');
    }

    return array('live' => null, 'method' => 'ig_undetermined');
}

// ============ FACEBOOK DETECTION ============

function detectFacebookLive($html, $username)
{
    if ($html === false || strlen($html) < 500) {
        return array('live' => null, 'method' => 'fetch_failed');
    }

    // Check for login wall
    if (strpos($html, 'login') !== false && strpos($html, 'Log In') !== false && strlen($html) < 50000) {
        return array('live' => null, 'method' => 'login_required');
    }

    // METHOD 1: Check JSON-LD structured data
    if (preg_match('/<script type="application\/ld\+json"[^>]*>(.+?)<\/script>/s', $html, $matches)) {
        $jsonData = @json_decode($matches[1], true);
        if ($jsonData !== null) {
            // Check for VideoObject with live indicators
            if (isset($jsonData['@type']) && $jsonData['@type'] === 'VideoObject') {
                if (isset($jsonData['isLiveBroadcast']) && $jsonData['isLiveBroadcast'] === true) {
                    return array('live' => true, 'method' => 'fb_jsonld_islive');
                }
                // Check if uploadDate is very recent (within last hour = likely live)
                if (isset($jsonData['uploadDate'])) {
                    $uploadTime = strtotime($jsonData['uploadDate']);
                    if ($uploadTime !== false && (time() - $uploadTime) < 3600) {
                        return array('live' => true, 'method' => 'fb_jsonld_recent_upload');
                    }
                }
            }
        }
    }

    // METHOD 2: Check for "is_live_stream" in embedded JSON
    if (preg_match('/"is_live_stream"\s*:\s*true/i', $html)) {
        return array('live' => true, 'method' => 'fb_json_is_live_stream');
    }

    // METHOD 3: Check for broadcast_status
    if (preg_match('/"broadcast_status"\s*:\s*"(LIVE|ACTIVE)"/i', $html)) {
        return array('live' => true, 'method' => 'fb_broadcast_status');
    }

    // METHOD 4: Check for video_broadcast_type
    if (preg_match('/"video_broadcast_type"\s*:\s*"LIVE"/i', $html)) {
        return array('live' => true, 'method' => 'fb_video_broadcast_type');
    }

    // METHOD 5: Check meta tags for live indicators
    if (preg_match('/<meta[^>]+property=["\']og:type["\'][^>]+content=["\']video\.other["\']/', $html)) {
        // Check if title or description contains "LIVE" or "is live"
        if (preg_match('/<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*(?:LIVE|is live)[^"\']*)["\']/', $html)) {
            return array('live' => true, 'method' => 'fb_meta_live_title');
        }
        if (preg_match('/<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']*(?:LIVE|is live now)[^"\']*)["\']/', $html)) {
            return array('live' => true, 'method' => 'fb_meta_live_desc');
        }
    }

    // METHOD 6: Check for LIVE badge in HTML
    if (preg_match('/>LIVE</i', $html) || preg_match('/class="[^"]*live[^"]*"[^>]*>LIVE/i', $html)) {
        return array('live' => true, 'method' => 'fb_html_live_badge');
    }

    // METHOD 7: Check for explicit offline/ended indicators
    if (preg_match('/"is_live_stream"\s*:\s*false/i', $html)) {
        return array('live' => false, 'method' => 'fb_json_not_live');
    }
    if (preg_match('/"broadcast_status"\s*:\s*"(STOPPED|ENDED)"/i', $html)) {
        return array('live' => false, 'method' => 'fb_broadcast_ended');
    }

    // If we have substantial HTML but no live indicators = likely offline
    if (strlen($html) > 30000 && strpos($html, 'facebook') !== false) {
        return array('live' => false, 'method' => 'fb_no_live_indicators');
    }

    return array('live' => null, 'method' => 'fb_undetermined');
}

// ============ YOUTUBE DETECTION ============

function detectYouTubeLive($html, $isVideoUrl = false)
{
    if ($html === false || strlen($html) < 1000) {
        return array('live' => null, 'method' => 'fetch_failed');
    }

    // PRIMARY: Check ytInitialPlayerResponse for live indicators
    if (preg_match('/ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var|let|const|<\/script>)/s', $html, $match)) {
        $data = @json_decode($match[1], true);
        if ($data !== null) {
            // Check if this is an upcoming/premiere stream (NOT actually live yet)
            if (isset($data['videoDetails']['isUpcoming'])) {
                if ($data['videoDetails']['isUpcoming'] === true) {
                    return array('live' => false, 'method' => 'yt_upcoming_stream', 'reason' => 'stream_not_started');
                }
            }

            // Check for startTime - if stream hasn't started yet, it's not live
            if (isset($data['playabilityStatus']['liveStreamability']['liveStreamabilityRenderer']['startTime'])) {
                $startTime = $data['playabilityStatus']['liveStreamability']['liveStreamabilityRenderer']['startTime'];
                if ($startTime > time()) {
                    return array('live' => false, 'method' => 'yt_scheduled_stream', 'reason' => 'starts_in_future');
                }
            }

            // Check if stream has ended (has endTimestamp or isReplay)
            if (isset($data['videoDetails']['isReplay'])) {
                if ($data['videoDetails']['isReplay'] === true) {
                    return array('live' => false, 'method' => 'yt_replay_ended', 'reason' => 'stream_ended');
                }
            }

            // Check videoDetails.isLive - must be true AND stream must be active
            if (isset($data['videoDetails']['isLive'])) {
                if ($data['videoDetails']['isLive'] === true) {
                    // Additional check: ensure we have liveStreamability with active status
                    if (isset($data['playabilityStatus']['liveStreamability'])) {
                        $liveStreamability = $data['playabilityStatus']['liveStreamability'];
                        
                        // Check for active live stream indicators
                        if (isset($liveStreamability['liveStreamabilityRenderer']['isLiveNow'])) {
                            if ($liveStreamability['liveStreamabilityRenderer']['isLiveNow'] === true) {
                                return array('live' => true, 'method' => 'yt_isLiveNow_true');
                            } else {
                                return array('live' => false, 'method' => 'yt_isLiveNow_false', 'reason' => 'not_live_now');
                            }
                        }
                        
                        // If has liveStreamability but no isLiveNow, check for stream start time
                        if (isset($liveStreamability['liveStreamabilityRenderer']['startTime'])) {
                            // Stream exists but may have ended - check if it's actually running
                            return array('live' => false, 'method' => 'yt_streamability_no_live', 'reason' => 'stream_not_active');
                        }
                    }
                    
                    // Fallback: isLive is true but no liveStreamability - likely ended or cached
                    return array('live' => false, 'method' => 'yt_isLive_no_streamability', 'reason' => 'cached_or_ended');
                } else {
                    return array('live' => false, 'method' => 'yt_isLive_false');
                }
            }

            // Check videoDetails.isLiveContent - secondary indicator
            if (isset($data['videoDetails']['isLiveContent'])) {
                if ($data['videoDetails']['isLiveContent'] === true) {
                    // This indicates the content TYPE is live, but not necessarily currently live
                    // Need additional verification
                    if (!isset($data['playabilityStatus']['liveStreamability'])) {
                        return array('live' => false, 'method' => 'yt_isLiveContent_no_stream', 'reason' => 'live_content_not_streaming');
                    }
                }
            }

            // Check for liveStreamability (present only for active live streams)
            if (isset($data['playabilityStatus']['liveStreamability'])) {
                $liveStreamability = $data['playabilityStatus']['liveStreamability'];
                
                // Verify it's actually an active live stream
                if (isset($liveStreamability['liveStreamabilityRenderer'])) {
                    $renderer = $liveStreamability['liveStreamabilityRenderer'];
                    
                    // Check for isLiveNow flag
                    if (isset($renderer['isLiveNow']) && $renderer['isLiveNow'] === true) {
                        return array('live' => true, 'method' => 'yt_liveStreamability_isLiveNow');
                    }
                    
                    // Check for start time to verify it's not a scheduled stream
                    if (isset($renderer['startTime'])) {
                        if ($renderer['startTime'] <= time()) {
                            // Stream should have started - check if there's an end time
                            if (!isset($renderer['endTime'])) {
                                // No end time and start time passed = likely live
                                // But we need isLive confirmation from videoDetails
                                return array('live' => null, 'method' => 'yt_stream_started_no_end');
                            } else {
                                // Has end time = stream ended
                                return array('live' => false, 'method' => 'yt_stream_ended', 'reason' => 'has_end_time');
                            }
                        } else {
                            // Stream starts in the future
                            return array('live' => false, 'method' => 'yt_stream_scheduled', 'reason' => 'future_start');
                        }
                    }
                }
            }
        }
    }

    // Check for isLiveBroadcast in JSON-LD - but verify it's not outdated
    if (preg_match('/"isLiveBroadcast"\s*:\s*true/i', $html)) {
        // JSON-LD can be stale - we need to verify with ytInitialPlayerResponse
        // If we reached here, ytInitialPlayerResponse didn't confirm it's actively live
        return array('live' => false, 'method' => 'yt_jsonld_stale', 'reason' => 'jsonld_without_active_confirmation');
    }

    // Direct pattern checks - these are less reliable, skip them
    // if (preg_match('/"isLive"\s*:\s*true/i', $html)) {
    //     return array('live' => true, 'method' => 'yt_isLive_true');
    // }

    // Check for live badge style - must be verified with player data
    if (strpos($html, 'BADGE_STYLE_TYPE_LIVE_NOW') !== false) {
        // Badge alone is not enough - could be stale
        // If we have ytInitialPlayerResponse and it didn't confirm live, trust that
        return array('live' => false, 'method' => 'yt_badge_unverified', 'reason' => 'badge_without_player_confirmation');
    }

    // Check for offline indicators
    if (preg_match('/"playabilityStatus"\s*:\s*\{[^}]*"status"\s*:\s*"LIVE_STREAM_OFFLINE"/i', $html)) {
        return array('live' => false, 'method' => 'yt_offline_status');
    }

    // If this was a video URL and we have content but no live indicators = video is not live
    if ($isVideoUrl && strlen($html) > 100000) {
        return array('live' => false, 'method' => 'yt_video_not_live');
    }

    // If this was a channel /live page with no live indicators = offline
    if (!$isVideoUrl && strlen($html) > 100000) {
        // Check for "offline" text or no stream indicators
        if (stripos($html, 'offline') !== false || stripos($html, 'not currently streaming') !== false) {
            return array('live' => false, 'method' => 'yt_channel_offline_text');
        }
        return array('live' => false, 'method' => 'yt_channel_not_live');
    }

    return array('live' => false, 'method' => 'yt_undetermined_default_offline');
}

// ============ URL PARSING ============

function parseYouTubeUrl($url)
{
    // Extract video ID from various YouTube URL formats
    $videoId = null;
    $channelId = null;

    // youtube.com/watch?v=VIDEO_ID
    if (preg_match('/youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/', $url, $match)) {
        $videoId = $match[1];
    }
    // youtu.be/VIDEO_ID
    else if (preg_match('/youtu\.be\/([a-zA-Z0-9_-]{11})/', $url, $match)) {
        $videoId = $match[1];
    }
    // youtube.com/live/VIDEO_ID
    else if (preg_match('/youtube\.com\/live\/([a-zA-Z0-9_-]{11})/', $url, $match)) {
        $videoId = $match[1];
    }
    // youtube.com/@username or youtube.com/c/channelname or youtube.com/channel/ID
    else if (preg_match('/youtube\.com\/(@[a-zA-Z0-9_-]+|c\/[a-zA-Z0-9_-]+|channel\/[a-zA-Z0-9_-]+)/', $url, $match)) {
        $channelId = $match[1];
    }

    return array('videoId' => $videoId, 'channelId' => $channelId);
}

function detectPlatformFromUrl($url)
{
    if (strpos($url, 'tiktok.com') !== false)
        return 'tiktok';
    if (strpos($url, 'twitch.tv') !== false)
        return 'twitch';
    if (strpos($url, 'kick.com') !== false)
        return 'kick';
    if (strpos($url, 'youtube.com') !== false || strpos($url, 'youtu.be') !== false)
        return 'youtube';
    if (strpos($url, 'instagram.com') !== false)
        return 'instagram';
    if (strpos($url, 'facebook.com') !== false || strpos($url, 'fb.com') !== false || strpos($url, 'fb.watch') !== false)
        return 'facebook';
    return null;
}

function extractUsernameFromUrl($url, $platform)
{
    switch ($platform) {
        case 'tiktok':
            if (preg_match('/tiktok\.com\/@([a-zA-Z0-9_.]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'twitch':
            if (preg_match('/twitch\.tv\/([a-zA-Z0-9_]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'kick':
            if (preg_match('/kick\.com\/([a-zA-Z0-9_]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'youtube':
            // Return channel identifier or video ID
            $parsed = parseYouTubeUrl($url);
            if ($parsed['videoId'])
                return 'video:' . $parsed['videoId'];
            if ($parsed['channelId'])
                return $parsed['channelId'];
            break;
        case 'instagram':
            // instagram.com/username/ or instagram.com/username/live/
            if (preg_match('/instagram\.com\/([a-zA-Z0-9_.]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'facebook':
            // facebook.com/username or facebook.com/pagename/videos/ or fb.watch/ID
            if (preg_match('/facebook\.com\/([a-zA-Z0-9.]+)/', $url, $match)) {
                return $match[1];
            }
            if (preg_match('/fb\.watch\/([a-zA-Z0-9]+)/', $url, $match)) {
                return 'watch:' . $match[1];
            }
            break;
    }
    return null;
}

// ============ ACCOUNT STATUS DETECTION ============

/**
 * Detect account status from HTML/API response
 * Returns: 'active', 'not_found', 'banned', 'error', 'unknown'
 */
function detectAccountStatus($html, $platform, $httpCode = 200)
{
    if ($html === false || strlen($html) < 100) {
        return 'error';
    }

    // HTTP 404 = account not found
    if ($httpCode === 404) {
        return 'not_found';
    }

    // Platform-specific detection
    switch ($platform) {
        case 'kick':
            // 404 error messages
            if (
                stripos($html, 'channel not found') !== false ||
                stripos($html, 'oops, something went wrong') !== false ||
                stripos($html, '404') !== false
            ) {
                return 'not_found';
            }
            break;

        case 'twitch':
            // Banned/deleted account messages
            if (
                stripos($html, 'time machine') !== false ||
                stripos($html, 'content is unavailable') !== false ||
                stripos($html, 'Sorry. Unless you') !== false
            ) {
                return 'not_found';
            }
            // Account suspended
            if (
                stripos($html, 'suspended') !== false ||
                stripos($html, 'banned') !== false
            ) {
                return 'banned';
            }
            break;

        case 'tiktok':
            // Account not found
            if (
                stripos($html, "Couldn't find this account") !== false ||
                stripos($html, "account not found") !== false
            ) {
                return 'not_found';
            }
            // Account banned
            if (
                stripos($html, 'account has been banned') !== false ||
                stripos($html, 'violat') !== false
            ) {
                return 'banned';
            }
            break;

        case 'youtube':
            // Channel terminated or doesn't exist
            if (
                stripos($html, 'This channel does not exist') !== false ||
                stripos($html, 'This account has been terminated') !== false ||
                stripos($html, 'channel was terminated') !== false
            ) {
                return 'banned';
            }
            // Video unavailable
            if (stripos($html, 'Video unavailable') !== false) {
                return 'not_found';
            }
            break;

        case 'instagram':
            // Account not found
            if (
                stripos($html, "Sorry, this page isn't available") !== false ||
                stripos($html, "The link you followed may be broken") !== false
            ) {
                return 'not_found';
            }
            break;

        case 'facebook':
            // Page not found
            if (
                stripos($html, "This content isn't available") !== false ||
                stripos($html, "The link you followed may be broken") !== false ||
                stripos($html, "Page Not Found") !== false
            ) {
                return 'not_found';
            }
            break;
    }

    // If we have substantial HTML and no error indicators, account is active
    if (strlen($html) > 5000) {
        return 'active';
    }

    return 'unknown';
}

// ============ MAIN DETECTION ROUTER ============


function checkLiveStatus($username, $platform, $originalUrl = null)
{
    global $PROXY_SERVICES, $NUM_VERIFICATION_CHECKS;

    // Special handling for YouTube video URLs
    $isYouTubeVideo = false;
    $targetUrl = null;

    if ($platform === 'youtube') {
        if (strpos($username, 'video:') === 0) {
            // This is a video ID
            $videoId = substr($username, 6);
            $targetUrl = "https://www.youtube.com/watch?v={$videoId}";
            $isYouTubeVideo = true;
            $username = $videoId; // For response
        } else {
            // Channel - go to /live page
            $channelPath = (strpos($username, '@') === 0) ? $username : "@{$username}";
            $targetUrl = "https://www.youtube.com/{$channelPath}/live";
        }
    } else {
        $urls = array(
            'tiktok' => "https://www.tiktok.com/@{$username}/live",
            'twitch' => "https://www.twitch.tv/{$username}",
            'kick' => null, // Kick uses API, not page scraping
            'instagram' => "https://www.instagram.com/{$username}/",
            'facebook' => strpos($username, 'watch:') === 0 ? "https://fb.watch/" . substr($username, 6) : "https://www.facebook.com/{$username}",
        );
        $targetUrl = isset($urls[$platform]) ? $urls[$platform] : null;
    }

    // Kick special handling - API with HTML fallback
    if ($platform === 'kick') {
        global $PROXY_SERVICES;
        
        $result = detectKickLive($username);
        $checkResults = array(array('method' => 'kick_api', 'result' => $result));
        
        // If API failed (live === null), try HTML fallback
        if ($result['live'] === null) {
            $kickUrl = "https://kick.com/{$username}";
            
            // Try to fetch Kick page via proxy for HTML parsing
            foreach ($PROXY_SERVICES as $proxyName => $proxyBase) {
                $html = fetchViaProxy($kickUrl, $proxyBase);
                if ($html !== false && strlen($html) > 5000) {
                    $htmlResult = detectKickLiveFromHtml($html, $username);
                    $checkResults[] = array('method' => 'kick_html_' . $proxyName, 'result' => $htmlResult);
                    
                    if ($htmlResult['live'] !== null) {
                        $result = $htmlResult;
                        break;
                    }
                }
            }
        }

        // Detect account status from Kick response
        $accountStatus = 'unknown';
        if ($result['method'] === 'kick_all_methods_failed' || $result['method'] === 'kick_api_failed') {
            $accountStatus = 'error';
        } else if (strpos($result['method'], 'undetermined') !== false) {
            $accountStatus = 'unknown';
        } else {
            $accountStatus = 'active';
        }

        return array(
            'live' => $result['live'],
            'method' => $result['method'],
            'checks' => count($checkResults) . ' attempts',
            'account_status' => $accountStatus,
            'viewers' => isset($result['viewers']) ? $result['viewers'] : null,
            'check_results' => $checkResults
        );
    }

    if ($targetUrl === null) {
        return array('live' => null, 'method' => 'invalid_platform', 'checks' => '0');
    }

    $isLive = null;
    $method = 'unknown';
    $liveCount = 0;
    $offlineCount = 0;
    $checkResults = array();

    // Verification passes with TikTok retry logic
    $storyData = array(); // Store story detection results
    
    // Calculate total attempts - TikTok gets extra retries due to rate limiting
    $maxAttempts = $NUM_VERIFICATION_CHECKS;
    if ($platform === 'tiktok') {
        global $TIKTOK_MAX_RETRIES, $TIKTOK_RETRY_DELAY_MS;
        $maxAttempts += $TIKTOK_MAX_RETRIES;
    }
    
    for ($i = 0; $i < $maxAttempts; $i++) {
        $html = false;
        $checkMethod = "attempt_" . ($i + 1);

        if ($i === 0) {
            $html = fetchUrl($targetUrl, 12);
            $checkMethod = 'direct';
        } else {
            // For TikTok retries, use a shorter delay and try direct fetch again
            if ($platform === 'tiktok') {
                usleep($TIKTOK_RETRY_DELAY_MS * 1000);
                // Alternate between direct and proxy for TikTok retries
                if ($i % 2 === 1) {
                    $html = fetchUrl($targetUrl, 15); // Longer timeout on retry
                    $checkMethod = 'direct_retry_' . $i;
                } else {
                    $proxyKeys = array_keys($PROXY_SERVICES);
                    $proxyName = $proxyKeys[$i % count($proxyKeys)];
                    $html = fetchViaProxy($targetUrl, $PROXY_SERVICES[$proxyName]);
                    $checkMethod = 'proxy_' . $proxyName;
                }
            } else {
                usleep(300000);
                $proxyKeys = array_keys($PROXY_SERVICES);
                $proxyName = $proxyKeys[array_rand($proxyKeys)];
                $html = fetchViaProxy($targetUrl, $PROXY_SERVICES[$proxyName]);
                $checkMethod = 'proxy_' . $proxyName;
            }
        }

        // Platform-specific detection
        $result = null;
        switch ($platform) {
            case 'tiktok':
                $result = detectTikTokLive($html);
                // Also check for stories on first successful fetch
                if ($html !== false && strlen($html) > 1000 && empty($storyData)) {
                    $storyData = detectTikTokStory($html);
                }
                break;
            case 'twitch':
                $result = detectTwitchLive($html);
                break;
            case 'youtube':
                $result = detectYouTubeLive($html, $isYouTubeVideo);
                break;
            case 'instagram':
                $result = detectInstagramLive($html, $username);
                break;
            case 'facebook':
                $result = detectFacebookLive($html, $username);
                break;
        }

        $checkResults[] = array(
            'attempt' => $i + 1,
            'fetch_method' => $checkMethod,
            'detection_method' => $result['method'],
            'result' => $result['live']
        );

        if ($result['live'] === true) {
            $liveCount++;
            $isLive = true;
            $method = $result['method'];
            break; // Early exit on LIVE
        } else if ($result['live'] === false) {
            $offlineCount++;
            $method = $result['method'];
            // For TikTok, if we got a definitive offline, don't retry more
            if ($platform === 'tiktok' && $result['method'] !== 'fetch_failed' && $result['method'] !== 'undetermined') {
                break;
            }
        }
        
        // For non-TikTok or if we have a definitive result, stop retrying
        if ($platform !== 'tiktok' && ($result['live'] === true || $result['live'] === false)) {
            break;
        }
    }

    // Determine final status
    if ($isLive === null) {
        $isLive = ($offlineCount > 0) ? false : false;
        $method = ($offlineCount > 0) ? 'consensus_offline' : 'fallback';
    }

    // Detect account status from last HTML check
    $accountStatus = 'unknown';
    if (!empty($checkResults)) {
        $lastCheck = end($checkResults);
        if (isset($lastCheck['html'])) {
            $accountStatus = detectAccountStatus($lastCheck['html'], $platform);
        }
    }

    $response = array(
        'live' => $isLive,
        'method' => $method,
        'checks' => "{$liveCount} live, {$offlineCount} offline",
        'account_status' => $accountStatus,
        'check_results' => $checkResults
    );

    // Add story data for TikTok
    if ($platform === 'tiktok' && !empty($storyData)) {
        if (isset($storyData['has_story']) && $storyData['has_story']) {
            $response['has_story'] = true;
            $response['story_count'] = $storyData['story_count'];
            if (isset($storyData['story_posted_at'])) {
                $response['story_posted_at'] = $storyData['story_posted_at'];
            }
        }
    }

    return $response;
}

// ============ MAIN ============

$user = isset($_GET['user']) ? trim($_GET['user']) : '';
$url = isset($_GET['url']) ? trim($_GET['url']) : '';
$platform = isset($_GET['platform']) ? strtolower(trim($_GET['platform'])) : '';

// If URL provided, extract platform and user
if (!empty($url)) {
    $detectedPlatform = detectPlatformFromUrl($url);
    if ($detectedPlatform) {
        $platform = $detectedPlatform;
        $extractedUser = extractUsernameFromUrl($url, $platform);
        if ($extractedUser) {
            $user = $extractedUser;
        }
    }
}

// Default platform to tiktok for legacy support
if (empty($platform)) {
    $platform = 'tiktok';
}

if ($user === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array(
        'error' => 'Missing user or url parameter',
        'usage' => array(
            'by_user' => '/fc/TLC.php?user=USERNAME&platform=PLATFORM',
            'by_url' => '/fc/TLC.php?url=STREAM_URL',
            'platforms' => $SUPPORTED_PLATFORMS
        )
    ));
    exit;
}

// Clean username
$user = ltrim($user, '@');

// Validate platform
if (!in_array($platform, $SUPPORTED_PLATFORMS)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array(
        'error' => 'Unsupported platform',
        'supported' => $SUPPORTED_PLATFORMS
    ));
    exit;
}

// Check live status
$result = checkLiveStatus($user, $platform, $url);

// For YouTube video URLs, show video ID instead of "video:ID"
$displayUser = $user;
if (strpos($user, 'video:') === 0) {
    $displayUser = substr($user, 6);
}

// Build response
$response = array(
    'user' => $displayUser,
    'platform' => $platform,
    'live' => $result['live'],
    'method' => $result['method'],
    'checks' => $result['checks'],
    'account_status' => isset($result['account_status']) ? $result['account_status'] : 'unknown',
    'checked_at' => gmdate('Y-m-d\TH:i:s\Z')
);

// Include viewers if available (Kick)
if (isset($result['viewers']) && $result['viewers'] !== null) {
    $response['viewers'] = $result['viewers'];
}

// Include story data if available (TikTok)
if (isset($result['has_story']) && $result['has_story']) {
    $response['has_story'] = true;
    $response['story_count'] = $result['story_count'];
    if (isset($result['story_posted_at'])) {
        $response['story_posted_at'] = $result['story_posted_at'];
    }
}

// Debug mode
if (isset($_GET['debug']) && $_GET['debug'] === '1') {
    $response['debug'] = array(
        'check_results' => $result['check_results'],
        'supported_platforms' => $SUPPORTED_PLATFORMS,
        'original_url' => $url,
    );
}

echo json_encode($response);
