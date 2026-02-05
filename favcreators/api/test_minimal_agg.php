<?php
// Minimal test of aggregation logic
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(60);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

echo json_encode(array('status' => 'starting'));
flush();

try {
    // Test query
    $sql = "SELECT id, name FROM creators WHERE follower_count >= 50000 LIMIT 2";
    $result = $conn->query($sql);

    if (!$result) {
        throw new Exception("Query failed: " . $conn->error);
    }

    $creators = array();
    while ($row = $result->fetch_assoc()) {
        $creators[] = $row;
    }

    echo json_encode(array(
        'success' => true,
        'creators_found' => count($creators),
        'creators' => $creators
    ));

} catch (Exception $e) {
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}

$conn->close();
?>