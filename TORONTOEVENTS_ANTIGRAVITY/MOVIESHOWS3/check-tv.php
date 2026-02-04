<?php
header('Content-Type: text/plain; charset=utf-8');

require_once 'api/db-config.php';

$pdo = getDbConnection();

echo "TV SHOWS CHECK\n";
echo "==============\n\n";

// Count TV shows total
$stmt = $pdo->query("SELECT COUNT(*) FROM movies WHERE type = 'tv'");
$tvTotal = $stmt->fetchColumn();
echo "Total TV shows in database: $tvTotal\n";

// Count TV shows WITH trailers
$stmt = $pdo->query("
    SELECT COUNT(DISTINCT m.id) 
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE m.type = 'tv' AND t.is_active = TRUE
");
$tvWithTrailers = $stmt->fetchColumn();
echo "TV shows WITH trailers: $tvWithTrailers\n\n";

// Sample TV shows with trailers
if ($tvWithTrailers > 0) {
    echo "Sample TV shows with trailers:\n";
    $stmt = $pdo->query("
        SELECT m.title, m.release_year, t.youtube_id
        FROM movies m
        INNER JOIN trailers t ON m.id = t.movie_id
        WHERE m.type = 'tv' AND t.is_active = TRUE
        LIMIT 10
    ");
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        echo "  - {$row['title']} ({$row['release_year']}) - YT: {$row['youtube_id']}\n";
    }
}
?>