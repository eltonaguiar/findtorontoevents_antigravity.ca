<?php
// Check which of user 2's creators have 50K+ followers
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

$user_id = 2;

// Get user 2's creators
$sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$result = $conn->query($sql);
$row = $result->fetch_assoc();
$creators_data = json_decode($row['creators'], true);

echo "=== User 2 Creators with 50K+ Followers ===\n\n";

$over_50k = array();

foreach ($creators_data as $creator) {
    if (!isset($creator['id']))
        continue;

    $id = $conn->real_escape_string($creator['id']);

    // Check follower count
    $check = $conn->query("SELECT id, name, follower_count FROM creators WHERE id = '$id'");

    if ($check && $check->num_rows > 0) {
        $c = $check->fetch_assoc();
        if ($c['follower_count'] >= 50000) {
            $over_50k[] = $c;
            echo sprintf("%-30s | %10s followers\n", $c['name'], number_format($c['follower_count']));
        }
    }
}

echo "\n=== Summary ===\n";
echo "Total creators user 2 follows: " . count($creators_data) . "\n";
echo "Creators with 50K+ followers: " . count($over_50k) . "\n";

$conn->close();
?>