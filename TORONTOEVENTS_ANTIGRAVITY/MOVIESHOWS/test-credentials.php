<?php
// Test Database Credentials - PHP 5.2 Compatible
header('Content-Type: text/plain; charset=utf-8');

echo "Testing Database Credentials\n";
echo "============================\n\n";

$dbname = 'ejaguiar1_tvmoviestrailers';

// Test 1
echo "Test 1: user=ejaguiar1, pass=tvmoviestrailers\n";
try {
    $pdo = new PDO("mysql:host=localhost;dbname=$dbname", 'ejaguiar1', 'tvmoviestrailers');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "  SUCCESS!\n\n";
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    echo "  Tables: " . count($tables) . "\n\n";
} catch (PDOException $e) {
    echo "  FAILED: " . $e->getMessage() . "\n\n";
}

// Test 2
echo "Test 2: user=ejaguiar1_tvmoviestrailers, pass=tvmoviestrailers\n";
try {
    $pdo = new PDO("mysql:host=localhost;dbname=$dbname", 'ejaguiar1_tvmoviestrailers', 'tvmoviestrailers');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "  SUCCESS!\n\n";
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    echo "  Tables: " . count($tables) . "\n\n";
} catch (PDOException $e) {
    echo "  FAILED: " . $e->getMessage() . "\n\n";
}

// Test 3
echo "Test 3: user=ejaguiar1_tvmovi, pass=tvmoviestrailers\n";
try {
    $pdo = new PDO("mysql:host=localhost;dbname=$dbname", 'ejaguiar1_tvmovi', 'tvmoviestrailers');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "  SUCCESS!\n\n";
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    echo "  Tables: " . count($tables) . "\n\n";
} catch (PDOException $e) {
    echo "  FAILED: " . $e->getMessage() . "\n\n";
}
?>