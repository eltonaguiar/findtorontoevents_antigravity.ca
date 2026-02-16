<?php
/**
 * Manually insert provider for testing
 */
header('Content-Type: text/plain');
require_once 'db-config.php';

$pdo = getDbConnection();

// Insert Netflix for Culinary Class Wars (ID: 580)
$sql = "INSERT INTO streaming_providers
    (movie_id, provider_id, provider_name, provider_logo, display_priority, is_active)
VALUES
    (580, '8', 'Netflix', 'https://image.tmdb.org/t/p/original/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg', 1, 1)
ON DUPLICATE KEY UPDATE
    provider_name = VALUES(provider_name),
    provider_logo = VALUES(provider_logo),
    is_active = 1,
    last_checked = NOW()";

try {
    $pdo->exec($sql);
    echo "✓ Netflix added to Culinary Class Wars (ID: 580)\n";
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}

// Verify
$stmt = $pdo->prepare("
    SELECT m.title, sp.provider_name
    FROM movies m
    INNER JOIN streaming_providers sp ON m.id = sp.movie_id
    WHERE m.id = 580
");
$stmt->execute();
$result = $stmt->fetch(PDO::FETCH_ASSOC);

if ($result) {
    echo "\nVerified: {$result['title']} → {$result['provider_name']}\n";
}
