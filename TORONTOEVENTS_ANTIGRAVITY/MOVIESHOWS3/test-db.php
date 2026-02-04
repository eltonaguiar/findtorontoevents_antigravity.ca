<?php
/**
 * Simple database test - check what's actually in the database
 */
header('Content-Type: text/plain; charset=utf-8');

require_once 'api/db-config.php';

$pdo = getDbConnection();

if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Database Test\n";
echo "=============\n\n";

// Check movies count
$stmt = $pdo->query("SELECT COUNT(*) FROM movies");
$movieCount = $stmt->fetchColumn();
echo "Total movies: $movieCount\n\n";

// Check movies with trailers
$stmt = $pdo->query("
    SELECT COUNT(DISTINCT m.id) 
    FROM movies m 
    INNER JOIN trailers t ON m.id = t.movie_id 
    WHERE t.is_active = TRUE
");
$moviesWithTrailers = $stmt->fetchColumn();
echo "Movies with trailers: $moviesWithTrailers\n\n";

// Get sample movies
echo "Sample movies:\n";
echo "==============\n";
$stmt = $pdo->query("
    SELECT 
        m.id,
        m.title,
        m.release_year,
        m.imdb_rating,
        (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE LIMIT 1) as trailer_id,
        (SELECT url FROM thumbnails WHERE movie_id = m.id LIMIT 1) as thumbnail
    FROM movies m
    LIMIT 10
");

while ($row = $stmt->fetch()) {
    echo "\nID: {$row['id']}\n";
    echo "Title: {$row['title']}\n";
    echo "Year: {$row['release_year']}\n";
    echo "Rating: {$row['imdb_rating']}\n";
    echo "Trailer: " . ($row['trailer_id'] ? $row['trailer_id'] : 'NONE') . "\n";
    echo "Thumbnail: " . ($row['thumbnail'] ? 'YES' : 'NO') . "\n";
    echo "---\n";
}

echo "\n\nDone!\n";
?>