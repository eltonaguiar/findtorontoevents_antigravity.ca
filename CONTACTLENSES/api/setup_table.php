<?php
/**
 * Contact Lens Checker - One-time table setup
 * Creates the contactlens_disclaimer table.
 * Call via: https://findtorontoevents.ca/CONTACTLENSES/api/setup_table.php
 * PHP 5.2 compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_config.php';

try {
    $pdo = cl_get_pdo();

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS contactlens_disclaimer (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_token VARCHAR(64) NOT NULL,
            ip_address VARCHAR(45) DEFAULT NULL,
            user_agent TEXT DEFAULT NULL,
            accepted_at DATETIME NOT NULL,
            disclaimer_version VARCHAR(10) NOT NULL DEFAULT '1.0',
            UNIQUE KEY idx_token_version (user_token, disclaimer_version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    // Verify table exists
    $stmt = $pdo->query("SHOW TABLES LIKE 'contactlens_disclaimer'");
    $exists = $stmt->fetch() ? true : false;

    echo json_encode(array(
        'success' => true,
        'table_exists' => $exists,
        'message' => $exists ? 'Table contactlens_disclaimer ready' : 'Table creation may have failed'
    ));
} catch (Exception $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}
