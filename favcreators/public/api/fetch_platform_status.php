<?php
/**
 * Platform status fetcher — checks public APIs and RSS feeds
 * for the latest content updates from a creator on a given platform.
 *
 * GET /api/fetch_platform_status.php?platform=twitch&user=nevsrealm
 * GET /api/fetch_platform_status.php?platform=kick&user=xqc
 * GET /api/fetch_platform_status.php?platform=youtube&user=@MrBeast
 * GET /api/fetch_platform_status.php?platform=reddit&user=spez
 * GET /api/fetch_platform_status.php?platform=twitter&user=elonmusk
 * GET /api/fetch_platform_status.php?platform=tiktok&user=nevsrealm
 * GET /api/fetch_platform_status.php?platform=instagram&user=nevsrealm
 *
 * Optional: &creator_id=xxx&creator_name=xxx (to save results to DB)
 * Optional: &save=1 (auto-save results to creator_status_updates table)
 *
 * Each platform fetcher returns a standardized response:
 * {
 *   "platform": "twitch",
 *   "username": "nevsrealm",
 *   "found": true,
 *   "updates": [
 *     {
 *       "update_type": "stream",
 *       "content_title": "Playing Elden Ring",
 *       "content_url": "https://twitch.tv/nevsrealm",
 *       "content_preview": "",
 *       "content_id": "stream_123",
 *       "is_live": true,
 *       "viewer_count": 500,
 *       "content_published_at": "2026-02-05 14:30:00"
 *     }
 *   ],
 *   "error": null
 * }
 *
 * PHP 5.2 compatible: uses $conn->query() with real_escape_string, no prepared statements.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 200 OK');
    exit;
}

// Check if this file is being included or directly accessed
$_FETCH_PLATFORM_DIRECT_ACCESS = (basename(__FILE__) == basename($_SERVER['SCRIPT_FILENAME']));

if ($_FETCH_PLATFORM_DIRECT_ACCESS) {
    $allowed_platforms = array('twitch', 'kick', 'tiktok', 'instagram', 'twitter', 'reddit', 'youtube');

    $platform = isset($_GET['platform']) ? strtolower(trim($_GET['platform'])) : null;
    $username = isset($_GET['user']) ? trim($_GET['user']) : null;
    $save = isset($_GET['save']) && $_GET['save'] == '1';
    $creator_id = isset($_GET['creator_id']) ? trim($_GET['creator_id']) : null;
    $creator_name = isset($_GET['creator_name']) ? trim($_GET['creator_name']) : null;

    if (!$platform) {
        header('HTTP/1.0 400 Bad Request'); header('Status: 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing required parameter: platform'));
        exit;
    }

    if ($platform === 'x') $platform = 'twitter';

    if (!in_array($platform, $allowed_platforms)) {
        header('HTTP/1.0 400 Bad Request'); header('Status: 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Invalid platform. Allowed: ' . implode(', ', $allowed_platforms)));
        exit;
    }

    if (!$username) {
        header('HTTP/1.0 400 Bad Request'); header('Status: 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing required parameter: user'));
        exit;
    }

    // Clean username (remove @ prefix, slashes, etc.)
    $username = ltrim($username, '@/');
    $username = preg_replace('#^(tiktok|twitter|instagram|reddit|kick|twitch|youtube)[/:]#i', '', $username);

    $start_time = microtime(true);

    // Dispatch to platform-specific fetcher
    $result = null;
    switch ($platform) {
        case 'twitch':
            $result = fetch_twitch_status($username);
            break;
        case 'kick':
            $result = fetch_kick_status($username);
            break;
        case 'tiktok':
            $result = fetch_tiktok_status($username);
            break;
        case 'instagram':
            $result = fetch_instagram_status($username);
            break;
        case 'twitter':
            $result = fetch_twitter_status($username);
            break;
        case 'reddit':
            $result = fetch_reddit_status($username);
            break;
        case 'youtube':
            $result = fetch_youtube_status($username);
            break;
        default:
            $result = array('platform' => $platform, 'username' => $username, 'found' => false, 'updates' => array(), 'error' => 'Platform not implemented');
    }

    $response_time = intval((microtime(true) - $start_time) * 1000);
    $result['response_time_ms'] = $response_time;

    // Optionally save results to DB
    if ($save && !empty($result['updates'])) {
        require_once dirname(__FILE__) . '/db_connect.php';
        require_once dirname(__FILE__) . '/creator_status_updates_schema.php';

        $cid = $creator_id ? $creator_id : $username;
        $cname = $creator_name ? $creator_name : $username;

        foreach ($result['updates'] as $update) {
            // Save directly to DB (no internal POST needed)
            save_status_update_direct($conn, $cid, $cname, $platform, $username, $update);
        }

        $result['saved'] = true;
        $conn->close();
    }

    echo json_encode(array_merge(array('ok' => true), $result));
    exit;
}
// End of direct access block - functions below are available when included

// ============================================================
// PLATFORM FETCHERS (available when included)
// ============================================================

/**
 * TWITCH — Uses the public GQL/Helix endpoint (no auth needed for basic checks).
 * Checks: is currently live, last VOD, stream info.
 */
function fetch_twitch_status($username) {
    $updates = array();
    $error = null;

    // Check live status via public Twitch page scraping (no API key needed)
    $url = "https://www.twitch.tv/" . urlencode($username);

    // Use decapi.me for simple live check (public, no auth)
    $decapi_url = "https://decapi.me/twitch/uptime/" . urlencode($username);
    $uptime_response = http_fetch($decapi_url);

    $is_live = false;
    $stream_title = '';

    // Only consider live if response looks like actual uptime (contains time units)
    // Responses like "2 hours, 30 minutes" or "45 minutes, 10 seconds" indicate live
    // Errors, "offline", "not found", etc. all mean not live
    if ($uptime_response !== false) {
        $response_lower = strtolower(trim($uptime_response));
        // Check for indicators that the user is NOT live
        $not_live_indicators = array('offline', 'not found', 'error', 'invalid', 'no user', 'bad request', 'does not exist');
        $is_error = false;
        foreach ($not_live_indicators as $indicator) {
            if (stripos($response_lower, $indicator) !== false) {
                $is_error = true;
                break;
            }
        }
        
        // Only mark as live if no errors AND response contains time units (hours, minutes, seconds, days)
        if (!$is_error && preg_match('/(hour|minute|second|day)/i', $uptime_response)) {
            $is_live = true;
            // Get stream title
            $title_url = "https://decapi.me/twitch/title/" . urlencode($username);
            $title_response = http_fetch($title_url);
            if ($title_response !== false && stripos($title_response, 'not found') === false && stripos($title_response, 'error') === false) {
                $stream_title = trim($title_response);
            }
        }
    }

    if ($is_live) {
        $updates[] = array(
            'update_type' => 'stream',
            'content_title' => $stream_title,
            'content_url' => $url,
            'content_preview' => 'Currently live on Twitch' . ($stream_title ? ': ' . $stream_title : ''),
            'content_id' => 'twitch_live_' . $username,
            'is_live' => true,
            'viewer_count' => 0,
            'content_published_at' => date('Y-m-d H:i:s')
        );
    }

    // Check last VOD via decapi
    $vod_url = "https://decapi.me/twitch/latest_video/" . urlencode($username);
    $vod_response = http_fetch($vod_url);
    if ($vod_response !== false && stripos($vod_response, 'No videos') === false && stripos($vod_response, 'not found') === false && trim($vod_response) !== '') {
        $updates[] = array(
            'update_type' => 'vod',
            'content_title' => 'Latest VOD',
            'content_url' => trim($vod_response),
            'content_preview' => '',
            'content_id' => 'twitch_vod_' . $username,
            'is_live' => false,
            'viewer_count' => 0,
            'content_published_at' => null
        );
    }

    return array(
        'platform' => 'twitch',
        'username' => $username,
        'account_url' => $url,
        'found' => !empty($updates) || $is_live,
        'is_live' => $is_live,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * KICK — Uses Kick's public API (v2).
 * Checks: is currently live, recent VODs.
 */
function fetch_kick_status($username) {
    $updates = array();
    $error = null;
    $is_live = false;
    $account_url = "https://kick.com/" . urlencode($username);

    // Kick public API v2
    $api_url = "https://kick.com/api/v2/channels/" . urlencode($username);
    $response = http_fetch($api_url);

    if ($response !== false) {
        $data = json_decode($response, true);
        if ($data && isset($data['livestream'])) {
            $ls = $data['livestream'];
            if ($ls && isset($ls['is_live']) && $ls['is_live']) {
                $is_live = true;
                $updates[] = array(
                    'update_type' => 'stream',
                    'content_title' => isset($ls['session_title']) ? $ls['session_title'] : '',
                    'content_url' => $account_url,
                    'content_preview' => 'Currently live on Kick',
                    'content_thumbnail' => isset($ls['thumbnail']['url']) ? $ls['thumbnail']['url'] : '',
                    'content_id' => isset($ls['id']) ? 'kick_live_' . $ls['id'] : 'kick_live_' . $username,
                    'is_live' => true,
                    'viewer_count' => isset($ls['viewer_count']) ? intval($ls['viewer_count']) : 0,
                    'content_published_at' => isset($ls['created_at']) ? date('Y-m-d H:i:s', strtotime($ls['created_at'])) : date('Y-m-d H:i:s')
                );
            }
        }

        // Check recent videos/clips
        if ($data && isset($data['previous_livestreams']) && is_array($data['previous_livestreams']) && count($data['previous_livestreams']) > 0) {
            $last_vod = $data['previous_livestreams'][0];
            $updates[] = array(
                'update_type' => 'vod',
                'content_title' => isset($last_vod['session_title']) ? $last_vod['session_title'] : 'Recent VOD',
                'content_url' => $account_url,
                'content_preview' => '',
                'content_thumbnail' => isset($last_vod['thumbnail']['url']) ? $last_vod['thumbnail']['url'] : '',
                'content_id' => isset($last_vod['id']) ? 'kick_vod_' . $last_vod['id'] : 'kick_vod_' . $username,
                'is_live' => false,
                'viewer_count' => isset($last_vod['viewer_count']) ? intval($last_vod['viewer_count']) : 0,
                'content_published_at' => isset($last_vod['created_at']) ? date('Y-m-d H:i:s', strtotime($last_vod['created_at'])) : null
            );
        }
    } else {
        $error = 'Could not reach Kick API';
    }

    return array(
        'platform' => 'kick',
        'username' => $username,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => $is_live,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * TIKTOK — Checks for live status and recent content.
 * Uses public page scraping since TikTok doesn't have a public API.
 */
function fetch_tiktok_status($username) {
    $updates = array();
    $error = null;
    $is_live = false;
    $account_url = "https://www.tiktok.com/@" . urlencode($username);

    // Check TikTok live status via the page
    $live_url = "https://www.tiktok.com/@" . urlencode($username) . "/live";
    $response = http_fetch($live_url);

    if ($response !== false) {
        // TikTok live pages contain "LIVE" indicators and room_id when streaming
        if (preg_match('/"isLiveStreaming"\s*:\s*true/i', $response) ||
            preg_match('/room_id/i', $response) ||
            (stripos($response, '"status":2') !== false && stripos($response, 'LiveRoom') !== false)) {
            $is_live = true;
            $title = '';
            if (preg_match('/"title"\s*:\s*"([^"]+)"/i', $response, $m)) {
                $title = $m[1];
            }
            $updates[] = array(
                'update_type' => 'stream',
                'content_title' => $title,
                'content_url' => $live_url,
                'content_preview' => 'Currently live on TikTok',
                'content_id' => 'tiktok_live_' . $username,
                'is_live' => true,
                'viewer_count' => 0,
                'content_published_at' => date('Y-m-d H:i:s')
            );
        }
    }

    // Try to get recent post info from profile page
    // TikTok embeds video data in __UNIVERSAL_DATA_FOR_REHYDRATION__ or SIGI_STATE
    $profile_response = http_fetch($account_url);
    if ($profile_response !== false) {
        $found_video = false;
        $one_year_ago = time() - (365 * 24 * 60 * 60);

        // Method 1: Look for itemList in the SIGI_STATE or rehydration data
        // Pattern: "ItemModule":{"videoId":{"id":"videoId","desc":"...","createTime":"timestamp"}}
        if (preg_match('/"ItemModule"\s*:\s*\{([^}]+\{[^}]*"createTime"\s*:\s*"?(\d+)"?[^}]*\})/s', $profile_response, $item_match)) {
            // Extract the first video in ItemModule
            if (preg_match('/"id"\s*:\s*"(\d{10,})"/', $item_match[1], $vid_m)) {
                $video_id = $vid_m[1];
                $post_time = intval($item_match[2]);
                
                // Only accept if timestamp is within the last year (not ancient data)
                if ($post_time > $one_year_ago) {
                    $desc = '';
                    if (preg_match('/"desc"\s*:\s*"([^"]{0,500})"/i', $item_match[1], $desc_m)) {
                        $desc = $desc_m[1];
                    }
                    $updates[] = array(
                        'update_type' => 'post',
                        'content_title' => $desc ? $desc : 'Recent TikTok post',
                        'content_url' => "https://www.tiktok.com/@" . urlencode($username) . "/video/" . $video_id,
                        'content_preview' => $desc,
                        'content_id' => 'tiktok_post_' . $video_id,
                        'is_live' => false,
                        'viewer_count' => 0,
                        'content_published_at' => date('Y-m-d H:i:s', $post_time)
                    );
                    $found_video = true;
                }
            }
        }

        // Method 2: Look for video data in webapp.video-detail pattern
        if (!$found_video && preg_match('/"webapp\.video-detail"[^{]*\{[^}]*"id"\s*:\s*"(\d{10,})"[^}]*"createTime"\s*:\s*"?(\d+)"?/s', $profile_response, $detail_m)) {
            $video_id = $detail_m[1];
            $post_time = intval($detail_m[2]);
            
            if ($post_time > $one_year_ago) {
                $updates[] = array(
                    'update_type' => 'post',
                    'content_title' => 'Recent TikTok post',
                    'content_url' => "https://www.tiktok.com/@" . urlencode($username) . "/video/" . $video_id,
                    'content_preview' => '',
                    'content_id' => 'tiktok_post_' . $video_id,
                    'is_live' => false,
                    'viewer_count' => 0,
                    'content_published_at' => date('Y-m-d H:i:s', $post_time)
                );
                $found_video = true;
            }
        }

        // Method 3: If no recent video found, check for profile and get follower info
        if (!$found_video) {
            // Check if profile exists by looking for follower count or user data
            $follower_count = 0;
            $nickname = $username;
            if (preg_match('/"followerCount"\s*:\s*(\d+)/i', $profile_response, $fc_m)) {
                $follower_count = intval($fc_m[1]);
            }
            if (preg_match('/"nickname"\s*:\s*"([^"]+)"/i', $profile_response, $nn_m)) {
                $nickname = $nn_m[1];
            }
            
            if ($follower_count > 0 || preg_match('/"uniqueId"\s*:\s*"' . preg_quote($username, '/') . '"/i', $profile_response)) {
                $updates[] = array(
                    'update_type' => 'profile',
                    'content_title' => $nickname . ' on TikTok',
                    'content_url' => $account_url,
                    'content_preview' => $follower_count > 0 ? number_format($follower_count) . ' followers - Visit for latest videos' : 'Profile active - Visit for latest videos',
                    'content_id' => 'tiktok_profile_' . $username,
                    'is_live' => false,
                    'viewer_count' => 0,
                    'content_published_at' => null
                );
                $error = 'Could not extract videos (JS-rendered) - profile link provided';
            }
        }
    }

    // Fallback: Return profile link if nothing else worked
    if (empty($updates)) {
        $updates[] = array(
            'update_type' => 'profile',
            'content_title' => '@' . $username . ' on TikTok',
            'content_url' => $account_url,
            'content_preview' => 'Visit profile for latest videos',
            'content_id' => 'tiktok_profile_' . $username,
            'is_live' => false,
            'viewer_count' => 0,
            'content_published_at' => null
        );
        if ($response === false && $profile_response === false) {
            $error = 'Could not reach TikTok';
        } else {
            $error = 'Profile not found or is private';
        }
    }

    return array(
        'platform' => 'tiktok',
        'username' => $username,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => $is_live,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * INSTAGRAM — Checks recent posts/stories via public page.
 * Limited due to Instagram's anti-scraping measures.
 */
function fetch_instagram_status($username) {
    $updates = array();
    $error = null;
    $account_url = "https://www.instagram.com/" . urlencode($username) . "/";

    // Instagram public JSON endpoint (may be rate-limited)
    $api_url = "https://www.instagram.com/api/v1/users/web_profile_info/?username=" . urlencode($username);
    $response = http_fetch($api_url, array(
        'X-IG-App-ID: 936619743392459',
        'X-Requested-With: XMLHttpRequest'
    ));

    if ($response !== false) {
        $data = json_decode($response, true);
        if ($data && isset($data['data']['user']['edge_owner_to_timeline_media']['edges'])) {
            $posts = $data['data']['user']['edge_owner_to_timeline_media']['edges'];
            if (!empty($posts)) {
                $latest = $posts[0]['node'];
                $caption = '';
                if (isset($latest['edge_media_to_caption']['edges'][0]['node']['text'])) {
                    $caption = substr($latest['edge_media_to_caption']['edges'][0]['node']['text'], 0, 500);
                }
                $updates[] = array(
                    'update_type' => 'post',
                    'content_title' => $caption ? $caption : 'Recent Instagram post',
                    'content_url' => "https://www.instagram.com/p/" . $latest['shortcode'] . "/",
                    'content_preview' => $caption,
                    'content_thumbnail' => isset($latest['thumbnail_src']) ? $latest['thumbnail_src'] : '',
                    'content_id' => 'ig_post_' . $latest['shortcode'],
                    'is_live' => false,
                    'like_count' => isset($latest['edge_liked_by']['count']) ? intval($latest['edge_liked_by']['count']) : 0,
                    'comment_count' => isset($latest['edge_media_to_comment']['count']) ? intval($latest['edge_media_to_comment']['count']) : 0,
                    'content_published_at' => isset($latest['taken_at_timestamp']) ? date('Y-m-d H:i:s', $latest['taken_at_timestamp']) : null
                );
            }
        }
    }

    // Fallback 1: try scraping the profile page for latest post timestamp
    if (empty($updates)) {
        $page_response = http_fetch($account_url);
        if ($page_response !== false) {
            // Try to find post timestamp
            if (preg_match('/"taken_at_timestamp"\s*:\s*(\d+)/', $page_response, $m)) {
                $updates[] = array(
                    'update_type' => 'post',
                    'content_title' => 'Recent Instagram post',
                    'content_url' => $account_url,
                    'content_preview' => '',
                    'content_id' => 'ig_latest_' . $username,
                    'is_live' => false,
                    'content_published_at' => date('Y-m-d H:i:s', intval($m[1]))
                );
            }
            // Check if profile exists (look for username or follower indicators)
            elseif (preg_match('/"username"\s*:\s*"' . preg_quote($username, '/') . '"/i', $page_response) ||
                    preg_match('/"edge_followed_by"\s*:\s*\{/', $page_response)) {
                // Profile exists but can't get post data
                $updates[] = array(
                    'update_type' => 'profile',
                    'content_title' => '@' . $username . ' on Instagram',
                    'content_url' => $account_url,
                    'content_preview' => 'Profile active - visit for latest posts',
                    'content_id' => 'ig_profile_' . $username,
                    'is_live' => false,
                    'content_published_at' => null
                );
                $error = 'Could not extract posts (API restricted) - profile link provided';
            }
        }
    }

    // Fallback 2: Return profile link if nothing else works
    if (empty($updates)) {
        $updates[] = array(
            'update_type' => 'profile',
            'content_title' => '@' . $username . ' on Instagram',
            'content_url' => $account_url,
            'content_preview' => 'Visit profile for latest posts (API restricted)',
            'content_id' => 'ig_profile_' . $username,
            'is_live' => false,
            'content_published_at' => null
        );
        $error = 'Could not fetch Instagram data (API restricted) - profile link provided';
    }

    return array(
        'platform' => 'instagram',
        'username' => $username,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => false,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * TWITTER/X — Checks recent tweets via public syndication API.
 * Uses Twitter's syndication/timeline endpoint (no auth needed).
 */
function fetch_twitter_status($username) {
    $updates = array();
    $error = null;
    $account_url = "https://x.com/" . urlencode($username);

    // Twitter syndication API (public, no auth needed)
    $syndication_url = "https://syndication.twitter.com/srv/timeline-profile/screen-name/" . urlencode($username);
    $response = http_fetch($syndication_url);

    if ($response !== false) {
        // Extract tweet data from HTML response
        // The syndication endpoint returns rendered HTML with tweet content
        if (preg_match_all('/<div[^>]*class="[^"]*timeline-Tweet-text[^"]*"[^>]*>(.*?)<\/div>/si', $response, $matches)) {
            if (!empty($matches[1])) {
                $tweet_text = strip_tags($matches[1][0]);
                $tweet_text = trim(html_entity_decode($tweet_text, ENT_QUOTES, 'UTF-8'));

                // Try to extract tweet URL
                $tweet_url = $account_url;
                if (preg_match('/data-tweet-id="(\d+)"/', $response, $id_match)) {
                    $tweet_url = "https://x.com/" . urlencode($username) . "/status/" . $id_match[1];
                }

                // Try to extract timestamp
                $published_at = null;
                if (preg_match('/datetime="([^"]+)"/', $response, $time_match)) {
                    $published_at = date('Y-m-d H:i:s', strtotime($time_match[1]));
                }

                $updates[] = array(
                    'update_type' => 'tweet',
                    'content_title' => substr($tweet_text, 0, 280),
                    'content_url' => $tweet_url,
                    'content_preview' => $tweet_text,
                    'content_id' => isset($id_match[1]) ? 'tweet_' . $id_match[1] : 'tweet_latest_' . $username,
                    'is_live' => false,
                    'like_count' => 0,
                    'content_published_at' => $published_at
                );
            }
        }
    }

    // Fallback 1: RSS Bridge instances
    if (empty($updates)) {
        $rss_bridge_instances = array(
            'https://rss-bridge.org/bridge01/?action=display&bridge=TwitterBridge&context=By+username&u=' . urlencode($username) . '&format=Atom',
            'https://wtf.roflcopter.fr/rss-bridge/?action=display&bridge=TwitterBridge&context=By+username&u=' . urlencode($username) . '&format=Atom'
        );
        foreach ($rss_bridge_instances as $bridge_url) {
            $rss_response = http_fetch($bridge_url);
            if ($rss_response !== false && stripos($rss_response, '<entry>') !== false) {
                if (preg_match('/<entry>.*?<title[^>]*>([^<]*)<\/title>.*?<link[^>]*href="([^"]*)".*?<updated>([^<]*)<\/updated>/si', $rss_response, $rss_m)) {
                    $tweet_text = html_entity_decode(trim($rss_m[1]), ENT_QUOTES, 'UTF-8');
                    $tweet_url = trim($rss_m[2]);
                    // Convert nitter/bridge URLs to x.com
                    $tweet_url = preg_replace('#https?://[^/]+/#', 'https://x.com/', $tweet_url);
                    
                    $updates[] = array(
                        'update_type' => 'tweet',
                        'content_title' => substr($tweet_text, 0, 280),
                        'content_url' => $tweet_url,
                        'content_preview' => $tweet_text,
                        'content_id' => 'tweet_bridge_' . md5($tweet_url),
                        'is_live' => false,
                        'content_published_at' => date('Y-m-d H:i:s', strtotime($rss_m[3]))
                    );
                    break;
                }
            }
        }
    }

    // Fallback 2: If still no data, return a profile link at minimum
    if (empty($updates)) {
        // Just indicate the profile exists but we can't get tweets
        $updates[] = array(
            'update_type' => 'profile',
            'content_title' => '@' . $username . ' on X/Twitter',
            'content_url' => $account_url,
            'content_preview' => 'Visit profile for latest tweets (API restricted)',
            'content_id' => 'twitter_profile_' . $username,
            'is_live' => false,
            'content_published_at' => null
        );
        $error = 'Could not fetch tweets (API restricted) - profile link provided';
    }

    return array(
        'platform' => 'twitter',
        'username' => $username,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => false,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * REDDIT — Uses Reddit's public JSON API.
 * Checks: recent posts and comments from a user's profile.
 */
function fetch_reddit_status($username) {
    $updates = array();
    $error = null;
    $account_url = "https://www.reddit.com/user/" . urlencode($username);

    // Reddit public JSON API (no auth needed, but rate-limited)
    $api_url = "https://www.reddit.com/user/" . urlencode($username) . "/submitted.json?limit=1&sort=new&raw_json=1";
    $response = http_fetch($api_url, array(), 'FavCreators/1.0 (by /u/findtorontoevents)');

    if ($response !== false) {
        $data = json_decode($response, true);
        if ($data && isset($data['data']['children']) && !empty($data['data']['children'])) {
            $post = $data['data']['children'][0]['data'];

            // Filter out NSFW content
            if (isset($post['over_18']) && $post['over_18']) {
                // Skip NSFW posts
            } else {
                $post_url = "https://www.reddit.com" . $post['permalink'];
                $updates[] = array(
                    'update_type' => 'post',
                    'content_title' => isset($post['title']) ? $post['title'] : 'Reddit post',
                    'content_url' => $post_url,
                    'content_preview' => isset($post['selftext']) ? substr($post['selftext'], 0, 500) : '',
                    'content_thumbnail' => (isset($post['thumbnail']) && filter_var($post['thumbnail'], FILTER_VALIDATE_URL)) ? $post['thumbnail'] : '',
                    'content_id' => 'reddit_' . $post['id'],
                    'is_live' => false,
                    'like_count' => isset($post['ups']) ? intval($post['ups']) : 0,
                    'comment_count' => isset($post['num_comments']) ? intval($post['num_comments']) : 0,
                    'content_published_at' => isset($post['created_utc']) ? date('Y-m-d H:i:s', intval($post['created_utc'])) : null
                );
            }
        }
    }

    // Also check for recent comments
    $comments_url = "https://www.reddit.com/user/" . urlencode($username) . "/comments.json?limit=1&sort=new&raw_json=1";
    $comments_response = http_fetch($comments_url, array(), 'FavCreators/1.0 (by /u/findtorontoevents)');

    if ($comments_response !== false) {
        $cdata = json_decode($comments_response, true);
        if ($cdata && isset($cdata['data']['children']) && !empty($cdata['data']['children'])) {
            $comment = $cdata['data']['children'][0]['data'];

            if (!(isset($comment['over_18']) && $comment['over_18'])) {
                $comment_url = isset($comment['permalink']) ? "https://www.reddit.com" . $comment['permalink'] : $account_url;
                $updates[] = array(
                    'update_type' => 'comment',
                    'content_title' => 'Comment in r/' . (isset($comment['subreddit']) ? $comment['subreddit'] : 'unknown'),
                    'content_url' => $comment_url,
                    'content_preview' => isset($comment['body']) ? substr($comment['body'], 0, 500) : '',
                    'content_id' => 'reddit_comment_' . $comment['id'],
                    'is_live' => false,
                    'like_count' => isset($comment['ups']) ? intval($comment['ups']) : 0,
                    'content_published_at' => isset($comment['created_utc']) ? date('Y-m-d H:i:s', intval($comment['created_utc'])) : null
                );
            }
        }
    }

    if (empty($updates) && $response === false) {
        $error = 'Could not reach Reddit API';
    }

    return array(
        'platform' => 'reddit',
        'username' => $username,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => false,
        'updates' => $updates,
        'error' => $error
    );
}

/**
 * YOUTUBE — Uses YouTube's public RSS feed.
 * Checks: latest uploaded video, live stream status.
 */
function fetch_youtube_status($username) {
    $updates = array();
    $error = null;
    $is_live = false;

    // Clean up the username - handle @handles, channel IDs, etc.
    $clean_user = ltrim($username, '@');
    $account_url = "https://www.youtube.com/@" . urlencode($clean_user);

    // Try RSS feed via @handle
    $rss_url = "https://www.youtube.com/feeds/videos.xml?user=" . urlencode($clean_user);
    $response = http_fetch($rss_url);

    // If user-based feed fails, try the handle page to get channel ID
    if ($response === false || stripos($response, '<entry>') === false) {
        // Try to get channel page and extract channel ID
        $page_response = http_fetch($account_url);
        if ($page_response !== false) {
            $channel_id = null;
            if (preg_match('/channel_id=([A-Za-z0-9_-]+)/', $page_response, $m)) {
                $channel_id = $m[1];
            } elseif (preg_match('/"channelId"\s*:\s*"([A-Za-z0-9_-]+)"/', $page_response, $m)) {
                $channel_id = $m[1];
            } elseif (preg_match('/data-channel-external-id="([A-Za-z0-9_-]+)"/', $page_response, $m)) {
                $channel_id = $m[1];
            }

            if ($channel_id) {
                $rss_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" . urlencode($channel_id);
                $response = http_fetch($rss_url);
            }

            // Check for live status from page
            if (stripos($page_response, '"isLive":true') !== false || stripos($page_response, '"isLiveNow":true') !== false) {
                $is_live = true;
            }
        }
    }

    // Parse RSS feed
    if ($response !== false && stripos($response, '<entry>') !== false) {
        // Extract latest video entry
        if (preg_match('/<entry>\s*<id>yt:video:([^<]+)<\/id>\s*<yt:videoId>([^<]+)<\/yt:videoId>\s*<yt:channelId>[^<]+<\/yt:channelId>\s*<title>([^<]+)<\/title>.*?<published>([^<]+)<\/published>/si', $response, $m)) {
            $video_id = $m[2];
            $title = html_entity_decode($m[3], ENT_QUOTES, 'UTF-8');
            $published = date('Y-m-d H:i:s', strtotime($m[4]));

            $updates[] = array(
                'update_type' => 'video',
                'content_title' => $title,
                'content_url' => "https://www.youtube.com/watch?v=" . $video_id,
                'content_preview' => '',
                'content_thumbnail' => "https://i.ytimg.com/vi/" . $video_id . "/hqdefault.jpg",
                'content_id' => 'yt_' . $video_id,
                'is_live' => false,
                'viewer_count' => 0,
                'content_published_at' => $published
            );
        }
    }

    // Add live stream if detected
    if ($is_live) {
        array_unshift($updates, array(
            'update_type' => 'stream',
            'content_title' => 'Live on YouTube',
            'content_url' => $account_url . '/live',
            'content_preview' => 'Currently live on YouTube',
            'content_id' => 'yt_live_' . $clean_user,
            'is_live' => true,
            'viewer_count' => 0,
            'content_published_at' => date('Y-m-d H:i:s')
        ));
    }

    if (empty($updates)) {
        $error = 'Could not fetch YouTube data (channel may not exist or has no public videos)';
    }

    return array(
        'platform' => 'youtube',
        'username' => $clean_user,
        'account_url' => $account_url,
        'found' => !empty($updates),
        'is_live' => $is_live,
        'updates' => $updates,
        'error' => $error
    );
}


// ============================================================
// HELPER FUNCTIONS
// ============================================================

/**
 * HTTP fetch helper using cURL or file_get_contents as fallback.
 */
function http_fetch($url, $extra_headers = array(), $user_agent = null) {
    if (!$user_agent) {
        $user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
    }

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if (!$ch) return false;

        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
        curl_setopt($ch, CURLOPT_USERAGENT, $user_agent);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);

        if (!empty($extra_headers)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $extra_headers);
        }

        $body = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($body === false || $http_code >= 400) return false;
        return $body;
    }

    // Fallback to file_get_contents
    if (ini_get('allow_url_fopen')) {
        $header_string = "User-Agent: " . $user_agent . "\r\n";
        if (!empty($extra_headers)) {
            $header_string .= implode("\r\n", $extra_headers) . "\r\n";
        }

        $opts = array('http' => array(
            'method' => 'GET',
            'header' => $header_string,
            'timeout' => 15,
            'ignore_errors' => true
        ));
        $ctx = stream_context_create($opts);
        $body = @file_get_contents($url, false, $ctx);
        return $body !== false ? $body : false;
    }

    return false;
}

/**
 * Save status update directly to DB (used when &save=1).
 * PHP 5.2 compatible: uses $conn->query() with real_escape_string, no prepared statements.
 */
function save_status_update_direct($conn, $creator_id, $creator_name, $platform, $username, $update) {
    $update_type = isset($update['update_type']) ? $update['update_type'] : 'post';
    $now = date('Y-m-d H:i:s');

    $content_title = isset($update['content_title']) ? $update['content_title'] : '';
    $content_url = isset($update['content_url']) ? $update['content_url'] : '';
    $content_preview = isset($update['content_preview']) ? $update['content_preview'] : '';
    $content_thumbnail = isset($update['content_thumbnail']) ? $update['content_thumbnail'] : '';
    $content_id = isset($update['content_id']) ? $update['content_id'] : '';
    $is_live = isset($update['is_live']) ? ($update['is_live'] ? 1 : 0) : 0;
    $viewer_count = isset($update['viewer_count']) ? intval($update['viewer_count']) : 0;
    $like_count = isset($update['like_count']) ? intval($update['like_count']) : 0;
    $comment_count = isset($update['comment_count']) ? intval($update['comment_count']) : 0;
    $content_published_at = isset($update['content_published_at']) ? $update['content_published_at'] : null;

    // Escape all values
    $esc_creator_id = $conn->real_escape_string($creator_id);
    $esc_creator_name = $conn->real_escape_string($creator_name);
    $esc_platform = $conn->real_escape_string($platform);
    $esc_username = $conn->real_escape_string($username);
    $esc_update_type = $conn->real_escape_string($update_type);
    $esc_content_title = $conn->real_escape_string($content_title);
    $esc_content_url = $conn->real_escape_string($content_url);
    $esc_content_preview = $conn->real_escape_string($content_preview);
    $esc_content_thumbnail = $conn->real_escape_string($content_thumbnail);
    $esc_content_id = $conn->real_escape_string($content_id);
    $esc_now = $conn->real_escape_string($now);
    $esc_content_published_at = ($content_published_at !== null) ? "'" . $conn->real_escape_string($content_published_at) . "'" : 'NULL';

    // Check if record exists
    $check_sql = "SELECT id FROM creator_status_updates WHERE creator_id = '$esc_creator_id' AND platform = '$esc_platform' AND update_type = '$esc_update_type'";
    $check_result = $conn->query($check_sql);
    $existing = ($check_result && $check_result->num_rows > 0) ? $check_result->fetch_assoc() : null;

    if ($existing) {
        $sql = "UPDATE creator_status_updates SET
            creator_name = '$esc_creator_name',
            username = '$esc_username',
            content_title = '$esc_content_title',
            content_url = '$esc_content_url',
            content_preview = '$esc_content_preview',
            content_thumbnail = '$esc_content_thumbnail',
            content_id = '$esc_content_id',
            is_live = " . intval($is_live) . ",
            viewer_count = " . intval($viewer_count) . ",
            like_count = " . intval($like_count) . ",
            comment_count = " . intval($comment_count) . ",
            content_published_at = $esc_content_published_at,
            last_checked = '$esc_now',
            last_updated = '$esc_now',
            check_count = check_count + 1,
            checked_by = 'fetch_platform_status'
            WHERE id = " . intval($existing['id']);
        $conn->query($sql);
    } else {
        $esc_account_url = $conn->real_escape_string($content_url);
        $sql = "INSERT INTO creator_status_updates
            (creator_id, creator_name, platform, username, account_url, update_type,
             content_title, content_url, content_preview, content_thumbnail, content_id,
             is_live, viewer_count, like_count, comment_count, content_published_at,
             last_checked, last_updated, check_count, checked_by)
            VALUES (
                '$esc_creator_id', '$esc_creator_name', '$esc_platform', '$esc_username', '$esc_account_url', '$esc_update_type',
                '$esc_content_title', '$esc_content_url', '$esc_content_preview', '$esc_content_thumbnail', '$esc_content_id',
                " . intval($is_live) . ", " . intval($viewer_count) . ", " . intval($like_count) . ", " . intval($comment_count) . ", $esc_content_published_at,
                '$esc_now', '$esc_now', 1, 'fetch_platform_status'
            )";
        $conn->query($sql);
    }
}
?>
