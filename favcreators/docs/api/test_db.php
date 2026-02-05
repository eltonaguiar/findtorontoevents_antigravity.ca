<?php
header('Content-Type: application/json');
$result = array('step' => 'start');

// Test 1: Include db_connect
try {
    require_once 'db_connect.php';
    $result['db_connect'] = 'success';
    $result['conn_exists'] = isset($conn);
} catch (Exception $e) {
    $result['db_connect'] = 'error: ' . $e->getMessage();
}

echo json_encode($result);