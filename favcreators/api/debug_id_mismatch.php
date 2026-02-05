<?php
// Check creator ID mismatch
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Creator ID Mismatch Debug ===\n\n";

// Check Zople
echo "ZOPLE:\n";
$sql = "SELECT id, name FROM creators WHERE name LIKE '%zople%'";
$result = $conn->query($sql);
while ($row = $result->fetch_assoc()) {
    echo "  creators table: ID = '{$row['id']}', Name = '{$row['name']}'\n";
}

$sql2 = "SELECT DISTINCT creator_id FROM creator_mentions WHERE creator_id LIKE '%zople%' OR creator_id IN (SELECT id FROM creators WHERE name LIKE '%zople%')";
$result2 = $conn->query($sql2);
if ($result2) {
    while ($row = $result2->fetch_assoc()) {
        echo "  creator_mentions: creator_id = '{$row['creator_id']}'\n";
    }
}

// Check content for Zople
$sql3 = "SELECT cm.id, cm.creator_id, cm.title FROM creator_mentions cm WHERE cm.creator_id IN (SELECT id FROM creators WHERE name LIKE '%zople%')";
$result3 = $conn->query($sql3);
echo "  Content found: " . ($result3 ? $result3->num_rows : 0) . " items\n";

echo "\nNINJA:\n";
$sql = "SELECT id, name FROM creators WHERE name LIKE '%ninja%'";
$result = $conn->query($sql);
while ($row = $result->fetch_assoc()) {
    echo "  creators table: ID = '{$row['id']}', Name = '{$row['name']}'\n";
}

$sql3 = "SELECT cm.id, cm.creator_id, cm.title FROM creator_mentions cm WHERE cm.creator_id IN (SELECT id FROM creators WHERE name LIKE '%ninja%')";
$result3 = $conn->query($sql3);
echo "  Content found: " . ($result3 ? $result3->num_rows : 0) . " items\n";

echo "\nAll creator_mentions with creator names:\n";
$sql4 = "SELECT DISTINCT cm.creator_id, c.name, COUNT(*) as count 
         FROM creator_mentions cm 
         LEFT JOIN creators c ON cm.creator_id = c.id 
         GROUP BY cm.creator_id 
         ORDER BY count DESC";
$result4 = $conn->query($sql4);
while ($row = $result4->fetch_assoc()) {
    echo sprintf(
        "  ID: %-40s | Name: %-20s | Count: %d\n",
        $row['creator_id'],
        $row['name'] ? $row['name'] : 'NOT FOUND',
        $row['count']
    );
}

$conn->close();
?>