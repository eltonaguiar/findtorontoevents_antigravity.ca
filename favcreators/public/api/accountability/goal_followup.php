<?php
/**
 * Accountability Coach — Morning Goal Follow-Up Dispatcher — PHP 5.2 compatible
 *
 * Called by GitHub Actions cron daily at 14:00 UTC (9 AM EST).
 * Sends a follow-up DM to every user with active (unpaused) goals
 * who has NOT opted out of morning follow-ups.
 *
 * The DM includes:
 *   - Summary of active goals & streaks
 *   - A "Stop Follow-ups" button (Discord component interaction)
 *   - An opt-out web link
 *   - Instructions for opting out via dashboard
 *
 * Requires: X-API-Key header matching EVENT_NOTIFY_API_KEY env var
 *
 * GET  ?dry_run=1  — preview who would be messaged (no DMs sent)
 * POST             — actually send follow-ups
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Allow GET with ?method=post as ModSecurity fallback (412 on POST)
$_is_post_intent = ($_SERVER['REQUEST_METHOD'] === 'POST')
    || (isset($_GET['method']) && $_GET['method'] === 'post');

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

// ── Ensure opt-out table exists ──
$conn->query("CREATE TABLE IF NOT EXISTS accountability_followup_optouts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_user_id VARCHAR(32) DEFAULT NULL,
    app_user_id INT DEFAULT NULL,
    opted_out_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_discord (discord_user_id),
    INDEX idx_app_user (app_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

// ── Ensure sent-today tracking table exists ──
$conn->query("CREATE TABLE IF NOT EXISTS accountability_followup_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_user_id VARCHAR(32) NOT NULL,
    sent_date DATE NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_date (discord_user_id, sent_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

// ── Fetch all distinct Discord users with active (unpaused) tasks ──
// LEFT JOIN to exclude opted-out users
$sql = "SELECT DISTINCT at2.discord_user_id
        FROM accountability_tasks at2
        LEFT JOIN accountability_followup_optouts afo
            ON at2.discord_user_id = afo.discord_user_id
        WHERE at2.discord_user_id IS NOT NULL
          AND at2.discord_user_id != ''
          AND (at2.is_paused = 0 OR at2.is_paused IS NULL)
          AND afo.id IS NULL";

$result = $conn->query($sql);
if (!$result) {
    echo json_encode(array('success' => true, 'sent' => 0, 'message' => 'No data yet or table missing'));
    exit;
}

$discord_config = get_discord_config();
$bot_token = $discord_config['bot_token'];

// Secret for opt-out token generation
$optout_secret = _discord_read_env('ACCOUNTABILITY_FOLLOWUP_SECRET', '');
if (!$optout_secret) $optout_secret = _discord_read_env('EVENT_NOTIFY_API_KEY', 'fallback_secret_key');

$sent = 0;
$skipped = 0;
$errors = array();
$previews = array();

// Today's date in EST for dedup
$estNow = new DateTime('now', new DateTimeZone('America/Toronto'));
$todayDate = $estNow->format('Y-m-d');
$currentHour = (int) $estNow->format('H');

// Only send between 8-10 AM EST to allow for cron timing variance
if ($currentHour < 8 || $currentHour > 10) {
    echo json_encode(array(
        'success' => true,
        'sent' => 0,
        'skipped' => 0,
        'message' => 'Outside 8-10 AM EST window (current hour: ' . $currentHour . '). No follow-ups sent.'
    ));
    $conn->close();
    exit;
}

while ($row = $result->fetch_assoc()) {
    $discordUserId = $row['discord_user_id'];

    // Check if already sent today
    $checkSql = "SELECT id FROM accountability_followup_log
                 WHERE discord_user_id = '" . $conn->real_escape_string($discordUserId) . "'
                   AND sent_date = '" . $conn->real_escape_string($todayDate) . "'";
    $checkResult = $conn->query($checkSql);
    if ($checkResult && $checkResult->num_rows > 0) {
        $skipped++;
        continue;
    }

    // Fetch user's active tasks summary
    $taskSql = "SELECT custom_name, task_template, current_streak,
                       completions_this_period, target_per_period
                FROM accountability_tasks
                WHERE discord_user_id = '" . $conn->real_escape_string($discordUserId) . "'
                  AND (is_paused = 0 OR is_paused IS NULL)
                ORDER BY current_streak DESC";
    $taskResult = $conn->query($taskSql);
    if (!$taskResult || $taskResult->num_rows === 0) {
        $skipped++;
        continue;
    }

    $tasks = array();
    $topStreak = 0;
    $totalTasks = 0;
    while ($t = $taskResult->fetch_assoc()) {
        $totalTasks++;
        $taskName = $t['custom_name'] ? $t['custom_name'] : ($t['task_template'] ? $t['task_template'] : 'Task');
        $streak = intval($t['current_streak']);
        $completions = intval($t['completions_this_period']);
        $target = intval($t['target_per_period']);
        if ($streak > $topStreak) $topStreak = $streak;
        $tasks[] = array(
            'name' => $taskName,
            'streak' => $streak,
            'completions' => $completions,
            'target' => $target
        );
    }

    // Build the motivational follow-up message
    $message = "**☀️ Good Morning! Daily Goal Follow-Up**\n\n";

    if ($topStreak > 0) {
        $message .= "🔥 Your best active streak: **" . $topStreak . " days** — keep it alive!\n\n";
    }

    $message .= "**Your " . $totalTasks . " active goal" . ($totalTasks > 1 ? "s" : "") . ":**\n";

    $taskCount = 0;
    foreach ($tasks as $t) {
        $taskCount++;
        if ($taskCount > 5) {
            $message .= "  _...and " . ($totalTasks - 5) . " more_\n";
            break;
        }
        $streakEmoji = $t['streak'] > 0 ? ' 🔥' . $t['streak'] : '';
        $progress = '';
        if ($t['target'] > 0) {
            $progress = ' (' . $t['completions'] . '/' . $t['target'] . ')';
        }
        $message .= "• **" . $t['name'] . "**" . $progress . $streakEmoji . "\n";
    }

    $message .= "\n💪 What will you work on today? Check in when you're done!\n";
    $message .= "\n📱 **Dashboard:** https://findtorontoevents.ca/fc/#/accountability";
    $message .= "\n💬 **Check in:** `/fc-coach checkin taskname:YOUR_TASK`";

    // Generate opt-out token
    $optoutToken = _generate_optout_token($discordUserId, $optout_secret);
    $optoutUrl = 'https://findtorontoevents.ca/fc/api/accountability/goal_followup_optout.php'
               . '?discord_id=' . urlencode($discordUserId)
               . '&token=' . urlencode($optoutToken);

    $message .= "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━";
    $message .= "\n🔕 **To stop these morning follow-ups:**";
    $message .= "\n• Click the **Stop Follow-ups** button below";
    $message .= "\n• Or visit: " . $optoutUrl;
    $message .= "\n• Or toggle it off in your [Accountability Dashboard](https://findtorontoevents.ca/fc/#/accountability)";

    // Build components (button for opt-out)
    $components = array(
        array(
            'type' => 1,
            'components' => array(
                array(
                    'type' => 2,
                    'style' => 4,
                    'label' => 'Stop Follow-ups',
                    'custom_id' => 'goal_followup_optout:' . $discordUserId,
                    'emoji' => array('name' => '🔕')
                ),
                array(
                    'type' => 2,
                    'style' => 5,
                    'label' => 'Open Dashboard',
                    'url' => 'https://findtorontoevents.ca/fc/#/accountability'
                )
            )
        )
    );

    if ($dryRun) {
        $previews[] = array(
            'discord_id' => $discordUserId,
            'tasks' => $totalTasks,
            'top_streak' => $topStreak,
            'message_preview' => substr($message, 0, 200) . '...'
        );
    } else {
        $dmSent = _send_followup_dm($discordUserId, $message, $components, $bot_token);
        if ($dmSent) {
            $sent++;
            // Log that we sent today
            $conn->query("INSERT IGNORE INTO accountability_followup_log
                          (discord_user_id, sent_date) VALUES
                          ('" . $conn->real_escape_string($discordUserId) . "', '" . $conn->real_escape_string($todayDate) . "')");
        } else {
            $errors[] = 'DM failed for user ' . $discordUserId;
        }
    }
}

$output = array(
    'success' => true,
    'dry_run' => $dryRun,
    'sent' => $sent,
    'skipped' => $skipped,
    'errors' => $errors,
    'date' => $todayDate,
    'hour_est' => $currentHour
);
if ($dryRun) $output['previews'] = $previews;

echo json_encode($output);
$conn->close();

// ── Helper: Generate HMAC-based opt-out token ──
function _generate_optout_token($discordUserId, $secret) {
    return substr(hash_hmac('sha256', 'optout:' . $discordUserId, $secret), 0, 32);
}

// ── Helper: Verify opt-out token ──
function _verify_optout_token($discordUserId, $token, $secret) {
    $expected = _generate_optout_token($discordUserId, $secret);
    return $token === $expected;
}

// ── Helper: Send Discord DM with components (buttons) ──
function _send_followup_dm($userId, $message, $components, $botToken) {
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

    // Step 2: Send message with components
    $payload = array(
        'content' => $message,
        'components' => $components
    );

    $ch2 = curl_init('https://discord.com/api/v10/channels/' . $channelId . '/messages');
    curl_setopt($ch2, CURLOPT_POST, true);
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_HTTPHEADER, array(
        'Authorization: Bot ' . $botToken,
        'Content-Type: application/json',
    ));
    curl_setopt($ch2, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch2, CURLOPT_TIMEOUT, 10);
    $resp2 = curl_exec($ch2);
    $httpCode2 = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
    curl_close($ch2);

    return $httpCode2 == 200;
}
