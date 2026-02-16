<?php
/**
 * Test provider data for specific movies
 */
header('Content-Type: text/plain; charset=utf-8');
require_once 'db-config.php';

$pdo = getDbConnection();

// Find Culinary Class Wars
echo "=== Looking for 'Culinary Class Wars' ===\n";
$stmt = $pdo->prepare("SELECT id, title, tmdb_id FROM movies WHERE title LIKE ? LIMIT 5");
$stmt->execute(array('%Culinary%'));
$movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

foreach ($movies as $movie) {
    echo "\nMovie: {$movie['title']} (ID: {$movie['id']}, TMDB: {$movie['tmdb_id']})\n";

    // Check providers
    $provStmt = $pdo->prepare("
        SELECT provider_id, provider_name, is_active
        FROM streaming_providers
        WHERE movie_id = ?
        ORDER BY display_priority
    ");
    $provStmt->execute(array($movie['id']));
    $providers = $provStmt->fetchAll(PDO::FETCH_ASSOC);

    if (count($providers) > 0) {
        echo "Providers:\n";
        foreach ($providers as $p) {
            $active = $p['is_active'] ? 'ACTIVE' : 'inactive';
            echo "  - {$p['provider_name']} (ID: {$p['provider_id']}) [{$active}]\n";
        }
    } else {
        echo "  No providers found - needs update\n";
    }
}

// Check total provider count
$stmt = $pdo->query("SELECT COUNT(*) as total FROM streaming_providers WHERE is_active = 1");
$total = $stmt->fetch(PDO::FETCH_ASSOC);
echo "\n\nTotal active provider associations: {$total['total']}\n";

// Show sample movies WITH providers
echo "\n=== Sample movies WITH providers ===\n";
$stmt = $pdo->query("
    SELECT m.title, COUNT(sp.id) as provider_count
    FROM movies m
    INNER JOIN streaming_providers sp ON m.id = sp.movie_id
    WHERE sp.is_active = 1
    GROUP BY m.id
    ORDER BY provider_count DESC
    LIMIT 10
");

foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
    echo "{$row['title']}: {$row['provider_count']} providers\n";
}
