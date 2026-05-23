<?php
/**
 * sync_status.php -- Monitoring endpoint for sync health.
 * Returns: last sync time, changelog size, unsynced count, conflict count, row counts.
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage: GET /sync_status.php?token=SECRET&db=ejaguiar1_favcreators
 *        GET /sync_status.php?token=SECRET&db=ALL
 */

header('Content-Type: application/json');

$expected_token   = isset($_GET['token']) ? $_GET['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $expected_token === '' || $expected_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

$db_host   = 'localhost';
$db_user   = 'DB_USER_PLACEHOLDER';
$db_pass   = 'DB_PASS_PLACEHOLDER';
$requested = isset($_GET['db']) ? $_GET['db'] : '';

require_once dirname(__FILE__) . '/sync_config.php';

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
    $db_result = array(
        'database' => $dbname,
        'site'     => sync_detect_site(),
    );

    $creds = sync_get_db_creds($dbname);
    $conn_user = ($creds !== null) ? $creds[0] : $db_user;
    $conn_pass = ($creds !== null) ? $creds[1] : $db_pass;
    $conn = @new mysqli($db_host, $conn_user, $conn_pass, $dbname);
    if ($conn->connect_error) {
        $db_result['error'] = 'Connection failed: ' . $conn->connect_error;
        $results[] = $db_result;
        continue;
    }
    $conn->set_charset('utf8mb4');

    // ── Changelog stats ──────────────────────────────────────────────────
    $cl_exists = $conn->query("SHOW TABLES LIKE 'sync_changelog'");
    if ($cl_exists && $cl_exists->num_rows > 0) {
        // Total entries
        $r = $conn->query("SELECT COUNT(*) AS c FROM sync_changelog");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $db_result['changelog_total'] = (int) $row['c'];
        } else {
            $db_result['changelog_total'] = 0;
        }

        // Unsynced (synced_to IS NULL)
        $r = $conn->query("SELECT COUNT(*) AS c FROM sync_changelog WHERE synced_to IS NULL");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $db_result['changelog_unsynced'] = (int) $row['c'];
        } else {
            $db_result['changelog_unsynced'] = 0;
        }

        // Latest entry
        $r = $conn->query("SELECT changed_at FROM sync_changelog ORDER BY changed_at DESC LIMIT 1");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $db_result['changelog_latest'] = $row['changed_at'];
        } else {
            $db_result['changelog_latest'] = null;
        }

        // Entries by origin
        $r = $conn->query("SELECT origin_site, COUNT(*) AS c FROM sync_changelog GROUP BY origin_site");
        $by_origin = array();
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $by_origin[$row['origin_site']] = (int) $row['c'];
            }
        }
        $db_result['changelog_by_origin'] = $by_origin;
    } else {
        $db_result['changelog_total']    = 0;
        $db_result['changelog_unsynced'] = 0;
        $db_result['changelog_latest']   = null;
        $db_result['changelog_message']  = 'sync_changelog table does not exist';
    }

    // ── Conflict stats ───────────────────────────────────────────────────
    $cf_exists = $conn->query("SHOW TABLES LIKE 'sync_conflicts'");
    if ($cf_exists && $cf_exists->num_rows > 0) {
        $r = $conn->query("SELECT COUNT(*) AS c FROM sync_conflicts WHERE resolved = 0");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $db_result['unresolved_conflicts'] = (int) $row['c'];
        } else {
            $db_result['unresolved_conflicts'] = 0;
        }

        $r = $conn->query("SELECT COUNT(*) AS c FROM sync_conflicts");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $db_result['total_conflicts'] = (int) $row['c'];
        } else {
            $db_result['total_conflicts'] = 0;
        }
    } else {
        $db_result['unresolved_conflicts'] = 0;
        $db_result['total_conflicts'] = 0;
    }

    // ── Table config ─────────────────────────────────────────────────────
    $tc_exists = $conn->query("SHOW TABLES LIKE 'sync_table_config'");
    if ($tc_exists && $tc_exists->num_rows > 0) {
        $r = $conn->query("SELECT table_name, merge_strategy, enabled, last_synced_at, last_row_count FROM sync_table_config ORDER BY table_name");
        $config = array();
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $config[] = $row;
            }
        }
        $db_result['table_config'] = $config;
    }

    // ── Current row counts ───────────────────────────────────────────────
    $tables_for_db = isset($user_tables_map[$dbname]) ? $user_tables_map[$dbname] : array();
    $row_counts = array();
    foreach ($tables_for_db as $tbl) {
        $esc_tbl = $conn->real_escape_string($tbl);
        $tbl_ex = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
        if ($tbl_ex && $tbl_ex->num_rows > 0) {
            $r = $conn->query("SELECT COUNT(*) AS c FROM `" . $esc_tbl . "`");
            if ($r) {
                $row = $r->fetch_assoc();
                $row_counts[$tbl] = (int) $row['c'];
            }
        } else {
            $row_counts[$tbl] = -1; // table doesn't exist
        }
    }
    $db_result['row_counts'] = $row_counts;

    $conn->close();
    $results[] = $db_result;
}

echo json_encode(array(
    'status'    => 'ok',
    'results'   => $results,
    'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
));
