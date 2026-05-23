<?php
/**
 * Now Playing API Endpoint
 * Proxies TMDB /movie/now_playing with file-based caching.
 * Returns movies currently in theaters for a given region.
 *
 * PHP 5.2 compatible — no closures, no short array syntax, no ?: or ??
 *
 * Parameters:
 *   region (string, optional) - ISO 3166-1 country code (default "CA")
 *   page   (int, optional)    - TMDB page number (default 1)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

// ============================================================
// CONFIGURATION
// ============================================================

// TMDB API key (same key used in MOVIESHOWS3 admin scripts)
$TMDB_API_KEY = '15d2ea6d0dc1d476efbca3eba2b9bbfb';

// Cache TTL in seconds (6 hours)
$CACHE_TTL = 21600;

// TMDB genre ID to name mapping (static, rarely changes)
$GENRE_MAP = array(
    28 => 'Action', 12 => 'Adventure', 16 => 'Animation',
    35 => 'Comedy', 80 => 'Crime', 99 => 'Documentary',
    18 => 'Drama', 10751 => 'Family', 14 => 'Fantasy',
    36 => 'History', 27 => 'Horror', 10402 => 'Music',
    9648 => 'Mystery', 10749 => 'Romance', 878 => 'Sci-Fi',
    10770 => 'TV Movie', 53 => 'Thriller', 10752 => 'War',
    37 => 'Western'
);

// ============================================================
// READ PARAMETERS
// ============================================================

$region = isset($_GET['region']) ? strtoupper(trim($_GET['region'])) : 'CA';
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
if ($page < 1) $page = 1;
if ($page > 5) $page = 5;

// Validate region (2-letter code)
if (!preg_match('/^[A-Z]{2}$/', $region)) {
    $region = 'CA';
}

// ============================================================
// CHECK CACHE
// ============================================================

$cache_file = sys_get_temp_dir() . '/fte_nowplaying_' . $region . '_' . $page . '.json';
$cache_valid = false;
$cache_age_minutes = 0;

if (file_exists($cache_file)) {
    $cache_time = filemtime($cache_file);
    $age = time() - $cache_time;
    $cache_age_minutes = (int)round($age / 60);

    if ($age < $CACHE_TTL) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $cached_data = json_decode($cached, true);
            if (is_array($cached_data) && isset($cached_data['ok']) && $cached_data['ok']) {
                $cached_data['cached'] = true;
                $cached_data['cache_age_minutes'] = $cache_age_minutes;
                echo json_encode($cached_data);
                exit;
            }
        }
    }
}

// ============================================================
// FETCH FROM TMDB
// ============================================================

$tmdb_url = 'https://api.themoviedb.org/3/movie/now_playing'
    . '?api_key=' . $TMDB_API_KEY
    . '&region=' . $region
    . '&language=en-US'
    . '&page=' . $page;

$response = _nowplaying_http_get($tmdb_url);

if ($response === false) {
    // TMDB failed — try US region as fallback if we were trying CA
    if ($region === 'CA') {
        $tmdb_url_us = 'https://api.themoviedb.org/3/movie/now_playing'
            . '?api_key=' . $TMDB_API_KEY
            . '&region=US'
            . '&language=en-US'
            . '&page=' . $page;
        $response = _nowplaying_http_get($tmdb_url_us);
    }

    if ($response === false) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Could not fetch now-playing data from TMDB.'
        ));
        exit;
    }
}

$data = json_decode($response, true);
if (!is_array($data) || !isset($data['results'])) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Invalid response from TMDB.'
    ));
    exit;
}

// ============================================================
// FORMAT RESULTS
// ============================================================

$movies = array();
foreach ($data['results'] as $item) {
    $title = isset($item['title']) ? $item['title'] : '';
    if ($title === '') continue;

    $poster_path = isset($item['poster_path']) ? $item['poster_path'] : '';
    $poster_url = '';
    if ($poster_path !== '') {
        $poster_url = 'https://image.tmdb.org/t/p/w185' . $poster_path;
    }

    $backdrop_path = isset($item['backdrop_path']) ? $item['backdrop_path'] : '';
    $backdrop_url = '';
    if ($backdrop_path !== '') {
        $backdrop_url = 'https://image.tmdb.org/t/p/w780' . $backdrop_path;
    }

    // Map genre IDs to names
    $genre_ids = isset($item['genre_ids']) ? $item['genre_ids'] : array();
    $genre_names_arr = array();
    foreach ($genre_ids as $gid) {
        if (isset($GENRE_MAP[$gid])) {
            $genre_names_arr[] = $GENRE_MAP[$gid];
        }
    }
    $genre_names = implode(', ', $genre_names_arr);

    $rating = isset($item['vote_average']) ? (float)$item['vote_average'] : 0;
    $release_date = isset($item['release_date']) ? $item['release_date'] : '';
    $overview = isset($item['overview']) ? $item['overview'] : '';
    $tmdb_id = isset($item['id']) ? (int)$item['id'] : 0;
    $popularity = isset($item['popularity']) ? (float)$item['popularity'] : 0;

    $movies[] = array(
        'id' => $tmdb_id,
        'title' => $title,
        'overview' => $overview,
        'poster_url' => $poster_url,
        'backdrop_url' => $backdrop_url,
        'rating' => round($rating, 1),
        'release_date' => $release_date,
        'genre_names' => $genre_names,
        'popularity' => round($popularity, 1)
    );
}

// Sort by popularity (most popular first)
usort($movies, '_nowplaying_sort_by_popularity');

$result = array(
    'ok' => true,
    'movies' => $movies,
    'total' => count($movies),
    'region' => $region,
    'cached' => false,
    'cache_age_minutes' => 0,
    'tmdb_attribution' => 'Data provided by TMDB (themoviedb.org)'
);

// Write cache
@file_put_contents($cache_file, json_encode($result));

echo json_encode($result);
exit;


// ============================================================
// INTERNAL FUNCTIONS
// ============================================================

function _nowplaying_sort_by_popularity($a, $b) {
    if ($a['popularity'] == $b['popularity']) return 0;
    return ($a['popularity'] > $b['popularity']) ? -1 : 1;
}

function _nowplaying_http_get($url) {
    // Try curl first
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response !== false && $code >= 200 && $code < 300) {
            return $response;
        }
    }

    // Fallback to file_get_contents
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 10,
            'header' => "User-Agent: FindTorontoEvents/1.0\r\n"
        )
    ));

    $response = @file_get_contents($url, false, $context);
    return ($response !== false) ? $response : false;
}
