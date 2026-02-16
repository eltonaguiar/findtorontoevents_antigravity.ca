<?php
/**
 * Batch Update All Providers
 *
 * Runs TMDB provider update for ALL movies in batches
 * Usage: batch-update-all-providers.php
 */

set_time_limit(0); // No timeout
header('Content-Type: text/plain; charset=utf-8');

require_once 'db-config.php';

echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║  BATCH UPDATE: All Movie Providers via TMDB               ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n\n";

$pdo = getDbConnection();

// Get total count
$stmt = $pdo->query("SELECT COUNT(*) as total FROM movies WHERE tmdb_id IS NOT NULL");
$total = $stmt->fetch(PDO::FETCH_ASSOC)['total'];

echo "Total movies to process: $total\n\n";

$batchSize = 500;
$batches = ceil($total / $batchSize);

echo "Processing in $batches batches of $batchSize...\n";
echo str_repeat("=", 60) . "\n\n";

$grandTotalProcessed = 0;
$grandTotalProviders = 0;

for ($i = 0; $i < $batches; $i++) {
    $offset = $i * $batchSize;
    echo "BATCH " . ($i + 1) . "/$batches (offset $offset)\n";
    echo str_repeat("-", 60) . "\n";

    // Call run-provider-update.php internally
    $_GET['limit'] = $batchSize;
    $_GET['offset'] = $offset;

    ob_start();
    include 'run-provider-update.php';
    $output = ob_get_clean();

    echo $output;

    // Parse summary
    if (preg_match('/Processed: (\d+)/', $output, $matches)) {
        $grandTotalProcessed += intval($matches[1]);
    }
    if (preg_match('/Providers added: (\d+)/', $output, $matches)) {
        $grandTotalProviders += intval($matches[1]);
    }

    echo "\n";

    // Small delay between batches
    sleep(2);
}

echo "\n";
echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║  GRAND TOTAL                                               ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n";
echo "Movies processed: $grandTotalProcessed\n";
echo "Providers added: $grandTotalProviders\n";
echo "\nAll done! 🎉\n";
