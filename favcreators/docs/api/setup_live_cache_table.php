<?php
/**
 * Setup streamer_live_cache table for caching live status
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/../db_config.php';

try {
    $pdo = getDBConnection();
    
    $sql = "
        CREATE TABLE IF NOT EXISTS streamer_live_cache (
            id INT AUTO_INCREMENT PRIMARY KEY,
            creator_id VARCHAR(255) NOT NULL,
            creator_name VARCHAR(255) NOT NULL,
            avatar_url TEXT,
            platform VARCHAR(50) NOT NULL,
            username VARCHAR(255) NOT NULL,
            is_live TINYINT(1) DEFAULT 0,
            stream_title TEXT,
            viewer_count INT DEFAULT NULL,
            started_at DATETIME DEFAULT NULL,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            next_check_date BIGINT DEFAULT NULL,
            UNIQUE KEY unique_creator_platform (creator_id, platform),
            INDEX idx_is_live (is_live),
            INDEX idx_checked_at (checked_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ";
    
    $pdo->exec($sql);
    
    echo json_encode(array(
        'success' => true,
        'message' => 'streamer_live_cache table created successfully'
    ));
    
} catch (PDOException $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}