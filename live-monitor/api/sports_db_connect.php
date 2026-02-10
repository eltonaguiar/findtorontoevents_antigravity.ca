<?php
/**
 * Database connection for Sports Betting APIs
 * Uses ejaguiar1_stocks database (shared with live-monitor)
 * Falls back to sports-specific DB if available
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

// Try dedicated sports DB first, fall back to shared stocks DB
$conn = @new mysqli($sports_servername, $sports_username, $sports_password, $sports_dbname);

if ($conn->connect_error) {
    // Fall back to shared database
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        echo json_encode(array('ok' => false, 'error' => 'Database connection failed: ' . $conn->connect_error));
        exit;
    }
}

$conn->set_charset('utf8');
?>
