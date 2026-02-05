<?php
/**
 * Manual database connection test: connect using project config and create/drop a test table.
 * Call from browser or CLI: php test_db_connect.php
 * Uses same credentials as db_connect.php (via db_config.php).
 */
error_reporting(E_ALL);
header('Content-Type: application/json; charset=utf-8');

require_once dirname(__FILE__) . '/db_connect.php';

$test_table = 'favcreators_test_connection_' . date('Ymd_His');

$result = [
    'connected' => true,
    'test_table_created' => false,
    'test_table_dropped' => false,
    'message' => '',
    'error' => null,
];

// Create test table
$create_sql = "CREATE TABLE IF NOT EXISTS `$test_table` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note VARCHAR(255) DEFAULT 'test row'
)";

if ($conn->query($create_sql) !== true) {
    $result['error'] = 'CREATE TABLE failed: ' . $conn->error;
    $result['connected'] = true;
    echo json_encode($result, JSON_PRETTY_PRINT);
    $conn->close();
    exit;
}
$result['test_table_created'] = true;
$result['message'] = "Test table `$test_table` created.";

// Optional: insert one row
$conn->query("INSERT INTO `$test_table` (note) VALUES ('PHP test script row')");

// Drop test table (cleanup)
if ($conn->query("DROP TABLE IF EXISTS `$test_table`") !== true) {
    $result['error'] = 'DROP TABLE failed: ' . $conn->error;
    echo json_encode($result, JSON_PRETTY_PRINT);
    $conn->close();
    exit;
}
$result['test_table_dropped'] = true;
$result['message'] = "Connected successfully. Test table created and dropped. Database is writable.";

echo json_encode($result, JSON_PRETTY_PRINT);
$conn->close();
