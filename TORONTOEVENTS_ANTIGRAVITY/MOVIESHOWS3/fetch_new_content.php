<?php
/**
 * Fetch New Content — Bulk fetch trending/upcoming movies & TV from TMDB
 * Inserts into MOVIESHOWS3 database with duplicate detection.
 *
 * Usage: ?key=ms2_sync_2024_findto&type=both&pages=5&mode=trending
 *   type:  movie | tv | both
 *   pages: 1-10 (number of TMDB pages to fetch, 20 results per page)
 *   mode:  trending | upcoming | popular | top_rated | now_playing
 *
 * PHP 5.2 compatible — no short array syntax, no ?? operator
 */
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(0); // Bulk fetch can make many TMDB API calls

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// ---- Auth check ----
$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'ms2_sync_2024_findto') {
    http_response_code(403);
    echo json_encode(array(
        'success' => false,
        'error' => 'Unauthorized. Provide ?key=...'
    ));
    exit;
}

// ---- Parameters ----
$type = isset($_GET['type']) ? $_GET['type'] : 'both';
$pages = isset($_GET['pages']) ? (int)$_GET['pages'] : 5;
$mode = isset($_GET['mode']) ? $_GET['mode'] : 'trending';

if ($pages < 1) $pages = 1;
if ($pages > 10) $pages = 10;

$validModes = array('trending', 'upcoming', 'popular', 'top_rated', 'now_playing', 'on_the_air');
if (!in_array($mode, $validModes)) {
    $mode = 'trending';
}

// ---- DB connection (use shared config with credential fallback) ----
$dbConfigPath = dirname(__FILE__) . '/api/db-config.php';
if (!file_exists($dbConfigPath)) {
    echo json_encode(array(
        'success' => false,
        'error' => 'Missing api/db-config.php'
    ));
    exit;
}

require_once $dbConfigPath;

if (!function_exists('getDbConnection')) {
    echo json_encode(array(
        'success' => false,
        'error' => 'getDbConnection() not defined'
    ));
    exit;
}

$pdo = getDbConnection();
if ($pdo === null) {
    echo json_encode(array(
        'success' => false,
        'error' => 'DB connection failed: check api/db-config.php credentials'
    ));
    exit;
}

// ---- TMDB API key (same as freestyle-search.php) ----
$TMDB_API_KEY = '6dc4a9654d9748dd817413924088c9d6';

// ---- Determine which types to fetch ----
$fetchTypes = array();
if ($type === 'both') {
    $fetchTypes = array('movie', 'tv');
} elseif ($type === 'movie') {
    $fetchTypes = array('movie');
} elseif ($type === 'tv') {
    $fetchTypes = array('tv');
} else {
    $fetchTypes = array('movie', 'tv');
}

// ---- Build TMDB endpoint per type/mode ----
function getTmdbEndpoint($mediaType, $mode, $apiKey, $page) {
    // Map mode to TMDB API endpoint
    if ($mediaType === 'tv') {
        switch ($mode) {
            case 'trending':
                return 'https://api.themoviedb.org/3/trending/tv/week?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            case 'popular':
                return 'https://api.themoviedb.org/3/tv/popular?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            case 'top_rated':
                return 'https://api.themoviedb.org/3/tv/top_rated?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            case 'on_the_air':
                return 'https://api.themoviedb.org/3/tv/on_the_air?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            default:
                return 'https://api.themoviedb.org/3/trending/tv/week?api_key=' . $apiKey . '&language=en-US&page=' . $page;
        }
    } else {
        switch ($mode) {
            case 'trending':
                return 'https://api.themoviedb.org/3/trending/movie/week?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            case 'upcoming':
                return 'https://api.themoviedb.org/3/movie/upcoming?api_key=' . $apiKey . '&language=en-US&region=CA&page=' . $page;
            case 'popular':
                return 'https://api.themoviedb.org/3/movie/popular?api_key=' . $apiKey . '&language=en-US&region=CA&page=' . $page;
            case 'top_rated':
                return 'https://api.themoviedb.org/3/movie/top_rated?api_key=' . $apiKey . '&language=en-US&page=' . $page;
            case 'now_playing':
                return 'https://api.themoviedb.org/3/movie/now_playing?api_key=' . $apiKey . '&language=en-US&region=CA&page=' . $page;
            default:
                return 'https://api.themoviedb.org/3/trending/movie/week?api_key=' . $apiKey . '&language=en-US&page=' . $page;
        }
    }
}

// ---- HTTP GET helper (cURL) ----
function _fetchContentCurlGet($url, $timeout) {
    if (!function_exists('curl_init')) {
        return false;
    }
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MovieShows3/1.0');
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($httpCode >= 200 && $httpCode < 400) {
        return $response;
    }
    return false;
}

// ---- Fetch trailer key from TMDB videos endpoint ----
function fetchTrailerKey($tmdbId, $mediaType, $apiKey) {
    $videoType = ($mediaType === 'tv') ? 'tv' : 'movie';
    $url = 'https://api.themoviedb.org/3/' . $videoType . '/' . $tmdbId . '/videos?api_key=' . $apiKey . '&language=en-US';
    $resp = _fetchContentCurlGet($url, 6);
    if (!$resp) return '';

    $data = json_decode($resp, true);
    if (!$data || !isset($data['results'])) return '';

    foreach ($data['results'] as $video) {
        if ($video['site'] === 'YouTube' && in_array($video['type'], array('Trailer', 'Teaser', 'Clip'))) {
            return $video['key'];
        }
    }
    return '';
}

// ---- Genre ID mapping ----
$GENRE_MAP = array(
    28 => 'Action', 12 => 'Adventure', 16 => 'Animation',
    35 => 'Comedy', 80 => 'Crime', 99 => 'Documentary',
    18 => 'Drama', 10751 => 'Family', 14 => 'Fantasy',
    36 => 'History', 27 => 'Horror', 10402 => 'Music',
    9648 => 'Mystery', 10749 => 'Romance', 878 => 'Sci-Fi',
    10770 => 'TV Movie', 53 => 'Thriller', 10752 => 'War',
    37 => 'Western',
    10759 => 'Action & Adventure', 10762 => 'Kids',
    10763 => 'News', 10764 => 'Reality', 10765 => 'Sci-Fi & Fantasy',
    10766 => 'Soap', 10767 => 'Talk', 10768 => 'War & Politics'
);

// ---- Process each type ----
$summary = array(
    'movies_added' => 0,
    'tv_added' => 0,
    'skipped' => 0,
    'errors' => 0,
    'fetched_from_tmdb' => 0
);
$results = array();

foreach ($fetchTypes as $mediaType) {
    for ($page = 1; $page <= $pages; $page++) {
        $url = getTmdbEndpoint($mediaType, $mode, $TMDB_API_KEY, $page);
        $response = _fetchContentCurlGet($url, 12);

        if ($response === false) {
            $results[] = array(
                'type' => $mediaType,
                'page' => $page,
                'status' => 'fetch_error',
                'error' => 'TMDB API request failed'
            );
            $summary['errors']++;
            continue;
        }

        $data = json_decode($response, true);
        if (!$data || !isset($data['results']) || count($data['results']) == 0) {
            continue;
        }

        $summary['fetched_from_tmdb'] += count($data['results']);

        foreach ($data['results'] as $item) {
            $tmdbId = isset($item['id']) ? (int)$item['id'] : 0;
            if ($tmdbId === 0) continue;

            $title = isset($item['title']) ? $item['title'] : (isset($item['name']) ? $item['name'] : '');
            if ($title === '') continue;

            $releaseDate = isset($item['release_date']) ? $item['release_date'] : (isset($item['first_air_date']) ? $item['first_air_date'] : '');
            $year = $releaseDate !== '' ? (int)substr($releaseDate, 0, 4) : 0;
            $overview = isset($item['overview']) ? $item['overview'] : '';
            $voteAvg = isset($item['vote_average']) ? round((float)$item['vote_average'], 1) : 0;
            $posterPath = isset($item['poster_path']) ? $item['poster_path'] : '';
            $thumbnail = $posterPath !== '' ? 'https://image.tmdb.org/t/p/w500' . $posterPath : '';

            // Genre mapping
            $genreIds = isset($item['genre_ids']) ? $item['genre_ids'] : array();
            $genreNamesArr = array();
            foreach ($genreIds as $gid) {
                if (isset($GENRE_MAP[$gid])) {
                    $genreNamesArr[] = $GENRE_MAP[$gid];
                }
            }
            $genreStr = implode(', ', $genreNamesArr);

            // Runtime — not available in list endpoint; set to 0
            $runtime = 0;

            $entry = array(
                'title' => $title,
                'tmdb_id' => $tmdbId,
                'type' => $mediaType,
                'status' => 'pending'
            );

            try {
                // Check duplicate by tmdb_id
                $checkStmt = $pdo->prepare("SELECT id, title FROM movies WHERE tmdb_id = ?");
                $checkStmt->execute(array($tmdbId));
                $existing = $checkStmt->fetch(PDO::FETCH_ASSOC);

                if ($existing) {
                    $entry['status'] = 'skipped';
                    $entry['reason'] = 'Already exists (id=' . $existing['id'] . ')';
                    $entry['movie_id'] = $existing['id'];
                    $results[] = $entry;
                    $summary['skipped']++;
                    continue;
                }

                // Fetch trailer key
                $trailerKey = fetchTrailerKey($tmdbId, $mediaType, $TMDB_API_KEY);

                // Skip if no trailer found (optional — can be relaxed)
                // We still insert even without a trailer; trailer can be added later

                // Begin transaction
                $pdo->beginTransaction();

                // Insert movie
                $insertMovie = $pdo->prepare(
                    "INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, tmdb_id, runtime, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())"
                );
                $insertMovie->execute(array(
                    $title,
                    $mediaType,
                    $genreStr,
                    $overview,
                    $year,
                    $voteAvg,
                    $tmdbId,
                    $runtime
                ));
                $movieId = $pdo->lastInsertId();

                // Insert trailer if found
                if ($trailerKey !== '') {
                    $insertTrailer = $pdo->prepare(
                        "INSERT INTO trailers (movie_id, youtube_id, is_active, priority, source, created_at)
                         VALUES (?, ?, TRUE, 1, 'tmdb_bulk', NOW())"
                    );
                    $insertTrailer->execute(array($movieId, $trailerKey));
                }

                // Insert thumbnail
                if ($thumbnail !== '') {
                    $insertThumb = $pdo->prepare(
                        "INSERT INTO thumbnails (movie_id, url, is_primary, created_at)
                         VALUES (?, ?, TRUE, NOW())"
                    );
                    $insertThumb->execute(array($movieId, $thumbnail));
                }

                $pdo->commit();

                $entry['status'] = 'added';
                $entry['movie_id'] = $movieId;
                $entry['trailer_key'] = $trailerKey;
                if ($mediaType === 'movie') {
                    $summary['movies_added']++;
                } else {
                    $summary['tv_added']++;
                }

            } catch (Exception $e) {
                if ($pdo->inTransaction()) {
                    $pdo->rollBack();
                }
                $entry['status'] = 'error';
                $entry['error'] = $e->getMessage();
                $summary['errors']++;
            }

            $results[] = $entry;
        }

        // Respect TMDB rate limits — small delay between pages
        if ($page < $pages) {
            usleep(250000); // 0.25s
        }
    }
}

// ---- Write pull log ----
$logEntry = array(
    'timestamp' => date('Y-m-d H:i:s'),
    'status' => ($summary['errors'] === 0) ? 'success' : 'partial',
    'movies_added' => $summary['movies_added'],
    'tv_added' => $summary['tv_added'],
    'skipped' => $summary['skipped'],
    'errors' => $summary['errors'],
    'mode' => $mode,
    'type' => $type,
    'pages' => $pages,
    'message' => 'Added ' . ($summary['movies_added'] + $summary['tv_added']) . ' new titles, skipped ' . $summary['skipped'] . ' duplicates'
);

$logFile = dirname(__FILE__) . '/log/pull_log.json';
$logDir = dirname($logFile);
if (!is_dir($logDir)) {
    @mkdir($logDir, 0755, true);
}

$existingLog = array();
if (file_exists($logFile)) {
    $raw = @file_get_contents($logFile);
    if ($raw !== false) {
        $decoded = json_decode($raw, true);
        if (is_array($decoded)) {
            $existingLog = $decoded;
        }
    }
}
$existingLog[] = $logEntry;
// Keep last 100 entries
if (count($existingLog) > 100) {
    $existingLog = array_slice($existingLog, -100);
}
@file_put_contents($logFile, json_encode($existingLog, JSON_PRETTY_PRINT));

// ---- Output ----
echo json_encode(array(
    'success' => ($summary['errors'] === 0),
    'summary' => $summary,
    'results' => array_slice($results, 0, 50), // Limit output to first 50 entries
    'total_results' => count($results),
    'log_entry' => $logEntry,
    'timestamp' => date('Y-m-d H:i:s')
));
?>
