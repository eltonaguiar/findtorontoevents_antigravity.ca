<?php
/**
 * One-time setup script to add Discord integration columns and tables.
 * Run via: https://findtorontoevents.ca/fc/api/setup_discord_tables.php
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

$results = array('ok' => true, 'actions' => array());

// 1. Add discord_id and discord_username to users table if not exists
$checkCol = $conn->query("SHOW COLUMNS FROM users LIKE 'discord_id'");
if ($checkCol && $checkCol->num_rows === 0) {
    $sql = "ALTER TABLE users 
            ADD COLUMN discord_id VARCHAR(32) DEFAULT NULL,
            ADD COLUMN discord_username VARCHAR(64) DEFAULT NULL";
    if ($conn->query($sql)) {
        $results['actions'][] = 'Added discord_id and discord_username columns to users table';
    } else {
        $results['actions'][] = 'Failed to add columns to users: ' . $conn->error;
    }
} else {
    $results['actions'][] = 'discord_id column already exists in users table';
}

// 2. Create notification_preferences table if not exists
$sql = "CREATE TABLE IF NOT EXISTS notification_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    creator_id VARCHAR(64) NOT NULL,
    discord_notify TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_creator (user_id, creator_id),
    INDEX idx_user_id (user_id),
    INDEX idx_creator_id (creator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if ($conn->query($sql)) {
    $results['actions'][] = 'Created notification_preferences table (or already exists)';
} else {
    $results['actions'][] = 'Failed to create notification_preferences: ' . $conn->error;
}

// 3. Create notification_log table to track sent notifications (prevent spam)
$sql = "CREATE TABLE IF NOT EXISTS notification_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(64) NOT NULL,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    users_notified INT DEFAULT 0,
    INDEX idx_creator_platform (creator_id, platform),
    INDEX idx_notified_at (notified_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if ($conn->query($sql)) {
    $results['actions'][] = 'Created notification_log table (or already exists)';
} else {
    $results['actions'][] = 'Failed to create notification_log: ' . $conn->error;
}

$results['message'] = 'Discord tables setup complete';
echo json_encode($results);

$conn->close();
