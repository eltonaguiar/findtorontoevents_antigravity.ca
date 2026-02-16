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

    // Fetch movies with basic info
    $stmt = $pdo->query("
        (SELECT
            m.id,
            m.title,
            m.type,
            m.genre,
            m.description,
            m.release_year,
            m.imdb_rating,
            m.tmdb_id,
            t.youtube_id as trailer_id,
            th.url as thumbnail
        FROM movies m
        INNER JOIN trailers t ON m.id = t.movie_id
        LEFT JOIN thumbnails th ON m.id = th.movie_id AND th.is_primary = TRUE
        WHERE t.is_active = TRUE AND m.type = 'movie'
        ORDER BY m.created_at DESC)
        UNION ALL
        (SELECT
            m.id,
            m.title,
            m.type,
            m.genre,
            m.description,
            m.release_year,
            m.imdb_rating,
            m.tmdb_id,
            t.youtube_id as trailer_id,
            th.url as thumbnail
        FROM movies m
        INNER JOIN trailers t ON m.id = t.movie_id
        LEFT JOIN thumbnails th ON m.id = th.movie_id AND th.is_primary = TRUE
        WHERE t.is_active = TRUE AND m.type = 'tv'
        ORDER BY m.created_at DESC)
    ");

    $movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Fetch streaming providers for all movies
    $movieIds = array_column($movies, 'id');
    $providers = [];

    if (!empty($movieIds)) {
        $placeholders = implode(',', array_fill(0, count($movieIds), '?'));
        $providerStmt = $pdo->prepare("
            SELECT
                movie_id,
                provider_id,
                provider_name,
                provider_logo,
                display_priority
            FROM streaming_providers
            WHERE movie_id IN ($placeholders) AND is_active = 1
            ORDER BY movie_id, display_priority ASC
        ");
        $providerStmt->execute($movieIds);

        // Group providers by movie_id
        foreach ($providerStmt->fetchAll(PDO::FETCH_ASSOC) as $provider) {
            $movieId = $provider['movie_id'];
            unset($provider['movie_id']);

            if (!isset($providers[$movieId])) {
                $providers[$movieId] = [];
            }

            $providers[$movieId][] = [
                'id' => $provider['provider_id'],
                'name' => $provider['provider_name'],
                'logo' => $provider['provider_logo']
            ];
        }
    }

    // Attach providers to movies
    foreach ($movies as &$movie) {
        $movie['providers'] = $providers[$movie['id']] ?? [];
    }
    unset($movie);

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