<?php
/**
 * Fetch NEW movies and TV shows from TMDB API
 * - Deduplicates by tmdb_id (never inserts same TMDB entry twice)
 * - Deduplicates trailers by youtube_id per movie (no duplicate YouTube URLs)
 * - Logs sync results to sync_log table
 * - Called by GitHub Actions workflow via HTTP
 *
 * Query params:
 *   ?key=SYNC_SECRET_KEY  (required, must match AUTH_KEY below)
 *   &type=movie|tv|both   (default: both)
 *   &pages=N              (pages per category, default: 3)
 *   &mode=trending|discover (default: trending)
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(300); // 5 minutes max

// --- AUTH ---
// The key is checked against the GitHub secret passed as a query param
$AUTH_KEY = 'ms2_sync_2024_findto';

$providedKey = isset($_GET['key']) ? $_GET['key'] : '';
if ($providedKey !== $AUTH_KEY) {
    header('HTTP/1.1 403 Forbidden');
    die("Unauthorized\n");
}

// --- CONFIG ---
$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$dbuser = 'ejaguiar1_tvmoviestrailers';
$dbpass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

$type = isset($_GET['type']) ? $_GET['type'] : 'both';
$pages = isset($_GET['pages']) ? min((int)$_GET['pages'], 10) : 3;
$mode = isset($_GET['mode']) ? $_GET['mode'] : 'trending';

// --- DB CONNECTION ---
try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $dbuser, $dbpass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    die("DB connection failed: " . $e->getMessage() . "\n");
}

echo "=== TMDB Fetch New Content ===\n";
echo "Mode: $mode | Type: $type | Pages: $pages\n";
echo "Time: " . date('Y-m-d H:i:s T') . "\n\n";

// --- PRE-LOAD existing tmdb_ids for fast dedup ---
$existingTmdb = array();
$stmt = $pdo->query("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL");
while ($row = $stmt->fetch()) {
    $existingTmdb[(int)$row['tmdb_id']] = true;
}
echo "Existing entries in DB: " . count($existingTmdb) . "\n\n";

// --- PRE-LOAD existing youtube_ids for trailer dedup ---
$existingYoutubeIds = array();
$stmt = $pdo->query("SELECT youtube_id FROM trailers");
while ($row = $stmt->fetch()) {
    $existingYoutubeIds[$row['youtube_id']] = true;
}
echo "Existing trailers in DB: " . count($existingYoutubeIds) . "\n\n";

$totalAdded = 0;
$totalSkipped = 0;
$totalTrailersAdded = 0;
$errors = 0;
$errorMessages = array();

/**
 * Make TMDB API request with bearer token
 */
function tmdb_request($url) {
    global $TMDB_READ_TOKEN;

    $ch = curl_init();
    curl_setopt_array($ch, array(
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_HTTPHEADER => array(
            'Authorization: Bearer ' . $TMDB_READ_TOKEN,
            'Accept: application/json'
        ),
        CURLOPT_SSL_VERIFYPEER => false
    ));
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200 || !$response) {
        return null;
    }
    return json_decode($response, true);
}

/**
 * Process a single movie/TV item from TMDB
 */
function process_item($item, $contentType) {
    global $pdo, $existingTmdb, $existingYoutubeIds, $TMDB_API_KEY;
    global $totalAdded, $totalSkipped, $totalTrailersAdded, $errors, $errorMessages;

    $tmdbId = (int)$item['id'];

    // DEDUP CHECK: Skip if tmdb_id already exists
    if (isset($existingTmdb[$tmdbId])) {
        $totalSkipped++;
        return;
    }

    // Get full details with videos
    $detailType = ($contentType === 'tv') ? 'tv' : 'movie';
    $detailUrl = "https://api.themoviedb.org/3/{$detailType}/{$tmdbId}?api_key={$TMDB_API_KEY}&append_to_response=videos";
    $details = tmdb_request($detailUrl);

    if (!$details) {
        $errors++;
        return;
    }

    // Extract fields
    $title = isset($details['title']) ? $details['title'] : (isset($details['name']) ? $details['name'] : 'Unknown');

    $genres = array();
    if (isset($details['genres'])) {
        foreach ($details['genres'] as $g) {
            $genres[] = $g['name'];
        }
    }
    $genreStr = implode(', ', $genres);

    $description = isset($details['overview']) ? $details['overview'] : '';

    if ($contentType === 'tv') {
        $releaseDate = isset($details['first_air_date']) ? $details['first_air_date'] : '';
    } else {
        $releaseDate = isset($details['release_date']) ? $details['release_date'] : '';
    }
    $releaseYear = $releaseDate ? (int)substr($releaseDate, 0, 4) : null;

    $rating = isset($details['vote_average']) ? round($details['vote_average'], 1) : null;
    $imdbId = isset($details['imdb_id']) ? $details['imdb_id'] : null;

    if ($contentType === 'tv') {
        $runtime = isset($details['episode_run_time'][0]) ? $details['episode_run_time'][0] : null;
    } else {
        $runtime = isset($details['runtime']) ? $details['runtime'] : null;
    }

    try {
        // Double-check DB for race condition
        $stmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ?");
        $stmt->execute(array($tmdbId));
        if ($stmt->fetch()) {
            $existingTmdb[$tmdbId] = true;
            $totalSkipped++;
            return;
        }

        // INSERT movie/tv
        $stmt = $pdo->prepare("
            INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, imdb_id, tmdb_id, runtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute(array(
            $title,
            $contentType,
            $genreStr,
            $description,
            $releaseYear,
            $rating,
            $imdbId,
            $tmdbId,
            $runtime
        ));
        $movieId = $pdo->lastInsertId();
        $existingTmdb[$tmdbId] = true;

        // Insert trailers (dedup by youtube_id)
        $trailersAdded = 0;
        if (isset($details['videos']['results'])) {
            foreach ($details['videos']['results'] as $video) {
                if ($video['site'] !== 'YouTube') continue;
                if (!in_array($video['type'], array('Trailer', 'Teaser'))) continue;

                $youtubeId = $video['key'];

                // DEDUP CHECK: Skip if this youtube_id already exists
                if (isset($existingYoutubeIds[$youtubeId])) {
                    continue;
                }

                $stmt = $pdo->prepare("
                    INSERT INTO trailers (movie_id, youtube_id, title, priority, source, is_active)
                    VALUES (?, ?, ?, ?, 'tmdb', TRUE)
                ");
                $priority = ($video['type'] === 'Trailer') ? 1 : 0;
                $stmt->execute(array($movieId, $youtubeId, $video['name'], $priority));
                $existingYoutubeIds[$youtubeId] = true;
                $trailersAdded++;
                $totalTrailersAdded++;
            }
        }

        // Insert thumbnail
        $posterPath = isset($item['poster_path']) ? $item['poster_path'] : (isset($details['poster_path']) ? $details['poster_path'] : null);
        if ($posterPath) {
            $thumbnailUrl = "https://image.tmdb.org/t/p/w500" . $posterPath;
            $stmt = $pdo->prepare("INSERT INTO thumbnails (movie_id, url, is_primary) VALUES (?, ?, TRUE)");
            $stmt->execute(array($movieId, $thumbnailUrl));
        }

        $totalAdded++;
        echo "  + [{$contentType}] {$title} ({$releaseYear}) - {$trailersAdded} trailers\n";

    } catch (PDOException $e) {
        $errors++;
        $msg = "Error inserting {$title}: " . $e->getMessage();
        $errorMessages[] = $msg;
        echo "  ! {$msg}\n";
    }

    // Rate limiting: 250ms
    usleep(250000);
}

// --- FETCH MOVIES ---
if ($type === 'movie' || $type === 'both') {
    echo "--- Fetching Movies ---\n";
    for ($page = 1; $page <= $pages; $page++) {
        if ($mode === 'trending') {
            $url = "https://api.themoviedb.org/3/trending/movie/week?api_key={$TMDB_API_KEY}&page={$page}";
        } else {
            $currentYear = date('Y');
            $url = "https://api.themoviedb.org/3/discover/movie?api_key={$TMDB_API_KEY}&primary_release_year={$currentYear}&sort_by=popularity.desc&page={$page}";
        }

        echo "Page {$page}...\n";
        $data = tmdb_request($url);

        if (!$data || !isset($data['results'])) {
            echo "  Failed to fetch page {$page}\n";
            $errors++;
            continue;
        }

        foreach ($data['results'] as $item) {
            process_item($item, 'movie');
        }
    }
    echo "\n";
}

// --- FETCH TV SHOWS ---
if ($type === 'tv' || $type === 'both') {
    echo "--- Fetching TV Shows ---\n";
    for ($page = 1; $page <= $pages; $page++) {
        if ($mode === 'trending') {
            $url = "https://api.themoviedb.org/3/trending/tv/week?api_key={$TMDB_API_KEY}&page={$page}";
        } else {
            $currentYear = date('Y');
            $url = "https://api.themoviedb.org/3/discover/tv?api_key={$TMDB_API_KEY}&first_air_date_year={$currentYear}&sort_by=popularity.desc&page={$page}";
        }

        echo "Page {$page}...\n";
        $data = tmdb_request($url);

        if (!$data || !isset($data['results'])) {
            echo "  Failed to fetch page {$page}\n";
            $errors++;
            continue;
        }

        foreach ($data['results'] as $item) {
            process_item($item, 'tv');
        }
    }
    echo "\n";
}

// --- LOG RESULTS TO sync_log ---
$status = ($errors > 0 && $totalAdded > 0) ? 'partial' : ($errors > 0 ? 'failed' : 'success');
$logMessage = "Mode:{$mode} Type:{$type} Pages:{$pages} Added:{$totalAdded} Skipped:{$totalSkipped} Trailers:{$totalTrailersAdded} Errors:{$errors}";
if (!empty($errorMessages)) {
    $logMessage .= " | " . implode('; ', array_slice($errorMessages, 0, 5));
}

try {
    $stmt = $pdo->prepare("INSERT INTO sync_log (sync_type, status, items_processed, error_message) VALUES (?, ?, ?, ?)");
    $stmt->execute(array(
        'tmdb_fetch_' . $type,
        $status,
        $totalAdded,
        substr($logMessage, 0, 500)
    ));
    echo "Sync logged to database.\n";
} catch (PDOException $e) {
    echo "Warning: Could not write sync log: " . $e->getMessage() . "\n";
}

// --- SUMMARY ---
echo "\n=== SUMMARY ===\n";
echo "New titles added: {$totalAdded}\n";
echo "Duplicates skipped: {$totalSkipped}\n";
echo "New trailers added: {$totalTrailersAdded}\n";
echo "Errors: {$errors}\n";
echo "Status: {$status}\n";

// Final DB count
$stmt = $pdo->query("SELECT COUNT(*) as total FROM movies");
$finalCount = $stmt->fetch();
echo "Total titles in database: " . $finalCount['total'] . "\n";
echo "Completed: " . date('Y-m-d H:i:s T') . "\n";
?>
