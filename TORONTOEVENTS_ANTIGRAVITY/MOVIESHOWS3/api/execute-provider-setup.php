<?php
/**
 * MASTER SETUP SCRIPT - Handles everything automatically
 * Access: https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/execute-provider-setup.php
 */

set_time_limit(600);
header('Content-Type: text/plain; charset=utf-8');

echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║  MOVIESHOWS3 Streaming Provider Setup                      ║\n";
echo "║  Automated installation and initial data load              ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n\n";

$startTime = microtime(true);

// Step 1: Check and migrate existing schema
echo "STEP 1: Checking existing schema...\n";
echo str_repeat("─", 60) . "\n";
ob_start();
include 'check-and-migrate-providers.php';
$output = ob_get_clean();
echo $output . "\n";

// Step 2: Ensure tables exist (idempotent)
echo "\nSTEP 2: Ensuring tables exist...\n";
echo str_repeat("─", 60) . "\n";
ob_start();
include 'setup-providers.php';
$output = ob_get_clean();
echo $output . "\n";

// Step 3: Run initial provider update (limit 100 for first run)
echo "\nSTEP 3: Loading initial provider data (100 movies)...\n";
echo str_repeat("─", 60) . "\n";
$_GET['limit'] = 100;
$_GET['offset'] = 0;
ob_start();
include 'run-provider-update.php';
$output = ob_get_clean();
echo $output . "\n";

$elapsed = round(microtime(true) - $startTime, 2);

echo "\n";
echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║  SETUP COMPLETE!                                           ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n";
echo "\n";
echo "⏱️  Total time: {$elapsed}s\n";
echo "\n";
echo "Next steps:\n";
echo "1. Test API: https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php\n";
echo "2. Load more: api/run-provider-update.php?limit=100&offset=100\n";
echo "3. Setup cron: 0 2 * * * php /path/to/jobs/update-streaming-providers.php\n";
echo "4. DELETE THIS FILE for security\n";
