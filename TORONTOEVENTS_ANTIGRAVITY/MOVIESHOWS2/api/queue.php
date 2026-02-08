<?php
/**
 * Manage user queue (add/remove/reorder movies)
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, DELETE');
header('Access-Control-Allow-Headers: Content-Type');

require_once 'db-config.php';

$pdo = getDbConnection();

if (!$pdo) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => 'Database connection failed'));
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$input = json_decode(file_get_contents('php://input'), true);

try {
    if ($method === 'GET') {
        // Get user's queue
        $userId = isset($_GET['user_id']) ? $_GET['user_id'] : 0;

        $stmt = $pdo->prepare("
            SELECT 
                uq.id,
                uq.position,
                uq.watched,
                uq.watch_count,
                uq.last_watched_at,
                m.id as movie_id,
                m.title,
                m.type,
                m.genre,
                m.description,
                m.release_year,
                m.imdb_rating,
                (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE ORDER BY priority DESC LIMIT 1) as trailer_id,
                (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
            FROM user_queues uq
            JOIN movies m ON uq.movie_id = m.id
            WHERE uq.user_id = ?
            ORDER BY uq.position ASC
        ");

        $stmt->execute(array($userId));
        $queue = $stmt->fetchAll();

        echo json_encode(array(
            'success' => true,
            'queue' => $queue
        ));

    } elseif ($method === 'POST') {
        // Add movie to queue
        $userId = isset($input['user_id']) ? $input['user_id'] : 0;
        $movieId = isset($input['movie_id']) ? $input['movie_id'] : 0;

        // Get next position
        $stmt = $pdo->prepare("SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM user_queues WHERE user_id = ?");
        $stmt->execute(array($userId));
        $nextPos = $stmt->fetchColumn();

        $stmt = $pdo->prepare("
            INSERT INTO user_queues (user_id, movie_id, position)
            VALUES (?, ?, ?)
            ON DUPLICATE KEY UPDATE position = ?
        ");

        $stmt->execute(array($userId, $movieId, $nextPos, $nextPos));

        echo json_encode(array(
            'success' => true,
            'message' => 'Movie added to queue'
        ));

    } elseif ($method === 'DELETE') {
        // Remove movie from queue
        $userId = isset($input['user_id']) ? $input['user_id'] : 0;
        $movieId = isset($input['movie_id']) ? $input['movie_id'] : 0;

        $stmt = $pdo->prepare("DELETE FROM user_queues WHERE user_id = ? AND movie_id = ?");
        $stmt->execute(array($userId, $movieId));

        echo json_encode(array(
            'success' => true,
            'message' => 'Movie removed from queue'
        ));
    }

} catch (PDOException $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => $e->getMessage()));
}
?>
