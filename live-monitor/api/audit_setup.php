<?php
/**
 * Setup audit_trails table for pick audit logging
 */

require_once dirname(__FILE__) . '/db_connect.php';

$sql = "CREATE TABLE IF NOT EXISTS audit_trails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_class VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    pick_timestamp DATETIME NOT NULL,
    generation_source VARCHAR(100) NOT NULL,
    reasons TEXT,
    supporting_data TEXT,
    pick_details TEXT,
    formatted_for_ai TEXT,
    KEY idx_pick (asset_class, symbol, pick_timestamp)
) ENGINE=MyISAM DEFAULT CHARSET=utf8";

if ($conn->query($sql) === TRUE) {
    // Also try adding formatted_for_ai column if table already exists without it
    $conn->query("ALTER TABLE audit_trails ADD COLUMN formatted_for_ai TEXT");

    echo json_encode(array(
        'success' => true,
        'message' => 'audit_trails table ready'
    ));
} else {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => $conn->error
    ));
}

$conn->close();
