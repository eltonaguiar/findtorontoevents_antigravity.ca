<?php
/**
 * Web-accessible provider update script
 * Access via: https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/run-provider-update.php?limit=50
 */

set_time_limit(600); // 10 minutes
header('Content-Type: text/plain');

require_once 'db-config.php';

define('TMDB_API_KEY', '9d4dc1f2ae8f51e0df753b5f5b6e2cd0');
define('TMDB_REGION', 'CA');

$PROVIDER_MAP = [
    '8' => ['name' => 'Netflix', 'priority' => 1],
    '9' => ['name' => 'Prime Video', 'priority' => 2],
    '337' => ['name' => 'Disney+', 'priority' => 3],
    '15' => ['name' => 'Hulu', 'priority' => 4],
    '350' => ['name' => 'Apple TV+', 'priority' => 5],
    '1899' => ['name' => 'Max', 'priority' => 6],
    '531' => ['name' => 'Paramount+', 'priority' => 7],
    '386' => ['name' => 'Peacock', 'priority' => 8],
    '230' => ['name' => 'Crave', 'priority' => 9],
    '73' => ['name' => 'Tubi', 'priority' => 10],
];

$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
$offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;

$pdo = getDbConnection();
if (!$pdo) {
    die("ERROR: Database connection failed\n");
}

echo "Starting provider update (limit=$limit, offset=$offset)...\n\n";

$stmt = $pdo->prepare("
    SELECT m.id, m.title, m.type, m.tmdb_id
    FROM movies m
    WHERE m.tmdb_id IS NOT NULL
    ORDER BY m.created_at DESC
    LIMIT :limit OFFSET :offset
");
$stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
$movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

echo "Processing " . count($movies) . " movies...\n\n";

$updated = 0;
$errors = 0;
$added = 0;

foreach ($movies as $movie) {
    $mediaType = ($movie['type'] === 'tv') ? 'tv' : 'movie';
    $url = "https://api.themoviedb.org/3/{$mediaType}/{$movie['tmdb_id']}/watch/providers?api_key=" . TMDB_API_KEY;

    echo "[{$movie['id']}] {$movie['title']} ({$mediaType})... ";
    flush();

    $response = @file_get_contents($url);

    if ($response === false) {
        echo "FAILED\n";
        $errors++;
        usleep(250000);
        continue;
    }

    $data = json_decode($response, true);

    if (!isset($data['results'][TMDB_REGION])) {
        echo "No CA data\n";
        $updated++;
        usleep(250000);
        continue;
    }

    $caData = $data['results'][TMDB_REGION];
    $providers = [];

    $sources = ['flatrate', 'rent', 'buy'];
    foreach ($sources as $source) {
        if (isset($caData[$source]) && is_array($caData[$source])) {
            foreach ($caData[$source] as $provider) {
                $providerId = strval($provider['provider_id']);

                if (isset($PROVIDER_MAP[$providerId])) {
                    $providers[$providerId] = [
                        'id' => $providerId,
                        'name' => $PROVIDER_MAP[$providerId]['name'],
                        'logo' => 'https://image.tmdb.org/t/p/original' . $provider['logo_path'],
                        'priority' => $PROVIDER_MAP[$providerId]['priority']
                    ];
                }
            }
        }
    }

    $pdo->beginTransaction();

    try {
        foreach ($providers as $provider) {
            $upsertStmt = $pdo->prepare("
                INSERT INTO streaming_providers
                    (movie_id, provider_id, provider_name, provider_logo, display_priority, is_active)
                VALUES
                    (:movie_id, :provider_id, :provider_name, :provider_logo, :priority, 1)
                ON DUPLICATE KEY UPDATE
                    provider_name = VALUES(provider_name),
                    provider_logo = VALUES(provider_logo),
                    display_priority = VALUES(display_priority),
                    is_active = 1,
                    last_checked = NOW()
            ");

            $upsertStmt->execute([
                'movie_id' => $movie['id'],
                'provider_id' => $provider['id'],
                'provider_name' => $provider['name'],
                'provider_logo' => $provider['logo'],
                'priority' => $provider['priority']
            ]);

            $added++;
        }

        $pdo->commit();
        echo "OK (" . count($providers) . " providers)\n";
        $updated++;

    } catch (Exception $e) {
        $pdo->rollBack();
        echo "ERROR: " . $e->getMessage() . "\n";
        $errors++;
    }

    usleep(250000); // Rate limiting
}

echo "\n=== SUMMARY ===\n";
echo "Processed: $updated\n";
echo "Providers added: $added\n";
echo "Errors: $errors\n";
echo "\nNext batch: run-provider-update.php?limit=$limit&offset=" . ($offset + $limit) . "\n";
