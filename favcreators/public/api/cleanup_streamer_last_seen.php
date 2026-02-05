<?php
/**
 * Cleanup script for streamer_last_seen tracking feature.
 * Removes old records and check logs to keep the database clean.
 * 
 * GET /api/cleanup_streamer_last_seen.php
 * GET /api/cleanup_streamer_last_seen.php?days=30
 * GET /api/cleanup_streamer_last_seen.php?dry_run=1
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

$days = isset($_GET['days']) ? intval($_GET['days']) : 7;
$dry_run = isset($_GET['dry_run']) && $_GET['dry_run'] == '1';

if ($days < 1) $days = 1;
if ($days > 365) $days = 365;

$results = [];

// Check old records in streamer_last_seen (offline records older than $days)
$old_offline_sql = "SELECT COUNT(*) as count FROM streamer_last_seen 
                    WHERE is_live = 0 AND last_checked < DATE_SUB(NOW(), INTERVAL ? DAY)";
$stmt = $conn->prepare($old_offline_sql);
$stmt->bind_param("i", $days);
$stmt->execute();
$result = $stmt->get_result();
$old_offline_count = $result->fetch_assoc()['count'];
$stmt->close();

$results['old_offline_records'] = [
    'count' => $old_offline_count,
    'criteria' => "is_live = 0 AND last_checked < DATE_SUB(NOW(), INTERVAL $days DAY)"
];

// Check old records in streamer_check_log
$old_logs_sql = "SELECT COUNT(*) as count FROM streamer_check_log 
                 WHERE checked_at < DATE_SUB(NOW(), INTERVAL ? DAY)";
$stmt = $conn->prepare($old_logs_sql);
$stmt->bind_param("i", $days);
$stmt->execute();
$result = $stmt->get_result();
$old_logs_count = $result->fetch_assoc()['count'];
$stmt->close();

$results['old_check_logs'] = [
    'count' => $old_logs_count,
    'criteria' => "checked_at < DATE_SUB(NOW(), INTERVAL $days DAY)"
];

if (!$dry_run && ($old_offline_count > 0 || $old_logs_count > 0)) {
    // Delete old offline records
    if ($old_offline_count > 0) {
        $delete_offline_sql = "DELETE FROM streamer_last_seen 
                               WHERE is_live = 0 AND last_checked < DATE_SUB(NOW(), INTERVAL ? DAY)";
        $stmt = $conn->prepare($delete_offline_sql);
        $stmt->bind_param("i", $days);
        $stmt->execute();
        $deleted_offline = $stmt->affected_rows;
        $stmt->close();
        $results['old_offline_records']['deleted'] = $deleted_offline;
    }
    
    // Delete old check logs
    if ($old_logs_count > 0) {
        $delete_logs_sql = "DELETE FROM streamer_check_log 
                            WHERE checked_at < DATE_SUB(NOW(), INTERVAL ? DAY)";
        $stmt = $conn->prepare($delete_logs_sql);
        $stmt->bind_param("i", $days);
        $stmt->execute();
        $deleted_logs = $stmt->affected_rows;
        $stmt->close();
        $results['old_check_logs']['deleted'] = $deleted_logs;
    }
}

// Get current counts
$current_counts = [];
$tables = ['streamer_last_seen', 'streamer_check_log'];

foreach ($tables as $table) {
    $result = $conn->query("SELECT COUNT(*) as count FROM $table");
    $current_counts[$table] = $result ? $result->fetch_assoc()['count'] : 0;
}

echo json_encode([
    'ok' => true,
    'dry_run' => $dry_run,
    'retention_days' => $days,
    'results' => $results,
    'current_counts' => $current_counts,
    'message' => $dry_run ? 'Dry run complete. No records deleted.' : 'Cleanup complete.'
]);

$conn->close();
?>