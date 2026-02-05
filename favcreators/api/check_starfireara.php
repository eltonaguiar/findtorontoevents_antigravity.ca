<?php
// Check Starfireara's actual follower count in database
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Starfireara Follower Count Check ===\n\n";

$sql = "SELECT id, name, follower_count FROM creators WHERE name LIKE '%Starfire%'";
$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo "ID: " . $row['id'] . "\n";
        echo "Name: " . $row['name'] . "\n";
        echo "Follower Count: " . $row['follower_count'] . "\n";
        echo "\n";
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

$conn->close();
?>