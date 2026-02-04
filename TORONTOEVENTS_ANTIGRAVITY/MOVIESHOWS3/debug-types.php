<?php
/**
 * Debug: Check what types we have in database
 */
header('Content-Type: text/plain; charset=utf-8');

require_once 'api/db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Database Type Analysis\n";
echo "======================\n\n";

// Count by type
$stmt = $pdo->query("
    SELECT type, COUNT(*) as count 
    FROM movies 
    GROUP BY type
");

echo "Movies by type:\n";
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo "  {$row['type']}: {$row['count']}\n";
}

echo "\n";

// Count movies with trailers by type
$stmt = $pdo->query("
    SELECT m.type, COUNT(DISTINCT m.id) as count 
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE t.is_active = TRUE
    GROUP BY m.type
");

echo "Movies WITH trailers by type:\n";
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo "  {$row['type']}: {$row['count']}\n";
}

echo "\n";

// Sample of what we have
$stmt = $pdo->query("
    SELECT m.title, m.type, m.release_year
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE t.is_active = TRUE
    LIMIT 10
");

echo "Sample movies with trailers:\n";
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo "  [{$row['type']}] {$row['title']} ({$row['release_year']})\n";
}
?>