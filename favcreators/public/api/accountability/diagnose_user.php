<?php
/**
 * Diagnostic: Check accountability state for a given user.
 * GET ?app_user_id=2  or  ?discord_id=XXXXX  or  ?username=positivevibesnow
 * Returns what tables have data for this user and why reminders might not fire.
 * DELETE THIS FILE AFTER USE.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/../db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$app_user_id = isset($_GET['app_user_id']) ? intval($_GET['app_user_id']) : 0;
$discord_id  = isset($_GET['discord_id'])  ? $conn->real_escape_string(trim($_GET['discord_id'])) : '';
$username    = isset($_GET['username'])     ? $conn->real_escape_string(trim($_GET['username']))   : '';

$out = array('query' => array('app_user_id' => $app_user_id, 'discord_id' => $discord_id, 'username' => $username));

// 1. Look up in main users table
$user_row = null;
if ($app_user_id) {
    $r = $conn->query("SELECT id, username, discord_id, discord_username FROM users WHERE id = " . $app_user_id);
    if ($r && $r->num_rows > 0) $user_row = $r->fetch_assoc();
}
if (!$user_row && $username) {
    $r = $conn->query("SELECT id, username, discord_id, discord_username FROM users WHERE username = '" . $username . "'");
    if ($r && $r->num_rows > 0) $user_row = $r->fetch_assoc();
}
if (!$user_row && $discord_id) {
    $r = $conn->query("SELECT id, username, discord_id, discord_username FROM users WHERE discord_id = '" . $discord_id . "'");
    if ($r && $r->num_rows > 0) $user_row = $r->fetch_assoc();
}
$out['users_table'] = $user_row ? $user_row : 'NOT FOUND';

// Resolve IDs from users table
if ($user_row) {
    if (!$app_user_id && isset($user_row['id'])) $app_user_id = intval($user_row['id']);
    if (!$discord_id && isset($user_row['discord_id']) && $user_row['discord_id']) $discord_id = $user_row['discord_id'];
}

// 2. Check accountability_users
$acc_user = null;
$conditions = array();
if ($discord_id) $conditions[] = "discord_user_id = '" . $discord_id . "'";
if ($app_user_id) $conditions[] = "app_user_id = " . $app_user_id;
if (count($conditions) > 0) {
    $r = $conn->query("SELECT * FROM accountability_users WHERE " . implode(' OR ', $conditions) . " LIMIT 1");
    if ($r && $r->num_rows > 0) $acc_user = $r->fetch_assoc();
}
$out['accountability_users'] = $acc_user ? $acc_user : 'NOT FOUND';

// 3. Check accountability_tasks
$tasks = array();
if (count($conditions) > 0) {
    $r = $conn->query("SELECT id, task_template, custom_name, is_paused, current_streak, discord_user_id, app_user_id FROM accountability_tasks WHERE " . implode(' OR ', $conditions));
    if ($r) { while ($row = $r->fetch_assoc()) $tasks[] = $row; }
}
$out['accountability_tasks'] = count($tasks) > 0 ? $tasks : 'NONE';
$out['active_tasks_count'] = 0;
foreach ($tasks as $t) {
    if (!$t['is_paused'] || $t['is_paused'] === '0') $out['active_tasks_count']++;
}

// 4. Check accountability_reminder_settings
$reminders = array();
if (count($conditions) > 0) {
    $r = $conn->query("SELECT * FROM accountability_reminder_settings WHERE " . implode(' OR ', $conditions));
    if ($r) { while ($row = $r->fetch_assoc()) $reminders[] = $row; }
}
$out['reminder_settings'] = count($reminders) > 0 ? $reminders : 'NONE';

// 5. Check opt-out status
$optout = null;
if (count($conditions) > 0) {
    $r = $conn->query("SELECT * FROM accountability_followup_optouts WHERE " . implode(' OR ', $conditions) . " LIMIT 1");
    if ($r && $r->num_rows > 0) $optout = $r->fetch_assoc();
}
$out['followup_optout'] = $optout ? $optout : 'NOT OPTED OUT';

// 6. Diagnosis
$reasons = array();
if ($out['users_table'] === 'NOT FOUND') {
    $reasons[] = 'User does not exist in main users table';
}
if ($out['accountability_users'] === 'NOT FOUND') {
    $reasons[] = 'No accountability_users profile — user has never run /fc-coach setup or created a task from dashboard';
}
if ($out['accountability_tasks'] === 'NONE') {
    $reasons[] = 'No accountability_tasks — no goals/tasks have been created for this user';
}
if ($out['active_tasks_count'] === 0 && is_array($out['accountability_tasks'])) {
    $reasons[] = 'All tasks are paused — reminders only fire for unpaused tasks';
}
if ($out['reminder_settings'] === 'NONE') {
    $reasons[] = 'No accountability_reminder_settings — per-task reminders (send_reminders.php) were never configured. This requires explicit setup.';
}
if (is_array($out['reminder_settings'])) {
    $has_discord_on = false;
    $has_dashboard_on = false;
    foreach ($out['reminder_settings'] as $rs) {
        if ($rs['discord_reminder']) $has_discord_on = true;
        if ($rs['dashboard_reminder']) $has_dashboard_on = true;
    }
    if (!$has_discord_on) $reasons[] = 'discord_reminder is OFF for all tasks in reminder_settings';
    if (!$has_dashboard_on) $reasons[] = 'dashboard_reminder is OFF for all tasks in reminder_settings';
}
$has_discord_id_anywhere = false;
if ($discord_id) $has_discord_id_anywhere = true;
if (is_array($out['accountability_tasks'])) {
    foreach ($out['accountability_tasks'] as $t) {
        if (isset($t['discord_user_id']) && $t['discord_user_id']) $has_discord_id_anywhere = true;
    }
}
if (!$has_discord_id_anywhere) {
    $reasons[] = 'No discord_user_id found anywhere — Discord DMs cannot be sent without a numeric Discord user ID';
}

$out['diagnosis'] = count($reasons) > 0 ? $reasons : array('Everything looks configured — check the GitHub Action logs for send_reminders.php errors');

echo json_encode($out);
$conn->close();
