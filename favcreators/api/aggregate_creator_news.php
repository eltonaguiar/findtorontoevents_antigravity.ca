<?php
// Aggregate creator news from multiple sources
// Searches for content ABOUT creators across Google News, YouTube, etc.
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(300);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

$results = array(
    'success' => true,
    'creators_processed' => 0,
    'items_added' => 0,
    'errors' => array(),
    'details' => array()
);

try {
    // Get creators with 50K+ followers to aggregate news for
    // Exclude starfireara (data is incorrect)
    $sql = "SELECT id, name, follower_count 
            FROM creators 
            WHERE follower_count >= 50000 
            AND LOWER(TRIM(name)) != 'starfireara'
            ORDER BY follower_count DESC 
            LIMIT 5";

    $creators_result = $conn->query($sql);

    if (!$creators_result) {
        throw new Exception("Failed to fetch creators: " . $conn->error);
    }

    while ($creator = $creators_result->fetch_assoc()) {
        $creator_id = $creator['id'];
        $creator_name = $creator['name'];

        $results['creators_processed']++;
        $items_found = 0;

        // 1. Search Google News RSS
        $news_items = fetch_google_news($creator_name);
        foreach ($news_items as $item) {
            if (insert_creator_mention($conn, $creator_id, $item)) {
                $items_found++;
                $results['items_added']++;
            }
        }

        // 2. Search YouTube (disabled for now - requires API key or complex scraping)
        // $youtube_items = fetch_youtube_search($creator_name);
        // foreach ($youtube_items as $item) {
        //     if (insert_creator_mention($conn, $creator_id, $item)) {
        //         $items_found++;
        //         $results['items_added']++;
        //     }
        // }

        $results['details'][] = array(
            'name' => $creator_name,
            'items_found' => $items_found
        );
    }

    $results['message'] = "Aggregated content for {$results['creators_processed']} creators";
    $results['timestamp'] = date('Y-m-d H:i:s');

} catch (Exception $e) {
    $results['success'] = false;
    $results['errors'][] = $e->getMessage();
}

// Output results immediately
echo json_encode($results);

if (isset($conn)) {
    $conn->close();
}

// ============================================================================
// Helper Functions
// ============================================================================

function fetch_google_news($creator_name)
{
    $items = array();
    $error_msg = '';

    // Define creator-specific exclusion filters
    // Keys are creator names (lowercase), values are arrays of terms to exclude
    $exclusion_filters = array(
        'ninja' => array('turtle', 'turtles', 'mutant', 'teenage', 'tmnt', 'splinter', 'shredder', 'donatello', 'leonardo', 'raphael', 'michelangelo')
    );

    try {
        $search_query = urlencode($creator_name . " streamer OR " . $creator_name . " twitch OR " . $creator_name . " youtube");
        $rss_url = "https://news.google.com/rss/search?q=$search_query&hl=en-US&gl=US&ceid=US:en";

        $context = stream_context_create(array(
            'http' => array(
                'timeout' => 15,
                'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        ));

        $rss_content = @file_get_contents($rss_url, false, $context);

        if ($rss_content) {
            $xml = @simplexml_load_string($rss_content);

            if ($xml && isset($xml->channel->item)) {
                $count = 0;
                foreach ($xml->channel->item as $rss_item) {
                    if ($count >= 3)
                        break; // Limit to 3 items per creator

                    // Get title and description for filtering
                    $title = (string) $rss_item->title;
                    $description = strip_tags((string) $rss_item->description);
                    $title_lower = strtolower($title);
                    $desc_lower = strtolower($description);

                    // Check if this creator has exclusion filters
                    $creator_name_lower = strtolower(trim($creator_name));
                    if (isset($exclusion_filters[$creator_name_lower])) {
                        $should_exclude = false;
                        foreach ($exclusion_filters[$creator_name_lower] as $exclude_term) {
                            if (strpos($title_lower, $exclude_term) !== false ||
                                strpos($desc_lower, $exclude_term) !== false) {
                                $should_exclude = true;
                                break;
                            }
                        }
                        if ($should_exclude) {
                            continue; // Skip this item
                        }
                    }

                    // Parse publication date with better fallback logic
                    $pub_date = (string) $rss_item->pubDate;
                    $timestamp = strtotime($pub_date);

                    // If strtotime fails or returns future date, use better fallback
                    if ($timestamp === false || $timestamp === -1 || $timestamp > time()) {
                        // Try alternative date format
                        $timestamp = @strtotime(str_replace(',', '', $pub_date));

                        // If still invalid, use 1 day ago (better than current time)
                        if ($timestamp === false || $timestamp === -1 || $timestamp > time()) {
                            $timestamp = time() - 86400; // 1 day ago as fallback
                        }
                    }

                    // Extract thumbnail from media:content or enclosure
                    $thumbnail_url = '';

                    // Try media:content (Google News often uses this)
                    if (isset($rss_item->children('media', true)->content)) {
                        $media_content = $rss_item->children('media', true)->content;
                        if (isset($media_content->attributes()->url)) {
                            $thumbnail_url = (string) $media_content->attributes()->url;
                        }
                    }

                    // Try media:thumbnail
                    if (empty($thumbnail_url) && isset($rss_item->children('media', true)->thumbnail)) {
                        $media_thumb = $rss_item->children('media', true)->thumbnail;
                        if (isset($media_thumb->attributes()->url)) {
                            $thumbnail_url = (string) $media_thumb->attributes()->url;
                        }
                    }

                    // Try enclosure tag
                    if (empty($thumbnail_url) && isset($rss_item->enclosure)) {
                        $enclosure = $rss_item->enclosure;
                        if (isset($enclosure->attributes()->url)) {
                            $enc_url = (string) $enclosure->attributes()->url;
                            // Only use if it's an image
                            if (isset($enclosure->attributes()->type)) {
                                $type = (string) $enclosure->attributes()->type;
                                if (strpos($type, 'image/') === 0) {
                                    $thumbnail_url = $enc_url;
                                }
                            }
                        }
                    }

                    // If no thumbnail from RSS, scrape article for Open Graph image
                    if (empty($thumbnail_url)) {
                        $article_url = (string) $rss_item->link;
                        $thumbnail_url = scrape_og_image($article_url);
                    }

                    $items[] = array(
                        'platform' => 'news',
                        'content_type' => 'article',
                        'content_url' => (string) $rss_item->link,
                        'title' => $title,
                        'description' => $description,
                        'thumbnail_url' => $thumbnail_url,
                        'author' => 'Google News',
                        'engagement_count' => 0,
                        'posted_at' => $timestamp
                    );

                    $count++;
                }
            } else {
                $error_msg = 'XML parse failed or no items';
            }
        } else {
            $error_msg = 'Failed to fetch RSS';
        }
    } catch (Exception $e) {
        $error_msg = $e->getMessage();
    }

    return $items;
}

function fetch_youtube_search($creator_name)
{
    $items = array();

    try {
        // YouTube RSS search (limited but doesn't require API key)
        $search_query = urlencode($creator_name);

        // Try to fetch from YouTube search results page and parse
        // Note: This is a simplified version. A production version would use YouTube Data API
        $search_url = "https://www.youtube.com/results?search_query=" . urlencode($creator_name . " news") . "&sp=CAI%253D";

        $context = stream_context_create(array(
            'http' => array(
                'timeout' => 15,
                'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        ));

        $html = @file_get_contents($search_url, false, $context);

        if ($html) {
            // Parse ytInitialData from the page
            if (preg_match('/var ytInitialData = ({.*?});/', $html, $matches)) {
                $data = json_decode($matches[1], true);

                if (isset($data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'])) {
                    $contents = $data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'];

                    $count = 0;
                    foreach ($contents as $section) {
                        if (!isset($section['itemSectionRenderer']['contents']))
                            continue;

                        foreach ($section['itemSectionRenderer']['contents'] as $item) {
                            if ($count >= 2)
                                break 2; // Limit to 2 YouTube items

                            if (isset($item['videoRenderer'])) {
                                $video = $item['videoRenderer'];
                                $video_id = $video['videoId'];

                                $items[] = array(
                                    'platform' => 'youtube',
                                    'content_type' => 'video',
                                    'content_url' => "https://www.youtube.com/watch?v=$video_id",
                                    'title' => (isset($video['title']['runs'][0]['text']) ? $video['title']['runs'][0]['text'] : 'YouTube Video'),
                                    'description' => '',
                                    'thumbnail_url' => (isset($video['thumbnail']['thumbnails'][0]['url']) ? $video['thumbnail']['thumbnails'][0]['url'] : ''),
                                    'author' => 'YouTube',
                                    'engagement_count' => 0,
                                    'posted_at' => time()
                                );

                                $count++;
                            }
                        }
                    }
                }
            }
        }
    } catch (Exception $e) {
        // Silently fail
    }

    return $items;
}

function scrape_og_image($url)
{
    // Scrape Open Graph image from article URL
    try {
        $context = stream_context_create(array(
            'http' => array(
                'timeout' => 5,
                'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        ));

        $html = @file_get_contents($url, false, $context);

        if ($html) {
            // Look for og:image meta tag
            if (preg_match('/<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?:\/\/[^"\']+)["\']/i', $html, $matches)) {
                return $matches[1];
            }

            // Try alternative format
            if (preg_match('/<meta[^>]+content=["\'](https?:\/\/[^"\']+)["\'][^>]+property=["\']og:image["\']/i', $html, $matches)) {
                return $matches[1];
            }

            // Try twitter:image as fallback
            if (preg_match('/<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](https?:\/\/[^"\']+)["\']/i', $html, $matches)) {
                return $matches[1];
            }
        }
    } catch (Exception $e) {
        // Silently fail
    }

    return ''; // No image found
}

function insert_creator_mention($conn, $creator_id, $data)
{
    // Check if this URL already exists for this creator
    $check_sql = "SELECT id FROM creator_mentions 
                  WHERE creator_id = '" . $conn->real_escape_string($creator_id) . "' 
                  AND content_url = '" . $conn->real_escape_string($data['content_url']) . "'";

    $check_result = $conn->query($check_sql);

    if ($check_result && $check_result->num_rows > 0) {
        return false; // Already exists
    }

    // Insert new mention
    $insert_sql = "INSERT INTO creator_mentions 
                   (creator_id, platform, content_type, content_url, title, description, thumbnail_url, author, engagement_count, posted_at) 
                   VALUES (
                       '" . $conn->real_escape_string($creator_id) . "',
                       '" . $conn->real_escape_string($data['platform']) . "',
                       '" . $conn->real_escape_string($data['content_type']) . "',
                       '" . $conn->real_escape_string($data['content_url']) . "',
                       '" . $conn->real_escape_string(substr($data['title'], 0, 500)) . "',
                       '" . $conn->real_escape_string(substr($data['description'], 0, 1000)) . "',
                       '" . $conn->real_escape_string($data['thumbnail_url']) . "',
                       '" . $conn->real_escape_string($data['author']) . "',
                       " . intval($data['engagement_count']) . ",
                       " . intval($data['posted_at']) . "
                   )";

    return $conn->query($insert_sql);
}
?>