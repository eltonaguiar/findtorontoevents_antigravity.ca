<?php
/**
 * Queue Management API
 * Handles user queue operations: get, add, remove, reorder, mark watched
 */

require_once 'db-config.php';

// Get user ID from session (placeholder - integrate with /fc login)
function getUserId()
{
    session_start();
    return $_SESSION['user_id'] ?? null;
}

/**
 * Get user's queue
 */
function getQueue($pdo, $userId)
{
    $sql = "SELECT uq.*, m.title, m.type, m.genre, m.description, m.release_year,
                   (SELECT COUNT(*) FROM trailers WHERE movie_id = m.id AND is_active = TRUE) as trailer_count,
                   (SELECT COUNT(*) FROM thumbnails WHERE movie_id = m.id) as thumbnail_count
            FROM user_queues uq
            JOIN movies m ON uq.movie_id = m.id
            WHERE uq.user_id = ?
            ORDER BY uq.position ASC";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([$userId]);
    $queue = $stmt->fetchAll();

    // Get trailers and thumbnails for each movie
    foreach ($queue as &$item) {
        $item['trailers'] = getMovieTrailers($pdo, $item['movie_id']);
        $item['thumbnails'] = getMovieThumbnails($pdo, $item['movie_id']);
    }

    sendJson(['queue' => $queue, 'count' => count($queue)]);
}

/**
 * Add movie to queue
 */
function addToQueue($pdo, $userId)
{
    $data = getRequestBody();

    if (!isset($data['movie_id'])) {
        sendError('movie_id is required', 400);
    }

    // Get next position
    $sql = "SELECT COALESCE(MAX(position), 0) + 1 as next_position 
            FROM user_queues WHERE user_id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$userId]);
    $position = $stmt->fetchColumn();

    // Check if already in queue
    $checkSql = "SELECT id FROM user_queues WHERE user_id = ? AND movie_id = ?";
    $checkStmt = $pdo->prepare($checkSql);
    $checkStmt->execute([$userId, $data['movie_id']]);

    if ($checkStmt->fetch()) {
        sendError('Movie already in queue', 409);
    }

    // Add to queue
    $sql = "INSERT INTO user_queues (user_id, movie_id, position) VALUES (?, ?, ?)";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$userId, $data['movie_id'], $position]);

    sendJson(['id' => $pdo->lastInsertId(), 'position' => $position], 201);
}

/**
 * Update queue item (position, watched status)
 */
function updateQueueItem($pdo, $userId, $itemId)
{
    $data = getRequestBody();

    // Verify ownership
    $checkSql = "SELECT id FROM user_queues WHERE id = ? AND user_id = ?";
    $checkStmt = $pdo->prepare($checkSql);
    $checkStmt->execute([$itemId, $userId]);

    if (!$checkStmt->fetch()) {
        sendError('Queue item not found', 404);
    }

    $updates = [];
    $params = [];

    if (isset($data['position'])) {
        $updates[] = "position = ?";
        $params[] = $data['position'];
    }

    if (isset($data['watched'])) {
        $updates[] = "watched = ?";
        $params[] = $data['watched'] ? 1 : 0;

        if ($data['watched']) {
            $updates[] = "watch_count = watch_count + 1";
            $updates[] = "last_watched_at = CURRENT_TIMESTAMP";
        }
    }

    if (empty($updates)) {
        sendError('No updates provided', 400);
    }

    $params[] = $itemId;
    $sql = "UPDATE user_queues SET " . implode(', ', $updates) . " WHERE id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);

    sendJson(['message' => 'Queue item updated']);
}

/**
 * Remove from queue
 */
function removeFromQueue($pdo, $userId, $itemId)
{
    $sql = "DELETE FROM user_queues WHERE id = ? AND user_id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$itemId, $userId]);

    if ($stmt->rowCount() === 0) {
        sendError('Queue item not found', 404);
    }

    // Reorder remaining items
    $sql = "SET @pos = 0; 
            UPDATE user_queues 
            SET position = (@pos := @pos + 1) 
            WHERE user_id = ? 
            ORDER BY position";
    $pdo->exec("SET @pos = 0");
    $stmt = $pdo->prepare("UPDATE user_queues SET position = (@pos := @pos + 1) WHERE user_id = ? ORDER BY position");
    $stmt->execute([$userId]);

    sendJson(['message' => 'Removed from queue']);
}

/**
 * Sync localStorage queue to database
 */
function syncQueue($pdo, $userId)
{
    $data = getRequestBody();

    if (!isset($data['queue']) || !is_array($data['queue'])) {
        sendError('queue array is required', 400);
    }

    $pdo->beginTransaction();

    try {
        // Clear existing queue
        $sql = "DELETE FROM user_queues WHERE user_id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([$userId]);

        // Insert new queue
        $sql = "INSERT INTO user_queues (user_id, movie_id, position, watched, watch_count) 
                VALUES (?, ?, ?, ?, ?)";
        $stmt = $pdo->prepare($sql);

        foreach ($data['queue'] as $index => $item) {
            $stmt->execute([
                $userId,
                $item['movie_id'],
                $index + 1,
                $item['watched'] ?? false,
                $item['watch_count'] ?? 0
            ]);
        }

        $pdo->commit();
        sendJson(['message' => 'Queue synced', 'count' => count($data['queue'])]);

    } catch (Exception $e) {
        $pdo->rollBack();
        sendError('Sync failed: ' . $e->getMessage(), 500);
    }
}

// Main request handler
$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$userId = getUserId();
if (!$userId) {
    sendError('Authentication required', 401);
}

$method = $_SERVER['REQUEST_METHOD'];
$path = $_GET['id'] ?? null;

switch ($method) {
    case 'GET':
        getQueue($pdo, $userId);
        break;

    case 'POST':
        if (isset($_GET['sync'])) {
            syncQueue($pdo, $userId);
        } else {
            addToQueue($pdo, $userId);
        }
        break;

    case 'PUT':
        if (!$path) {
            sendError('Item ID required', 400);
        }
        updateQueueItem($pdo, $userId, $path);
        break;

    case 'DELETE':
        if (!$path) {
            sendError('Item ID required', 400);
        }
        removeFromQueue($pdo, $userId, $path);
        break;

    default:
        sendError('Method not allowed', 405);
}
