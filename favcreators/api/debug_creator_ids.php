<?php
// Debug creator ID mismatch
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Creator ID Mismatch Debug ===\n\n";

$user_id = 2;

// Get user's followed creators
$user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$user_list_result = $conn->query($user_list_sql);

if ($user_list_result && $user_list_result->num_rows > 0) {
    $row = $user_list_result->fetch_assoc();
    $creators_data = json_decode($row['creators'], true);

    echo "User 2 follows " . count($creators_data) . " creators\n";
    echo "Sample creator IDs from user_lists:\n";
    for ($i = 0; $i < min(5, count($creators_data)); $i++) {
        if (isset($creators_data[$i]['id']) && isset($creators_data[$i]['name'])) {
            echo "  - ID: '" . $creators_data[$i]['id'] . "', Name: " . $creators_data[$i]['name'] . "\n";
        }
    }
}

echo "\n";

// Get creators table IDs
echo "Creators in creators table:\n";
$creators_sql = "SELECT id, name FROM creators LIMIT 10";
$creators_result = $conn->query($creators_sql);
if ($creators_result) {
    while ($row = $creators_result->fetch_assoc()) {
        echo "  - ID: '" . $row['id'] . "', Name: " . $row['name'] . "\n";
    }
}

echo "\n";

// Check creator_mentions
echo "Creator mentions:\n";
$mentions_sql = "SELECT DISTINCT creator_id, COUNT(*) as count FROM creator_mentions GROUP BY creator_id";
$mentions_result = $conn->query($mentions_sql);
if ($mentions_result) {
    while ($row = $mentions_result->fetch_assoc()) {
        echo "  - Creator ID: '" . $row['creator_id'] . "', Mentions: " . $row['count'] . "\n";
    }
}

$conn->close();
?>