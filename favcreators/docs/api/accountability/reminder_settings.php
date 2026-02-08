<?php
/**
 * Accountability Reminder Settings API — PHP 5.2 compatible
 *
 * GET  — Fetch all reminder settings for a user
 *   ?discord_id=123  or  ?app_user_id=7
 *
 * POST — Save/update reminder settings for one or more tasks
 *   { "discord_id": "123", "settings": [ { "task_id": 1, "discord_reminder": true, ... } ] }
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/../db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('success' => false, 'error' => 'Database not available'));
    exit;
}

// Ensure table exists (auto-setup)
$conn->query("CREATE TABLE IF NOT EXISTS accountability_reminder_settings (
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
    INDEX idx_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

// ────────────────────── GET: fetch settings ──────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $discord_id = isset($_GET['discord_id']) ? $conn->real_escape_string(trim($_GET['discord_id'])) : '';
    $app_user_id = isset($_GET['app_user_id']) ? intval($_GET['app_user_id']) : 0;

    if (!$discord_id && !$app_user_id) {
        echo json_encode(array('success' => false, 'error' => 'Provide discord_id or app_user_id'));
        exit;
    }

    $conditions = array();
    if ($discord_id) $conditions[] = "discord_user_id = '" . $discord_id . "'";
    if ($app_user_id) $conditions[] = "app_user_id = " . $app_user_id;

    $sql = "SELECT id, task_id, discord_reminder, dashboard_reminder, reminder_time, timezone,
                   last_discord_reminder, last_dashboard_reminder, created_at, updated_at
            FROM accountability_reminder_settings
            WHERE " . implode(' OR ', $conditions);

    $result = $conn->query($sql);
    if (!$result) {
        echo json_encode(array('success' => false, 'error' => 'Query failed: ' . $conn->error));
        exit;
    }

    $settings = array();
    while ($row = $result->fetch_assoc()) {
        $settings[] = array(
            'id' => (int)$row['id'],
            'task_id' => (int)$row['task_id'],
            'discord_reminder' => $row['discord_reminder'] ? true : false,
            'dashboard_reminder' => $row['dashboard_reminder'] ? true : false,
            'reminder_time' => $row['reminder_time'],
            'timezone' => $row['timezone'],
            'last_discord_reminder' => $row['last_discord_reminder'],
            'last_dashboard_reminder' => $row['last_dashboard_reminder'],
        );
    }

    echo json_encode(array('success' => true, 'settings' => $settings));
    exit;
}

// ────────────────────── POST: save settings ──────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) {
        echo json_encode(array('success' => false, 'error' => 'Invalid JSON'));
        exit;
    }

    $discord_id = isset($input['discord_id']) ? $conn->real_escape_string(trim($input['discord_id'])) : '';
    $app_user_id = isset($input['app_user_id']) ? intval($input['app_user_id']) : 0;

    if (!$discord_id && !$app_user_id) {
        echo json_encode(array('success' => false, 'error' => 'Provide discord_id or app_user_id'));
        exit;
    }

    $settingsInput = isset($input['settings']) ? $input['settings'] : array();
    if (!is_array($settingsInput) || count($settingsInput) === 0) {
        echo json_encode(array('success' => false, 'error' => 'settings array is required'));
        exit;
    }

    $saved = 0;
    $errors = array();

    $d_id_sql = $discord_id ? "'" . $discord_id . "'" : 'NULL';
    $a_id_sql = $app_user_id ? $app_user_id : 'NULL';

    foreach ($settingsInput as $s) {
        $task_id = isset($s['task_id']) ? intval($s['task_id']) : 0;
        if (!$task_id) { $errors[] = 'Missing task_id in entry'; continue; }

        $discord_rem = !empty($s['discord_reminder']) ? 1 : 0;
        $dashboard_rem = !empty($s['dashboard_reminder']) ? 1 : 0;
        $reminder_time = isset($s['reminder_time']) ? $conn->real_escape_string(trim($s['reminder_time'])) : '09:00';
        $tz = isset($s['timezone']) ? $conn->real_escape_string(trim($s['timezone'])) : 'America/Toronto';

        // Validate time format
        if (!preg_match('/^\d{2}:\d{2}$/', $reminder_time)) {
            $reminder_time = '09:00';
        }

        // Upsert
        $sql = "INSERT INTO accountability_reminder_settings
                    (discord_user_id, app_user_id, task_id, discord_reminder, dashboard_reminder, reminder_time, timezone)
                VALUES ($d_id_sql, $a_id_sql, $task_id, $discord_rem, $dashboard_rem, '$reminder_time', '$tz')
                ON DUPLICATE KEY UPDATE
                    discord_reminder = VALUES(discord_reminder),
                    dashboard_reminder = VALUES(dashboard_reminder),
                    reminder_time = VALUES(reminder_time),
                    timezone = VALUES(timezone)";

        if ($conn->query($sql)) {
            $saved++;
        } else {
            $errors[] = 'Save failed for task ' . $task_id . ': ' . $conn->error;
        }
    }

    echo json_encode(array(
        'success' => count($errors) === 0,
        'saved' => $saved,
        'errors' => $errors,
    ));
    exit;
}

echo json_encode(array('success' => false, 'error' => 'Method not allowed'));
