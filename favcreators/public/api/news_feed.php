<?php
/**
 * News Feed Aggregator API
 * Fetches, caches, and serves RSS news from 20+ sources across 4 categories.
 *
 * Actions:
 *   ?action=get       — Read articles (cache + DB), filtered by category/source/search
 *   ?action=fetch     — Force re-fetch feeds, store to DB
 *   ?action=sources   — List all configured sources with status
 *
 * Params:
 *   &category=toronto|canada|us|world|all  (default: all)
 *   &source=cbc_toronto|blogto|...         (filter by source key)
 *   &search=keyword                        (search titles/descriptions)
 *   &page=1                                (pagination)
 *   &per_page=20                           (items per page, max 50)
 *
 * PHP 5.2 compatible. Separate DB: ejaguiar1_news
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once(dirname(__FILE__) . '/news_feed_schema.php');

// ────────────────────────────────────────────────────────────
//  Source Configuration
// ────────────────────────────────────────────────────────────

function _nf_get_sources() {
    return array(
        // ── Toronto ──
        array('name' => 'BlogTO',               'key' => 'blogto',            'url' => 'https://feeds.feedburner.com/blogto',                                          'category' => 'toronto', 'domain' => 'blogto.com'),
        array('name' => 'Narcity Toronto',       'key' => 'narcity_toronto',   'url' => 'https://www.narcity.com/feeds/toronto.rss',                                    'category' => 'toronto', 'domain' => 'narcity.com'),
        array('name' => 'CBC Toronto',           'key' => 'cbc_toronto',       'url' => 'https://www.cbc.ca/webfeed/rss/rss-canada-toronto',                            'category' => 'toronto', 'domain' => 'cbc.ca'),
        array('name' => 'Global News Toronto',   'key' => 'global_toronto',    'url' => 'https://globalnews.ca/toronto/feed/',                                          'category' => 'toronto', 'domain' => 'globalnews.ca'),
        array('name' => 'NOW Toronto',           'key' => 'now_toronto',       'url' => 'https://nowtoronto.com/feed/',                                                 'category' => 'toronto', 'domain' => 'nowtoronto.com'),
        array('name' => 'Toronto Sun',           'key' => 'toronto_sun',       'url' => 'https://torontosun.com/category/news/feed',                                    'category' => 'toronto', 'domain' => 'torontosun.com'),
        array('name' => 'Daily Hive Toronto',    'key' => 'dailyhive_toronto', 'url' => 'https://dailyhive.com/feed/toronto',                                           'category' => 'toronto', 'domain' => 'dailyhive.com'),
        array('name' => 'Streets of Toronto',    'key' => 'streets_toronto',   'url' => 'https://streetsoftoronto.com/feed/',                                           'category' => 'toronto', 'domain' => 'streetsoftoronto.com'),

        // ── Canadian ──
        array('name' => 'CBC Canada',            'key' => 'cbc_canada',        'url' => 'https://www.cbc.ca/webfeed/rss/rss-canada',                                    'category' => 'canada',  'domain' => 'cbc.ca'),
        array('name' => 'CBC Politics',          'key' => 'cbc_politics',      'url' => 'https://www.cbc.ca/webfeed/rss/rss-politics',                                  'category' => 'canada',  'domain' => 'cbc.ca'),
        array('name' => 'Global News Canada',    'key' => 'global_canada',     'url' => 'https://globalnews.ca/feed/',                                                  'category' => 'canada',  'domain' => 'globalnews.ca'),
        array('name' => 'National Post',         'key' => 'national_post',     'url' => 'https://nationalpost.com/feed/',                                               'category' => 'canada',  'domain' => 'nationalpost.com'),
        array('name' => 'CBC Business',          'key' => 'cbc_business',      'url' => 'https://www.cbc.ca/webfeed/rss/rss-business',                                  'category' => 'canada',  'domain' => 'cbc.ca'),
        array('name' => 'CBC Top Stories',       'key' => 'cbc_top',           'url' => 'https://www.cbc.ca/webfeed/rss/rss-topstories',                                'category' => 'canada',  'domain' => 'cbc.ca'),

        // ── US ──
        array('name' => 'CNN',                   'key' => 'cnn',              'url' => 'http://rss.cnn.com/rss/cnn_topstories.rss',                                     'category' => 'us',      'domain' => 'cnn.com'),
        array('name' => 'NPR',                   'key' => 'npr',              'url' => 'https://feeds.npr.org/1001/rss.xml',                                            'category' => 'us',      'domain' => 'npr.org'),
        array('name' => 'NBC News',              'key' => 'nbc_news',         'url' => 'https://feeds.nbcnews.com/nbcnews/public/news',                                 'category' => 'us',      'domain' => 'nbcnews.com'),

        // ── US ── (cont.)
        array('name' => 'Dexerto',               'key' => 'dexerto',          'url' => 'https://www.dexerto.com/feed/',                                                  'category' => 'us',      'domain' => 'dexerto.com'),

        // ── World ──
        array('name' => 'BBC World',             'key' => 'bbc_world',        'url' => 'https://feeds.bbci.co.uk/news/world/rss.xml',                                   'category' => 'world',   'domain' => 'bbc.co.uk'),
        array('name' => 'Al Jazeera',            'key' => 'aljazeera',        'url' => 'https://www.aljazeera.com/xml/rss/all.xml',                                     'category' => 'world',   'domain' => 'aljazeera.com'),
        array('name' => 'The Guardian World',    'key' => 'guardian_world',   'url' => 'https://www.theguardian.com/world/rss',                                          'category' => 'world',   'domain' => 'theguardian.com')
    );
}

// ────────────────────────────────────────────────────────────
//  HTTP Fetch
// ────────────────────────────────────────────────────────────

function _nf_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 400 && $body !== false) {
            return $body;
        }
        return false;
    }

    $ctx = stream_context_create(array(
        'http' => array(
            'timeout' => 15,
            'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'follow_location' => true,
            'max_redirects' => 3
        ),
        'ssl' => array(
            'verify_peer' => false,
            'verify_peer_name' => false
        )
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body !== false) ? $body : false;
}

// ────────────────────────────────────────────────────────────
//  File Cache
// ────────────────────────────────────────────────────────────

function _nf_cache_path($source_key) {
    return sys_get_temp_dir() . '/fte_news_' . $source_key . '.json';
}

function _nf_read_cache($source_key, $ttl) {
    $path = _nf_cache_path($source_key);
    if (!file_exists($path)) return false;
    $age = time() - filemtime($path);
    if ($age > $ttl) return false;
    $raw = @file_get_contents($path);
    if ($raw === false) return false;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : false;
}

function _nf_read_stale_cache($source_key, $max_age) {
    $path = _nf_cache_path($source_key);
    if (!file_exists($path)) return false;
    $age = time() - filemtime($path);
    if ($age > $max_age) return false;
    $raw = @file_get_contents($path);
    if ($raw === false) return false;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : false;
}

function _nf_write_cache($source_key, $articles) {
    $path = _nf_cache_path($source_key);
    @file_put_contents($path, json_encode($articles));
}

// ────────────────────────────────────────────────────────────
//  RSS Parser
// ────────────────────────────────────────────────────────────

function _nf_strip_cdata($str) {
    $str = preg_replace('/<!\[CDATA\[/', '', $str);
    $str = preg_replace('/\]\]>/', '', $str);
    return trim($str);
}

function _nf_extract_image($item_xml) {
    // media:thumbnail
    if (preg_match('/<media:thumbnail[^>]+url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    // media:content with image
    if (preg_match('/<media:content[^>]+url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        if (preg_match('/\.(jpg|jpeg|png|gif|webp)/i', $m[1]) || preg_match('/medium=["\']image["\']/i', $item_xml)) {
            return $m[1];
        }
    }
    // enclosure with image type
    if (preg_match('/<enclosure[^>]+url=["\']([^"\']+)["\'][^>]*type=["\']image/i', $item_xml, $m)) {
        return $m[1];
    }
    if (preg_match('/<enclosure[^>]+type=["\']image[^"\']*["\'][^>]*url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    // img tag in description
    if (preg_match('/<img[^>]+src=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    return '';
}

function _nf_parse_rss($xml_string, $source) {
    $articles = array();

    // Try simplexml first
    $parsed = _nf_parse_rss_simplexml($xml_string, $source);
    if ($parsed !== false && count($parsed) > 0) {
        return $parsed;
    }

    // Fallback: regex parsing
    if (!preg_match_all('/<item[^>]*>(.*?)<\/item>/si', $xml_string, $items)) {
        // Try <entry> for Atom feeds
        if (!preg_match_all('/<entry[^>]*>(.*?)<\/entry>/si', $xml_string, $items)) {
            return $articles;
        }
    }

    $logo = 'https://www.google.com/s2/favicons?domain=' . $source['domain'] . '&sz=32';

    foreach ($items[1] as $item_xml) {
        // Title
        $title = '';
        if (preg_match('/<title[^>]*>(.*?)<\/title>/si', $item_xml, $m)) {
            $title = _nf_strip_cdata($m[1]);
            $title = strip_tags($title);
            $title = html_entity_decode($title, ENT_QUOTES, 'UTF-8');
        }
        if (empty($title)) continue;

        // Link
        $link = '';
        if (preg_match('/<link[^>]*>(.*?)<\/link>/si', $item_xml, $m)) {
            $link = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($link) && preg_match('/<link[^>]+href=["\']([^"\']+)["\']/i', $item_xml, $m)) {
            $link = trim($m[1]);
        }
        if (empty($link) && preg_match('/<guid[^>]*>(.*?)<\/guid>/si', $item_xml, $m)) {
            $guid = trim(_nf_strip_cdata($m[1]));
            if (strpos($guid, 'http') === 0) $link = $guid;
        }
        if (empty($link)) continue;

        // Date
        $pub_date = '';
        if (preg_match('/<pubDate[^>]*>(.*?)<\/pubDate>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<dc:date[^>]*>(.*?)<\/dc:date>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<published[^>]*>(.*?)<\/published>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<updated[^>]*>(.*?)<\/updated>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        $ts = !empty($pub_date) ? strtotime($pub_date) : time();
        if ($ts === false || $ts <= 0) $ts = time();

        // Description
        $desc = '';
        if (preg_match('/<description[^>]*>(.*?)<\/description>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        if (empty($desc) && preg_match('/<content:encoded[^>]*>(.*?)<\/content:encoded>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        if (empty($desc) && preg_match('/<summary[^>]*>(.*?)<\/summary>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        $desc = strip_tags($desc);
        $desc = html_entity_decode($desc, ENT_QUOTES, 'UTF-8');
        $desc = preg_replace('/\s+/', ' ', $desc);
        if (strlen($desc) > 300) {
            $desc = substr($desc, 0, 297) . '...';
        }

        // Image
        $image = _nf_extract_image($item_xml);

        $articles[] = array(
            'title'       => $title,
            'link'        => $link,
            'source_name' => $source['name'],
            'source_key'  => $source['key'],
            'source_logo' => $logo,
            'category'    => $source['category'],
            'pub_date'    => date('Y-m-d H:i:s', $ts),
            'pub_ts'      => $ts,
            'description' => $desc,
            'image_url'   => $image
        );
    }

    return $articles;
}

function _nf_parse_rss_simplexml($xml_string, $source) {
    if (!function_exists('simplexml_load_string')) return false;

    libxml_use_internal_errors(true);
    $xml = @simplexml_load_string($xml_string);
    if ($xml === false) return false;

    $articles = array();
    $logo = 'https://www.google.com/s2/favicons?domain=' . $source['domain'] . '&sz=32';

    // RSS 2.0 format
    $items_list = array();
    if (isset($xml->channel->item)) {
        foreach ($xml->channel->item as $item) {
            $items_list[] = $item;
        }
    }
    // Atom format
    if (count($items_list) === 0 && isset($xml->entry)) {
        foreach ($xml->entry as $item) {
            $items_list[] = $item;
        }
    }

    if (count($items_list) === 0) return false;

    $ns = $xml->getNamespaces(true);
    $media_ns = isset($ns['media']) ? $ns['media'] : 'http://search.yahoo.com/mrss/';

    foreach ($items_list as $item) {
        $title = trim((string)$item->title);
        if (empty($title)) continue;
        $title = html_entity_decode($title, ENT_QUOTES, 'UTF-8');

        // Link
        $link = '';
        if (isset($item->link)) {
            $link_val = (string)$item->link;
            if (!empty($link_val)) {
                $link = $link_val;
            }
        }
        if (empty($link) && isset($item->link['href'])) {
            $link = (string)$item->link['href'];
        }
        if (empty($link) && isset($item->link)) {
            $attrs = $item->link->attributes();
            if (isset($attrs['href'])) {
                $link = (string)$attrs['href'];
            }
        }
        if (empty($link) && isset($item->guid)) {
            $guid = (string)$item->guid;
            if (strpos($guid, 'http') === 0) $link = $guid;
        }
        if (empty($link)) continue;

        // Date
        $pub_date = '';
        if (isset($item->pubDate)) $pub_date = (string)$item->pubDate;
        if (empty($pub_date) && isset($item->published)) $pub_date = (string)$item->published;
        if (empty($pub_date) && isset($item->updated)) $pub_date = (string)$item->updated;
        $ts = !empty($pub_date) ? strtotime($pub_date) : time();
        if ($ts === false || $ts <= 0) $ts = time();

        // Description
        $desc = '';
        if (isset($item->description)) $desc = strip_tags((string)$item->description);
        if (empty($desc) && isset($item->summary)) $desc = strip_tags((string)$item->summary);
        $desc = html_entity_decode(trim($desc), ENT_QUOTES, 'UTF-8');
        $desc = preg_replace('/\s+/', ' ', $desc);
        if (strlen($desc) > 300) $desc = substr($desc, 0, 297) . '...';

        // Image via media namespace
        $image = '';
        $media = $item->children($media_ns);
        if (isset($media->thumbnail)) {
            $attrs = $media->thumbnail->attributes();
            if (isset($attrs['url'])) $image = (string)$attrs['url'];
        }
        if (empty($image) && isset($media->content)) {
            $attrs = $media->content->attributes();
            if (isset($attrs['url'])) $image = (string)$attrs['url'];
        }
        if (empty($image) && isset($item->enclosure)) {
            $enc_attrs = $item->enclosure->attributes();
            $enc_type = isset($enc_attrs['type']) ? (string)$enc_attrs['type'] : '';
            if (strpos($enc_type, 'image') !== false && isset($enc_attrs['url'])) {
                $image = (string)$enc_attrs['url'];
            }
        }
        // Fallback: img in raw description
        if (empty($image) && isset($item->description)) {
            $raw_desc = (string)$item->description;
            if (preg_match('/<img[^>]+src=["\']([^"\']+)["\']/i', $raw_desc, $m2)) {
                $image = $m2[1];
            }
        }

        $articles[] = array(
            'title'       => $title,
            'link'        => $link,
            'source_name' => $source['name'],
            'source_key'  => $source['key'],
            'source_logo' => $logo,
            'category'    => $source['category'],
            'pub_date'    => date('Y-m-d H:i:s', $ts),
            'pub_ts'      => $ts,
            'description' => $desc,
            'image_url'   => $image
        );
    }

    return (count($articles) > 0) ? $articles : false;
}

// ────────────────────────────────────────────────────────────
//  Time Ago
// ────────────────────────────────────────────────────────────

function _nf_time_ago($datetime_str) {
    $ts = strtotime($datetime_str);
    if ($ts === false) return '';
    $diff = time() - $ts;
    if ($diff < 0) return 'just now';
    if ($diff < 60) return 'just now';
    if ($diff < 3600) return floor($diff / 60) . 'm ago';
    if ($diff < 86400) return floor($diff / 3600) . 'h ago';
    if ($diff < 172800) return 'yesterday';
    if ($diff < 604800) return floor($diff / 86400) . 'd ago';
    return date('M j', $ts);
}

// ────────────────────────────────────────────────────────────
//  Fetch Single Source
// ────────────────────────────────────────────────────────────

function _nf_fetch_single($source) {
    $cache_ttl = 1800; // 30 minutes
    $stale_ttl = 7200; // 2 hours stale fallback

    // Check fresh cache
    $cached = _nf_read_cache($source['key'], $cache_ttl);
    if ($cached !== false) {
        return $cached;
    }

    // Fetch RSS
    $xml_string = _nf_http_get($source['url']);
    if ($xml_string === false || empty($xml_string)) {
        // Try stale cache
        $stale = _nf_read_stale_cache($source['key'], $stale_ttl);
        if ($stale !== false) return $stale;
        return array();
    }

    // Parse
    $articles = _nf_parse_rss($xml_string, $source);

    // Cache results (even if empty, to avoid hammering)
    _nf_write_cache($source['key'], $articles);

    return $articles;
}

// ────────────────────────────────────────────────────────────
//  Fetch All Sources
// ────────────────────────────────────────────────────────────

function _nf_fetch_all($category) {
    $sources = _nf_get_sources();
    $all_articles = array();

    foreach ($sources as $src) {
        if ($category !== 'all' && $src['category'] !== $category) continue;
        $articles = _nf_fetch_single($src);
        foreach ($articles as $art) {
            $all_articles[] = $art;
        }
    }

    // Sort by date descending
    usort($all_articles, '_nf_sort_by_date');

    return $all_articles;
}

function _nf_sort_by_date($a, $b) {
    $ta = isset($a['pub_ts']) ? $a['pub_ts'] : 0;
    $tb = isset($b['pub_ts']) ? $b['pub_ts'] : 0;
    if ($ta == $tb) return 0;
    return ($ta > $tb) ? -1 : 1;
}

// ────────────────────────────────────────────────────────────
//  Database Storage
// ────────────────────────────────────────────────────────────

function _nf_store_articles($conn, $articles) {
    if (!$conn || count($articles) === 0) return;

    $now = date('Y-m-d H:i:s');
    $inserted = 0;

    foreach ($articles as $art) {
        $title = $conn->real_escape_string($art['title']);
        $link  = $conn->real_escape_string($art['link']);
        $sname = $conn->real_escape_string($art['source_name']);
        $skey  = $conn->real_escape_string($art['source_key']);
        $slogo = $conn->real_escape_string(isset($art['source_logo']) ? $art['source_logo'] : '');
        $cat   = $conn->real_escape_string($art['category']);
        $pdate = $conn->real_escape_string($art['pub_date']);
        $desc  = $conn->real_escape_string(isset($art['description']) ? $art['description'] : '');
        $img   = $conn->real_escape_string(isset($art['image_url']) ? $art['image_url'] : '');

        $sql = "INSERT INTO news_articles (title, link, source_name, source_key, source_logo, category, pub_date, description, image_url, fetched_at)
                VALUES ('$title', '$link', '$sname', '$skey', '$slogo', '$cat', '$pdate', '$desc', '$img', '$now')
                ON DUPLICATE KEY UPDATE title='$title', description='$desc', image_url='$img', fetched_at='$now'";
        if ($conn->query($sql)) $inserted++;
    }

    return $inserted;
}

function _nf_update_source_status($conn, $source_key, $count, $error) {
    if (!$conn) return;
    $now  = date('Y-m-d H:i:s');
    $skey = $conn->real_escape_string($source_key);
    $err  = $conn->real_escape_string($error);

    $sql = "INSERT INTO news_sources (name, source_key, feed_url, category, last_fetched, article_count, last_error)
            VALUES ('', '$skey', '', '', '$now', $count, '$err')
            ON DUPLICATE KEY UPDATE last_fetched='$now', article_count=$count, last_error='$err'";
    $conn->query($sql);
}

function _nf_get_from_db($conn, $category, $source_filter, $search, $page, $per_page) {
    if (!$conn) return false;

    $where = array();
    if ($category !== 'all') {
        $where[] = "category='" . $conn->real_escape_string($category) . "'";
    }
    if (!empty($source_filter)) {
        $where[] = "source_key='" . $conn->real_escape_string($source_filter) . "'";
    }
    if (!empty($search)) {
        $esc = $conn->real_escape_string($search);
        $where[] = "(title LIKE '%$esc%' OR description LIKE '%$esc%')";
    }

    $where_sql = count($where) > 0 ? ' WHERE ' . implode(' AND ', $where) : '';

    // Count
    $count_res = $conn->query("SELECT COUNT(*) as cnt FROM news_articles" . $where_sql);
    $total = 0;
    if ($count_res) {
        $row = $count_res->fetch_assoc();
        $total = (int)$row['cnt'];
    }

    // Fetch page
    $offset = ($page - 1) * $per_page;
    $sql = "SELECT * FROM news_articles" . $where_sql . " ORDER BY pub_date DESC LIMIT $offset, $per_page";
    $result = $conn->query($sql);

    $articles = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $row['time_ago'] = _nf_time_ago($row['pub_date']);
            $row['pub_ts']   = strtotime($row['pub_date']);
            $articles[] = $row;
        }
    }

    return array('articles' => $articles, 'total' => $total);
}

// ────────────────────────────────────────────────────────────
//  Seed sources table
// ────────────────────────────────────────────────────────────

function _nf_seed_sources($conn) {
    if (!$conn) return;
    $sources = _nf_get_sources();
    foreach ($sources as $src) {
        $name = $conn->real_escape_string($src['name']);
        $key  = $conn->real_escape_string($src['key']);
        $url  = $conn->real_escape_string($src['url']);
        $cat  = $conn->real_escape_string($src['category']);
        $logo = 'https://www.google.com/s2/favicons?domain=' . $conn->real_escape_string($src['domain']) . '&sz=32';
        $conn->query("INSERT IGNORE INTO news_sources (name, source_key, feed_url, category, logo_url, is_active) VALUES ('$name', '$key', '$url', '$cat', '$logo', 1)");
    }
}

// ────────────────────────────────────────────────────────────
//  Action Router
// ────────────────────────────────────────────────────────────

$action   = isset($_GET['action'])   ? strtolower(trim($_GET['action']))   : 'get';
$category = isset($_GET['category']) ? strtolower(trim($_GET['category'])) : 'all';
$source_f = isset($_GET['source'])   ? trim($_GET['source'])               : '';
$search   = isset($_GET['search'])   ? trim($_GET['search'])               : '';
$page     = isset($_GET['page'])     ? max(1, (int)$_GET['page'])          : 1;
$per_page = isset($_GET['per_page']) ? min(50, max(1, (int)$_GET['per_page'])) : 20;

$valid_cats = array('all', 'toronto', 'canada', 'us', 'world');
if (!in_array($category, $valid_cats)) $category = 'all';

// Connect DB (optional — API works without it)
$nf_conn = _nf_db_connect();
if ($nf_conn) {
    _nf_ensure_tables($nf_conn);
}

// ── ACTION: sources ──
if ($action === 'sources') {
    $sources = _nf_get_sources();
    $out = array();
    foreach ($sources as $src) {
        $cache_file = _nf_cache_path($src['key']);
        $last_fetched = file_exists($cache_file) ? date('Y-m-d H:i:s', filemtime($cache_file)) : null;
        $cache_age = file_exists($cache_file) ? (int)((time() - filemtime($cache_file)) / 60) : null;
        $out[] = array(
            'name'          => $src['name'],
            'key'           => $src['key'],
            'category'      => $src['category'],
            'feed_url'      => $src['url'],
            'logo'          => 'https://www.google.com/s2/favicons?domain=' . $src['domain'] . '&sz=32',
            'last_fetched'  => $last_fetched,
            'cache_age_min' => $cache_age
        );
    }
    echo json_encode(array('ok' => true, 'sources' => $out, 'total' => count($out)));
    exit;
}

// ── ACTION: fetch ──
if ($action === 'fetch') {
    $sources = _nf_get_sources();
    $total_articles = 0;
    $source_results = array();

    foreach ($sources as $src) {
        if ($category !== 'all' && $src['category'] !== $category) continue;

        $xml_string = _nf_http_get($src['url']);
        $articles = array();
        $error = '';

        if ($xml_string === false || empty($xml_string)) {
            $error = 'Failed to fetch feed';
        } else {
            $articles = _nf_parse_rss($xml_string, $src);
            if (count($articles) === 0) {
                $error = 'No articles parsed';
            }
        }

        _nf_write_cache($src['key'], $articles);

        if ($nf_conn && count($articles) > 0) {
            _nf_store_articles($nf_conn, $articles);
        }
        if ($nf_conn) {
            _nf_update_source_status($nf_conn, $src['key'], count($articles), $error);
        }

        $source_results[] = array(
            'source' => $src['name'],
            'key'    => $src['key'],
            'count'  => count($articles),
            'error'  => $error
        );
        $total_articles += count($articles);
    }

    echo json_encode(array(
        'ok'             => true,
        'action'         => 'fetch',
        'category'       => $category,
        'total_articles' => $total_articles,
        'sources'        => $source_results,
        'fetched_at'     => date('Y-m-d H:i:s')
    ));
    exit;
}

// ── ACTION: get (default) ──

// Strategy: try DB first (has search/pagination), fallback to file cache aggregation
$db_result = false;
if ($nf_conn) {
    $db_result = _nf_get_from_db($nf_conn, $category, $source_f, $search, $page, $per_page);
}

if ($db_result !== false && $db_result['total'] > 0) {
    // Serve from DB
    echo json_encode(array(
        'ok'         => true,
        'source'     => 'database',
        'category'   => $category,
        'articles'   => $db_result['articles'],
        'total'      => $db_result['total'],
        'page'       => $page,
        'per_page'   => $per_page,
        'fetched_at' => date('Y-m-d H:i:s')
    ));
} else {
    // Fallback: fetch from RSS cache/live
    $all_articles = _nf_fetch_all($category);

    // Store to DB if available
    if ($nf_conn && count($all_articles) > 0) {
        _nf_seed_sources($nf_conn);
        _nf_store_articles($nf_conn, $all_articles);
    }

    // Apply source filter
    if (!empty($source_f)) {
        $filtered = array();
        foreach ($all_articles as $art) {
            if ($art['source_key'] === $source_f) $filtered[] = $art;
        }
        $all_articles = $filtered;
    }

    // Apply search filter
    if (!empty($search)) {
        $filtered = array();
        $search_lower = strtolower($search);
        foreach ($all_articles as $art) {
            if (strpos(strtolower($art['title']), $search_lower) !== false ||
                strpos(strtolower($art['description']), $search_lower) !== false) {
                $filtered[] = $art;
            }
        }
        $all_articles = $filtered;
    }

    $total = count($all_articles);

    // Paginate
    $offset = ($page - 1) * $per_page;
    $page_articles = array_slice($all_articles, $offset, $per_page);

    // Add time_ago
    foreach ($page_articles as $idx => $art) {
        $page_articles[$idx]['time_ago'] = _nf_time_ago($art['pub_date']);
    }

    echo json_encode(array(
        'ok'         => true,
        'source'     => 'rss_cache',
        'category'   => $category,
        'articles'   => $page_articles,
        'total'      => $total,
        'page'       => $page,
        'per_page'   => $per_page,
        'fetched_at' => date('Y-m-d H:i:s')
    ));
}

if ($nf_conn) $nf_conn->close();
