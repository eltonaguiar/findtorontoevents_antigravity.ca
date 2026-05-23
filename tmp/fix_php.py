content = r'''<?php
/**
 * Simple movies API - returns movies with trailers
 * Plain text output to avoid ModSecurity blocking JSON
 */
header('Content-Type: application/json');
// CORS headers are handled exclusively by .htaccess in this directory
// to prevent duplicate Access-Control-Allow-Origin headers.
// NOTE: Do NOT add header('Access-Control-Allow-Origin') here --
// findtorontoevents.ca runs PHP 5.2.17 which lacks header_remove(),
// and duplicating the header causes browsers to reject CORS requests.

require_once 'db-config.php';

try {
    $pdo = getDbConnection();

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
?>'''

target = r'E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS3\api\get-movies.php'
with open(target, 'w', newline='\n') as f:
    f.write(content)
print(f'Written {len(content)} bytes to {target}')
