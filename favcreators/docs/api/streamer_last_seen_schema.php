<?php
/**
 * Schema for streamer_last_seen tracking feature.
 * Tracks when a live streamer was last seen online for quick updates across users.
 * 
 * Include this once; then run the SQL via $conn->query().
 */

if (!isset($conn) || !$conn) return;

$tables = array(
    'streamer_last_seen' => "CREATE TABLE IF NOT EXISTS streamer_last_seen (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creator_id VARCHAR(64) NOT NULL,
        creator_name VARCHAR(255) NOT NULL,
        platform VARCHAR(32) NOT NULL,
        username VARCHAR(255) NOT NULL,
        account_url VARCHAR(1024) DEFAULT '',
        is_live TINYINT(1) DEFAULT 0,
        last_seen_online DATETIME,
        last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
        stream_title VARCHAR(512) DEFAULT '',
        viewer_count INT DEFAULT 0,
        check_count INT DEFAULT 1,
        first_seen_by VARCHAR(255) DEFAULT '',
        UNIQUE KEY uq_creator_platform (creator_id, platform),
        INDEX idx_is_live (is_live),
        INDEX idx_last_seen_online (last_seen_online),
        INDEX idx_last_checked (last_checked)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'streamer_check_log' => "CREATE TABLE IF NOT EXISTS streamer_check_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creator_id VARCHAR(64) NOT NULL,
        creator_name VARCHAR(255) NOT NULL,
        platform VARCHAR(32) NOT NULL,
        was_live TINYINT(1) DEFAULT 0,
        checked_by VARCHAR(255) DEFAULT '',
        checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        response_time_ms INT DEFAULT 0,
        INDEX idx_creator_id (creator_id),
        INDEX idx_checked_at (checked_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
);

foreach ($tables as $name => $sql) {
    $result = $conn->query($sql);
    if (!$result) {
        error_log("Failed to create table $name: " . $conn->error);
    }
}
?>