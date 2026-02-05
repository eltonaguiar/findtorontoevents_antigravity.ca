<?php
/**
 * Thumbnail Proxy API
 * 
 * Tries multiple methods to fetch thumbnails:
 * 1. Multiple YouTube thumbnail resolutions
 * 2. Mobile YouTube URLs
 * 3. Noembed/OEmbed APIs
 * 4. Direct URL validation
 * 5. Fallback placeholder
 * 
 * Usage:
 *   GET /thumbnail_proxy.php?url=https://youtube.com/watch?v=xxx
 *   GET /thumbnail_proxy.php?video_id=xxx&platform=youtube
 *   GET /thumbnail_proxy.php?fix_missing=1&limit=50
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// YouTube thumbnail URL patterns (in order of preference)
function get_youtube_thumbnail_urls($video_id) {
    return array(
        "https://i.ytimg.com/vi/$video_id/maxresdefault.jpg",
        "https://i.ytimg.com/vi/$video_id/sddefault.jpg",
        "https://i.ytimg.com/vi/$video_id/hqdefault.jpg",
        "https://i.ytimg.com/vi/$video_id/mqdefault.jpg",
        "https://i.ytimg.com/vi/$video_id/default.jpg",
        "https://img.youtube.com/vi/$video_id/maxresdefault.jpg",
        "https://img.youtube.com/vi/$video_id/hqdefault.jpg",
        "https://img.youtube.com/vi/$video_id/0.jpg",
        "https://i3.ytimg.com/vi/$video_id/hqdefault.jpg",
        "https://i1.ytimg.com/vi/$video_id/hqdefault.jpg"
    );
}

// Extract video ID from various YouTube URL formats
function extract_youtube_video_id($url) {
    $patterns = array(
        '/youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/',
        '/youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/',
        '/youtube\.com\/v\/([a-zA-Z0-9_-]{11})/',
        '/youtu\.be\/([a-zA-Z0-9_-]{11})/',
        '/youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/',
        '/youtube\.com\/live\/([a-zA-Z0-9_-]{11})/'
    );
    
    foreach ($patterns as $pattern) {
        if (preg_match($pattern, $url, $matches)) {
            return $matches[1];
        }
    }
    return null;
}

// Check if a URL returns a valid image (not 404 or placeholder)
function check_thumbnail_url($url, $timeout = 5) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_NOBODY, true);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    
    curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $content_type = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    $content_length = curl_getinfo($ch, CURLINFO_CONTENT_LENGTH_DOWNLOAD);
    curl_close($ch);
    
    // Valid if 200 OK and is an image with reasonable size
    // YouTube placeholder images are typically very small (< 1KB)
    if ($http_code == 200) {
        if (strpos($content_type, 'image') !== false) {
            // Filter out YouTube's gray placeholder (usually ~1KB)
            if ($content_length > 2000 || $content_length == -1) {
                return true;
            }
        }
    }
    return false;
}

// Try OEmbed API for thumbnail
function get_oembed_thumbnail($url) {
    $oembed_endpoints = array(
        "https://noembed.com/embed?url=" . urlencode($url),
        "https://www.youtube.com/oembed?url=" . urlencode($url) . "&format=json"
    );
    
    foreach ($oembed_endpoints as $endpoint) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (compatible; ThumbnailBot/1.0)');
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($http_code == 200 && $response) {
            $data = json_decode($response, true);
            if (isset($data['thumbnail_url']) && !empty($data['thumbnail_url'])) {
                return $data['thumbnail_url'];
            }
        }
    }
    return null;
}

// Try to get thumbnail from Google News article
function get_news_thumbnail($url) {
    // For news.google.com URLs, try to extract the original article thumbnail
    if (strpos($url, 'news.google.com') !== false) {
        // News thumbnails are harder to get - return a news icon placeholder
        return null;
    }
    
    // Try fetching the page and extracting og:image
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (compatible; Googlebot/2.1)');
    
    $html = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code == 200 && $html) {
        // Try og:image
        if (preg_match('/<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']/', $html, $matches)) {
            return $matches[1];
        }
        if (preg_match('/<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']/', $html, $matches)) {
            return $matches[1];
        }
        // Try twitter:image
        if (preg_match('/<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']/', $html, $matches)) {
            return $matches[1];
        }
    }
    return null;
}

// Main thumbnail resolution function
function resolve_thumbnail($url, $platform = null) {
    $result = array(
        'original_url' => $url,
        'thumbnail_url' => null,
        'method' => null,
        'attempts' => array()
    );
    
    // Detect platform if not specified
    if (!$platform) {
        if (strpos($url, 'youtube.com') !== false || strpos($url, 'youtu.be') !== false) {
            $platform = 'youtube';
        } elseif (strpos($url, 'news.google.com') !== false) {
            $platform = 'news';
        } elseif (strpos($url, 'tiktok.com') !== false) {
            $platform = 'tiktok';
        } elseif (strpos($url, 'twitter.com') !== false || strpos($url, 'x.com') !== false) {
            $platform = 'twitter';
        } elseif (strpos($url, 'instagram.com') !== false) {
            $platform = 'instagram';
        }
    }
    
    // YouTube-specific handling
    if ($platform === 'youtube') {
        $video_id = extract_youtube_video_id($url);
        if ($video_id) {
            $thumbnail_urls = get_youtube_thumbnail_urls($video_id);
            
            foreach ($thumbnail_urls as $thumb_url) {
                $result['attempts'][] = array('url' => $thumb_url, 'method' => 'youtube_direct');
                if (check_thumbnail_url($thumb_url)) {
                    $result['thumbnail_url'] = $thumb_url;
                    $result['method'] = 'youtube_direct';
                    $result['video_id'] = $video_id;
                    return $result;
                }
            }
            
            // Try OEmbed as fallback
            $oembed_thumb = get_oembed_thumbnail($url);
            $result['attempts'][] = array('url' => $oembed_thumb, 'method' => 'oembed');
            if ($oembed_thumb && check_thumbnail_url($oembed_thumb)) {
                $result['thumbnail_url'] = $oembed_thumb;
                $result['method'] = 'oembed';
                return $result;
            }
            
            // Last resort: return hqdefault even if we couldn't verify
            $result['thumbnail_url'] = "https://i.ytimg.com/vi/$video_id/hqdefault.jpg";
            $result['method'] = 'youtube_fallback';
            return $result;
        }
    }
    
    // News article handling
    if ($platform === 'news' || strpos($url, 'news.google.com') !== false) {
        $news_thumb = get_news_thumbnail($url);
        $result['attempts'][] = array('url' => $news_thumb, 'method' => 'news_og_image');
        if ($news_thumb && check_thumbnail_url($news_thumb)) {
            $result['thumbnail_url'] = $news_thumb;
            $result['method'] = 'news_og_image';
            return $result;
        }
        // News items often don't have accessible thumbnails
        $result['method'] = 'news_unavailable';
        return $result;
    }
    
    // TikTok - try OEmbed
    if ($platform === 'tiktok') {
        $tiktok_oembed = "https://www.tiktok.com/oembed?url=" . urlencode($url);
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $tiktok_oembed);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $response = curl_exec($ch);
        curl_close($ch);
        
        if ($response) {
            $data = json_decode($response, true);
            if (isset($data['thumbnail_url'])) {
                $result['thumbnail_url'] = $data['thumbnail_url'];
                $result['method'] = 'tiktok_oembed';
                return $result;
            }
        }
    }
    
    // Generic: try fetching og:image from the URL
    $og_thumb = get_news_thumbnail($url);
    if ($og_thumb && check_thumbnail_url($og_thumb)) {
        $result['thumbnail_url'] = $og_thumb;
        $result['method'] = 'og_image';
        return $result;
    }
    
    return $result;
}

// Handle batch fixing of missing thumbnails
function fix_missing_thumbnails($limit = 50) {
    // Try multiple db_connect paths
    $db_paths = array(
        dirname(__FILE__) . '/db_connect.php',
        dirname(__FILE__) . '/../public/api/db_connect.php',
        dirname(dirname(__FILE__)) . '/public/api/db_connect.php'
    );
    
    foreach ($db_paths as $path) {
        if (file_exists($path)) {
            require_once $path;
            break;
        }
    }
    
    global $conn;
    if (!isset($conn) || !$conn) {
        return array('error' => 'Database not available');
    }
    
    // Find items with missing or potentially broken thumbnails
    $sql = "SELECT id, content_url, platform, thumbnail_url 
            FROM creator_mentions 
            WHERE thumbnail_url IS NULL 
               OR thumbnail_url = '' 
               OR thumbnail_url LIKE '%placeholder%'
            ORDER BY posted_at DESC 
            LIMIT " . intval($limit);
    
    $result = $conn->query($sql);
    if (!$result) {
        return array('error' => 'Query failed: ' . $conn->error);
    }
    
    $fixed = array();
    $failed = array();
    
    while ($row = $result->fetch_assoc()) {
        $thumb_result = resolve_thumbnail($row['content_url'], $row['platform']);
        
        if ($thumb_result['thumbnail_url']) {
            // Update the database
            $new_thumb = $conn->real_escape_string($thumb_result['thumbnail_url']);
            $update_sql = "UPDATE creator_mentions SET thumbnail_url = '$new_thumb' WHERE id = " . intval($row['id']);
            $conn->query($update_sql);
            
            $fixed[] = array(
                'id' => $row['id'],
                'url' => $row['content_url'],
                'new_thumbnail' => $thumb_result['thumbnail_url'],
                'method' => $thumb_result['method']
            );
        } else {
            $failed[] = array(
                'id' => $row['id'],
                'url' => $row['content_url'],
                'reason' => ($thumb_result['method'] ? $thumb_result['method'] : 'no_method_succeeded')
            );
        }
    }
    
    return array(
        'fixed_count' => count($fixed),
        'failed_count' => count($failed),
        'fixed' => $fixed,
        'failed' => $failed
    );
}

// Main request handling
$action = isset($_GET['action']) ? $_GET['action'] : 'resolve';

if ($action === 'fix_missing' || isset($_GET['fix_missing'])) {
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    echo json_encode(fix_missing_thumbnails($limit));
    exit;
}

// Single URL resolution
$url = isset($_GET['url']) ? $_GET['url'] : null;
$video_id = isset($_GET['video_id']) ? $_GET['video_id'] : null;
$platform = isset($_GET['platform']) ? $_GET['platform'] : null;

if ($video_id && $platform === 'youtube') {
    $url = "https://www.youtube.com/watch?v=" . $video_id;
}

if (!$url) {
    echo json_encode(array(
        'error' => 'Missing URL parameter',
        'usage' => array(
            'single' => '/thumbnail_proxy.php?url=https://youtube.com/watch?v=xxx',
            'batch_fix' => '/thumbnail_proxy.php?fix_missing=1&limit=50'
        )
    ));
    exit;
}

$result = resolve_thumbnail($url, $platform);
echo json_encode($result);
?>
