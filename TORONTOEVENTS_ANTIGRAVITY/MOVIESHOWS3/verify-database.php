<?php
/**
 * Verify Database Tables
 * Lists all tables and row counts
 */

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'virus2016';

header('Content-Type: text/plain; charset=utf-8');

echo "Database Verification\n";
echo "=====================\n\n";

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    echo "Connected to database: $dbname\n\n";

    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);

    if (count($tables) == 0) {
        echo "NO TABLES FOUND - Database is empty!\n";
        echo "\nPlease run init-database.php to create tables.\n";
    } else {
        echo "Found " . count($tables) . " tables:\n\n";
        foreach ($tables as $table) {
            $countStmt = $pdo->query("SELECT COUNT(*) FROM `" . $table . "`");
            $count = $countStmt->fetchColumn();
            echo "  " . str_pad($table, 30) . " : " . $count . " rows\n";
        }
    }

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>