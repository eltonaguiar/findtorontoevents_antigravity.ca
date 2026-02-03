<?php
/**
 * UPDATE #35: Simple test endpoint to verify POST works
 */

require_once 'db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'POST') {
    $data = getRequestBody();

    // Log what we received
    error_log("POST data: " . print_r($data, true));

    if (!isset($data['title'])) {
        sendError('Title is required', 400);
    }

    try {
        $sql = "INSERT INTO movies (title, type, release_year, genre, description, source) 
                VALUES (?, ?, ?, ?, ?, ?)";

        $stmt = $pdo->prepare($sql);
        $result = $stmt->execute(array(
            $data['title'],
            isset($data['type']) ? $data['type'] : 'movie',
            isset($data['release_year']) ? $data['release_year'] : null,
            isset($data['genre']) ? $data['genre'] : null,
            isset($data['description']) ? $data['description'] : null,
            isset($data['source']) ? $data['source'] : 'manual'
        ));

        if ($result) {
            $movieId = $pdo->lastInsertId();
            sendJson(array('id' => $movieId, 'message' => 'Movie created'), 201);
        } else {
            sendError('Insert failed', 500);
        }
    } catch (Exception $e) {
        error_log("Error: " . $e->getMessage());
        sendError('Database error: ' . $e->getMessage(), 500);
    }
} else {
    sendError('Method not allowed', 405);
}
