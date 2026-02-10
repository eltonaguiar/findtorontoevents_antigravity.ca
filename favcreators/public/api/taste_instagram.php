<?php
/**
 * Instagram Public Profile Scraper for Taste Profile
 * 
 * Attempts to extract music-related data from public Instagram profiles.
 * Works server-side (PHP 5.2 compatible).
 * 
 * Usage: GET /fc/api/taste_instagram.php?handle=eltoront0
 * 
 * NOTE: Instagram heavily restricts scraping. This uses multiple fallback
 * methods but may return limited data. For best results, combine with
 * other platform data (Spotify, YouTube).
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$handle = isset($_GET['handle']) ? trim($_GET['handle']) : '';
$handle = ltrim($handle, '@');

if ($handle === '') {
    echo json_encode(array('error' => 'Missing handle parameter'));
    exit;
}

// Validate handle (alphanumeric + dots + underscores)
if (!preg_match('/^[a-zA-Z0-9._]{1,30}$/', $handle)) {
    echo json_encode(array('error' => 'Invalid Instagram handle'));
    exit;
}

/**
 * Fetch a URL with curl, returning the response body.
 */
function taste_fetch_url($url, $headers_arr) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    if (!empty($headers_arr)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_arr);
    }
    
    // Mimic browser
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    
    $body = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($code >= 200 && $code < 400 && $body !== false) {
        return $body;
    }
    return false;
}

/**
 * Method 1: Try the Instagram web profile page and extract og: tags
 */
function scrape_instagram_og($handle) {
    $url = 'https://www.instagram.com/' . $handle . '/';
    $html = taste_fetch_url($url, array(
        'Accept: text/html,application/xhtml+xml',
        'Accept-Language: en-US,en;q=0.9',
    ));
    
    if ($html === false) {
        return null;
    }
    
    $result = array(
        'handle' => $handle,
        'name' => '',
        'bio' => '',
        'profile_pic' => '',
        'followers' => 0,
        'following' => 0,
        'posts_count' => 0,
    );
    
    // Extract og:title (usually "Name (@handle)")
    if (preg_match('/<meta\s+property="og:title"\s+content="([^"]+)"/i', $html, $m)) {
        $result['name'] = html_entity_decode($m[1]);
    }
    
    // Extract og:description (bio + follower counts)
    if (preg_match('/<meta\s+property="og:description"\s+content="([^"]+)"/i', $html, $m)) {
        $desc = html_entity_decode($m[1]);
        $result['bio'] = $desc;
        
        // Parse follower counts from description
        // Format: "1,234 Followers, 567 Following, 89 Posts - ..."
        if (preg_match('/([\d,]+)\s*Followers/i', $desc, $fm)) {
            $result['followers'] = (int) str_replace(',', '', $fm[1]);
        }
        if (preg_match('/([\d,]+)\s*Following/i', $desc, $fm)) {
            $result['following'] = (int) str_replace(',', '', $fm[1]);
        }
        if (preg_match('/([\d,]+)\s*Posts/i', $desc, $fm)) {
            $result['posts_count'] = (int) str_replace(',', '', $fm[1]);
        }
    }
    
    // Extract og:image (profile pic)
    if (preg_match('/<meta\s+property="og:image"\s+content="([^"]+)"/i', $html, $m)) {
        $result['profile_pic'] = html_entity_decode($m[1]);
    }
    
    // Try to extract music-related data from shared_data JSON
    $music_tags = array();
    
    // Look for music mentions in bio
    $music_keywords = array('spotify', 'soundcloud', 'apple music', 'music', 'producer', 
                           'singer', 'rapper', 'dj', 'artist', 'band', 'musician');
    $bio_lower = strtolower($result['bio']);
    foreach ($music_keywords as $kw) {
        if (strpos($bio_lower, $kw) !== false) {
            $music_tags[] = $kw;
        }
    }
    
    // Extract any URLs from bio (Spotify, YouTube, etc.)
    $links = array();
    if (preg_match_all('/https?:\/\/[^\s"<]+/i', $html, $url_matches)) {
        foreach ($url_matches[0] as $found_url) {
            if (strpos($found_url, 'spotify.com') !== false) {
                $links[] = array('platform' => 'spotify', 'url' => $found_url);
            } elseif (strpos($found_url, 'youtube.com') !== false || strpos($found_url, 'youtu.be') !== false) {
                $links[] = array('platform' => 'youtube', 'url' => $found_url);
            } elseif (strpos($found_url, 'soundcloud.com') !== false) {
                $links[] = array('platform' => 'soundcloud', 'url' => $found_url);
            } elseif (strpos($found_url, 'tiktok.com') !== false) {
                $links[] = array('platform' => 'tiktok', 'url' => $found_url);
            } elseif (strpos($found_url, 'linktr.ee') !== false) {
                $links[] = array('platform' => 'linktree', 'url' => $found_url);
            }
        }
    }
    
    $result['music_tags'] = $music_tags;
    $result['external_links'] = $links;
    
    return $result;
}

/**
 * Method 2: Try the ?__a=1&__d=dis JSON endpoint (often blocked)
 */
function scrape_instagram_json($handle) {
    $url = 'https://www.instagram.com/' . $handle . '/?__a=1&__d=dis';
    $json_str = taste_fetch_url($url, array(
        'Accept: application/json',
        'X-Requested-With: XMLHttpRequest',
    ));
    
    if ($json_str === false) {
        return null;
    }
    
    $data = json_decode($json_str, true);
    if (!$data || !isset($data['graphql'])) {
        return null;
    }
    
    $user = isset($data['graphql']['user']) ? $data['graphql']['user'] : null;
    if (!$user) {
        return null;
    }
    
    $result = array(
        'handle' => $handle,
        'name' => isset($user['full_name']) ? $user['full_name'] : '',
        'bio' => isset($user['biography']) ? $user['biography'] : '',
        'profile_pic' => isset($user['profile_pic_url_hd']) ? $user['profile_pic_url_hd'] : '',
        'followers' => isset($user['edge_followed_by']['count']) ? (int) $user['edge_followed_by']['count'] : 0,
        'following' => isset($user['edge_follow']['count']) ? (int) $user['edge_follow']['count'] : 0,
        'posts_count' => isset($user['edge_owner_to_timeline_media']['count']) ? (int) $user['edge_owner_to_timeline_media']['count'] : 0,
        'is_verified' => isset($user['is_verified']) ? $user['is_verified'] : false,
        'category' => isset($user['category_name']) ? $user['category_name'] : '',
    );
    
    // Extract recent posts for music analysis
    $posts = array();
    $music_tags = array();
    
    if (isset($user['edge_owner_to_timeline_media']['edges'])) {
        foreach ($user['edge_owner_to_timeline_media']['edges'] as $edge) {
            $node = $edge['node'];
            $caption = '';
            if (isset($node['edge_media_to_caption']['edges'][0]['node']['text'])) {
                $caption = $node['edge_media_to_caption']['edges'][0]['node']['text'];
            }
            
            $post = array(
                'id' => isset($node['shortcode']) ? $node['shortcode'] : '',
                'type' => isset($node['__typename']) ? $node['__typename'] : '',
                'caption' => $caption,
                'likes' => isset($node['edge_liked_by']['count']) ? (int) $node['edge_liked_by']['count'] : 0,
                'timestamp' => isset($node['taken_at_timestamp']) ? (int) $node['taken_at_timestamp'] : 0,
            );
            
            // Check for music references in caption
            if (preg_match_all('/#(\w+)/i', $caption, $hashtags)) {
                $post['hashtags'] = $hashtags[1];
                foreach ($hashtags[1] as $tag) {
                    $tag_lower = strtolower($tag);
                    if (strpos($tag_lower, 'music') !== false || strpos($tag_lower, 'song') !== false 
                        || strpos($tag_lower, 'artist') !== false || strpos($tag_lower, 'rap') !== false
                        || strpos($tag_lower, 'hiphop') !== false || strpos($tag_lower, 'rock') !== false
                        || strpos($tag_lower, 'edm') !== false || strpos($tag_lower, 'rnb') !== false) {
                        $music_tags[] = $tag;
                    }
                }
            }
            
            // Check for @ mentions (potential artist references)
            if (preg_match_all('/@([a-zA-Z0-9._]+)/i', $caption, $mentions)) {
                $post['mentions'] = $mentions[1];
            }
            
            $posts[] = $post;
        }
    }
    
    $result['recent_posts'] = $posts;
    $result['music_tags'] = array_values(array_unique($music_tags));
    
    return $result;
}


// === Main execution ===

$result = null;

// Try Method 2 first (JSON - more data)
$result = scrape_instagram_json($handle);

// Fallback to Method 1 (OG tags)
if ($result === null) {
    $result = scrape_instagram_og($handle);
}

if ($result !== null) {
    $result['source'] = 'instagram';
    $result['scanned_at'] = date('c');
    echo json_encode($result);
} else {
    header('HTTP/1.1 503 Service Unavailable');
    echo json_encode(array(
        'error' => 'Could not scrape Instagram profile. Instagram may be blocking server-side requests.',
        'handle' => $handle,
        'suggestion' => 'Try the browser-based approach or paste your profile data manually.',
    ));
}
