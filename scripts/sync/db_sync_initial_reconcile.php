<?php
/**
 * db_sync_initial_reconcile.php -- One-time deterministic merge of existing data.
 *
 * Run ONCE before enabling bi-directional sync. This script:
 *   1. Exports all user-related data from this site
 *   2. Compares with remote site data (provided via POST)
 *   3. Identifies matched users by email, unmatched users
 *   4. Applies per-table merge rules to resolve differences
 *   5. Generates baseline changelog entries marked as "already synced"
 *   6. Reports all decisions made
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage: Two modes:
 *
 *   MODE 1: Export local data for comparison
 *     GET /db_sync_initial_reconcile.php?token=SECRET&db=ejaguiar1_favcreators&mode=export
 *
 *   MODE 2: Reconcile (receives remote data, merges with local, reports differences)
 *     POST /db_sync_initial_reconcile.php
 *     Body: { "token": "...", "db": "...", "mode": "reconcile",
 *             "remote_site": "...", "remote_data": { "users": [...], ... },
 *             "dry_run": true }
 */

header('Content-Type: application/json');

// ── Auth & Params ────────────────────────────────────────────────────────────
$is_post = ($_SERVER['REQUEST_METHOD'] === 'POST');

if ($is_post) {
    $raw = file_get_contents('php://input');
    $input = json_decode($raw, true);
    if (!is_array($input)) $input = array();
    $provided_token = isset($input['token']) ? $input['token'] : '';
    $dbname         = isset($input['db'])    ? $input['db']    : '';
    $mode           = isset($input['mode'])  ? $input['mode']  : 'reconcile';
    $dry_run        = isset($input['dry_run']) ? (bool) $input['dry_run'] : false;
    $remote_site    = isset($input['remote_site']) ? $input['remote_site'] : '';
    $remote_data    = isset($input['remote_data']) ? $input['remote_data'] : array();
} else {
    $provided_token = isset($_GET['token']) ? $_GET['token'] : '';
    $dbname         = isset($_GET['db'])    ? $_GET['db']    : '';
    $mode           = isset($_GET['mode'])  ? $_GET['mode']  : 'export';
    $dry_run        = isset($_GET['dry_run']) ? ((int) $_GET['dry_run'] > 0) : false;
    $remote_site    = '';
    $remote_data    = array();
}

$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $provided_token === '' || $provided_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

$db_host = 'localhost';
$db_user = 'DB_USER_PLACEHOLDER';
$db_pass = 'DB_PASS_PLACEHOLDER';

require_once dirname(__FILE__) . '/sync_config.php';
require_once dirname(__FILE__) . '/sync_helpers.php';

$user_tables_map = sync_get_user_tables();
$tables_for_db = isset($user_tables_map[$dbname]) ? $user_tables_map[$dbname] : array();

if (count($tables_for_db) === 0) {
    echo json_encode(array('error' => 'Invalid database or no user tables defined'));
    exit;
}

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

$this_site = sync_detect_site();

// ═══════════════════════════════════════════════════════════════════════════════
// MODE: EXPORT -- Return all user data from this site as JSON
// ═══════════════════════════════════════════════════════════════════════════════
if ($mode === 'export') {
    $exported = array();

    foreach ($tables_for_db as $tbl) {
        $esc_tbl = $conn->real_escape_string($tbl);
        $check = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
        if (!$check || $check->num_rows === 0) {
            $exported[$tbl] = array();
            continue;
        }

        $rows = array();
        $result = $conn->query("SELECT * FROM `" . $esc_tbl . "`");
        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $rows[] = $row;
            }
        }
        $exported[$tbl] = $rows;
    }

    $conn->close();
    echo json_encode(array(
        'status'    => 'ok',
        'site'      => $this_site,
        'database'  => $dbname,
        'mode'      => 'export',
        'data'      => $exported,
        'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
    ));
    exit;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MODE: RECONCILE -- Compare remote data with local, merge, report
// ═══════════════════════════════════════════════════════════════════════════════

$report = array(
    'matched_users'     => array(),
    'local_only_users'  => array(),
    'remote_only_users' => array(),
    'table_reports'     => array(),
    'actions_taken'     => array(),
    'errors'            => array(),
);

$strategies = sync_get_merge_strategies();
$aggregate_rules = sync_get_aggregate_rules();
$pk_defs = sync_get_primary_keys();

// ── Step 1: Build user maps ─────────────────────────────────────────────────
$local_users = array(); // email => full row
$result = @$conn->query("SELECT * FROM users");
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $email = isset($row['email']) ? $row['email'] : '';
        if ($email !== '') {
            $local_users[$email] = $row;
        }
    }
}

$remote_users = array(); // email => full row
$remote_user_rows = isset($remote_data['users']) ? $remote_data['users'] : array();
foreach ($remote_user_rows as $row) {
    $email = isset($row['email']) ? $row['email'] : '';
    if ($email !== '') {
        $remote_users[$email] = $row;
    }
}

// ── Step 2: Match users ─────────────────────────────────────────────────────
$all_emails = array_unique(array_merge(array_keys($local_users), array_keys($remote_users)));

$user_id_map = array(); // remote_user_id => local_user_id

foreach ($all_emails as $email) {
    $has_local  = isset($local_users[$email]);
    $has_remote = isset($remote_users[$email]);

    if ($has_local && $has_remote) {
        $local_id  = (int) $local_users[$email]['id'];
        $remote_id = (int) $remote_users[$email]['id'];
        $user_id_map[$remote_id] = $local_id;
        $report['matched_users'][] = array(
            'email'     => $email,
            'local_id'  => $local_id,
            'remote_id' => $remote_id,
        );
    } elseif ($has_local && !$has_remote) {
        $report['local_only_users'][] = array(
            'email'    => $email,
            'local_id' => (int) $local_users[$email]['id'],
        );
    } elseif (!$has_local && $has_remote) {
        // Create user locally
        $remote_row = $remote_users[$email];
        $remote_id  = (int) $remote_row['id'];

        if (!$dry_run) {
            $esc_email = $conn->real_escape_string($email);
            $esc_pw    = $conn->real_escape_string(isset($remote_row['password'])     ? $remote_row['password']     : '');
            $esc_role  = $conn->real_escape_string(isset($remote_row['role'])          ? $remote_row['role']          : 'user');
            $esc_name  = $conn->real_escape_string(isset($remote_row['display_name'])  ? $remote_row['display_name']  : '');

            $sql = "INSERT INTO users (email, password, role, display_name, origin_site, sync_version) "
                 . "VALUES ('" . $esc_email . "', '" . $esc_pw . "', '" . $esc_role . "', "
                 . "'" . $esc_name . "', '" . $conn->real_escape_string($remote_site) . "', 1)";

            if ($conn->query($sql)) {
                $new_id = (int) $conn->insert_id;
                $user_id_map[$remote_id] = $new_id;
                $report['remote_only_users'][] = array(
                    'email'        => $email,
                    'remote_id'    => $remote_id,
                    'created_as'   => $new_id,
                    'origin'       => $remote_site,
                );
                $report['actions_taken'][] = 'Created user ' . $email . ' (id=' . $new_id . ') from ' . $remote_site;
            } else {
                $report['errors'][] = 'Failed to create user ' . $email . ': ' . $conn->error;
            }
        } else {
            $report['remote_only_users'][] = array(
                'email'      => $email,
                'remote_id'  => $remote_id,
                'would_create' => true,
            );
        }
    }
}

// ── Step 3: Reconcile per-table data ─────────────────────────────────────────
foreach ($tables_for_db as $tbl) {
    if ($tbl === 'users') continue; // already handled

    $strategy   = isset($strategies[$tbl]) ? $strategies[$tbl] : 'LWW';
    $pk_cols    = isset($pk_defs[$tbl])    ? $pk_defs[$tbl]    : array('id');
    $remote_rows = isset($remote_data[$tbl]) ? $remote_data[$tbl] : array();

    $tbl_report = array(
        'table'        => $tbl,
        'strategy'     => $strategy,
        'remote_rows'  => count($remote_rows),
        'merged'       => 0,
        'inserted'     => 0,
        'skipped'      => 0,
    );

    $esc_tbl = $conn->real_escape_string($tbl);
    $check = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
    if (!$check || $check->num_rows === 0) {
        $tbl_report['skipped'] = count($remote_rows);
        $tbl_report['note'] = 'Table does not exist locally';
        $report['table_reports'][] = $tbl_report;
        continue;
    }

    foreach ($remote_rows as $remote_row) {
        // Remap user_id if present
        if (isset($remote_row['user_id'])) {
            $rid = (int) $remote_row['user_id'];
            if (isset($user_id_map[$rid])) {
                $remote_row['user_id'] = $user_id_map[$rid];
            } else {
                // Can't map this user -- skip
                $tbl_report['skipped']++;
                continue;
            }
        }

        // Remap app_user_id if present (accountability tables)
        if (isset($remote_row['app_user_id']) && $remote_row['app_user_id'] !== null) {
            $rid = (int) $remote_row['app_user_id'];
            if (isset($user_id_map[$rid])) {
                $remote_row['app_user_id'] = $user_id_map[$rid];
            }
        }

        // Build PK for lookup
        $pk_vals = array();
        foreach ($pk_cols as $col) {
            $pk_vals[$col] = isset($remote_row[$col]) ? $remote_row[$col] : '';
        }

        // Check if exists locally
        $where_parts = array();
        foreach ($pk_vals as $col => $val) {
            $where_parts[] = "`" . $conn->real_escape_string($col) . "` = '" . $conn->real_escape_string($val) . "'";
        }
        $where = implode(' AND ', $where_parts);
        $local_result = @$conn->query("SELECT * FROM `" . $esc_tbl . "` WHERE " . $where . " LIMIT 1");
        $local_row = null;
        if ($local_result && $local_result->num_rows > 0) {
            $local_row = $local_result->fetch_assoc();
        }

        if ($local_row === null) {
            // Insert remote row locally
            if (!$dry_run) {
                $cols = array();
                $vals = array();
                foreach ($remote_row as $col => $val) {
                    if ($col === 'id') {
                        // Skip auto-increment unless it's a PK we need
                        if (count($pk_cols) === 1 && $pk_cols[0] === 'id') {
                            continue;
                        }
                    }
                    $cols[] = '`' . $conn->real_escape_string($col) . '`';
                    if ($val === null) {
                        $vals[] = 'NULL';
                    } else {
                        $vals[] = "'" . $conn->real_escape_string($val) . "'";
                    }
                }
                $sql = "INSERT IGNORE INTO `" . $esc_tbl . "` (" . implode(', ', $cols) . ") "
                     . "VALUES (" . implode(', ', $vals) . ")";
                $conn->query($sql);
            }
            $tbl_report['inserted']++;
        } else {
            // Row exists -- apply merge strategy
            if ($strategy === 'JSON_UNION' && $tbl === 'user_lists') {
                if (!$dry_run) {
                    $local_json  = isset($local_row['creators'])  ? $local_row['creators']  : '[]';
                    $remote_json = isset($remote_row['creators']) ? $remote_row['creators'] : '[]';
                    $merged = sync_json_merge_creators($local_json, $remote_json);
                    $conn->query("UPDATE `" . $esc_tbl . "` SET creators = '" . $conn->real_escape_string($merged) . "' WHERE " . $where);
                }
                $tbl_report['merged']++;
            } elseif ($strategy === 'AGGREGATE') {
                $rules = isset($aggregate_rules[$tbl]) ? $aggregate_rules[$tbl] : array();
                if (!$dry_run && count($rules) > 0) {
                    $merged = sync_aggregate_merge($local_row, $remote_row, $rules);
                    $set_parts = array();
                    foreach ($rules as $field => $func) {
                        $val = isset($merged[$field]) ? $merged[$field] : null;
                        if ($val !== null) {
                            $set_parts[] = "`" . $conn->real_escape_string($field) . "` = '" . $conn->real_escape_string($val) . "'";
                        }
                    }
                    if (count($set_parts) > 0) {
                        $conn->query("UPDATE `" . $esc_tbl . "` SET " . implode(', ', $set_parts) . " WHERE " . $where);
                    }
                }
                $tbl_report['merged']++;
            } else {
                // LWW / UNION: keep local (Site A wins for initial reconciliation)
                $tbl_report['skipped']++;
            }
        }
    }

    $report['table_reports'][] = $tbl_report;
}

// ── Step 4: Mark everything as synced (baseline) ─────────────────────────────
if (!$dry_run) {
    $now = gmdate('Y-m-d H:i:s');
    $both_sites = json_encode(array($this_site, $remote_site));
    $esc_both = $conn->real_escape_string($both_sites);

    // Insert a single baseline entry so we know reconciliation happened
    $conn->query("INSERT INTO sync_changelog (table_name, operation, row_key, row_data, user_email, origin_site, sync_version, changed_at, synced_to) "
               . "VALUES ('_reconciliation', 'INSERT', 'baseline', "
               . "'" . $conn->real_escape_string(json_encode(array(
                   'remote_site' => $remote_site,
                   'matched_users' => count($report['matched_users']),
                   'remote_only_users' => count($report['remote_only_users']),
                   'tables_processed' => count($report['table_reports']),
               ))) . "', "
               . "'system', '" . $conn->real_escape_string($this_site) . "', 1, "
               . "'" . $now . "', '" . $esc_both . "')");

    $report['actions_taken'][] = 'Baseline reconciliation entry created';
}

$conn->close();

echo json_encode(array(
    'status'    => (count($report['errors']) === 0) ? 'ok' : 'partial',
    'dry_run'   => $dry_run,
    'site'      => $this_site,
    'database'  => $dbname,
    'mode'      => 'reconcile',
    'report'    => $report,
    'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
));
