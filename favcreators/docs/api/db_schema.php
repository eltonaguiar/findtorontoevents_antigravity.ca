<?php
/**
 * Schema for FavCreators: creators table (global pool + guest list), user_lists, creator_defaults, user_notes.
 * Include this once; then run the SQL via $conn->query().
 */
if (!isset($conn) || !$conn) return;

$tables = array(
    'creator_defaults' => "CREATE TABLE IF NOT EXISTS creator_defaults (
        creator_id VARCHAR(64) PRIMARY KEY,
        note TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )",
    'user_notes' => "CREATE TABLE IF NOT EXISTS user_notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        creator_id VARCHAR(64) NOT NULL,
        note TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_creator (user_id, creator_id)
    )",
    'user_secondary_notes' => "CREATE TABLE IF NOT EXISTS user_secondary_notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        creator_id VARCHAR(64) NOT NULL,
        secondary_note TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_creator_secondary (user_id, creator_id)
    )",
    'user_link_lists' => "CREATE TABLE IF NOT EXISTS user_link_lists (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        list_name VARCHAR(255) NOT NULL,
        links TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_list_name (user_id, list_name)
    )",
    'user_lists' => "CREATE TABLE IF NOT EXISTS user_lists (
        user_id INT PRIMARY KEY,
        creators LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )",
    'creators' => "CREATE TABLE IF NOT EXISTS creators (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        bio TEXT,
        avatar_url VARCHAR(1024) DEFAULT '',
        category VARCHAR(128) DEFAULT '',
        reason VARCHAR(255) DEFAULT '',
        tags TEXT,
        accounts TEXT,
        is_favorite TINYINT(1) DEFAULT 0,
        is_pinned TINYINT(1) DEFAULT 0,
        in_guest_list TINYINT(1) DEFAULT 0,
        guest_sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )",
    'favcreatorslogs' => "CREATE TABLE IF NOT EXISTS favcreatorslogs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(64) NOT NULL,
        endpoint VARCHAR(128),
        user_id INT,
        user_email VARCHAR(255),
        user_ip VARCHAR(45),
        status VARCHAR(16) NOT NULL,
        message TEXT,
        payload_summary TEXT,
        error_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_email (user_email),
        INDEX idx_action (action),
        INDEX idx_created_at (created_at),
        INDEX idx_status (status)
    )"
);

foreach ($tables as $name => $sql) {
    $conn->query($sql);
}
