<?php
// Database migration script - Creates creator_mentions table
// Path: /findtorontoevents.ca/fc/api/ensure_creator_mentions_table.php

header('Content-Type: application/json');

require_once 'db_config.php';

try {
    $conn = get_db_connection();

    $sql = "CREATE TABLE IF NOT EXISTS creator_mentions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creator_id INT NOT NULL,
        platform VARCHAR(50) NOT NULL,
        content_type VARCHAR(50) NOT NULL,
        content_url TEXT NOT NULL,
        title TEXT,
        description TEXT,
        thumbnail_url TEXT,
        author VARCHAR(255),
        engagement_count INT DEFAULT 0,
        posted_at INT NOT NULL,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_creator_platform (creator_id, platform),
        INDEX idx_posted_at (posted_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

    if ($conn->query($sql) === TRUE) {
        echo json_encode(array(
            'success' => true,
            'message' => 'creator_mentions table created successfully'
        ));
    } else {
        throw new Exception($conn->error);
    }

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}
?>