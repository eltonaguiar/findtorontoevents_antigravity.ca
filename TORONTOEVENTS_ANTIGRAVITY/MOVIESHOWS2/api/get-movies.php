<?php
/**
 * Get movies from database with trailers and thumbnails
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db-config.php';

$pdo = getDbConnection();

if (!$pdo) {
    http_response_code(500);
    echo json_encode(['error' => 'Database connection failed']);
    exit;
}

try {
    // Get all movies with their trailers and thumbnails
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
            (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE ORDER BY priority DESC LIMIT 1) as trailer_id,
            (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
        FROM movies m
        ORDER BY m.created_at DESC
        LIMIT 100
    ");

    $movies = $stmt->fetchAll();

    echo json_encode([
        'success' => true,
        'count' => count($movies),
        'movies' => $movies
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
?>