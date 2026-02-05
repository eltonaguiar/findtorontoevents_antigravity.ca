<?php
// Check what content exists for each creator
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Content Count by Creator ===\n\n";

$sql = "SELECT 
            c.id,
            c.name,
            c.follower_count,
            COUNT(cm.id) as content_count
        FROM creators c
        LEFT JOIN creator_mentions cm ON c.id = cm.creator_id
        WHERE c.follower_count >= 50000
        GROUP BY c.id
        ORDER BY content_count DESC, c.follower_count DESC";

$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo sprintf(
            "%-30s | Followers: %10s | Content: %3d\n",
            $row['name'],
            number_format($row['follower_count']),
            $row['content_count']
        );
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

$conn->close();
?>