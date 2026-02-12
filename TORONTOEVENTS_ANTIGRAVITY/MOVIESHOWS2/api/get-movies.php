<?php
/**
 * Get movies from database with trailers and thumbnails
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db-config.php';

$pdo = getDbConnection();

if (!$pdo) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => 'Database connection failed'));
    exit;
}

try {
    // Get movies that have active trailers, ordered by newest first
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
        ORDER BY m.imdb_rating DESC, m.created_at DESC
        LIMIT 500
    ");

    $movies = $stmt->fetchAll();

    echo json_encode(array(
        'success' => true,
        'count' => count($movies),
        'movies' => $movies
    ));

} catch (PDOException $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => $e->getMessage()));
}
?>