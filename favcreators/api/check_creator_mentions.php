<?php
// Check all content in creator_mentions
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== All Content in creator_mentions ===\n\n";

$sql = "SELECT 
            cm.id,
            cm.creator_id,
            c.name as creator_name,
            cm.title,
            cm.platform,
            cm.posted_at
        FROM creator_mentions cm
        LEFT JOIN creators c ON cm.creator_id = c.id
        ORDER BY cm.posted_at DESC
        LIMIT 50";

$result = $conn->query($sql);

if ($result) {
    echo "Total rows: " . $result->num_rows . "\n\n";

    while ($row = $result->fetch_assoc()) {
        echo sprintf(
            "ID: %3d | Creator: %-20s | Platform: %-10s | %s\n",
            $row['id'],
            $row['creator_name'] ? $row['creator_name'] : 'ID:' . $row['creator_id'],
            $row['platform'],
            substr($row['title'], 0, 60)
        );
    }
} else {
    echo "ERROR: " . $conn->error . "\n";
}

echo "\n\n=== Content by Creator ===\n";

$sql2 = "SELECT 
            c.name,
            COUNT(cm.id) as count
        FROM creators c
        LEFT JOIN creator_mentions cm ON c.id = cm.creator_id
        GROUP BY c.id
        HAVING count > 0
        ORDER BY count DESC";

$result2 = $conn->query($sql2);

while ($row = $result2->fetch_assoc()) {
    echo sprintf("%-30s: %3d items\n", $row['name'], $row['count']);
}

$conn->close();
?>