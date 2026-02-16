<?php
/**
 * Check existing provider table schema and migrate if needed
 * Run this BEFORE setup-providers.php
 */

header('Content-Type: text/plain');
require_once 'db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("ERROR: Database connection failed\n");
}

echo "Checking existing streaming_providers schema...\n\n";

// Check if table exists
$stmt = $pdo->query("SHOW TABLES LIKE 'streaming_providers'");
$tableExists = $stmt->rowCount() > 0;

if (!$tableExists) {
    echo "✓ No existing table found - safe to proceed with setup-providers.php\n";
    exit(0);
}

// Check schema
echo "Table exists! Checking schema...\n";
$stmt = $pdo->query("DESCRIBE streaming_providers");
$columns = $stmt->fetchAll(PDO::FETCH_ASSOC);

$columnNames = array_column($columns, 'Field');
echo "Existing columns: " . implode(', ', $columnNames) . "\n\n";

// Detect old schema
$hasOldSchema = in_array('provider_logo_url', $columnNames);
$hasNewSchema = in_array('provider_logo', $columnNames) && in_array('display_priority', $columnNames);

if ($hasOldSchema && !$hasNewSchema) {
    echo "⚠️  OLD SCHEMA DETECTED (from add-streaming-providers.php)\n";
    echo "Migrating to new schema...\n\n";

    try {
        // Rename logo column
        $pdo->exec("ALTER TABLE streaming_providers CHANGE provider_logo_url provider_logo VARCHAR(500)");
        echo "✓ Renamed provider_logo_url → provider_logo\n";

        // Add display_priority
        $pdo->exec("ALTER TABLE streaming_providers ADD COLUMN display_priority INT DEFAULT 0 AFTER provider_logo");
        echo "✓ Added display_priority column\n";

        // Rename timestamp columns
        $pdo->exec("ALTER TABLE streaming_providers CHANGE first_detected_at first_seen DATETIME DEFAULT CURRENT_TIMESTAMP");
        echo "✓ Renamed first_detected_at → first_seen\n";

        $pdo->exec("ALTER TABLE streaming_providers CHANGE last_verified_at last_checked DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP");
        echo "✓ Renamed last_verified_at → last_checked\n";

        // Change provider_id to VARCHAR(10)
        $pdo->exec("ALTER TABLE streaming_providers MODIFY provider_id VARCHAR(10) NOT NULL COMMENT 'TMDB provider ID (e.g., 8=Netflix, 9=Prime)'");
        echo "✓ Changed provider_id to VARCHAR(10)\n";

        // Drop unused columns
        $pdo->exec("ALTER TABLE streaming_providers DROP COLUMN IF EXISTS region");
        $pdo->exec("ALTER TABLE streaming_providers DROP COLUMN IF EXISTS monetization_type");
        $pdo->exec("ALTER TABLE streaming_providers DROP COLUMN IF EXISTS link");
        $pdo->exec("ALTER TABLE streaming_providers DROP COLUMN IF EXISTS removed_at");
        echo "✓ Dropped unused columns (region, monetization_type, link, removed_at)\n";

        echo "\n✅ Migration complete! Old schema updated to new format.\n";

    } catch (Exception $e) {
        echo "❌ Migration error: " . $e->getMessage() . "\n";
        exit(1);
    }

} elseif ($hasNewSchema) {
    echo "✓ New schema already in place - no migration needed\n";

} else {
    echo "⚠️  Unknown schema - manual inspection required\n";
    exit(1);
}

// Check for history table
$stmt = $pdo->query("SHOW TABLES LIKE 'streaming_provider_history'");
$historyExists = $stmt->rowCount() > 0;

if (!$historyExists) {
    echo "\nCreating streaming_provider_history table...\n";
    $pdo->exec("
        CREATE TABLE streaming_provider_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            movie_id INT NOT NULL,
            provider_id VARCHAR(10) NOT NULL,
            provider_name VARCHAR(100) NOT NULL,
            action ENUM('added', 'removed') NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_movie_history (movie_id, timestamp),
            INDEX idx_provider_history (provider_id, timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "✓ Created streaming_provider_history table\n";
}

// Check row count
$stmt = $pdo->query("SELECT COUNT(*) FROM streaming_providers");
$count = $stmt->fetchColumn();
echo "\n📊 Current provider records: $count\n";

if ($count === 0) {
    echo "   → Run run-provider-update.php to populate data\n";
}

echo "\n✅ All checks complete!\n";
