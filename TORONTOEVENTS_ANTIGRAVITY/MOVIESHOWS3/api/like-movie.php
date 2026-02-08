<?php
session_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.0 204 No Content');
    exit;
}

// Check if user is logged in
if (!isset($_SESSION['user'])) {
    header('HTTP/1.0 401 Unauthorized');
    echo json_encode(array('error' => 'Not authenticated'));
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('error' => 'Use POST to like/unlike'));
    exit;
}

// Get POST data
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!isset($data['movie_id'])) {
    echo json_encode(array('error' => 'movie_id required'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

$user_id = (int) $_SESSION['user']['id'];
$movie_id = (int) $data['movie_id'];

// Create movie_likes table if it doesn't exist
$conn->query("CREATE TABLE IF NOT EXISTS movie_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_movie (user_id, movie_id),
    INDEX idx_user (user_id),
    INDEX idx_movie (movie_id)
)");

// Check if already liked
$check_query = "SELECT id FROM movie_likes WHERE user_id = $user_id AND movie_id = $movie_id";
$check_result = $conn->query($check_query);

if ($check_result->num_rows > 0) {
    // Unlike - remove the like
    $delete_query = "DELETE FROM movie_likes WHERE user_id = $user_id AND movie_id = $movie_id";
    $conn->query($delete_query);
    $is_liked = false;
    $action = 'unliked';
} else {
    // Like - add the like
    $insert_query = "INSERT INTO movie_likes (user_id, movie_id) VALUES ($user_id, $movie_id)";
    $conn->query($insert_query);
    $is_liked = true;
    $action = 'liked';
}

// Get total like count for this movie
$count_query = "SELECT COUNT(*) as count FROM movie_likes WHERE movie_id = $movie_id";
$count_result = $conn->query($count_query);
$count_row = $count_result->fetch_assoc();
$like_count = (int) $count_row['count'];

echo json_encode(array(
    'success' => true,
    'action' => $action,
    'is_liked' => $is_liked,
    'like_count' => $like_count,
    'movie_id' => $movie_id
));

$conn->close();
?>