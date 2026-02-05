<?php
// Debug script to test the new query
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Testing User-Specific Creator News Query ===\n\n";

$user_id = 2;

// Test 1: Check if user_creators table exists and has data for user 2
echo "Test 1: User 2's followed creators\n";
$sql1 = "SELECT uc.creator_id, c.name FROM user_creators uc INNER JOIN creators c ON uc.creator_id = c.id WHERE uc.user_id = $user_id";
$result1 = $conn->query($sql1);
if ($result1) {
    echo "Found " . $result1->num_rows . " creators:\n";
    while ($row = $result1->fetch_assoc()) {
        echo "  - ID: " . $row['creator_id'] . ", Name: " . $row['name'] . "\n";
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

echo "\n";

// Test 2: Check creators with 50K+ followers
echo "Test 2: Creators with 50K+ followers\n";
$sql2 = "SELECT id, name, follower_count FROM creators WHERE follower_count >= 50000";
$result2 = $conn->query($sql2);
if ($result2) {
    echo "Found " . $result2->num_rows . " creators:\n";
    while ($row = $result2->fetch_assoc()) {
        echo "  - ID: " . $row['id'] . ", Name: " . $row['name'] . ", Followers: " . $row['follower_count'] . "\n";
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

echo "\n";

// Test 3: Try the full query
echo "Test 3: Full query (user 2's followed creators with 50K+ followers and content)\n";
$sql3 = "SELECT DISTINCT 
            c.id,
            c.name,
            c.avatar_url,
            c.follower_count,
            COUNT(cm.id) as content_count
        FROM creators c
        INNER JOIN user_creators uc ON c.id = uc.creator_id
        INNER JOIN creator_mentions cm ON c.id = cm.creator_id
        WHERE uc.user_id = $user_id
          AND c.follower_count >= 50000
        GROUP BY c.id
        ORDER BY content_count DESC";

$result3 = $conn->query($sql3);
if ($result3) {
    echo "Found " . $result3->num_rows . " creators with content:\n";
    while ($row = $result3->fetch_assoc()) {
        echo "  - ID: " . $row['id'] . ", Name: " . $row['name'] . ", Content: " . $row['content_count'] . "\n";
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

$conn->close();
?>