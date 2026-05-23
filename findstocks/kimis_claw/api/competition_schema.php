<?php
/**
 * Schema for Kimi's Claw - creates tables if needed
 * 
 * This file contains database schema setup functions.
 * It should NOT output anything directly.
 */

// Prevent direct access
if (!defined('KIMIS_CLAW_API')) {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Direct access not allowed'));
    exit;
}

/**
 * Setup Kimi's Claw schema
 * @param mysqli $conn Database connection
 * @return bool True on success, false on failure
 */
function _kc_setup_schema($conn) {
    if (!($conn instanceof mysqli)) {
        return false;
    }
    
    $result = $conn->query("CREATE TABLE IF NOT EXISTS kc_algorithms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        UNIQUE KEY unique_algo_name (algorithm_name)
    )");
    
    return ($result !== false);
}
