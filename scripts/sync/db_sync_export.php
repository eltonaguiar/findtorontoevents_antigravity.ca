<?php
/**
 * db_sync_export.php -- Export unsynced changelog entries from this site.
 * Returns paginated JSON of changelog entries that haven't been synced
 * to the requesting destination site.
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage:
 *   GET /db_sync_export.php?token=SECRET&db=ejaguiar1_favcreators&dest=torontoevent.net
 *   GET /db_sync_export.php?token=SECRET&db=ejaguiar1_favcreators&dest=torontoevent.net&offset=0&limit=1000
 *   GET /db_sync_export.php?token=SECRET&db=ejaguiar1_favcreators&dest=torontoevent.net&dry_run=1
 *
 * Response: JSON with entries array, total_unsynced count, and row_counts for safeguard checks.
 */

header('Content-Type: application/json');

// ── Auth ─────────────────────────────────────────────────────────────────────
$expected_token = isset($_GET['token']) ? $_GET['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $expected_token === '' || $expected_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// ── Params ───────────────────────────────────────────────────────────────────
$db_host  = 'localhost';
$db_user  = 'DB_USER_PLACEHOLDER';
$db_pass  = 'DB_PASS_PLACEHOLDER';
$dbname   = isset($_GET['db'])   ? $_GET['db']   : '';
$dest     = isset($_GET['dest']) ? $_GET['dest'] : '';
$offset   = isset($_GET['offset']) ? max(0, (int) $_GET['offset']) : 0;
$limit    = isset($_GET['limit'])  ? min(5000, max(1, (int) $_GET['limit'])) : 1000;
$dry_run  = isset($_GET['dry_run']) ? ((int) $_GET['dry_run']) : 0;

if ($dbname === '' || $dest === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Missing db or dest parameter'));
    exit;
}

if (!preg_match('/^[a-zA-Z0-9_]+$/', $dbname)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Invalid database name'));
    exit;
}

require_once dirname(__FILE__) . '/sync_config.php';

// ── Connect ──────────────────────────────────────────────────────────────────
$creds = sync_get_db_creds($dbname);
$conn_user = ($creds !== null) ? $creds[0] : $db_user;
$conn_pass = ($creds !== null) ? $creds[1] : $db_pass;
$conn = @new mysqli($db_host, $conn_user, $conn_pass, $dbname);
if ($conn->connect_error) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => 'DB connection failed: ' . $conn->connect_error));
    exit;
}
$conn->set_charset('utf8mb4');

// ── Check sync_changelog exists ──────────────────────────────────────────────
$tbl_check = $conn->query("SHOW TABLES LIKE 'sync_changelog'");
if (!$tbl_check || $tbl_check->num_rows === 0) {
    echo json_encode(array(
        'status'  => 'ok',
        'message' => 'sync_changelog table does not exist yet',
        'entries' => array(),
        'total_unsynced' => 0,
    ));
    $conn->close();
    exit;
}

// ── Fetch unsynced entries ───────────────────────────────────────────────────
// An entry is "unsynced" to destination if:
//   1. synced_to IS NULL (never synced anywhere), OR
//   2. synced_to does not contain the destination site name
// AND the entry did NOT originate from the destination (prevent ping-pong).

$esc_dest = $conn->real_escape_string($dest);

// Count total unsynced
$count_sql = "SELECT COUNT(*) AS c FROM sync_changelog "
           . "WHERE origin_site != '" . $esc_dest . "' "
           . "AND (synced_to IS NULL OR synced_to NOT LIKE '%" . $esc_dest . "%')";
$count_result = $conn->query($count_sql);
$total_unsynced = 0;
if ($count_result) {
    $crow = $count_result->fetch_assoc();
    $total_unsynced = (int) $crow['c'];
}

// Fetch batch
$fetch_sql = "SELECT id, table_name, operation, row_key, row_data, user_email, "
           . "origin_site, sync_version, changed_at "
           . "FROM sync_changelog "
           . "WHERE origin_site != '" . $esc_dest . "' "
           . "AND (synced_to IS NULL OR synced_to NOT LIKE '%" . $esc_dest . "%') "
           . "ORDER BY changed_at ASC, id ASC "
           . "LIMIT " . $limit . " OFFSET " . $offset;

$entries = array();
$fetch_result = $conn->query($fetch_sql);
if ($fetch_result) {
    while ($row = $fetch_result->fetch_assoc()) {
        $entries[] = array(
            'id'           => (int) $row['id'],
            'table_name'   => $row['table_name'],
            'operation'    => $row['operation'],
            'row_key'      => $row['row_key'],
            'row_data'     => $row['row_data'],
            'user_email'   => $row['user_email'],
            'origin_site'  => $row['origin_site'],
            'sync_version' => (int) $row['sync_version'],
            'changed_at'   => $row['changed_at'],
        );
    }
}

// ── Row counts for safeguard checks ──────────────────────────────────────────
$user_tables_map = sync_get_user_tables();
$tables_for_db = isset($user_tables_map[$dbname]) ? $user_tables_map[$dbname] : array();
$row_counts = array();

foreach ($tables_for_db as $tbl) {
    $esc_tbl = $conn->real_escape_string($tbl);
    $tbl_exists = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
    if ($tbl_exists && $tbl_exists->num_rows > 0) {
        $cnt = $conn->query("SELECT COUNT(*) AS c FROM `" . $esc_tbl . "`");
        if ($cnt) {
            $r = $cnt->fetch_assoc();
            $row_counts[$tbl] = (int) $r['c'];
        }
    }
}

$conn->close();

echo json_encode(array(
    'status'         => 'ok',
    'dry_run'        => (bool) $dry_run,
    'source_site'    => sync_detect_site(),
    'dest_site'      => $dest,
    'database'       => $dbname,
    'total_unsynced' => $total_unsynced,
    'offset'         => $offset,
    'limit'          => $limit,
    'returned'       => count($entries),
    'entries'        => $entries,
    'row_counts'     => $row_counts,
    'timestamp'      => gmdate('Y-m-d\TH:i:s\Z'),
));
