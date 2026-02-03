<?php
/**
 * Trailers API Endpoint
 * GET /api/trailers.php?movie_id=X - Get trailers for a movie
 * POST /api/trailers.php - Add new trailer
 * PUT /api/trailers.php?id=X - Update trailer (priority, status)
 * DELETE /api/trailers.php?id=X - Delete/deactivate trailer
 */

require_once 'db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$method = $_SERVER['REQUEST_METHOD'];
$trailerId = isset($_GET['id']) ? intval($_GET['id']) : null;
$movieId = isset($_GET['movie_id']) ? intval($_GET['movie_id']) : null;

try {
    switch ($method) {
        case 'GET':
            if ($movieId) {
                getMovieTrailers($pdo, $movieId);
            } elseif ($trailerId) {
                getTrailer($pdo, $trailerId);
            } else {
                sendError('movie_id or id parameter required', 400);
            }
            break;

        case 'POST':
            addTrailer($pdo);
            break;

        case 'PUT':
            if (!$trailerId) {
                sendError('Trailer ID required', 400);
            }
            updateTrailer($pdo, $trailerId);
            break;

        case 'DELETE':
            if (!$trailerId) {
                sendError('Trailer ID required', 400);
            }
            deleteTrailer($pdo, $trailerId);
            break;

        default:
            sendError('Method not allowed', 405);
    }
} catch (Exception $e) {
    error_log("Trailers API Error: " . $e->getMessage());
    sendError('Internal server error', 500, $e->getMessage());
}

/**
 * Get all trailers for a movie
 */
function getMovieTrailers($pdo, $movieId)
{
    $sql = "SELECT * FROM trailers WHERE movie_id = ? ORDER BY priority DESC, view_count DESC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$movieId]);
    $trailers = $stmt->fetchAll();

    sendJson(['trailers' => $trailers, 'count' => count($trailers)]);
}

/**
 * Get single trailer
 */
function getTrailer($pdo, $trailerId)
{
    $sql = "SELECT * FROM trailers WHERE id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$trailerId]);
    $trailer = $stmt->fetch();

    if (!$trailer) {
        sendError('Trailer not found', 404);
    }

    sendJson($trailer);
}

/**
 * Add new trailer
 */
function addTrailer($pdo)
{
    $data = getRequestBody();

    if (!isset($data['movie_id']) || !isset($data['youtube_id'])) {
        sendError('movie_id and youtube_id are required', 400);
    }

    // Check if trailer already exists for this movie
    $checkSql = "SELECT id FROM trailers WHERE movie_id = ? AND youtube_id = ?";
    $checkStmt = $pdo->prepare($checkSql);
    $checkStmt->execute([$data['movie_id'], $data['youtube_id']]);

    if ($checkStmt->fetch()) {
        sendError('Trailer already exists for this movie', 409);
    }

    $sql = "INSERT INTO trailers (movie_id, youtube_id, title, priority, source, view_count, duration) 
            VALUES (?, ?, ?, ?, ?, ?, ?)";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        $data['movie_id'],
        $data['youtube_id'],
        $data['title'] ?? null,
        $data['priority'] ?? 0,
        $data['source'] ?? 'manual',
        $data['view_count'] ?? 0,
        $data['duration'] ?? null
    ]);

    $trailerId = $pdo->lastInsertId();

    sendJson(['id' => $trailerId, 'message' => 'Trailer added successfully'], 201);
}

/**
 * Update trailer (priority, status, error tracking)
 */
function updateTrailer($pdo, $trailerId)
{
    $data = getRequestBody();

    $fields = [];
    $values = [];

    $allowedFields = ['priority', 'is_active', 'error_count', 'title', 'view_count', 'duration'];

    foreach ($allowedFields as $field) {
        if (isset($data[$field])) {
            $fields[] = "$field = ?";
            $values[] = $data[$field];
        }
    }

    // Always update last_checked when updating
    $fields[] = "last_checked = NOW()";

    if (count($fields) === 1) { // Only last_checked
        sendError('No fields to update', 400);
    }

    $values[] = $trailerId;
    $sql = "UPDATE trailers SET " . implode(', ', $fields) . " WHERE id = ?";

    $stmt = $pdo->prepare($sql);
    $stmt->execute($values);

    if ($stmt->rowCount() === 0) {
        sendError('Trailer not found', 404);
    }

    sendJson(['message' => 'Trailer updated successfully']);
}

/**
 * Delete/deactivate trailer
 */
function deleteTrailer($pdo, $trailerId)
{
    // Soft delete by setting is_active = false
    $sql = "UPDATE trailers SET is_active = 0 WHERE id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$trailerId]);

    if ($stmt->rowCount() === 0) {
        sendError('Trailer not found', 404);
    }

    sendJson(['message' => 'Trailer deactivated successfully']);
}
