<?php
// Add Pokimane to creators table and user 2's list
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Adding Pokimane ===\n\n";

// Check if Pokimane already exists
$check = $conn->query("SELECT id FROM creators WHERE name = 'Pokimane'");

if ($check->num_rows == 0) {
    // Add Pokimane
    $id = 'pokimane-1';
    $insert = "INSERT INTO creators (id, name, follower_count, avatar_url) 
               VALUES ('$id', 'Pokimane', 9000000, 'https://static-cdn.jtvnw.net/jtv_user_pictures/pokimane-profile_image-f8b6b5a48c9b0e5e-300x300.png')";

    if ($conn->query($insert)) {
        echo "✅ Added Pokimane to creators table (ID: $id)\n";
    } else {
        echo "❌ Error: " . $conn->error . "\n";
    }
} else {
    echo "✓ Pokimane already exists\n";
}

// Add to user 2's list
$user_id = 2;
$sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$result = $conn->query($sql);
$row = $result->fetch_assoc();
$creators_data = json_decode($row['creators'], true);

// Check if Pokimane is already in the list
$has_pokimane = false;
foreach ($creators_data as $c) {
    if (isset($c['name']) && strtolower($c['name']) == 'pokimane') {
        $has_pokimane = true;
        break;
    }
}

if (!$has_pokimane) {
    $creators_data[] = array(
        'id' => 'pokimane-1',
        'name' => 'Pokimane',
        'avatarUrl' => 'https://static-cdn.jtvnw.net/jtv_user_pictures/pokimane-profile_image-f8b6b5a48c9b0e5e-300x300.png'
    );

    $new_json = json_encode($creators_data);
    $update = "UPDATE user_lists SET creators = '" . $conn->real_escape_string($new_json) . "' WHERE user_id = $user_id";

    if ($conn->query($update)) {
        echo "✅ Added Pokimane to user 2's followed list\n";
    } else {
        echo "❌ Error: " . $conn->error . "\n";
    }
} else {
    echo "✓ Pokimane already in user 2's list\n";
}

echo "\nUser 2 now follows " . count($creators_data) . " creators\n";

$conn->close();
?>