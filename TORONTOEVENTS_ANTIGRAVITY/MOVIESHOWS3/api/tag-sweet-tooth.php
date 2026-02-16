<?php
/**
 * Manually tag Sweet Tooth with Netflix
 */
header('Content-Type: text/plain');
require_once 'db-config.php';

$pdo = getDbConnection();

// Find Sweet Tooth
$stmt = $pdo->prepare("SELECT id, title, tmdb_id FROM movies WHERE title LIKE ?");
$stmt->execute(array('%Sweet Tooth%'));
$movie = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$movie) {
    die("Sweet Tooth not found in database\n");
}

echo "Found: {$movie['title']} (ID: {$movie['id']}, TMDB: {$movie['tmdb_id']})\n\n";

// Check TMDB for providers
$tmdbId = $movie['tmdb_id'];
$url = "https://api.themoviedb.org/3/tv/{$tmdbId}/watch/providers?api_key=b84ff7bfe35ffad8779b77bcbbda317f";

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
$response = curl_exec($ch);
curl_close($ch);

$data = json_decode($response, true);

if (isset($data['results']['CA']['flatrate'])) {
    echo "TMDB Canada providers:\n";
    foreach ($data['results']['CA']['flatrate'] as $provider) {
        echo "  - {$provider['provider_name']} (ID: {$provider['provider_id']})\n";
    }
    echo "\n";
}

// Insert Netflix
$sql = "INSERT INTO streaming_providers
    (movie_id, provider_id, provider_name, provider_logo, display_priority, is_active)
VALUES
    (?, '8', 'Netflix', 'https://image.tmdb.org/t/p/original/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg', 1, 1)
ON DUPLICATE KEY UPDATE
    is_active = 1,
    last_checked = NOW()";

$stmt = $pdo->prepare($sql);
$stmt->execute(array($movie['id']));

echo "✅ Netflix added to Sweet Tooth\n";

// Verify
$stmt = $pdo->prepare("
    SELECT sp.provider_name
    FROM streaming_providers sp
    WHERE sp.movie_id = ? AND sp.is_active = 1
");
$stmt->execute(array($movie['id']));
$providers = $stmt->fetchAll(PDO::FETCH_ASSOC);

echo "\nCurrent providers for Sweet Tooth:\n";
foreach ($providers as $p) {
    echo "  - {$p['provider_name']}\n";
}
