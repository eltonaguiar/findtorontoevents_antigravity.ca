<?php
session_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 204 No Content');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

// Create table if it doesn't exist
$conn->query("CREATE TABLE IF NOT EXISTS movie_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_movie (user_id, movie_id),
    INDEX idx_user (user_id),
    INDEX idx_movie (movie_id)
)");

// Get all like counts
$count_query = "SELECT movie_id, COUNT(*) as count FROM movie_likes GROUP BY movie_id";
$count_result = $conn->query($count_query);

$like_counts = array();
while ($row = $count_result->fetch_assoc()) {
    $like_counts[(int) $row['movie_id']] = (int) $row['count'];
}

// If user is logged in, get their liked movies
$user_likes = array();
if (isset($_SESSION['user'])) {
    $user_id = (int) $_SESSION['user']['id'];
    $user_query = "SELECT movie_id FROM movie_likes WHERE user_id = $user_id";
    $user_result = $conn->query($user_query);

    while ($row = $user_result->fetch_assoc()) {
        $user_likes[] = (int) $row['movie_id'];
    }
}

echo json_encode(array(
    'like_counts' => $like_counts,
    'user_likes' => $user_likes
));

$conn->close();
?>