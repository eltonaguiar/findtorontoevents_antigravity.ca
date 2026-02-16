#!/usr/bin/env php
<?php
/**
 * Streaming Provider Update Job
 *
 * Fetches streaming availability from TMDB Watch Providers API
 * and stores in database for server-side filtering.
 *
 * Usage:
 *   php update-streaming-providers.php [--all] [--movie-id=123]
 *
 * Options:
 *   --all         Update all movies (default: only movies without provider data)
 *   --movie-id    Update specific movie by ID
 *   --days=N      Update movies checked more than N days ago (default: 7)
 *
 * Cron: 0 2 * * * /path/to/update-streaming-providers.php >> /var/log/provider-updates.log 2>&1
 */

require_once __DIR__ . '/../api/db-config.php';

// TMDB Configuration
define('TMDB_API_KEY', '9d4dc1f2ae8f51e0df753b5f5b6e2cd0'); // From frontend code
define('TMDB_REGION', 'CA'); // Canada region

// Provider mapping (from MOVIESHOWS3 frontend)
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

// Parse command-line options
$options = getopt('', ['all', 'movie-id:', 'days:']);
$updateAll = isset($options['all']);
$specificMovieId = $options['movie-id'] ?? null;
$daysSinceCheck = intval($options['days'] ?? 7);

// Database connection
$pdo = getDbConnection();
if (!$pdo) {
    die("[ERROR] Database connection failed\n");
}

echo "[INFO] Starting streaming provider update job at " . date('Y-m-d H:i:s') . "\n";

// Get movies to update
$whereConditions = [];
$params = [];

if ($specificMovieId) {
    $whereConditions[] = "m.id = :movie_id";
    $params['movie_id'] = $specificMovieId;
} elseif (!$updateAll) {
    // Only update movies not checked recently or never checked
    $whereConditions[] = "(
        m.id NOT IN (SELECT DISTINCT movie_id FROM streaming_providers WHERE last_checked > DATE_SUB(NOW(), INTERVAL :days DAY))
        OR m.id NOT IN (SELECT DISTINCT movie_id FROM streaming_providers)
    )";
    $params['days'] = $daysSinceCheck;
}

$whereClause = $whereConditions ? 'WHERE ' . implode(' AND ', $whereConditions) : '';

$stmt = $pdo->prepare("
    SELECT m.id, m.title, m.type, m.tmdb_id
    FROM movies m
    $whereClause
    ORDER BY m.created_at DESC
");

$stmt->execute($params);
$movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

$totalMovies = count($movies);
echo "[INFO] Found $totalMovies movies to update\n";

if ($totalMovies === 0) {
    echo "[INFO] No movies to update. Exiting.\n";
    exit(0);
}

$updated = 0;
$errors = 0;
$removed = 0;
$added = 0;

foreach ($movies as $movie) {
    if (!$movie['tmdb_id']) {
        echo "[SKIP] {$movie['title']} (ID: {$movie['id']}) - No TMDB ID\n";
        continue;
    }

    $mediaType = ($movie['type'] === 'tv') ? 'tv' : 'movie';
    $url = "https://api.themoviedb.org/3/{$mediaType}/{$movie['tmdb_id']}/watch/providers?api_key=" . TMDB_API_KEY;

    echo "[FETCH] {$movie['title']} (TMDB: {$movie['tmdb_id']}, Type: {$mediaType})... ";

    $response = @file_get_contents($url);

    if ($response === false) {
        echo "FAILED\n";
        $errors++;
        sleep(1); // Rate limiting
        continue;
    }

    $data = json_decode($response, true);

    if (!isset($data['results'][TMDB_REGION])) {
        echo "No CA data\n";
        // Mark existing providers as inactive
        markProvidersInactive($pdo, $movie['id']);
        $updated++;
        sleep(0.5);
        continue;
    }

    $caData = $data['results'][TMDB_REGION];
    $providers = [];

    // Collect providers from all sources (flatrate, rent, buy)
    $sources = ['flatrate', 'rent', 'buy'];
    foreach ($sources as $source) {
        if (isset($caData[$source]) && is_array($caData[$source])) {
            foreach ($caData[$source] as $provider) {
                $providerId = strval($provider['provider_id']);

                // Only track providers we care about
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

    // Update database
    $pdo->beginTransaction();

    try {
        // Get current providers
        $currentStmt = $pdo->prepare("
            SELECT provider_id
            FROM streaming_providers
            WHERE movie_id = :movie_id AND is_active = 1
        ");
        $currentStmt->execute(['movie_id' => $movie['id']]);
        $currentProviderIds = array_column($currentStmt->fetchAll(PDO::FETCH_ASSOC), 'provider_id');

        $newProviderIds = array_keys($providers);

        // Find removed providers
        $removedProviderIds = array_diff($currentProviderIds, $newProviderIds);
        foreach ($removedProviderIds as $providerId) {
            // Mark as inactive
            $updateStmt = $pdo->prepare("
                UPDATE streaming_providers
                SET is_active = 0, last_checked = NOW()
                WHERE movie_id = :movie_id AND provider_id = :provider_id
            ");
            $updateStmt->execute([
                'movie_id' => $movie['id'],
                'provider_id' => $providerId
            ]);

            // Log to history
            $historyStmt = $pdo->prepare("
                INSERT INTO streaming_provider_history (movie_id, provider_id, provider_name, action)
                SELECT :movie_id, provider_id, provider_name, 'removed'
                FROM streaming_providers
                WHERE movie_id = :movie_id AND provider_id = :provider_id
                LIMIT 1
            ");
            $historyStmt->execute([
                'movie_id' => $movie['id'],
                'provider_id' => $providerId
            ]);

            $removed++;
        }

        // Insert/update new providers
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

            $result = $upsertStmt->execute([
                'movie_id' => $movie['id'],
                'provider_id' => $provider['id'],
                'provider_name' => $provider['name'],
                'provider_logo' => $provider['logo'],
                'priority' => $provider['priority']
            ]);

            // Track if this is a new provider
            if (in_array($provider['id'], array_diff($newProviderIds, $currentProviderIds))) {
                $historyStmt = $pdo->prepare("
                    INSERT INTO streaming_provider_history (movie_id, provider_id, provider_name, action)
                    VALUES (:movie_id, :provider_id, :provider_name, 'added')
                ");
                $historyStmt->execute([
                    'movie_id' => $movie['id'],
                    'provider_id' => $provider['id'],
                    'provider_name' => $provider['name']
                ]);

                $added++;
            }
        }

        $pdo->commit();
        echo "OK (" . count($providers) . " providers)\n";
        $updated++;

    } catch (Exception $e) {
        $pdo->rollBack();
        echo "ERROR: " . $e->getMessage() . "\n";
        $errors++;
    }

    // Rate limiting: 40 requests per 10 seconds = 0.25s delay
    usleep(250000);
}

echo "\n[SUMMARY]\n";
echo "  Movies processed: $updated\n";
echo "  Providers added: $added\n";
echo "  Providers removed: $removed\n";
echo "  Errors: $errors\n";
echo "  Completed at " . date('Y-m-d H:i:s') . "\n";

/**
 * Mark all providers for a movie as inactive
 */
function markProvidersInactive($pdo, $movieId) {
    $stmt = $pdo->prepare("
        UPDATE streaming_providers
        SET is_active = 0, last_checked = NOW()
        WHERE movie_id = :movie_id AND is_active = 1
    ");
    $stmt->execute(['movie_id' => $movieId]);
}
