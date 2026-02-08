<?php
/**
 * Admin Add Single Title - Add a specific movie/TV show by TMDB ID
 *
 * Query params:
 *   ?key=AUTH_KEY       (required)
 *   &tmdb_id=12345      (required)
 *   &type=movie|tv      (required)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$AUTH_KEY = 'ms2_sync_2024_findto';
$providedKey = isset($_GET['key']) ? $_GET['key'] : '';
if ($providedKey !== $AUTH_KEY) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('success' => false, 'error' => 'Unauthorized'));
    exit;
}

$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$dbuser = 'ejaguiar1_tvmoviestrailers';
$dbpass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

$tmdbId = isset($_GET['tmdb_id']) ? (int)$_GET['tmdb_id'] : 0;
$contentType = isset($_GET['type']) ? $_GET['type'] : '';

if (!$tmdbId || !in_array($contentType, array('movie', 'tv'))) {
    echo json_encode(array('success' => false, 'error' => 'Missing tmdb_id or type'));
    exit;
}

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $dbuser, $dbpass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    echo json_encode(array('success' => false, 'error' => 'DB connection failed'));
    exit;
}

// Check if already exists
$stmt = $pdo->prepare("SELECT id, title FROM movies WHERE tmdb_id = ?");
$stmt->execute(array($tmdbId));
$existing = $stmt->fetch();
if ($existing) {
    echo json_encode(array('success' => false, 'error' => 'Already in database', 'title' => $existing['title'], 'id' => $existing['id']));
    exit;
}

// Fetch from TMDB
$detailUrl = "https://api.themoviedb.org/3/{$contentType}/{$tmdbId}?api_key={$TMDB_API_KEY}&append_to_response=videos";
$ch = curl_init();
curl_setopt_array($ch, array(
    CURLOPT_URL => $detailUrl,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 15,
    CURLOPT_HTTPHEADER => array('Authorization: Bearer ' . $TMDB_READ_TOKEN, 'Accept: application/json'),
    CURLOPT_SSL_VERIFYPEER => false
));
$response = curl_exec($ch);
curl_close($ch);
$details = json_decode($response, true);

if (!$details || isset($details['status_code'])) {
    echo json_encode(array('success' => false, 'error' => 'TMDB item not found'));
    exit;
}

$title = isset($details['title']) ? $details['title'] : (isset($details['name']) ? $details['name'] : 'Unknown');
$genres = array();
if (isset($details['genres'])) { foreach ($details['genres'] as $g) $genres[] = $g['name']; }
$genreStr = implode(', ', $genres);
$description = isset($details['overview']) ? $details['overview'] : '';
$releaseDate = ($contentType === 'tv') ? (isset($details['first_air_date']) ? $details['first_air_date'] : '') : (isset($details['release_date']) ? $details['release_date'] : '');
$releaseYear = $releaseDate ? (int)substr($releaseDate, 0, 4) : null;
$rating = isset($details['vote_average']) ? round($details['vote_average'], 1) : null;
$imdbId = isset($details['imdb_id']) ? $details['imdb_id'] : null;
$runtime = ($contentType === 'tv') ? (isset($details['episode_run_time'][0]) ? $details['episode_run_time'][0] : null) : (isset($details['runtime']) ? $details['runtime'] : null);

try {
    $stmt = $pdo->prepare("INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, imdb_id, tmdb_id, runtime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute(array($title, $contentType, $genreStr, $description, $releaseYear, $rating, $imdbId, $tmdbId, $runtime));
    $movieId = $pdo->lastInsertId();

    $trailersAdded = 0;
    if (isset($details['videos']['results'])) {
        $existingYt = array();
        $stmt2 = $pdo->query("SELECT youtube_id FROM trailers");
        while ($r = $stmt2->fetch()) $existingYt[$r['youtube_id']] = true;

        foreach ($details['videos']['results'] as $video) {
            if ($video['site'] !== 'YouTube') continue;
            if (!in_array($video['type'], array('Trailer', 'Teaser'))) continue;
            if (isset($existingYt[$video['key']])) continue;
            $stmt = $pdo->prepare("INSERT INTO trailers (movie_id, youtube_id, title, priority, source, is_active) VALUES (?, ?, ?, ?, 'tmdb', TRUE)");
            $priority = ($video['type'] === 'Trailer') ? 1 : 0;
            $stmt->execute(array($movieId, $video['key'], $video['name'], $priority));
            $trailersAdded++;
        }
    }

    $posterPath = isset($details['poster_path']) ? $details['poster_path'] : null;
    if ($posterPath) {
        $stmt = $pdo->prepare("INSERT INTO thumbnails (movie_id, url, is_primary) VALUES (?, ?, TRUE)");
        $stmt->execute(array($movieId, "https://image.tmdb.org/t/p/w500" . $posterPath));
    }

    // Log
    $stmt = $pdo->prepare("INSERT INTO sync_log (sync_type, status, items_processed, error_message) VALUES (?, 'success', 1, ?)");
    $stmt->execute(array('admin_add_single', "Added: {$title} ({$releaseYear}) tmdb:{$tmdbId}"));

    echo json_encode(array(
        'success' => true,
        'title' => $title,
        'type' => $contentType,
        'year' => $releaseYear,
        'id' => (int)$movieId,
        'trailers_added' => $trailersAdded,
        'poster' => $posterPath ? "https://image.tmdb.org/t/p/w200{$posterPath}" : null
    ));

} catch (PDOException $e) {
    echo json_encode(array('success' => false, 'error' => $e->getMessage()));
}
?>
