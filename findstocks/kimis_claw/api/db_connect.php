<?php
/**
 * Database connection for Kimi's Claw API
 * 
 * This file establishes a database connection and returns JSON on error.
 * It should be included AFTER output buffering is started.
 */

// Prevent direct access
if (!defined('KIMIS_CLAW_API')) {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Direct access not allowed'));
    exit;
}

// Include config (no output)
require_once dirname(__FILE__) . '/db_config.php';

// Attempt connection with error suppression
$conn = @new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    ob_clean();
    header('Content-Type: application/json');
    header('Access-Control-Allow-Origin: *');
    echo json_encode(array(
        'ok' => false, 
        'error' => 'Database connection failed: ' . $conn->connect_error,
        'error_code' => $conn->connect_errno
    ));
    exit;
}

// Set charset
$conn->set_charset('utf8');
