<?php
require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

// Get a sample of recent items with their timestamps
$sql = "SELECT id, creator_id, title, posted_at, 
        FROM_UNIXTIME(posted_at) as readable_date,
        UNIX_TIMESTAMP() as current_time,
        (UNIX_TIMESTAMP() - posted_at) as age_seconds
        FROM creator_mentions 
        ORDER BY id DESC 
        LIMIT 10";

$result = $conn->query($sql);

$items = array();
while ($row = $result->fetch_assoc()) {
    $items[] = $row;
}

echo json_encode(array(
    'items' => $items,
    'current_server_time' => time(),
    'current_readable' => date('Y-m-d H:i:s')
), JSON_PRETTY_PRINT);

$conn->close();
?>