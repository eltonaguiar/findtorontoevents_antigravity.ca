<?php
/**
 * Freestyle Search API — TMDB + YouTube + Multiple Failovers
 * Uses cURL for outbound HTTP (file_get_contents blocked on this host)
 * Compatible with PHP 5.2+
 * Failover chain: Piped → Invidious → Official YT API → Dailymotion API →
 *   Internet Archive → Dailymotion scrape → Vimeo scrape
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

$TMDB_V3_KEY = '6dc4a9654d9748dd817413924088c9d6';
$YOUTUBE_API_KEY = getenv('YOUTUBE_API_KEY');

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$type = isset($_GET['type']) ? $_GET['type'] : 'multi';

if (empty($query)) {
    echo json_encode(array('success' => false, 'error' => 'Search query is required'));
    exit;
}

if ($type === 'youtube') {
    // PRIMARY: YouTube InnerTube API (internal JSON API — no HTML parsing, most reliable)
    $result = searchYouTubeInnerTube($query);
    // Fallback: Scrape YouTube search page with consent cookie bypass
    if (!$result['success']) {
        $result = searchYouTubeScrape($query);
    }
    // Fallback: Piped/Invidious proxies
    if (!$result['success']) {
        $result = searchYouTube($query);
    }
    // Fallback: Dailymotion API (free, no key needed)
    if (!$result['success']) {
        $result = searchDailymotionAPI($query);
    }
    // Fallback: Internet Archive (free, no key)
    if (!$result['success']) {
        $result = searchInternetArchive($query);
    }
} else {
    $result = searchTMDB($query, $type);
}

echo json_encode($result);

function curlGet($url, $timeout = 10) {
    if (!function_exists('curl_init')) {
        return false;
    }
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MovieShows/1.0');
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($httpCode >= 200 && $httpCode < 400) {
        return $response;
    }
    return false;
}

// PRIMARY: YouTube InnerTube API — YouTube's internal JSON API
// No HTML parsing needed, no consent page issues, returns structured JSON
function searchYouTubeInnerTube($query) {
    // This is YouTube's public InnerTube API key (embedded in youtube.com JS)
    $url = 'https://www.youtube.com/youtubei/v1/search?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8';
    $body = json_encode(array(
        'context' => array(
            'client' => array(
                'clientName' => 'WEB',
                'clientVersion' => '2.20240101.00.00',
                'hl' => 'en',
                'gl' => 'US'
            )
        ),
        'query' => $query
    ));

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 12);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Content-Type: application/json',
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin: https://www.youtube.com',
        'Referer: https://www.youtube.com/'
    ));
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if (!$response || $httpCode < 200 || $httpCode >= 400) {
        return array('success' => false, 'error' => 'InnerTube API failed (HTTP ' . $httpCode . ')');
    }

    $jsonData = json_decode($response, true);
    if (!$jsonData) {
        return array('success' => false, 'error' => 'InnerTube JSON parse failed');
    }

    return parseYouTubeSearchData($jsonData, 'youtube_innertube');
}

// Shared parser for YouTube search JSON (works with both InnerTube API and HTML-scraped ytInitialData)
function parseYouTubeSearchData($jsonData, $source) {
    $results = array();
    $contents = null;

    // Path: contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.contents[].itemSectionRenderer.contents
    if (isset($jsonData['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'])) {
        $sections = $jsonData['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'];
        foreach ($sections as $section) {
            if (isset($section['itemSectionRenderer']['contents'])) {
                $contents = $section['itemSectionRenderer']['contents'];
                break;
            }
        }
    }

    if (!$contents) {
        return array('success' => false, 'error' => 'No search results in YouTube data structure');
    }

    foreach ($contents as $item) {
        if (!isset($item['videoRenderer'])) continue;
        $v = $item['videoRenderer'];
        $videoId = isset($v['videoId']) ? $v['videoId'] : '';
        if (empty($videoId) || strlen($videoId) != 11) continue;

        $title = 'Untitled';
        if (isset($v['title']['runs'][0]['text'])) {
            $title = $v['title']['runs'][0]['text'];
        }

        $description = '';
        if (isset($v['detailedMetadataSnippets'][0]['snippetText']['runs'])) {
            foreach ($v['detailedMetadataSnippets'][0]['snippetText']['runs'] as $run) {
                $description .= $run['text'];
            }
        } elseif (isset($v['descriptionSnippet']['runs'])) {
            foreach ($v['descriptionSnippet']['runs'] as $run) {
                $description .= $run['text'];
            }
        }

        $channel = '';
        if (isset($v['ownerText']['runs'][0]['text'])) {
            $channel = $v['ownerText']['runs'][0]['text'];
        } elseif (isset($v['longBylineText']['runs'][0]['text'])) {
            $channel = $v['longBylineText']['runs'][0]['text'];
        }

        $duration = '';
        if (isset($v['lengthText']['simpleText'])) {
            $duration = $v['lengthText']['simpleText'];
        }

        $views = '';
        if (isset($v['viewCountText']['simpleText'])) {
            $views = $v['viewCountText']['simpleText'];
        } elseif (isset($v['shortViewCountText']['simpleText'])) {
            $views = $v['shortViewCountText']['simpleText'];
        }

        $results[] = array(
            'title' => $title,
            'description' => substr($description, 0, 200),
            'trailer_id' => $videoId,
            'thumbnail' => 'https://img.youtube.com/vi/' . $videoId . '/hqdefault.jpg',
            '_isYouTube' => true,
            '_channel' => $channel,
            '_duration' => $duration,
            '_views' => $views
        );

        if (count($results) >= 20) break;
    }

    if (count($results) > 0) {
        return array(
            'success' => true,
            'results' => $results,
            'total_results' => count($results),
            'source' => $source
        );
    }

    return array('success' => false, 'error' => 'No video results parsed from YouTube data');
}

// FALLBACK: Scrape YouTube search results HTML with consent cookie bypass
function searchYouTubeScrape($query) {
    $url = 'https://www.youtube.com/results?search_query=' . urlencode($query) . '&sp=EgIQAQ%3D%3D&hl=en&gl=US';
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 12);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Accept-Language: en-US,en;q=0.9',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    ));
    // Consent cookie bypasses GDPR consent page that blocks server-side requests
    curl_setopt($ch, CURLOPT_COOKIE, 'CONSENT=PENDING+987; SOCS=CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMxMTE0LjA3X3AxGgJlbiACGgYIgJnsBhAB');
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if (!$response || $httpCode < 200 || $httpCode >= 400) {
        return array('success' => false, 'error' => 'YouTube page fetch failed (HTTP ' . $httpCode . ')');
    }

    // Extract ytInitialData JSON from the HTML
    $jsonData = null;
    if (preg_match('/var\s+ytInitialData\s*=\s*(\{.+?\});\s*<\/script>/s', $response, $match)) {
        $jsonData = json_decode($match[1], true);
    }
    // Fallback patterns for different YouTube page formats
    if (!$jsonData && preg_match('/ytInitialData\s*=\s*(\{.+?\});\s*/s', $response, $match)) {
        $jsonData = json_decode($match[1], true);
    }
    if (!$jsonData && preg_match('/window\["ytInitialData"\]\s*=\s*(\{.+?\});\s*/s', $response, $match)) {
        $jsonData = json_decode($match[1], true);
    }

    if (!$jsonData) {
        return array('success' => false, 'error' => 'Could not parse YouTube search data from HTML');
    }

    return parseYouTubeSearchData($jsonData, 'youtube_scrape');
}

function searchYouTube($query) {
    // Piped API instances
    $instances = array(
        'https://pipedapi.kavin.rocks',
        'https://pipedapi-libre.kavin.rocks',
        'https://pipedapi.adminforge.de',
        'https://pipedapi.leptons.xyz',
        'https://piped-api.privacy.com.de',
        'https://pipedapi.nosebs.ru'
    );

    foreach ($instances as $baseUrl) {
        $url = $baseUrl . '/search?q=' . urlencode($query) . '&filter=videos';
        $response = curlGet($url, 8);
        if ($response === false) continue;

        $data = json_decode($response, true);
        if (!$data || !isset($data['items'])) continue;

        $results = array();
        $items = array_slice($data['items'], 0, 20);
        foreach ($items as $item) {
            if (!isset($item['url'])) continue;

            $videoId = '';
            if (preg_match('/[?&]v=([a-zA-Z0-9_-]{11})/', $item['url'], $matches)) {
                $videoId = $matches[1];
            }
            if (empty($videoId) && isset($item['thumbnail'])) {
                if (preg_match('/\/vi\/([a-zA-Z0-9_-]{11})\//', $item['thumbnail'], $matches)) {
                    $videoId = $matches[1];
                }
            }
            if (empty($videoId)) continue;

            $duration = '';
            if (isset($item['duration']) && $item['duration'] > 0) {
                $mins = floor($item['duration'] / 60);
                $secs = $item['duration'] % 60;
                $duration = $mins . ':' . str_pad($secs, 2, '0', STR_PAD_LEFT);
            }

            $results[] = array(
                'title' => isset($item['title']) ? $item['title'] : 'Untitled',
                'description' => isset($item['shortDescription']) ? $item['shortDescription'] : (isset($item['uploaderName']) ? $item['uploaderName'] : ''),
                'trailer_id' => $videoId,
                'thumbnail' => 'https://img.youtube.com/vi/' . $videoId . '/hqdefault.jpg',
                '_isYouTube' => true,
                '_channel' => isset($item['uploaderName']) ? $item['uploaderName'] : '',
                '_duration' => $duration,
                '_views' => isset($item['views']) ? number_format($item['views']) . ' views' : ''
            );
        }

        if (count($results) > 0) {
            return array(
                'success' => true,
                'results' => $results,
                'total_results' => count($results),
                'source' => 'youtube'
            );
        }
    }

    // Fallback: Invidious API
    $invInstances = array(
        'https://inv.nadeko.net',
        'https://invidious.fdn.fr',
        'https://vid.puffyan.us',
        'https://invidious.privacydev.net',
        'https://invidious.lunar.icu'
    );

    foreach ($invInstances as $baseUrl) {
        $url = $baseUrl . '/api/v1/search?q=' . urlencode($query) . '&type=video';
        $response = curlGet($url, 8);
        if ($response === false) continue;

        $data = json_decode($response, true);
        if (!$data || !is_array($data)) continue;

        $results = array();
        $items = array_slice($data, 0, 20);
        foreach ($items as $item) {
            if (!isset($item['videoId'])) continue;

            $duration = '';
            if (isset($item['lengthSeconds']) && $item['lengthSeconds'] > 0) {
                $mins = floor($item['lengthSeconds'] / 60);
                $secs = $item['lengthSeconds'] % 60;
                $duration = $mins . ':' . str_pad($secs, 2, '0', STR_PAD_LEFT);
            }

            $results[] = array(
                'title' => isset($item['title']) ? $item['title'] : 'Untitled',
                'description' => isset($item['description']) ? $item['description'] : (isset($item['author']) ? $item['author'] : ''),
                'trailer_id' => $item['videoId'],
                'thumbnail' => 'https://img.youtube.com/vi/' . $item['videoId'] . '/hqdefault.jpg',
                '_isYouTube' => true,
                '_channel' => isset($item['author']) ? $item['author'] : '',
                '_duration' => $duration,
                '_views' => isset($item['viewCount']) ? number_format($item['viewCount']) . ' views' : ''
            );
        }

        if (count($results) > 0) {
            return array(
                'success' => true,
                'results' => $results,
                'total_results' => count($results),
                'source' => 'youtube'
            );
        }
    }

    // Official YouTube API if key is set
    global $YOUTUBE_API_KEY;
    if ($YOUTUBE_API_KEY) {
        $url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&q=' . urlencode($query) . '&type=video&maxResults=20&key=' . $YOUTUBE_API_KEY;
        $response = curlGet($url, 8);
        if ($response) {
            $data = json_decode($response, true);
            if (isset($data['items']) && count($data['items']) > 0) {
                $results = array();
                foreach ($data['items'] as $item) {
                    $videoId = $item['id']['videoId'];
                    $results[] = array(
                        'title' => $item['snippet']['title'],
                        'description' => $item['snippet']['description'],
                        'trailer_id' => $videoId,
                        'thumbnail' => 'https://img.youtube.com/vi/' . $videoId . '/hqdefault.jpg',
                        '_isYouTube' => true,
                        '_channel' => $item['snippet']['channelTitle']
                    );
                }
                return array(
                    'success' => true,
                    'results' => $results,
                    'total_results' => count($results),
                    'source' => 'youtube_official'
                );
            }
        }
    }

    return array(
        'success' => false,
        'error' => 'YouTube search is temporarily unavailable.',
        'results' => array()
    );
}

// Dailymotion API — FREE, no key required
function searchDailymotionAPI($query) {
    $url = 'https://api.dailymotion.com/videos?search=' . urlencode($query)
         . '&fields=id,title,description,thumbnail_url,duration,owner.screenname,views_total'
         . '&limit=20&sort=relevance';
    $response = curlGet($url, 8);
    if (!$response) {
        return array('success' => false, 'error' => 'Dailymotion API unreachable');
    }

    $data = json_decode($response, true);
    if (!$data || !isset($data['list']) || count($data['list']) == 0) {
        return array('success' => false, 'error' => 'No Dailymotion results');
    }

    $results = array();
    foreach ($data['list'] as $item) {
        if (!isset($item['id'])) continue;

        $duration = '';
        if (isset($item['duration']) && $item['duration'] > 0) {
            $mins = floor($item['duration'] / 60);
            $secs = $item['duration'] % 60;
            $duration = $mins . ':' . str_pad($secs, 2, '0', STR_PAD_LEFT);
        }

        $results[] = array(
            'title' => isset($item['title']) ? $item['title'] : 'Untitled',
            'description' => isset($item['description']) ? substr($item['description'], 0, 200) : '',
            'trailer_id' => $item['id'],
            'thumbnail' => isset($item['thumbnail_url']) ? $item['thumbnail_url'] : '',
            '_isDailymotion' => true,
            '_isYouTube' => false,
            '_channel' => isset($item['owner.screenname']) ? $item['owner.screenname'] : '',
            '_duration' => $duration,
            '_views' => isset($item['views_total']) ? number_format($item['views_total']) . ' views' : ''
        );
    }

    if (count($results) > 0) {
        return array(
            'success' => true,
            'results' => $results,
            'total_results' => count($results),
            'source' => 'dailymotion'
        );
    }
    return array('success' => false, 'error' => 'No Dailymotion results');
}

// Internet Archive — FREE, no key required
function searchInternetArchive($query) {
    $url = 'https://archive.org/advancedsearch.php?q=' . urlencode($query)
         . '+AND+mediatype%3A(movies)&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=description&fl%5B%5D=creator'
         . '&rows=20&page=1&output=json';
    $response = curlGet($url, 10);
    if (!$response) {
        return array('success' => false, 'error' => 'Internet Archive unreachable');
    }

    $data = json_decode($response, true);
    if (!isset($data['response']['docs']) || count($data['response']['docs']) == 0) {
        return array('success' => false, 'error' => 'No Internet Archive results');
    }

    $results = array();
    foreach ($data['response']['docs'] as $doc) {
        if (!isset($doc['identifier'])) continue;
        $results[] = array(
            'title' => isset($doc['title']) ? $doc['title'] : 'Untitled',
            'description' => isset($doc['description']) ? substr($doc['description'], 0, 200) : '',
            'trailer_id' => $doc['identifier'],
            'thumbnail' => 'https://archive.org/services/img/' . $doc['identifier'],
            '_isArchive' => true,
            '_isYouTube' => false,
            '_channel' => isset($doc['creator']) ? (is_array($doc['creator']) ? $doc['creator'][0] : $doc['creator']) : ''
        );
    }

    if (count($results) > 0) {
        return array(
            'success' => true,
            'results' => $results,
            'total_results' => count($results),
            'source' => 'internet_archive'
        );
    }
    return array('success' => false, 'error' => 'No Internet Archive results');
}

// Dailymotion HTML scrape fallback
function searchDailymotionScrape($query) {
    $url = 'https://www.dailymotion.com/search/' . urlencode($query) . '/videos';
    $response = curlGet($url, 10);
    if (!$response) {
        return array('success' => false, 'error' => 'Dailymotion scrape failed');
    }

    $results = array();
    // Try JSON-LD structured data first
    if (preg_match_all('/"@type"\s*:\s*"VideoObject".*?"url"\s*:\s*"([^"]+)".*?"name"\s*:\s*"([^"]+)".*?"thumbnailUrl"\s*:\s*"([^"]+)"/s', $response, $matches, PREG_SET_ORDER)) {
        foreach ($matches as $match) {
            $videoId = '';
            if (preg_match('/\/video\/([a-z0-9]+)/i', $match[1], $idMatch)) {
                $videoId = $idMatch[1];
            }
            if ($videoId) {
                $results[] = array(
                    'title' => html_entity_decode($match[2]),
                    'description' => '',
                    'trailer_id' => $videoId,
                    'thumbnail' => $match[3],
                    '_isDailymotion' => true,
                    '_isYouTube' => false
                );
            }
        }
    }

    // Fallback: try video URLs from href attributes
    if (count($results) == 0) {
        if (preg_match_all('/href="\/video\/([a-z0-9]+)[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"/si', $response, $matches, PREG_SET_ORDER)) {
            foreach ($matches as $match) {
                $results[] = array(
                    'title' => html_entity_decode($match[3]),
                    'description' => '',
                    'trailer_id' => $match[1],
                    'thumbnail' => $match[2],
                    '_isDailymotion' => true,
                    '_isYouTube' => false
                );
            }
        }
    }

    if (count($results) > 0) {
        return array(
            'success' => true,
            'results' => array_slice($results, 0, 20),
            'total_results' => count($results),
            'source' => 'dailymotion_scrape'
        );
    }
    return array('success' => false, 'error' => 'No results from Dailymotion scrape');
}

// Vimeo HTML scrape fallback
function searchVimeoScrape($query) {
    $url = 'https://vimeo.com/search?q=' . urlencode($query);
    $response = curlGet($url, 10);
    if (!$response) {
        return array('success' => false, 'error' => 'Vimeo scrape failed');
    }

    $results = array();
    // Vimeo embeds video data as JSON in the page
    if (preg_match('/window\.vimeo\.clip_page_config\s*=\s*(\{.+?\});/s', $response, $configMatch)) {
        $config = json_decode($configMatch[1], true);
        // Extract from config if available
    }

    // Fallback: regex for video links
    if (preg_match_all('/href="\/(\d{6,12})"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"[^>]*/si', $response, $matches, PREG_SET_ORDER)) {
        foreach ($matches as $match) {
            $results[] = array(
                'title' => html_entity_decode($match[3]),
                'description' => '',
                'trailer_id' => $match[1],
                'thumbnail' => $match[2],
                '_isVimeo' => true,
                '_isYouTube' => false
            );
        }
    }

    if (count($results) > 0) {
        return array(
            'success' => true,
            'results' => array_slice($results, 0, 20),
            'total_results' => count($results),
            'source' => 'vimeo_scrape'
        );
    }
    return array('success' => false, 'error' => 'No results from Vimeo scrape');
}

// TMDB search for movie/TV types
function searchTMDB($query, $type) {
    global $TMDB_V3_KEY;

    $searchType = ($type === 'movie') ? 'movie' : (($type === 'tv') ? 'tv' : 'multi');
    $url = 'https://api.themoviedb.org/3/search/' . $searchType . '?api_key=' . $TMDB_V3_KEY . '&query=' . urlencode($query) . '&language=en-US&page=1';

    $response = curlGet($url, 10);
    if ($response === false) {
        return array('success' => false, 'error' => 'TMDB API unavailable. External requests may be blocked on this host.');
    }

    $data = json_decode($response, true);
    if (!$data || !isset($data['results'])) {
        return array('success' => false, 'error' => 'Invalid TMDB response: ' . substr($response, 0, 100));
    }

    $results = array();
    $items = array_slice($data['results'], 0, 20);
    foreach ($items as $item) {
        $mediaType = isset($item['media_type']) ? $item['media_type'] : $type;
        if ($mediaType === 'person') continue;

        $title = isset($item['title']) ? $item['title'] : (isset($item['name']) ? $item['name'] : 'Untitled');
        $releaseDate = isset($item['release_date']) ? $item['release_date'] : (isset($item['first_air_date']) ? $item['first_air_date'] : '');
        $year = $releaseDate ? substr($releaseDate, 0, 4) : '';

        // Get trailer from TMDB videos endpoint
        $trailerId = '';
        $tmdbId = $item['id'];
        $videoType = ($mediaType === 'tv') ? 'tv' : 'movie';
        $videosUrl = 'https://api.themoviedb.org/3/' . $videoType . '/' . $tmdbId . '/videos?api_key=' . $TMDB_V3_KEY . '&language=en-US';

        $videosResp = curlGet($videosUrl, 5);
        if ($videosResp) {
            $videosData = json_decode($videosResp, true);
            if (isset($videosData['results'])) {
                foreach ($videosData['results'] as $video) {
                    if ($video['site'] === 'YouTube' && in_array($video['type'], array('Trailer', 'Teaser', 'Clip'))) {
                        $trailerId = $video['key'];
                        break;
                    }
                }
            }
        }

        $thumbnail = !empty($item['poster_path']) ? 'https://image.tmdb.org/t/p/w300' . $item['poster_path'] : '';
        $backdrop = !empty($item['backdrop_path']) ? 'https://image.tmdb.org/t/p/w780' . $item['backdrop_path'] : '';
        $overview = isset($item['overview']) ? substr($item['overview'], 0, 200) : '';
        $voteAvg = !empty($item['vote_average']) ? round($item['vote_average'], 1) : null;

        $results[] = array(
            'title' => $title,
            'type' => $mediaType === 'tv' ? 'tv' : 'movie',
            'description' => $overview,
            'release_year' => $year,
            'imdb_rating' => $voteAvg,
            'tmdb_id' => $tmdbId,
            'trailer_id' => $trailerId,
            'thumbnail' => $trailerId ? 'https://img.youtube.com/vi/' . $trailerId . '/hqdefault.jpg' : $thumbnail,
            'backdrop' => $backdrop,
            'genre' => '',
            '_isYouTube' => false
        );
    }

    $totalResults = isset($data['total_results']) ? $data['total_results'] : count($results);

    return array(
        'success' => true,
        'results' => $results,
        'total_results' => $totalResults,
        'source' => 'tmdb'
    );
}
?>
