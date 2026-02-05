<?php
// Check what creators user 2 follows
require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

$user_id = 2;

// Get creators that user 2 follows
$sql = "SELECT uc.user_id, c.id, c.name, c.follower_count 
        FROM user_creators uc 
        INNER JOIN creators c ON uc.creator_id = c.id 
        WHERE uc.user_id = $user_id";

$result = $conn->query($sql);

$creators = array();
while ($row = $result->fetch_assoc()) {
    $creators[] = $row;
}

echo json_encode(array(
    'user_id' => $user_id,
    'followed_creators' => $creators,
    'count' => count($creators)
));

$conn->close();
?>