<?php
// accountability_summary.php — PHP 5.2 compatible (array(), no closures, no
// short array syntax). Read-only aggregate of the accountability_* tables for
// the "Self-improvement & accountability" section on findtorontoevents.ca/audit.
// CORS-open on purpose: the /audit dashboard (different origin) fetches this.
// Usage: GET /fc/api/accountability_summary.php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store');

require_once dirname(__FILE__) . '/db_connect.php';

function acc_row_count($conn, $sql) {
    $r = $conn->query($sql);
    if (!$r) return 0;
    $row = $r->fetch_row();
    return $row ? (int) $row[0] : 0;
}

$out = array();
$out['generated_at'] = gmdate('Y-m-d\TH:i:s\Z');

// ---- active tasks with streaks -------------------------------------------
$tasks = array();
$sql = "SELECT t.id, t.user_id, COALESCE(NULLIF(t.custom_name,''), t.task_template) AS name,
               t.frequency_type, t.target_per_period, t.current_streak, t.longest_streak,
               t.streak_tier, t.shields, t.is_paused, t.recovery_mode, t.escalation_level,
               t.last_checkin, t.deadline_pushes_total, t.punishment_text, t.benefits_text,
               u.timezone
        FROM accountability_tasks t
        LEFT JOIN accountability_users u ON u.id = t.user_id
        ORDER BY t.is_paused ASC, t.current_streak DESC";
$r = @$conn->query($sql);
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $last = $row['last_checkin'];
        $hours = null;
        if ($last && $last != '0000-00-00 00:00:00') {
            $ts = strtotime($last . ' UTC');
            if ($ts !== false) $hours = round((time() - $ts) / 3600, 1);
        }
        $checks = acc_row_count($conn, "SELECT COUNT(*) FROM accountability_checkins WHERE task_id = " . (int)$row['id']);
        $recent = acc_row_count($conn, "SELECT COUNT(*) FROM accountability_checkins WHERE task_id = " . (int)$row['id'] .
                                        " AND checkin_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)");
        $tasks[] = array(
            'id' => (int)$row['id'],
            'user_id' => (int)$row['user_id'],
            'name' => $row['name'],
            'frequency' => $row['frequency_type'],
            'target_per_period' => (int)$row['target_per_period'],
            'streak' => (int)$row['current_streak'],
            'longest' => (int)$row['longest_streak'],
            'tier' => $row['streak_tier'],
            'shields' => (int)$row['shields'],
            'paused' => (int)$row['is_paused'],
            'recovery' => (int)$row['recovery_mode'],
            'escalation' => (int)$row['escalation_level'],
            'last_checkin' => ($last && $last != '0000-00-00 00:00:00') ? $last : null,
            'hours_since_checkin' => $hours,
            'checkins_total' => $checks,
            'checkins_7d' => $recent,
            'deadline_pushes' => (int)$row['deadline_pushes_total'],
            'punishment' => $row['punishment_text'],
            'benefit' => $row['benefits_text'],
            'timezone' => $row['timezone']
        );
    }
}
$out['tasks'] = $tasks;

// ---- super goals ----------------------------------------------------------
$goals = array();
$r = @$conn->query("SELECT id, user_id, name, icon FROM accountability_super_goals ORDER BY created_at DESC LIMIT 10");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $gid = (int)$row['id'];
        $goals[] = array(
            'id' => $gid,
            'user_id' => (int)$row['user_id'],
            'name' => $row['name'],
            'icon' => $row['icon'],
            'tasks' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_super_goal_tasks WHERE super_goal_id = " . $gid)
        );
    }
}
$out['super_goals'] = $goals;

// ---- detected behaviour patterns -----------------------------------------
$patterns = array();
$r = @$conn->query("SELECT id, user_id, summary_text, lift, consistency_pct, occurrence_count, status, detected_at
                    FROM accountability_patterns ORDER BY detected_at DESC LIMIT 10");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $patterns[] = array(
            'summary' => $row['summary_text'],
            'lift' => $row['lift'] !== null ? (float)$row['lift'] : null,
            'consistency_pct' => $row['consistency_pct'] !== null ? (int)$row['consistency_pct'] : null,
            'occurrences' => (int)$row['occurrence_count'],
            'status' => $row['status'],
            'detected_at' => $row['detected_at']
        );
    }
}
$out['patterns'] = $patterns;

// ---- headline counters ----------------------------------------------------
$out['counters'] = array(
    'users' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_users"),
    'active_tasks' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_tasks WHERE is_paused = 0"),
    'paused_tasks' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_tasks WHERE is_paused = 1"),
    'checkins_total' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_checkins"),
    'checkins_7d' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_checkins WHERE checkin_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)"),
    'checkins_today' => acc_row_count($conn, "SELECT COUNT(*) FROM accountability_checkins WHERE DATE(checkin_time) = CURDATE()")
);

echo json_encode($out);
$conn->close();
// No closing PHP tag — intentional (PHP-only file best practice)
