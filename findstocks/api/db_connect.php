<?php
/**
 * Database connection for stock portfolio system
 * PHP 5.2 compatible - uses mysqli
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once dirname(__FILE__) . '/db_config.php';

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed: ' . $conn->connect_error));
    exit;
}

$conn->set_charset('utf8');
?>
