<?php
// Simple list of all creators in database
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== All Creators in Database ===\n\n";

$sql = "SELECT id, name, follower_count FROM creators ORDER BY name";
$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo sprintf(
            "ID: %-30s | Name: %-30s | Followers: %10d\n",
            $row['id'],
            $row['name'],
            $row['follower_count']
        );
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

$conn->close();
?>