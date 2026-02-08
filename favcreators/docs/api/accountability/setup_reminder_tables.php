<?php
/**
 * One-time setup: creates the accountability_reminder_settings table.
 * Run via: https://findtorontoevents.ca/fc/api/accountability/setup_reminder_tables.php
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/../db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('ok' => false, 'error' => 'Database not available'));
    exit;
}

$results = array('ok' => true, 'actions' => array());

// 1. Create accountability_reminder_settings table
$sql = "CREATE TABLE IF NOT EXISTS accountability_reminder_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_user_id VARCHAR(32) DEFAULT NULL,
    app_user_id INT DEFAULT NULL,
    task_id INT NOT NULL,
    discord_reminder TINYINT(1) DEFAULT 0,
    dashboard_reminder TINYINT(1) DEFAULT 0,
    reminder_time VARCHAR(5) DEFAULT '09:00',
    timezone VARCHAR(64) DEFAULT 'America/Toronto',
    last_discord_reminder DATETIME DEFAULT NULL,
    last_dashboard_reminder DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_task (discord_user_id, app_user_id, task_id),
    INDEX idx_discord_user (discord_user_id),
    INDEX idx_app_user (app_user_id),
    INDEX idx_task (task_id),
    INDEX idx_discord_reminder (discord_reminder),
    INDEX idx_dashboard_reminder (dashboard_reminder)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if ($conn->query($sql)) {
    $results['actions'][] = 'Created accountability_reminder_settings table (or already exists)';
} else {
    $results['actions'][] = 'Failed: ' . $conn->error;
    $results['ok'] = false;
}

// 2. Create accountability_reminder_log table (prevents duplicate sends)
$sql2 = "CREATE TABLE IF NOT EXISTS accountability_reminder_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_id INT NOT NULL,
    channel VARCHAR(16) NOT NULL COMMENT 'discord or dashboard',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_text TEXT DEFAULT NULL,
    INDEX idx_setting (setting_id),
    INDEX idx_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if ($conn->query($sql2)) {
    $results['actions'][] = 'Created accountability_reminder_log table (or already exists)';
} else {
    $results['actions'][] = 'Failed: ' . $conn->error;
    $results['ok'] = false;
}

$results['message'] = 'Reminder tables setup complete';
echo json_encode($results);
$conn->close();
