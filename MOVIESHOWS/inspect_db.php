<?php
$host = 'mysql.50webs.com';
$db = 'ejaguiar1_tvmoviestrailers';
$user = 'ejaguiar1_tvmoviestrailers';
$pass = 'virus2016';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$db", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Get table structure
    $tables = $pdo->query('SHOW TABLES')->fetchAll(PDO::FETCH_COLUMN);
    echo "Tables in database:\n";
    foreach ($tables as $table) {
        echo "- $table\n";
        $count = $pdo->query("SELECT COUNT(*) FROM $table")->fetchColumn();
        echo "  Records: $count\n";
    }

    // Get structure of main tables
    foreach ($tables as $table) {
        echo "\nStructure of $table:\n";
        $columns = $pdo->query("DESCRIBE $table")->fetchAll(PDO::FETCH_ASSOC);
        foreach ($columns as $col) {
            echo "  - {$col['Field']} ({$col['Type']}) {$col['Null']} {$col['Key']}\n";
        }
    }

    // Sample data from movies table
    echo "\n\nSample data from movies table:\n";
    $samples = $pdo->query("SELECT * FROM movies ORDER BY release_year DESC LIMIT 10")->fetchAll(PDO::FETCH_ASSOC);
    foreach ($samples as $row) {
        echo "ID: {$row['id']}, Title: {$row['title']}, Type: {$row['type']}, Year: {$row['release_year']}\n";
    }

    // Count by year and type
    echo "\n\nCount by year and type:\n";
    $yearCounts = $pdo->query("SELECT release_year, type, COUNT(*) as count FROM movies GROUP BY release_year, type ORDER BY release_year DESC")->fetchAll(PDO::FETCH_ASSOC);
    foreach ($yearCounts as $row) {
        echo "Year: {$row['release_year']}, Type: {$row['type']}, Count: {$row['count']}\n";
    }

} catch (PDOException $e) {
    echo 'Connection failed: ' . $e->getMessage();
}
