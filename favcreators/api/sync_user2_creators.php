<?php
// Simplified sync - just for user 2
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(120);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Syncing User 2 Creators ===\n\n";

// Known follower counts
$known_followers = array(
    'zople' => 600000,
    'lofe' => 2150000,
    'adin ross' => 500000
);

$user_id = 2;

// Get user 2's creators
$sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$result = $conn->query($sql);

if (!$result) {
    die("ERROR: " . $conn->error . "\n");
}

$row = $result->fetch_assoc();
$creators_data = json_decode($row['creators'], true);

echo "User 2 follows " . count($creators_data) . " creators\n\n";

$added = 0;
$updated = 0;
$errors = 0;

foreach ($creators_data as $creator) {
    if (!isset($creator['id']) || !isset($creator['name']))
        continue;

    $id = $conn->real_escape_string($creator['id']);
    $name = $conn->real_escape_string($creator['name']);

    // Check if exists
    $check = $conn->query("SELECT id, follower_count FROM creators WHERE id = '$id'");

    if ($check->num_rows == 0) {
        // Add creator
        $follower_count = 0;
        $name_lower = strtolower($name);
        if (isset($known_followers[$name_lower])) {
            $follower_count = $known_followers[$name_lower];
        }

        $avatar = isset($creator['avatarUrl']) ? $conn->real_escape_string($creator['avatarUrl']) : '';

        $insert = "INSERT INTO creators (id, name, follower_count, avatar_url) VALUES ('$id', '$name', $follower_count, '$avatar')";

        if ($conn->query($insert)) {
            echo "✅ ADDED: $name (ID: $id, Followers: $follower_count)\n";
            $added++;
        } else {
            echo "❌ ERROR adding $name: " . $conn->error . "\n";
            $errors++;
        }
    } else {
        // Update if we have better follower count
        $existing = $check->fetch_assoc();
        $name_lower = strtolower($name);

        if (isset($known_followers[$name_lower]) && $existing['follower_count'] != $known_followers[$name_lower]) {
            $new_count = $known_followers[$name_lower];
            $conn->query("UPDATE creators SET follower_count = $new_count WHERE id = '$id'");
            echo "🔄 UPDATED: $name (Followers: {$existing['follower_count']} → $new_count)\n";
            $updated++;
        }
    }
}

echo "\n=== Summary ===\n";
echo "Added: $added\n";
echo "Updated: $updated\n";
echo "Errors: $errors\n";

$conn->close();
?>