<?php
/**
 * Accountability Coach — Daily Reminder Dispatcher — PHP 5.2 compatible
 *
 * Called by cron / GitHub Action hourly.
 * Checks each user's reminder_time + timezone, and if it's time:
 *   - Sends a Discord DM if discord_reminder is on
 *   - Creates a web_notification row if dashboard_reminder is on
 *
 * Requires: X-API-Key header matching EVENT_NOTIFY_API_KEY env var
 *
 * GET  ?dry_run=1  — preview who would be reminded (no DMs sent)
 * POST             — actually send reminders
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/../db_connect.php';
require_once dirname(__FILE__) . '/../discord_config.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('success' => false, 'error' => 'Database not available'));
    exit;
}

// Auth check
$apiKey = isset($_SERVER['HTTP_X_API_KEY']) ? $_SERVER['HTTP_X_API_KEY'] : '';
$expectedKey = _discord_read_env('ACCOUNTABILITY_REMINDER_KEY', '');
if (!$expectedKey) $expectedKey = _discord_read_env('EVENT_NOTIFY_API_KEY', '');

if (!$apiKey || $apiKey !== $expectedKey) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('success' => false, 'error' => 'Unauthorized'));
    exit;
}

$dryRun = isset($_GET['dry_run']) && $_GET['dry_run'] === '1';

// Ensure tables exist
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

// Fetch all active reminder settings joined with tasks
$sql = "SELECT rs.*, at2.custom_name, at2.task_template, at2.current_streak,
               at2.completions_this_period, at2.target_per_period, at2.is_paused
        FROM accountability_reminder_settings rs
        LEFT JOIN accountability_tasks at2 ON rs.task_id = at2.id
        WHERE (rs.discord_reminder = 1 OR rs.dashboard_reminder = 1)
          AND (at2.is_paused IS NULL OR at2.is_paused = 0)";

$result = $conn->query($sql);
if (!$result) {
    // Tables might not exist yet
    echo json_encode(array('success' => true, 'sent_discord' => 0, 'sent_dashboard' => 0, 'message' => 'No data yet'));
    exit;
}

$discord_config = get_discord_config();
$bot_token = $discord_config['bot_token'];

$sentDiscord = 0;
$sentDashboard = 0;
$skipped = 0;
$errors = array();
$previews = array();

while ($row = $result->fetch_assoc()) {
    $tz = $row['timezone'] ? $row['timezone'] : 'America/Toronto';

    // Get current hour in user's timezone (PHP 5.2 compatible with DateTime)
    $nowInTz = new DateTime('now', new DateTimeZone($tz));
    $currentHour = $nowInTz->format('H');
    $reminderHour = substr($row['reminder_time'], 0, 2);

    // Only send if we're in the right hour window
    if ($currentHour !== $reminderHour) {
        $skipped++;
        continue;
    }

    // Check if already sent today
    $todayDate = $nowInTz->format('Y-m-d');
    $taskName = $row['custom_name'] ? $row['custom_name'] : ($row['task_template'] ? $row['task_template'] : 'your task');
    $streak = intval($row['current_streak']);
    $completions = intval($row['completions_this_period']);
    $target = intval($row['target_per_period']);

    // Build motivational message
    $progress = $target > 0 ? round(($completions / $target) * 100) : 0;
    $message = "**🎯 Accountability Check-In: " . $taskName . "**\n\n";
    if ($streak > 0) {
        $message .= "🔥 You're on a **" . $streak . "-day streak**! Don't break it!\n";
    }
    if ($target > 0) {
        $message .= "📊 Progress this period: **" . $completions . "/" . $target . "** (" . $progress . "%)\n";
    }
    if ($progress >= 100) {
        $message .= "✅ You've hit your target! Keep the momentum going.\n";
    } elseif ($progress >= 50) {
        $message .= "💪 You're over halfway — finish strong today!\n";
    } else {
        $message .= "⏰ Time to get moving! Check in when you're done.\n";
    }
    $message .= "\n📱 Dashboard: https://findtorontoevents.ca/fc/#/accountability";
    $message .= "\n💬 Or use `/fc-coach checkin taskname:" . $taskName . "` in Discord";

    // Discord DM
    if ($row['discord_reminder'] && $row['discord_user_id'] && $bot_token) {
        $lastSent = $row['last_discord_reminder'];
        if ($lastSent && substr($lastSent, 0, 10) === $todayDate) {
            // Already sent today — skip
        } else {
            if ($dryRun) {
                $previews[] = array('channel' => 'discord', 'discord_id' => $row['discord_user_id'], 'task' => $taskName, 'message' => $message);
            } else {
                $dmSent = _send_discord_dm($row['discord_user_id'], $message, $bot_token);
                if ($dmSent) {
                    $sentDiscord++;
                    $conn->query("UPDATE accountability_reminder_settings SET last_discord_reminder = NOW() WHERE id = " . intval($row['id']));
                } else {
                    $errors[] = "Discord DM failed for user " . $row['discord_user_id'] . ", task " . $taskName;
                }
            }
        }
    }

    // Dashboard web notification
    if ($row['dashboard_reminder']) {
        $lastDashSent = $row['last_dashboard_reminder'];
        if ($lastDashSent && substr($lastDashSent, 0, 10) === $todayDate) {
            // Already sent today — skip
        } else {
            $title = "🎯 Time to check in: " . $taskName;
            if ($streak > 0) {
                $body = "You're on a " . $streak . "-day streak! Don't break it. " . $completions . "/" . $target . " done this period.";
            } else {
                $body = "Time to make progress on " . $taskName . ". " . $completions . "/" . $target . " done this period.";
            }

            if ($dryRun) {
                $previews[] = array('channel' => 'dashboard', 'discord_id' => $row['discord_user_id'], 'app_user_id' => $row['app_user_id'], 'task' => $taskName, 'title' => $title);
            } else {
                $esc_discord = $row['discord_user_id'] ? "'" . $conn->real_escape_string($row['discord_user_id']) . "'" : 'NULL';
                $esc_app = $row['app_user_id'] ? intval($row['app_user_id']) : 'NULL';
                $esc_title = $conn->real_escape_string($title);
                $esc_body = $conn->real_escape_string($body);

                $notifSql = "INSERT INTO accountability_web_notifications (discord_user_id, app_user_id, type, title, body)
                             VALUES ($esc_discord, $esc_app, 'reminder', '$esc_title', '$esc_body')";
                if ($conn->query($notifSql)) {
                    $sentDashboard++;
                    $conn->query("UPDATE accountability_reminder_settings SET last_dashboard_reminder = NOW() WHERE id = " . intval($row['id']));
                }
            }
        }
    }
}

$output = array(
    'success' => true,
    'dry_run' => $dryRun,
    'sent_discord' => $sentDiscord,
    'sent_dashboard' => $sentDashboard,
    'skipped' => $skipped,
    'errors' => $errors,
);
if ($dryRun) $output['previews'] = $previews;

echo json_encode($output);
$conn->close();

// ── Helper: Send Discord DM ──
function _send_discord_dm($userId, $message, $botToken) {
    // Step 1: Create DM channel
    $ch = curl_init('https://discord.com/api/v10/users/@me/channels');
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Authorization: Bot ' . $botToken,
        'Content-Type: application/json',
    ));
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(array('recipient_id' => $userId)));
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    $resp = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode != 200 || !$resp) return false;

    $data = json_decode($resp, true);
    $channelId = isset($data['id']) ? $data['id'] : '';
    if (!$channelId) return false;

    // Step 2: Send message
    $ch2 = curl_init("https://discord.com/api/v10/channels/" . $channelId . "/messages");
    curl_setopt($ch2, CURLOPT_POST, true);
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_HTTPHEADER, array(
        'Authorization: Bot ' . $botToken,
        'Content-Type: application/json',
    ));
    curl_setopt($ch2, CURLOPT_POSTFIELDS, json_encode(array('content' => $message)));
    curl_setopt($ch2, CURLOPT_TIMEOUT, 10);
    $resp2 = curl_exec($ch2);
    $httpCode2 = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
    curl_close($ch2);

    return $httpCode2 == 200;
}
