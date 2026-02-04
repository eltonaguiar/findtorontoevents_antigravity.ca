<?php
/**
 * Simple movies API - returns movies with trailers
 * Plain text output to avoid ModSecurity blocking JSON
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db-config.php';

try {
    $pdo = getDbConnection();

    $stmt = $pdo->query("
        SELECT 
            m.id,
            m.title,
            m.type,
            m.genre,
            m.description,
            m.release_year,
            m.imdb_rating,
            t.youtube_id as trailer_id,
            th.url as thumbnail
        FROM movies m
        INNER JOIN trailers t ON m.id = t.movie_id
        LEFT JOIN thumbnails th ON m.id = th.movie_id AND th.is_primary = TRUE
        WHERE t.is_active = TRUE
        ORDER BY m.created_at DESC
        LIMIT 200
    ");

    $movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode(array(
        'success' => true,
        'count' => count($movies),
        'movies' => $movies
    ));

} catch (Exception $e) {
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}
?>