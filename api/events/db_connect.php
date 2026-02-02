<?php
/**
 * db_connect.php — Events database connection
 * PHP 5.2 compatible (no anonymous functions, no __DIR__)
 */
error_reporting(0);
ini_set('display_errors', '0');
set_error_handler(create_function('', 'return true;'));
if (!headers_sent()) {
    header('Content-Type: application/json');
}
require_once dirname(__FILE__) . '/db_config.php';

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('error' => 'Database connection failed: ' . $conn->connect_error));
    exit;
}
?>
