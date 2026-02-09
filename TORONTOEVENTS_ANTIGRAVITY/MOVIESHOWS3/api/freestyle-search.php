<?php
/**
 * Freestyle Search API - Search TMDB or YouTube for any content (experimental)
 * Returns movies/TV shows with trailer info from TMDB, or YouTube videos
 * 
 * Query params:
 *   ?q=search+term   (required)
 *   &type=movie|tv|multi|youtube  (default: multi)
 *   &page=1          (default: 1)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';
$YOUTUBE_API_KEY = 'AIzaSyDNuBsKqOLKBpC_d8DFiUv0rFNZOoD4laI';

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$type = isset($_GET['type']) ? $_GET['type'] : 'multi';
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
if ($page < 1) $page = 1;
if ($page > 5) $page = 5;

if ($query === '') {
    echo json_encode(array('success' => false, 'error' => 'Missing search query (?q=...)'));
    exit;
}

// ========== YOUTUBE SEARCH ==========
if ($type === 'youtube') {
    $ytUrl = "https://www.googleapis.com/youtube/v3/search"
        . "?part=snippet"
        . "&q=" . urlencode($query)
        . "&type=video"
        . "&maxResults=15"
        . "&order=relevance"
        . "&key=" . $YOUTUBE_API_KEY;

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $ytUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $ytResp = curl_exec($ch);
    $ytCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    // If YouTube API fails (quota, etc.), try Invidious as fallback
    if ($ytCode !== 200 || !$ytResp) {
        // Fallback: Invidious API
        $invUrl = "https://vid.puffyan.us/api/v1/search?q=" . urlencode($query) . "&type=video&page=" . $page;
        $ch2 = curl_init();
        curl_setopt($ch2, CURLOPT_URL, $invUrl);
        curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch2, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch2, CURLOPT_SSL_VERIFYPEER, false);
        $invResp = curl_exec($ch2);
        $invCode = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
        curl_close($ch2);

        if ($invCode === 200 && $invResp) {
            $invData = json_decode($invResp, true);
            if (is_array($invData)) {
                $results = array();
                foreach ($invData as $v) {
                    if (!isset($v['videoId'])) continue;
                    $durationSec = isset($v['lengthSeconds']) ? (int)$v['lengthSeconds'] : 0;
                    $durMin = floor($durationSec / 60);
                    $durSec = $durationSec % 60;
                    $durStr = $durMin . ':' . str_pad($durSec, 2, '0', STR_PAD_LEFT);

                    $results[] = array(
                        'tmdb_id' => null,
                        'title' => isset($v['title']) ? $v['title'] : 'Untitled',
                        'type' => 'video',
                        'genre' => '',
                        'description' => isset($v['description']) ? substr($v['description'], 0, 300) : '',
                        'release_year' => null,
                        'imdb_rating' => null,
                        'trailer_id' => $v['videoId'],
                        'thumbnail' => 'https://img.youtube.com/vi/' . $v['videoId'] . '/hqdefault.jpg',
                        'backdrop' => null,
                        '_isFreestyle' => true,
                        '_isYouTube' => true,
                        '_channel' => isset($v['author']) ? $v['author'] : '',
                        '_duration' => $durStr,
                        '_viewCount' => isset($v['viewCount']) ? (int)$v['viewCount'] : 0
                    );
                    if (count($results) >= 15) break;
                }

                echo json_encode(array(
                    'success' => true,
                    'query' => $query,
                    'total_results' => count($results),
                    'page' => $page,
                    'source' => 'invidious',
                    'results' => $results
                ));
                exit;
            }
        }

        echo json_encode(array('success' => false, 'error' => 'YouTube search unavailable. Try again later.'));
        exit;
    }

    $ytData = json_decode($ytResp, true);
    $ytItems = isset($ytData['items']) ? $ytData['items'] : array();

    // Fetch video details (duration, view count) for the IDs
    $videoIds = array();
    foreach ($ytItems as $ytItem) {
        if (isset($ytItem['id']['videoId'])) {
            $videoIds[] = $ytItem['id']['videoId'];
        }
    }

    $videoDurations = array();
    $videoViews = array();
    if (count($videoIds) > 0) {
        $detailUrl = "https://www.googleapis.com/youtube/v3/videos"
            . "?part=contentDetails,statistics"
            . "&id=" . implode(',', $videoIds)
            . "&key=" . $YOUTUBE_API_KEY;

        $ch3 = curl_init();
        curl_setopt($ch3, CURLOPT_URL, $detailUrl);
        curl_setopt($ch3, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch3, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch3, CURLOPT_SSL_VERIFYPEER, false);
        $detailResp = curl_exec($ch3);
        curl_close($ch3);

        if ($detailResp) {
            $detailData = json_decode($detailResp, true);
            if (isset($detailData['items'])) {
                foreach ($detailData['items'] as $dItem) {
                    $vid = $dItem['id'];
                    // Parse ISO 8601 duration (PT#H#M#S)
                    if (isset($dItem['contentDetails']['duration'])) {
                        $dur = $dItem['contentDetails']['duration'];
                        $hours = 0; $mins = 0; $secs = 0;
                        if (preg_match('/(\d+)H/', $dur, $m)) $hours = (int)$m[1];
                        if (preg_match('/(\d+)M/', $dur, $m)) $mins = (int)$m[1];
                        if (preg_match('/(\d+)S/', $dur, $m)) $secs = (int)$m[1];
                        if ($hours > 0) {
                            $videoDurations[$vid] = $hours . ':' . str_pad($mins, 2, '0', STR_PAD_LEFT) . ':' . str_pad($secs, 2, '0', STR_PAD_LEFT);
                        } else {
                            $videoDurations[$vid] = $mins . ':' . str_pad($secs, 2, '0', STR_PAD_LEFT);
                        }
                    }
                    if (isset($dItem['statistics']['viewCount'])) {
                        $videoViews[$vid] = (int)$dItem['statistics']['viewCount'];
                    }
                }
            }
        }
    }

    $results = array();
    foreach ($ytItems as $ytItem) {
        if (!isset($ytItem['id']['videoId'])) continue;
        $videoId = $ytItem['id']['videoId'];
        $snippet = isset($ytItem['snippet']) ? $ytItem['snippet'] : array();

        $results[] = array(
            'tmdb_id' => null,
            'title' => isset($snippet['title']) ? $snippet['title'] : 'Untitled',
            'type' => 'video',
            'genre' => '',
            'description' => isset($snippet['description']) ? substr($snippet['description'], 0, 300) : '',
            'release_year' => isset($snippet['publishedAt']) ? (int)substr($snippet['publishedAt'], 0, 4) : null,
            'imdb_rating' => null,
            'trailer_id' => $videoId,
            'thumbnail' => 'https://img.youtube.com/vi/' . $videoId . '/hqdefault.jpg',
            'backdrop' => null,
            '_isFreestyle' => true,
            '_isYouTube' => true,
            '_channel' => isset($snippet['channelTitle']) ? $snippet['channelTitle'] : '',
            '_duration' => isset($videoDurations[$videoId]) ? $videoDurations[$videoId] : '',
            '_viewCount' => isset($videoViews[$videoId]) ? $videoViews[$videoId] : 0
        );
    }

    $totalResults = isset($ytData['pageInfo']['totalResults']) ? (int)$ytData['pageInfo']['totalResults'] : count($results);

    echo json_encode(array(
        'success' => true,
        'query' => $query,
        'total_results' => $totalResults,
        'page' => $page,
        'source' => 'youtube',
        'results' => $results
    ));
    exit;
}

// ========== TMDB SEARCH ==========
$searchType = ($type === 'multi') ? 'multi' : $type;
$url = "https://api.themoviedb.org/3/search/" . $searchType . "?api_key=" . $TMDB_API_KEY . "&query=" . urlencode($query) . "&page=" . $page . "&include_adult=false";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 15);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'Authorization: Bearer ' . $TMDB_READ_TOKEN,
    'Accept: application/json'
));
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200 || !$response) {
    echo json_encode(array('success' => false, 'error' => 'TMDB API request failed'));
    exit;
}

$data = json_decode($response, true);
if (!isset($data['results'])) {
    echo json_encode(array('success' => false, 'error' => 'Invalid TMDB response'));
    exit;
}

// For each result, try to get a trailer
$results = array();
foreach ($data['results'] as $item) {
    $mediaType = isset($item['media_type']) ? $item['media_type'] : $type;
    if ($mediaType === 'person') continue;

    $tmdbId = (int)$item['id'];
    $title = isset($item['title']) ? $item['title'] : (isset($item['name']) ? $item['name'] : 'Unknown');
    $releaseDate = isset($item['release_date']) ? $item['release_date'] : (isset($item['first_air_date']) ? $item['first_air_date'] : '');
    $year = $releaseDate ? (int)substr($releaseDate, 0, 4) : null;
    $poster = isset($item['poster_path']) ? 'https://image.tmdb.org/t/p/w500' . $item['poster_path'] : null;
    $backdrop = isset($item['backdrop_path']) ? 'https://image.tmdb.org/t/p/w780' . $item['backdrop_path'] : null;
    $rating = isset($item['vote_average']) ? round($item['vote_average'], 1) : null;
    $overview = isset($item['overview']) ? $item['overview'] : '';
    $genreIds = isset($item['genre_ids']) ? $item['genre_ids'] : array();

    // Fetch trailer for this item
    $trailerId = null;
    $videoType = ($mediaType === 'tv') ? 'tv' : 'movie';
    $videoUrl = "https://api.themoviedb.org/3/" . $videoType . "/" . $tmdbId . "/videos?api_key=" . $TMDB_API_KEY;

    $ch2 = curl_init();
    curl_setopt($ch2, CURLOPT_URL, $videoUrl);
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch2, CURLOPT_HTTPHEADER, array(
        'Authorization: Bearer ' . $TMDB_READ_TOKEN,
        'Accept: application/json'
    ));
    curl_setopt($ch2, CURLOPT_SSL_VERIFYPEER, false);
    $videoResponse = curl_exec($ch2);
    $videoHttpCode = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
    curl_close($ch2);

    if ($videoHttpCode === 200 && $videoResponse) {
        $videoData = json_decode($videoResponse, true);
        if (isset($videoData['results'])) {
            // Prefer official trailers, then teasers
            foreach ($videoData['results'] as $vid) {
                if (isset($vid['site']) && $vid['site'] === 'YouTube') {
                    if (isset($vid['type']) && $vid['type'] === 'Trailer') {
                        $trailerId = $vid['key'];
                        break;
                    }
                    if ($trailerId === null && isset($vid['type']) && ($vid['type'] === 'Teaser' || $vid['type'] === 'Clip')) {
                        $trailerId = $vid['key'];
                    }
                }
            }
        }
    }

    // Map genre IDs to names
    $genreMap = array(
        28 => 'Action', 12 => 'Adventure', 16 => 'Animation', 35 => 'Comedy',
        80 => 'Crime', 99 => 'Documentary', 18 => 'Drama', 10751 => 'Family',
        14 => 'Fantasy', 36 => 'History', 27 => 'Horror', 10402 => 'Music',
        9648 => 'Mystery', 10749 => 'Romance', 878 => 'Sci-Fi', 10770 => 'TV Movie',
        53 => 'Thriller', 10752 => 'War', 37 => 'Western',
        10759 => 'Action & Adventure', 10762 => 'Kids', 10763 => 'News',
        10764 => 'Reality', 10765 => 'Sci-Fi & Fantasy', 10766 => 'Soap',
        10767 => 'Talk', 10768 => 'War & Politics'
    );
    $genres = array();
    foreach ($genreIds as $gid) {
        if (isset($genreMap[$gid])) {
            $genres[] = $genreMap[$gid];
        }
    }

    $results[] = array(
        'tmdb_id' => $tmdbId,
        'title' => $title,
        'type' => $mediaType,
        'genre' => implode(', ', $genres),
        'description' => $overview,
        'release_year' => $year,
        'imdb_rating' => $rating,
        'trailer_id' => $trailerId,
        'thumbnail' => $poster,
        'backdrop' => $backdrop,
        '_isFreestyle' => true
    );

    // Limit to 10 results to keep trailer fetching fast
    if (count($results) >= 10) break;
}

echo json_encode(array(
    'success' => true,
    'query' => $query,
    'total_results' => isset($data['total_results']) ? $data['total_results'] : count($results),
    'page' => $page,
    'results' => $results
));
?>
