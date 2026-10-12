<?php
/**
 * Get movies from database with trailers and thumbnails
 */
error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

require_once 'db-config.php';
require_once dirname(__FILE__) . '/../../MOVIESHOWS3/api/tmdb-ratings.php';

$pdo = getDbConnection();

if (!$pdo) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('success' => false, 'error' => 'Database connection failed'));
    exit;
}

try {
    $stmt = $pdo->query("
        SELECT
            m.id,
            m.title,
            m.type,
            m.genre,
            m.description,
            m.release_year,
            m.imdb_rating,
            m.imdb_id,
            m.tmdb_id,
            m.runtime,
            t.youtube_id as trailer_id,
            (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
        FROM movies m
        INNER JOIN trailers t ON t.movie_id = m.id AND t.is_active = TRUE
        WHERE t.youtube_id IS NOT NULL AND t.youtube_id != ''
        GROUP BY m.id
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 5000
    ");

    $movies = $stmt->fetchAll();
    $movies = attachTmdbRatingDetails($pdo, $movies);

    echo json_encode(array(
        'success' => true,
        'count' => count($movies),
        'rating_source' => 'TMDB',
        'rating_scale' => 10,
        'movies' => $movies
    ));

} catch (PDOException $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('success' => false, 'error' => $e->getMessage()));
}
?>
