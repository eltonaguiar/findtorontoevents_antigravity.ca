<?php
/**
 * Playlist Sharing API
 * Create and share playlists
 */

require_once 'db-config.php';

function getUserId()
{
    session_start();
    return $_SESSION['user_id'] ?? null;
}

/**
 * Generate unique share code
 */
function generateShareCode()
{
    return substr(md5(uniqid(rand(), true)), 0, 12);
}

/**
 * Create shareable playlist
 */
function createPlaylist($pdo, $userId)
{
    $data = getRequestBody();

    if (!isset($data['movies']) || !is_array($data['movies'])) {
        sendError('movies array is required', 400);
    }

    $shareCode = generateShareCode();

    $pdo->beginTransaction();

    try {
        // Create playlist
        $sql = "INSERT INTO shared_playlists (share_code, user_id, title, description, is_public) 
                VALUES (?, ?, ?, ?, ?)";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            $shareCode,
            $userId,
            $data['title'] ?? 'My MovieShows Playlist',
            $data['description'] ?? null,
            $data['is_public'] ?? false
        ]);

        $playlistId = $pdo->lastInsertId();

        // Add movies to playlist
        $sql = "INSERT INTO playlist_items (playlist_id, movie_id, position) VALUES (?, ?, ?)";
        $stmt = $pdo->prepare($sql);

        foreach ($data['movies'] as $index => $movieId) {
            $stmt->execute([$playlistId, $movieId, $index + 1]);
        }

        $pdo->commit();

        $shareUrl = "https://findtorontoevents.ca/MOVIESHOWS/?playlist=" . $shareCode;

        sendJson([
            'id' => $playlistId,
            'share_code' => $shareCode,
            'share_url' => $shareUrl,
            'movie_count' => count($data['movies'])
        ], 201);

    } catch (Exception $e) {
        $pdo->rollBack();
        sendError('Failed to create playlist: ' . $e->getMessage(), 500);
    }
}

/**
 * Get playlist by share code
 */
function getPlaylist($pdo, $shareCode)
{
    // Increment view count
    $sql = "UPDATE shared_playlists SET view_count = view_count + 1 WHERE share_code = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$shareCode]);

    // Get playlist
    $sql = "SELECT * FROM shared_playlists WHERE share_code = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$shareCode]);
    $playlist = $stmt->fetch();

    if (!$playlist) {
        sendError('Playlist not found', 404);
    }

    // Check if expired
    if ($playlist['expires_at'] && strtotime($playlist['expires_at']) < time()) {
        sendError('Playlist has expired', 410);
    }

    // Get movies
    $sql = "SELECT pi.position, m.* 
            FROM playlist_items pi
            JOIN movies m ON pi.movie_id = m.id
            WHERE pi.playlist_id = ?
            ORDER BY pi.position";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$playlist['id']]);
    $movies = $stmt->fetchAll();

    // Get trailers and thumbnails for each movie
    foreach ($movies as &$movie) {
        $movie['trailers'] = getMovieTrailers($pdo, $movie['id']);
        $movie['thumbnails'] = getMovieThumbnails($pdo, $movie['id']);
    }

    $playlist['movies'] = $movies;
    $playlist['movie_count'] = count($movies);

    sendJson($playlist);
}

/**
 * Copy playlist to user's queue
 */
function copyPlaylistToQueue($pdo, $userId, $shareCode)
{
    // Get playlist
    $sql = "SELECT id FROM shared_playlists WHERE share_code = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$shareCode]);
    $playlist = $stmt->fetch();

    if (!$playlist) {
        sendError('Playlist not found', 404);
    }

    // Get movies from playlist
    $sql = "SELECT movie_id FROM playlist_items WHERE playlist_id = ? ORDER BY position";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$playlist['id']]);
    $movies = $stmt->fetchAll(PDO::FETCH_COLUMN);

    // Get next position in user's queue
    $sql = "SELECT COALESCE(MAX(position), 0) as max_pos FROM user_queues WHERE user_id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$userId]);
    $startPosition = $stmt->fetchColumn() + 1;

    // Add to queue
    $sql = "INSERT IGNORE INTO user_queues (user_id, movie_id, position) VALUES (?, ?, ?)";
    $stmt = $pdo->prepare($sql);

    $added = 0;
    foreach ($movies as $index => $movieId) {
        $stmt->execute([$userId, $movieId, $startPosition + $index]);
        $added += $stmt->rowCount();
    }

    sendJson(['message' => 'Playlist copied to queue', 'added' => $added]);
}

/**
 * Delete playlist
 */
function deletePlaylist($pdo, $userId, $playlistId)
{
    $sql = "DELETE FROM shared_playlists WHERE id = ? AND user_id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$playlistId, $userId]);

    if ($stmt->rowCount() === 0) {
        sendError('Playlist not found', 404);
    }

    sendJson(['message' => 'Playlist deleted']);
}

// Main request handler
$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$method = $_SERVER['REQUEST_METHOD'];
$shareCode = $_GET['code'] ?? null;
$playlistId = $_GET['id'] ?? null;

switch ($method) {
    case 'GET':
        if (!$shareCode) {
            sendError('Share code required', 400);
        }
        getPlaylist($pdo, $shareCode);
        break;

    case 'POST':
        $userId = getUserId();
        if (!$userId) {
            sendError('Authentication required', 401);
        }

        if (isset($_GET['copy']) && $shareCode) {
            copyPlaylistToQueue($pdo, $userId, $shareCode);
        } else {
            createPlaylist($pdo, $userId);
        }
        break;

    case 'DELETE':
        $userId = getUserId();
        if (!$userId) {
            sendError('Authentication required', 401);
        }

        if (!$playlistId) {
            sendError('Playlist ID required', 400);
        }
        deletePlaylist($pdo, $userId, $playlistId);
        break;

    default:
        sendError('Method not allowed', 405);
}
