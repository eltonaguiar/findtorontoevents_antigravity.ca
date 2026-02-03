<?php
/**
 * Database initialization and testing script
 * Tests connection and creates schema
 */

require_once '../api/db-config.php';

echo "MovieShows Database Initialization\n";
echo "===================================\n\n";

// Test connection
echo "Testing database connection...\n";
$pdo = getDbConnection();

if (!$pdo) {
    die("✗ Database connection failed!\n");
}

echo "✓ Database connection successful!\n\n";

// Read and execute schema
echo "Creating database schema...\n";
$schemaFile = __DIR__ . '/../database/schema.sql';

if (!file_exists($schemaFile)) {
    die("✗ Schema file not found: $schemaFile\n");
}

$schema = file_get_contents($schemaFile);

// Split into individual statements
$statements = array_filter(
    array_map('trim', explode(';', $schema)),
    function ($stmt) {
        return !empty($stmt) && !preg_match('/^--/', $stmt);
    }
);

$success = 0;
$failed = 0;

foreach ($statements as $statement) {
    try {
        $pdo->exec($statement);
        $success++;
    } catch (PDOException $e) {
        $failed++;
        echo "✗ Error: " . $e->getMessage() . "\n";
    }
}

echo "\n";
echo "✓ Schema creation complete!\n";
echo "  Successful: $success\n";
echo "  Failed: $failed\n\n";

// Verify tables
echo "Verifying tables...\n";
$tables = ['movies', 'trailers', 'thumbnails', 'content_sources', 'sync_log'];

foreach ($tables as $table) {
    try {
        $stmt = $pdo->query("SELECT COUNT(*) FROM $table");
        $count = $stmt->fetchColumn();
        echo "  ✓ $table: $count rows\n";
    } catch (PDOException $e) {
        echo "  ✗ $table: " . $e->getMessage() . "\n";
    }
}

echo "\n✓ Database initialization complete!\n";
