<?php
// Check user_lists structure for user 2
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== User 2's Creator List ===\n\n";

$user_id = 2;

$sql = "SELECT * FROM user_lists WHERE user_id = $user_id";
$result = $conn->query($sql);

if ($result && $result->num_rows > 0) {
    $row = $result->fetch_assoc();
    echo "User ID: " . $row['user_id'] . "\n";
    echo "Creators (raw): " . substr($row['creators'], 0, 500) . "...\n\n";

    // Try to decode JSON
    $creators_data = json_decode($row['creators'], true);
    if ($creators_data) {
        echo "Decoded creators (" . count($creators_data) . " total):\n";
        foreach ($creators_data as $creator) {
            if (isset($creator['id']) && isset($creator['name'])) {
                echo "  - ID: " . $creator['id'] . ", Name: " . $creator['name'] . "\n";
            }
        }
    } else {
        echo "Failed to decode JSON\n";
    }
} else {
    echo "No data found for user $user_id\n";
    if ($conn->error) {
        echo "ERROR: " . $conn->error . "\n";
    }
}

$conn->close();
?>