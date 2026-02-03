<?php
/**
 * Simple Database Initialization Script
 * Access via: https://findtorontoevents.ca/MOVIESHOWS/init-database.php
 */

// Database credentials
$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'tvmoviestrailers';

header('Content-Type: text/plain; charset=utf-8');

echo "MovieShows Database Initialization\n";
echo "===================================\n\n";

try {
    // Connect to database
    echo "Connecting to database...\n";
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "✓ Connected successfully!\n\n";

    // Read schema file
    echo "Reading schema file...\n";
    $schemaFile = __DIR__ . '/database/schema.sql';

    if (!file_exists($schemaFile)) {
        die("✗ Schema file not found: $schemaFile\n");
    }

    $schema = file_get_contents($schemaFile);
    echo "✓ Schema loaded (" . strlen($schema) . " bytes)\n\n";

    // Split into individual statements
    echo "Executing SQL statements...\n";
    $statements = array_filter(
        array_map('trim', explode(';', $schema)),
        function ($stmt) {
            return !empty($stmt) && !preg_match('/^--/', $stmt) && !preg_match('/^\/\*/', $stmt);
        }
    );

    $success = 0;
    $failed = 0;
    $errors = [];

    foreach ($statements as $statement) {
        try {
            $pdo->exec($statement);
            $success++;
        } catch (PDOException $e) {
            $failed++;
            $errors[] = $e->getMessage();
        }
    }

    echo "✓ Execution complete!\n";
    echo "  Successful: $success\n";
    echo "  Failed: $failed\n\n";

    if (!empty($errors)) {
        echo "Errors:\n";
        foreach ($errors as $error) {
            echo "  - $error\n";
        }
        echo "\n";
    }

    // Verify tables
    echo "Verifying tables...\n";
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);

    echo "✓ Found " . count($tables) . " tables:\n";
    foreach ($tables as $table) {
        $countStmt = $pdo->query("SELECT COUNT(*) FROM $table");
        $count = $countStmt->fetchColumn();
        echo "  ✓ $table: $count rows\n";
    }

    echo "\n✓ Database initialization complete!\n";

} catch (PDOException $e) {
    echo "✗ Error: " . $e->getMessage() . "\n";
    exit(1);
}
