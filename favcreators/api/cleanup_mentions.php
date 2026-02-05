<?php
// Clean up existing creator_mentions and re-aggregate with fixed script
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

$results = array(
    'success' => true,
    'deleted_count' => 0,
    'message' => ''
);

try {
    // Delete all existing creator_mentions
    $delete_sql = "DELETE FROM creator_mentions";

    if ($conn->query($delete_sql)) {
        $results['deleted_count'] = $conn->affected_rows;
        $results['message'] = "Deleted {$results['deleted_count']} existing records. Ready to re-aggregate.";
    } else {
        throw new Exception("Failed to delete records: " . $conn->error);
    }

} catch (Exception $e) {
    $results['success'] = false;
    $results['message'] = $e->getMessage();
}

echo json_encode($results);
$conn->close();
?>