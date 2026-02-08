<?php
/**
 * Admin Fetch by Year - Targeted gap filling
 * Fetches movies/TV shows for a specific year from TMDB
 *
 * Query params:
 *   ?key=AUTH_KEY       (required)
 *   &year=2024          (required)
 *   &type=movie|tv|both (default: both)
 *   &pages=N            (default: 3, max 10)
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(300);

$AUTH_KEY = 'ms2_sync_2024_findto';
$providedKey = isset($_GET['key']) ? $_GET['key'] : '';
if ($providedKey !== $AUTH_KEY) {
    header('HTTP/1.1 403 Forbidden');
    die("Unauthorized\n");
}

$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$dbuser = 'ejaguiar1_tvmoviestrailers';
$dbpass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

$year = isset($_GET['year']) ? (int)$_GET['year'] : 0;
$type = isset($_GET['type']) ? $_GET['type'] : 'both';
$pages = isset($_GET['pages']) ? min((int)$_GET['pages'], 10) : 3;

if ($year < 1900 || $year > 2030) {
    die("Invalid year. Must be between 1900 and 2030.\n");
}

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $dbuser, $dbpass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    die("DB connection failed: " . $e->getMessage() . "\n");
}

echo "=== Fetch by Year: {$year} ===\n";
echo "Type: {$type} | Pages: {$pages}\n";
echo "Time: " . date('Y-m-d H:i:s T') . "\n\n";

// Load existing tmdb_ids
$existingTmdb = array();
$stmt = $pdo->query("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL");
while ($row = $stmt->fetch()) {
    $existingTmdb[(int)$row['tmdb_id']] = true;
}

$existingYoutubeIds = array();
$stmt = $pdo->query("SELECT youtube_id FROM trailers");
while ($row = $stmt->fetch()) {
    $existingYoutubeIds[$row['youtube_id']] = true;
}

echo "Existing DB entries: " . count($existingTmdb) . "\n\n";

$totalAdded = 0;
$totalSkipped = 0;
$totalTrailers = 0;
$errors = 0;

function tmdb_request_year($url) {
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
    if ($httpCode !== 200 || !$response) return null;
    return json_decode($response, true);
}

function process_year_item($item, $contentType) {
    global $pdo, $existingTmdb, $existingYoutubeIds, $TMDB_API_KEY;
    global $totalAdded, $totalSkipped, $totalTrailers, $errors;

    $tmdbId = (int)$item['id'];
    if (isset($existingTmdb[$tmdbId])) {
        $totalSkipped++;
        return;
    }

    $detailType = ($contentType === 'tv') ? 'tv' : 'movie';
    $detailUrl = "https://api.themoviedb.org/3/{$detailType}/{$tmdbId}?api_key={$TMDB_API_KEY}&append_to_response=videos";
    $details = tmdb_request_year($detailUrl);
    if (!$details) { $errors++; return; }

    $title = isset($details['title']) ? $details['title'] : (isset($details['name']) ? $details['name'] : 'Unknown');
    $genres = array();
    if (isset($details['genres'])) {
        foreach ($details['genres'] as $g) $genres[] = $g['name'];
    }
    $genreStr = implode(', ', $genres);
    $description = isset($details['overview']) ? $details['overview'] : '';
    $releaseDate = ($contentType === 'tv') ?
        (isset($details['first_air_date']) ? $details['first_air_date'] : '') :
        (isset($details['release_date']) ? $details['release_date'] : '');
    $releaseYear = $releaseDate ? (int)substr($releaseDate, 0, 4) : null;
    $rating = isset($details['vote_average']) ? round($details['vote_average'], 1) : null;
    $imdbId = isset($details['imdb_id']) ? $details['imdb_id'] : null;
    $runtime = ($contentType === 'tv') ?
        (isset($details['episode_run_time'][0]) ? $details['episode_run_time'][0] : null) :
        (isset($details['runtime']) ? $details['runtime'] : null);

    try {
        $stmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ?");
        $stmt->execute(array($tmdbId));
        if ($stmt->fetch()) { $existingTmdb[$tmdbId] = true; $totalSkipped++; return; }

        $stmt = $pdo->prepare("INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, imdb_id, tmdb_id, runtime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->execute(array($title, $contentType, $genreStr, $description, $releaseYear, $rating, $imdbId, $tmdbId, $runtime));
        $movieId = $pdo->lastInsertId();
        $existingTmdb[$tmdbId] = true;

        $trailersAdded = 0;
        if (isset($details['videos']['results'])) {
            foreach ($details['videos']['results'] as $video) {
                if ($video['site'] !== 'YouTube') continue;
                if (!in_array($video['type'], array('Trailer', 'Teaser'))) continue;
                $youtubeId = $video['key'];
                if (isset($existingYoutubeIds[$youtubeId])) continue;
                $stmt = $pdo->prepare("INSERT INTO trailers (movie_id, youtube_id, title, priority, source, is_active) VALUES (?, ?, ?, ?, 'tmdb', TRUE)");
                $priority = ($video['type'] === 'Trailer') ? 1 : 0;
                $stmt->execute(array($movieId, $youtubeId, $video['name'], $priority));
                $existingYoutubeIds[$youtubeId] = true;
                $trailersAdded++;
                $totalTrailers++;
            }
        }

        $posterPath = isset($item['poster_path']) ? $item['poster_path'] : (isset($details['poster_path']) ? $details['poster_path'] : null);
        if ($posterPath) {
            $stmt = $pdo->prepare("INSERT INTO thumbnails (movie_id, url, is_primary) VALUES (?, ?, TRUE)");
            $stmt->execute(array($movieId, "https://image.tmdb.org/t/p/w500" . $posterPath));
        }

        $totalAdded++;
        echo "  + [{$contentType}] {$title} ({$releaseYear}) - {$trailersAdded} trailers\n";
    } catch (PDOException $e) {
        $errors++;
        echo "  ! Error: " . $e->getMessage() . "\n";
    }
    usleep(250000);
}

// Fetch movies for year
if ($type === 'movie' || $type === 'both') {
    echo "--- Movies for {$year} ---\n";
    for ($page = 1; $page <= $pages; $page++) {
        $url = "https://api.themoviedb.org/3/discover/movie?api_key={$TMDB_API_KEY}&primary_release_year={$year}&sort_by=popularity.desc&page={$page}";
        echo "Page {$page}...\n";
        $data = tmdb_request_year($url);
        if (!$data || !isset($data['results'])) { echo "  Failed\n"; $errors++; continue; }
        foreach ($data['results'] as $item) process_year_item($item, 'movie');
    }
    echo "\n";
}

// Fetch TV shows for year
if ($type === 'tv' || $type === 'both') {
    echo "--- TV Shows for {$year} ---\n";
    for ($page = 1; $page <= $pages; $page++) {
        $url = "https://api.themoviedb.org/3/discover/tv?api_key={$TMDB_API_KEY}&first_air_date_year={$year}&sort_by=popularity.desc&page={$page}";
        echo "Page {$page}...\n";
        $data = tmdb_request_year($url);
        if (!$data || !isset($data['results'])) { echo "  Failed\n"; $errors++; continue; }
        foreach ($data['results'] as $item) process_year_item($item, 'tv');
    }
    echo "\n";
}

// Log to sync_log
$status = ($errors > 0 && $totalAdded > 0) ? 'partial' : ($errors > 0 ? 'failed' : 'success');
$logMsg = "Year:{$year} Type:{$type} Pages:{$pages} Added:{$totalAdded} Skipped:{$totalSkipped} Trailers:{$totalTrailers} Errors:{$errors}";
try {
    $stmt = $pdo->prepare("INSERT INTO sync_log (sync_type, status, items_processed, error_message) VALUES (?, ?, ?, ?)");
    $stmt->execute(array('tmdb_fetch_year_' . $year, $status, $totalAdded, substr($logMsg, 0, 500)));
} catch (PDOException $e) {}

echo "=== SUMMARY ===\n";
echo "Year: {$year}\n";
echo "Added: {$totalAdded}\n";
echo "Skipped: {$totalSkipped}\n";
echo "Trailers: {$totalTrailers}\n";
echo "Errors: {$errors}\n";
echo "Status: {$status}\n";

// Count for this year
$stmt = $pdo->prepare("SELECT type, COUNT(*) as count FROM movies WHERE release_year = ? GROUP BY type");
$stmt->execute(array($year));
$yearCounts = $stmt->fetchAll();
echo "\nYear {$year} now has:\n";
foreach ($yearCounts as $yc) {
    echo "  {$yc['type']}: {$yc['count']}\n";
}

$stmt = $pdo->query("SELECT COUNT(*) as total FROM movies");
echo "\nTotal in database: " . $stmt->fetchColumn() . "\n";
echo "Done: " . date('Y-m-d H:i:s T') . "\n";
?>
