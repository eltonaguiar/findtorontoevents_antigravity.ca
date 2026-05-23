<?php
/**
 * Sync streaming providers from MOVIESHOWS3 database into MOVIESHOWS2 database.
 * Creates the streaming_providers table if needed, then cross-references
 * movies by tmdb_id to copy provider data.
 *
 * Usage:
 *   Dry run: ?mode=dry
 *   Execute: ?mode=run
 */
header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// MOVIESHOWS2 DB
$ms2_host = 'localhost';
$ms2_db = 'ejaguiar1_tvmoviestrailers';
$ms2_user = 'ejaguiar1_tvmoviestrailers';
$ms2_pass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

// MOVIESHOWS3 DB
$ms3_host = 'localhost';
$ms3_db = 'ejaguiar1_movieshows';
$ms3_user = 'ejaguiar1_movieshows';
$ms3_pass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

$mode = isset($_GET['mode']) ? $_GET['mode'] : 'dry';

echo "=================================================================\n";
echo "MOVIESHOWS2 PROVIDER SYNC (from MOVIESHOWS3)\n";
echo "=================================================================\n";
echo "Mode: " . ($mode === 'run' ? 'EXECUTING' : 'DRY RUN (add ?mode=run to execute)') . "\n";
echo "Time: " . date('Y-m-d H:i:s') . "\n\n";

try {
    // Connect to both databases
    $ms2 = new PDO("mysql:host=$ms2_host;dbname=$ms2_db;charset=utf8mb4", $ms2_user, $ms2_pass);
    $ms2->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $ms2->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    echo "Connected to MOVIESHOWS2 DB\n";

    $ms3 = new PDO("mysql:host=$ms3_host;dbname=$ms3_db;charset=utf8mb4", $ms3_user, $ms3_pass);
    $ms3->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $ms3->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    echo "Connected to MOVIESHOWS3 DB\n\n";

    // Step 1: Create streaming_providers table in MS2 if not exists
    if ($mode === 'run') {
        $ms2->exec("CREATE TABLE IF NOT EXISTS streaming_providers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            movie_id INT NOT NULL,
            provider_name VARCHAR(100) NOT NULL,
            provider_logo VARCHAR(500),
            provider_tmdb_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_movie_provider (movie_id, provider_name),
            INDEX idx_movie_id (movie_id),
            INDEX idx_provider_name (provider_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
        echo "Created/verified streaming_providers table in MS2\n\n";
    } else {
        echo "Would create streaming_providers table in MS2\n\n";
    }

    // Step 2: Get all MS2 movies with tmdb_id
    $ms2_movies = $ms2->query("SELECT id, title, tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND tmdb_id > 0")->fetchAll();
    echo "MS2 movies with tmdb_id: " . count($ms2_movies) . "\n";

    // Build lookup by tmdb_id
    $ms2_lookup = array();
    foreach ($ms2_movies as $m) {
        $ms2_lookup[$m['tmdb_id']] = $m;
    }

    // Step 3: Get all MS3 provider data
    $ms3_providers = $ms3->query("
        SELECT sp.movie_id, sp.provider_name, sp.provider_logo, m.tmdb_id, m.title
        FROM streaming_providers sp
        JOIN movies m ON m.id = sp.movie_id
        WHERE m.tmdb_id IS NOT NULL AND m.tmdb_id > 0
    ")->fetchAll();
    echo "MS3 provider entries: " . count($ms3_providers) . "\n\n";

    // Step 4: Check existing MS2 providers (if table exists)
    $existing_ms2 = array();
    try {
        $rows = $ms2->query("SELECT movie_id, provider_name FROM streaming_providers")->fetchAll();
        foreach ($rows as $r) {
            $existing_ms2[$r['movie_id'] . '|' . $r['provider_name']] = true;
        }
        echo "Existing MS2 provider entries: " . count($existing_ms2) . "\n";
    } catch (PDOException $e) {
        echo "No existing streaming_providers table yet\n";
    }

    // Step 5: Match and sync
    $matched = 0;
    $added = 0;
    $skipped = 0;
    $not_found = 0;

    if ($mode === 'run') {
        $insert = $ms2->prepare("INSERT IGNORE INTO streaming_providers (movie_id, provider_name, provider_logo) VALUES (?, ?, ?)");
    }

    foreach ($ms3_providers as $sp) {
        $tmdb_id = $sp['tmdb_id'];
        if (!isset($ms2_lookup[$tmdb_id])) {
            $not_found++;
            continue;
        }

        $ms2_movie = $ms2_lookup[$tmdb_id];
        $key = $ms2_movie['id'] . '|' . $sp['provider_name'];

        if (isset($existing_ms2[$key])) {
            $skipped++;
            continue;
        }

        $matched++;
        if ($mode === 'run') {
            $insert->execute(array($ms2_movie['id'], $sp['provider_name'], $sp['provider_logo']));
            $added++;
        }
    }

    echo "\n--- RESULTS ---\n";
    echo "  MS3 providers matched to MS2 movies: $matched\n";
    echo "  Already existed (skipped): $skipped\n";
    echo "  MS3 movies not in MS2: $not_found\n";
    if ($mode === 'run') {
        echo "  Actually inserted: $added\n";
    } else {
        echo "  Would insert: $matched\n";
    }

    // Step 6: Show sample matches
    echo "\n--- SAMPLE MATCHES ---\n";
    $sample_count = 0;
    foreach ($ms3_providers as $sp) {
        $tmdb_id = $sp['tmdb_id'];
        if (isset($ms2_lookup[$tmdb_id])) {
            $ms2_movie = $ms2_lookup[$tmdb_id];
            echo "  MS3 \"" . $sp['title'] . "\" -> MS2 \"" . $ms2_movie['title'] . "\" [" . $sp['provider_name'] . "]\n";
            $sample_count++;
            if ($sample_count >= 20) {
                echo "  ... (showing first 20)\n";
                break;
            }
        }
    }

    // Check The Wrecking Crew specifically
    echo "\n--- THE WRECKING CREW CHECK ---\n";
    $wc_ms2 = $ms2->query("SELECT id, title, tmdb_id FROM movies WHERE title LIKE '%Wrecking Crew%'")->fetchAll();
    if (count($wc_ms2) > 0) {
        foreach ($wc_ms2 as $wc) {
            echo "  Found in MS2: ID=" . $wc['id'] . ", title=\"" . $wc['title'] . "\", tmdb_id=" . $wc['tmdb_id'] . "\n";
        }
    } else {
        echo "  NOT FOUND in MS2 database\n";
    }
    $wc_ms3 = $ms3->query("SELECT m.id, m.title, m.tmdb_id, sp.provider_name FROM movies m LEFT JOIN streaming_providers sp ON sp.movie_id = m.id WHERE m.title LIKE '%Wrecking Crew%'")->fetchAll();
    if (count($wc_ms3) > 0) {
        foreach ($wc_ms3 as $wc) {
            echo "  Found in MS3: ID=" . $wc['id'] . ", title=\"" . $wc['title'] . "\", tmdb_id=" . $wc['tmdb_id'] . ", provider=" . ($wc['provider_name'] ? $wc['provider_name'] : 'NONE') . "\n";
        }
    }

    echo "\n=================================================================\n";
    echo "DONE\n";
    echo "=================================================================\n";

} catch (PDOException $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
}
?>