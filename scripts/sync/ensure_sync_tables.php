<?php
/**
 * ensure_sync_tables.php -- Create all sync infrastructure tables.
 * Deploy to both sites and call via HTTP to set up:
 *   sync_changelog, sync_conflicts, sync_table_config
 * Also adds origin_site and sync_version columns to user tables if missing.
 *
 * Protected by DB_SCRIPT_TOKEN.
 * PHP 5.2-safe.
 *
 * Usage: GET /ensure_sync_tables.php?token=SECRET&db=ejaguiar1_favcreators
 *        GET /ensure_sync_tables.php?token=SECRET&db=ALL
 */

header('Content-Type: application/json');

// ── Auth ─────────────────────────────────────────────────────────────────────
$expected_token = isset($_GET['token']) ? $_GET['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER'; // replaced at deploy time

if ($configured_token === '' || $expected_token === '' || $expected_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// ── Config ───────────────────────────────────────────────────────────────────
$db_host = 'localhost';
$db_user = 'DB_USER_PLACEHOLDER';   // replaced at deploy time
$db_pass = 'DB_PASS_PLACEHOLDER';   // replaced at deploy time

$requested_db = isset($_GET['db']) ? $_GET['db'] : '';
$dry_run = isset($_GET['dry_run']) ? ((int) $_GET['dry_run']) : 0;

require_once dirname(__FILE__) . '/sync_config.php';

$user_tables_map = sync_get_user_tables();
$all_dbs = array_keys($user_tables_map);

if ($requested_db === 'ALL') {
    $dbs_to_process = $all_dbs;
} elseif ($requested_db !== '' && in_array($requested_db, $all_dbs)) {
    $dbs_to_process = array($requested_db);
} else {
    echo json_encode(array(
        'error' => 'Invalid db parameter. Use one of: ' . implode(', ', $all_dbs) . ', or ALL'
    ));
    exit;
}

$results = array();

foreach ($dbs_to_process as $dbname) {
    $db_result = array(
        'database' => $dbname,
        'actions'  => array(),
        'errors'   => array(),
    );

    $creds = sync_get_db_creds($dbname);
    $conn_user = ($creds !== null) ? $creds[0] : $db_user;
    $conn_pass = ($creds !== null) ? $creds[1] : $db_pass;
    $conn = @new mysqli($db_host, $conn_user, $conn_pass, $dbname);
    if ($conn->connect_error) {
        $db_result['errors'][] = 'Connection failed: ' . $conn->connect_error;
        $results[] = $db_result;
        continue;
    }
    $conn->set_charset('utf8mb4');

    // ── 1. Create sync_changelog table ───────────────────────────────────
    $sql_changelog = "CREATE TABLE IF NOT EXISTS sync_changelog (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        table_name VARCHAR(128) NOT NULL,
        operation VARCHAR(8) NOT NULL,
        row_key VARCHAR(512) NOT NULL,
        row_data MEDIUMTEXT DEFAULT NULL,
        user_email VARCHAR(255) DEFAULT NULL,
        origin_site VARCHAR(64) NOT NULL,
        sync_version INT UNSIGNED NOT NULL DEFAULT 1,
        changed_at DATETIME NOT NULL,
        synced_to MEDIUMTEXT DEFAULT NULL,
        INDEX idx_changed (changed_at),
        INDEX idx_origin (origin_site),
        INDEX idx_table_op (table_name, operation),
        INDEX idx_email (user_email)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

    if ($dry_run) {
        $db_result['actions'][] = '[DRY RUN] Would create sync_changelog';
    } else {
        if ($conn->query($sql_changelog)) {
            $db_result['actions'][] = 'Created sync_changelog (or already exists)';
        } else {
            $db_result['errors'][] = 'sync_changelog: ' . $conn->error;
        }
    }

    // ── 2. Create sync_conflicts table ───────────────────────────────────
    $sql_conflicts = "CREATE TABLE IF NOT EXISTS sync_conflicts (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        table_name VARCHAR(128) NOT NULL,
        row_key VARCHAR(512) NOT NULL,
        local_data MEDIUMTEXT DEFAULT NULL,
        remote_data MEDIUMTEXT DEFAULT NULL,
        local_version INT UNSIGNED DEFAULT NULL,
        remote_version INT UNSIGNED DEFAULT NULL,
        local_site VARCHAR(64) DEFAULT NULL,
        remote_site VARCHAR(64) DEFAULT NULL,
        conflict_type VARCHAR(64) NOT NULL,
        resolved TINYINT(1) DEFAULT 0,
        resolution_note TEXT DEFAULT NULL,
        created_at DATETIME NOT NULL,
        resolved_at DATETIME DEFAULT NULL,
        INDEX idx_unresolved (resolved, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

    if ($dry_run) {
        $db_result['actions'][] = '[DRY RUN] Would create sync_conflicts';
    } else {
        if ($conn->query($sql_conflicts)) {
            $db_result['actions'][] = 'Created sync_conflicts (or already exists)';
        } else {
            $db_result['errors'][] = 'sync_conflicts: ' . $conn->error;
        }
    }

    // ── 3. Create sync_table_config table ────────────────────────────────
    $sql_config = "CREATE TABLE IF NOT EXISTS sync_table_config (
        table_name VARCHAR(128) PRIMARY KEY,
        merge_strategy VARCHAR(32) NOT NULL DEFAULT 'LWW',
        min_row_threshold INT NOT NULL DEFAULT 0,
        enabled TINYINT(1) NOT NULL DEFAULT 1,
        last_synced_at DATETIME DEFAULT NULL,
        last_row_count INT DEFAULT NULL,
        notes TEXT DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

    if ($dry_run) {
        $db_result['actions'][] = '[DRY RUN] Would create sync_table_config';
    } else {
        if ($conn->query($sql_config)) {
            $db_result['actions'][] = 'Created sync_table_config (or already exists)';
        } else {
            $db_result['errors'][] = 'sync_table_config: ' . $conn->error;
        }
    }

    // ── 4. Seed sync_table_config with merge strategies ──────────────────
    $strategies = sync_get_merge_strategies();
    $thresholds = sync_get_safeguard_thresholds();
    $tables_for_db = isset($user_tables_map[$dbname]) ? $user_tables_map[$dbname] : array();

    foreach ($tables_for_db as $tbl) {
        $strategy  = isset($strategies[$tbl]) ? $strategies[$tbl] : 'LWW';
        $threshold = isset($thresholds[$tbl]) ? $thresholds[$tbl] : (isset($thresholds['_default']) ? $thresholds['_default'] : 0);

        $esc_tbl       = $conn->real_escape_string($tbl);
        $esc_strategy  = $conn->real_escape_string($strategy);

        $sql_seed = "INSERT INTO sync_table_config (table_name, merge_strategy, min_row_threshold) "
                  . "VALUES ('" . $esc_tbl . "', '" . $esc_strategy . "', " . (int)$threshold . ") "
                  . "ON DUPLICATE KEY UPDATE merge_strategy = '" . $esc_strategy . "', "
                  . "min_row_threshold = " . (int)$threshold;

        if ($dry_run) {
            $db_result['actions'][] = '[DRY RUN] Would seed config for ' . $tbl;
        } else {
            if ($conn->query($sql_seed)) {
                $db_result['actions'][] = 'Seeded config for ' . $tbl . ' (' . $strategy . ')';
            } else {
                $db_result['errors'][] = 'seed ' . $tbl . ': ' . $conn->error;
            }
        }
    }

    // ── 5. Add origin_site and sync_version columns to user tables ───────
    foreach ($tables_for_db as $tbl) {
        $esc_tbl = $conn->real_escape_string($tbl);

        // Check if table exists first
        $check = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
        if (!$check || $check->num_rows === 0) {
            $db_result['actions'][] = 'Skipped columns for ' . $tbl . ' (table does not exist yet)';
            continue;
        }

        // Add sync_version if missing
        $cols = $conn->query("SHOW COLUMNS FROM `" . $esc_tbl . "` LIKE 'sync_version'");
        if ($cols && $cols->num_rows === 0) {
            $alter = "ALTER TABLE `" . $esc_tbl . "` ADD COLUMN sync_version INT UNSIGNED NOT NULL DEFAULT 0";
            if ($dry_run) {
                $db_result['actions'][] = '[DRY RUN] Would add sync_version to ' . $tbl;
            } else {
                if ($conn->query($alter)) {
                    $db_result['actions'][] = 'Added sync_version to ' . $tbl;
                } else {
                    $db_result['errors'][] = 'alter ' . $tbl . ' sync_version: ' . $conn->error;
                }
            }
        } else {
            $db_result['actions'][] = $tbl . ' already has sync_version';
        }

        // Add origin_site to users table only
        if ($tbl === 'users') {
            $cols2 = $conn->query("SHOW COLUMNS FROM `users` LIKE 'origin_site'");
            if ($cols2 && $cols2->num_rows === 0) {
                $alter2 = "ALTER TABLE `users` ADD COLUMN origin_site VARCHAR(64) DEFAULT NULL";
                if ($dry_run) {
                    $db_result['actions'][] = '[DRY RUN] Would add origin_site to users';
                } else {
                    if ($conn->query($alter2)) {
                        $db_result['actions'][] = 'Added origin_site to users';
                    } else {
                        $db_result['errors'][] = 'alter users origin_site: ' . $conn->error;
                    }
                }
            } else {
                $db_result['actions'][] = 'users already has origin_site';
            }
        }
    }

    // ── 6. Report current row counts ─────────────────────────────────────
    $row_counts = array();
    foreach ($tables_for_db as $tbl) {
        $esc_tbl = $conn->real_escape_string($tbl);
        $check = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
        if ($check && $check->num_rows > 0) {
            $cnt = $conn->query("SELECT COUNT(*) AS c FROM `" . $esc_tbl . "`");
            if ($cnt) {
                $r = $cnt->fetch_assoc();
                $row_counts[$tbl] = (int) $r['c'];
            }
        }
    }
    $db_result['row_counts'] = $row_counts;

    $conn->close();
    $results[] = $db_result;
}

echo json_encode(array(
    'status'    => 'ok',
    'dry_run'   => (bool) $dry_run,
    'site'      => sync_detect_site(),
    'results'   => $results,
    'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
));
