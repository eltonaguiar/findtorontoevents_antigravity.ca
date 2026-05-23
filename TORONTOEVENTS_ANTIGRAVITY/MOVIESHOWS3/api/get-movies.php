<?php
/**
 * Movies API - returns movies with trailers + streaming providers
 */
// Suppress HTML error output — always return clean JSON
error_reporting(0);
ini_set('display_errors', '0');

// CORS headers — set here in PHP to avoid duplication with .htaccess
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

// Handle OPTIONS preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$dbConfigPath = dirname(__FILE__) . '/db-config.php';
if (!file_exists($dbConfigPath)) {
    echo json_encode(array(
        'success' => false,
        'error' => 'Missing db-config.php'
    ));
    exit;
}

require_once $dbConfigPath;

try {
    if (!function_exists('getDbConnection')) {
        throw new Exception('getDbConnection() is not defined');
    }

    $pdo = getDbConnection();
    if ($pdo === null) {
        throw new Exception('Database connection failed — check db-config.php credentials');
    }

    // Return one row per movie to prevent inflated counts when multiple trailers/thumbnails exist.
    $stmt = $pdo->query("
        SELECT
            m.id,
            m.title,
            m.type,
            m.genre,
            m.description,
            m.release_year,
            m.imdb_rating,
            m.tmdb_id,
            (
                SELECT t.youtube_id
                FROM trailers t
                WHERE t.movie_id = m.id
                  AND t.is_active = TRUE
                  AND t.youtube_id IS NOT NULL
                  AND t.youtube_id != ''
                ORDER BY t.priority ASC, t.id ASC
                LIMIT 1
            ) AS trailer_id,
            (
                SELECT th.url
                FROM thumbnails th
                WHERE th.movie_id = m.id
                ORDER BY th.is_primary DESC, th.id ASC
                LIMIT 1
            ) AS thumbnail
        FROM movies m
        WHERE EXISTS (
            SELECT 1
            FROM trailers t2
            WHERE t2.movie_id = m.id
              AND t2.is_active = TRUE
              AND t2.youtube_id IS NOT NULL
              AND t2.youtube_id != ''
        )
        ORDER BY m.created_at DESC
    ");

    $movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Fetch streaming providers (if table exists)
    $providers = array();
    try {
        $provStmt = $pdo->query("
            SELECT movie_id, provider_name, provider_logo
            FROM streaming_providers
            ORDER BY movie_id, provider_name
        ");
        $provRows = $provStmt->fetchAll(PDO::FETCH_ASSOC);
        foreach ($provRows as $row) {
            $mid = $row['movie_id'];
            if (!isset($providers[$mid])) {
                $providers[$mid] = array();
            }
            $providers[$mid][] = array(
                'name' => $row['provider_name'],
                'logo' => $row['provider_logo']
            );
        }
    } catch (Exception $e2) {
        // streaming_providers table may not exist yet — continue without it
    }

    // Merge providers into movie data
    foreach ($movies as &$movie) {
        $mid = $movie['id'];
        $movie['providers'] = isset($providers[$mid]) ? $providers[$mid] : array();
    }
    unset($movie);

    $movieCount = 0;
    $tvCount = 0;
    foreach ($movies as $movieRow) {
        if ($movieRow['type'] === 'movie') {
            $movieCount++;
        } elseif ($movieRow['type'] === 'tv') {
            $tvCount++;
        }
    }

    echo json_encode(array(
        'success' => true,
        'count' => count($movies),
        'movie_count' => $movieCount,
        'tv_count' => $tvCount,
        'movies' => $movies
    ));

} catch (Exception $e) {
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}
?>
