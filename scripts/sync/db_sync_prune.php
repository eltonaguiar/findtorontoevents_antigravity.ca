<?php
/**
 * db_sync_prune.php -- Prune old synced changelog entries.
 * Deletes entries older than retention period that have been synced to all sites.
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage: GET /db_sync_prune.php?token=SECRET&db=ejaguiar1_favcreators
 *        GET /db_sync_prune.php?token=SECRET&db=ALL&dry_run=1
 */

header('Content-Type: application/json');

$expected_token   = isset($_GET['token']) ? $_GET['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $expected_token === '' || $expected_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

$db_host    = 'localhost';
$db_user    = 'DB_USER_PLACEHOLDER';
$db_pass    = 'DB_PASS_PLACEHOLDER';
$requested  = isset($_GET['db']) ? $_GET['db'] : '';
$dry_run    = isset($_GET['dry_run']) ? ((int) $_GET['dry_run']) : 0;

require_once dirname(__FILE__) . '/sync_config.php';

$retention_days = sync_get_retention_days();
$user_tables_map = sync_get_user_tables();
$all_dbs = array_keys($user_tables_map);

if ($requested === 'ALL') {
    $dbs = $all_dbs;
} elseif ($requested !== '' && in_array($requested, $all_dbs)) {
    $dbs = array($requested);
} else {
    echo json_encode(array('error' => 'Invalid db parameter'));
    exit;
}

$results = array();

foreach ($dbs as $dbname) {
    $creds = sync_get_db_creds($dbname);
    $conn_user = ($creds !== null) ? $creds[0] : $db_user;
    $conn_pass = ($creds !== null) ? $creds[1] : $db_pass;
    $conn = @new mysqli($db_host, $conn_user, $conn_pass, $dbname);
    if ($conn->connect_error) {
        $results[] = array('db' => $dbname, 'error' => $conn->connect_error);
        continue;
    }
    $conn->set_charset('utf8mb4');

    // Check table exists
    $check = $conn->query("SHOW TABLES LIKE 'sync_changelog'");
    if (!$check || $check->num_rows === 0) {
        $results[] = array('db' => $dbname, 'message' => 'No sync_changelog table');
        $conn->close();
        continue;
    }

    // Count prunable entries (synced_to IS NOT NULL AND older than retention)
    $cutoff = gmdate('Y-m-d H:i:s', time() - ($retention_days * 86400));
    $esc_cutoff = $conn->real_escape_string($cutoff);

    $count_sql = "SELECT COUNT(*) AS c FROM sync_changelog "
               . "WHERE synced_to IS NOT NULL AND changed_at < '" . $esc_cutoff . "'";
    $cnt = $conn->query($count_sql);
    $prunable = 0;
    if ($cnt) {
        $row = $cnt->fetch_assoc();
        $prunable = (int) $row['c'];
    }

    // Also count total
    $total_sql = "SELECT COUNT(*) AS c FROM sync_changelog";
    $tot = $conn->query($total_sql);
    $total = 0;
    if ($tot) {
        $row = $tot->fetch_assoc();
        $total = (int) $row['c'];
    }

    $deleted = 0;
    if (!$dry_run && $prunable > 0) {
        $del_sql = "DELETE FROM sync_changelog "
                 . "WHERE synced_to IS NOT NULL AND changed_at < '" . $esc_cutoff . "'";
        if ($conn->query($del_sql)) {
            $deleted = $conn->affected_rows;
        }
    }

    $results[] = array(
        'db'       => $dbname,
        'total'    => $total,
        'prunable' => $prunable,
        'deleted'  => $deleted,
        'cutoff'   => $cutoff,
    );

    $conn->close();
}

echo json_encode(array(
    'status'         => 'ok',
    'dry_run'        => (bool) $dry_run,
    'retention_days' => $retention_days,
    'results'        => $results,
    'timestamp'      => gmdate('Y-m-d\TH:i:s\Z'),
));
