<?php
session_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 204 No Content');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

// Auto-create table
$conn->query("CREATE TABLE IF NOT EXISTS movie_watch_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    trailer_id VARCHAR(50),
    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_duration_seconds INT DEFAULT 0,
    completed TINYINT(1) DEFAULT 0,
    INDEX idx_user (user_id),
    INDEX idx_movie (movie_id),
    INDEX idx_user_movie (user_id, movie_id)
)");

// GET - retrieve watch history for logged-in user
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (!isset($_SESSION['user'])) {
        echo json_encode(array('watched_ids' => array()));
        exit;
    }

    $user_id = (int) $_SESSION['user']['id'];
    $query = "SELECT DISTINCT movie_id FROM movie_watch_history WHERE user_id = $user_id";
    $result = $conn->query($query);

    $watched_ids = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $watched_ids[] = (int) $row['movie_id'];
        }
    }

    echo json_encode(array('watched_ids' => $watched_ids));
    $conn->close();
    exit;
}

// POST - record a watch event
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_SESSION['user'])) {
        echo json_encode(array('ok' => false, 'error' => 'Not authenticated'));
        $conn->close();
        exit;
    }

    $input = file_get_contents('php://input');
    $data = json_decode($input, true);

    if (!$data || !isset($data['movie_id'])) {
        echo json_encode(array('ok' => false, 'error' => 'movie_id required'));
        $conn->close();
        exit;
    }

    $user_id = (int) $_SESSION['user']['id'];
    $movie_id = (int) $data['movie_id'];
    $trailer_id = isset($data['trailer_id']) ? $conn->real_escape_string($data['trailer_id']) : '';
    $duration = isset($data['duration']) ? (int) $data['duration'] : 0;
    $completed = isset($data['completed']) && $data['completed'] ? 1 : 0;

    $query = "INSERT INTO movie_watch_history (user_id, movie_id, trailer_id, watch_duration_seconds, completed) VALUES ($user_id, $movie_id, '$trailer_id', $duration, $completed)";
    $conn->query($query);

    echo json_encode(array('ok' => true, 'movie_id' => $movie_id));
    $conn->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'Use GET or POST'));
$conn->close();
?>
