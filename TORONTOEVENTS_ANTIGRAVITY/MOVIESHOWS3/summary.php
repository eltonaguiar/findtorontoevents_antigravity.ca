<?php
header('Content-Type: text/plain; charset=utf-8');

require_once 'api/db-config.php';

$pdo = getDbConnection();

echo "DATABASE SUMMARY\n";
echo "================\n\n";

// Total counts by type
$stmt = $pdo->query("
    SELECT 
        m.type,
        COUNT(DISTINCT m.id) as total,
        COUNT(DISTINCT CASE WHEN t.id IS NOT NULL THEN m.id END) as with_trailers
    FROM movies m
    LEFT JOIN trailers t ON m.id = t.movie_id AND t.is_active = TRUE
    GROUP BY m.type
");

echo "Content Summary:\n";
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo "  {$row['type']}: {$row['total']} total, {$row['with_trailers']} with trailers\n";
}

// By year
echo "\nBy Year:\n";
$stmt = $pdo->query("
    SELECT 
        m.release_year,
        m.type,
        COUNT(DISTINCT m.id) as count
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE t.is_active = TRUE
    GROUP BY m.release_year, m.type
    ORDER BY m.release_year DESC, m.type
");

while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo "  {$row['release_year']} - {$row['type']}: {$row['count']}\n";
}
?>