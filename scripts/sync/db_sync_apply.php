<?php
/**
 * db_sync_apply.php -- Apply changelog entries from a remote site.
 * Receives JSON POST with entries, resolves user_id via denormalized email,
 * applies per-table merge strategies, logs conflicts, supports dry-run.
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage: POST /db_sync_apply.php
 *   Body (JSON): {
 *     "token": "SECRET",
 *     "db": "ejaguiar1_favcreators",
 *     "source_site": "findtorontoevents.ca",
 *     "source_row_counts": {"users": 10, ...},
 *     "entries": [ ... changelog entries ... ],
 *     "dry_run": false
 *   }
 *
 * Response: JSON with applied/skipped/conflict counts.
 */

header('Content-Type: application/json');

$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!is_array($input)) {
    $input = array();
}

// ── Auth ─────────────────────────────────────────────────────────────────────
$provided_token  = isset($input['token']) ? $input['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $provided_token === '' || $provided_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// ── Params ───────────────────────────────────────────────────────────────────
$db_host     = 'localhost';
$db_user     = 'DB_USER_PLACEHOLDER';
$db_pass     = 'DB_PASS_PLACEHOLDER';
$dbname      = isset($input['db'])          ? $input['db']          : '';
$source_site = isset($input['source_site']) ? $input['source_site'] : '';
$entries     = isset($input['entries'])     ? $input['entries']     : array();
$dry_run     = isset($input['dry_run'])     ? (bool) $input['dry_run'] : false;
$source_row_counts = isset($input['source_row_counts']) ? $input['source_row_counts'] : array();

if ($dbname === '' || $source_site === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Missing db or source_site'));
    exit;
}

require_once dirname(__FILE__) . '/sync_config.php';
require_once dirname(__FILE__) . '/sync_helpers.php';

$_allowed_dbs = array_keys(sync_get_user_tables());
if (!in_array($dbname, $_allowed_dbs)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Database not in allowed list: ' . implode(', ', $_allowed_dbs)));
    exit;
}

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

// ── Safeguard: Check row counts before applying ─────────────────────────────
$safeguard_warnings = array();
$skipped_tables = array();

$user_tables_map = sync_get_user_tables();
$tables_for_db = isset($user_tables_map[$dbname]) ? $user_tables_map[$dbname] : array();

foreach ($tables_for_db as $tbl) {
    $esc_tbl = $conn->real_escape_string($tbl);
    $tbl_exists = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
    if (!$tbl_exists || $tbl_exists->num_rows === 0) continue;

    $cnt = $conn->query("SELECT COUNT(*) AS c FROM `" . $esc_tbl . "`");
    if (!$cnt) continue;
    $cnt_row = $cnt->fetch_assoc();
    $local_count = $cnt_row ? (int) $cnt_row['c'] : 0;

    $source_count = isset($source_row_counts[$tbl]) ? (int) $source_row_counts[$tbl] : -1;

    // Safeguard: source has 0 rows but local has real data
    if ($source_count === 0 && $local_count > 0) {
        $safeguard_warnings[] = $tbl . ': source has 0 rows but local has ' . $local_count . ' -- SKIPPING';
        $skipped_tables[$tbl] = true;
    }

    // Delta alert: would lose >10% of rows
    $threshold = sync_get_delta_alert_threshold();
    if ($source_count >= 0 && $local_count > 10) {
        $delta = $local_count - $source_count;
        if ($delta > 0 && ($delta / $local_count) > $threshold) {
            $safeguard_warnings[] = $tbl . ': source has ' . $source_count . ' vs local ' . $local_count
                                  . ' (would lose ' . round(($delta / $local_count) * 100, 1) . '%) -- WARNING';
        }
    }
}

// ── Build user email-to-id mapping for this site ─────────────────────────────
$email_to_id = array();
$id_to_email = array();

$users_exist = $conn->query("SHOW TABLES LIKE 'users'");
if ($users_exist && $users_exist->num_rows > 0) {
    $user_rows = $conn->query("SELECT id, email FROM users");
    if ($user_rows) {
        while ($u = $user_rows->fetch_assoc()) {
            $email_to_id[$u['email']] = (int) $u['id'];
            $id_to_email[(int) $u['id']] = $u['email'];
        }
    }
}

// ── Process entries ──────────────────────────────────────────────────────────
$stats = array(
    'applied'   => 0,
    'skipped'   => 0,
    'conflicts' => 0,
    'errors'    => 0,
    'new_users_created' => 0,
);
$applied_ids = array(); // changelog entry IDs that were successfully applied
$conflict_details = array();
$error_details = array();

$strategies = sync_get_merge_strategies();
$aggregate_rules = sync_get_aggregate_rules();
$pk_defs = sync_get_primary_keys();
$this_site = sync_detect_site();

foreach ($entries as $entry) {
    $tbl       = isset($entry['table_name'])   ? $entry['table_name']   : '';
    $op        = isset($entry['operation'])     ? $entry['operation']     : '';
    $row_key   = isset($entry['row_key'])       ? $entry['row_key']       : '';
    $row_data  = isset($entry['row_data'])      ? $entry['row_data']      : null;
    $email     = isset($entry['user_email'])    ? $entry['user_email']    : '';
    $origin    = isset($entry['origin_site'])   ? $entry['origin_site']   : $source_site;
    $version   = isset($entry['sync_version'])  ? (int) $entry['sync_version'] : 1;
    $changed   = isset($entry['changed_at'])    ? $entry['changed_at']    : '';
    $entry_id  = isset($entry['id'])            ? (int) $entry['id']      : 0;

    // Skip if table is in the skipped set (safeguard)
    if (isset($skipped_tables[$tbl])) {
        $stats['skipped']++;
        continue;
    }

    // Decode row_data if it's a JSON string
    $row_array = null;
    if ($row_data !== null && is_string($row_data)) {
        $row_array = json_decode($row_data, true);
    } elseif (is_array($row_data)) {
        $row_array = $row_data;
    }

    // Parse the remote PK values
    $remote_pk = sync_deserialize_pk($row_key);

    // ── User ID resolution ───────────────────────────────────────────────
    // If the row references a user_id and we have an email, map to local ID
    $local_user_id = null;
    if ($email !== '' && isset($remote_pk['user_id'])) {
        if (isset($email_to_id[$email])) {
            $local_user_id = $email_to_id[$email];
        } else {
            // User doesn't exist locally -- create them if this is a user table insert
            if ($tbl === 'users' && $op === 'INSERT' && is_array($row_array)) {
                if (!$dry_run) {
                    $local_user_id = _apply_create_user($conn, $row_array, $origin, $email);
                    if ($local_user_id !== null) {
                        $email_to_id[$email] = $local_user_id;
                        $id_to_email[$local_user_id] = $email;
                        $stats['new_users_created']++;
                    }
                } else {
                    $stats['new_users_created']++;
                    $stats['applied']++;
                    $applied_ids[] = $entry_id;
                    continue;
                }
            } elseif ($tbl !== 'users') {
                // Non-user table but user doesn't exist locally -- skip
                $stats['skipped']++;
                continue;
            }
        }
    }

    // Rewrite user_id in PK and row_data for local context
    if ($local_user_id !== null && isset($remote_pk['user_id'])) {
        $remote_pk['user_id'] = $local_user_id;
        if (is_array($row_array) && isset($row_array['user_id'])) {
            $row_array['user_id'] = $local_user_id;
        }
    }

    // ── Strategy-based apply ─────────────────────────────────────────────
    $strategy = isset($strategies[$tbl]) ? $strategies[$tbl] : 'LWW';

    if ($dry_run) {
        $stats['applied']++;
        $applied_ids[] = $entry_id;
        continue;
    }

    $apply_result = _apply_entry($conn, $tbl, $op, $remote_pk, $row_array, $version, $changed, $strategy, $aggregate_rules, $origin, $email, $this_site, $source_site);

    if ($apply_result === 'applied') {
        $stats['applied']++;
        $applied_ids[] = $entry_id;
    } elseif ($apply_result === 'skipped') {
        $stats['skipped']++;
    } elseif (strpos($apply_result, 'conflict:') === 0) {
        $stats['conflicts']++;
        $conflict_details[] = $tbl . '/' . $row_key . ': ' . $apply_result;
    } else {
        $stats['errors']++;
        $error_details[] = $tbl . '/' . $row_key . ': ' . $apply_result;
    }
}

$conn->close();

echo json_encode(array(
    'status'             => ($stats['errors'] === 0) ? 'ok' : 'partial',
    'dry_run'            => $dry_run,
    'this_site'          => $this_site,
    'source_site'        => $source_site,
    'database'           => $dbname,
    'stats'              => $stats,
    'applied_ids'        => $applied_ids,
    'safeguard_warnings' => $safeguard_warnings,
    'conflict_details'   => $conflict_details,
    'error_details'      => $error_details,
    'timestamp'          => gmdate('Y-m-d\TH:i:s\Z'),
));

// ═══════════════════════════════════════════════════════════════════════════════
// Internal functions
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Create a new user on this site from synced data.
 */
function _apply_create_user($conn, $row_array, $origin, $email) {
    $esc_email = $conn->real_escape_string($email);
    $esc_pw    = isset($row_array['password'])     ? $conn->real_escape_string($row_array['password'])     : '';
    $esc_role  = isset($row_array['role'])          ? $conn->real_escape_string($row_array['role'])          : 'user';
    $esc_name  = isset($row_array['display_name'])  ? $conn->real_escape_string($row_array['display_name'])  : '';
    $esc_orig  = $conn->real_escape_string($origin);

    $sql = "INSERT INTO users (email, password, role, display_name, origin_site, sync_version) "
         . "VALUES ('" . $esc_email . "', '" . $esc_pw . "', '" . $esc_role . "', "
         . "'" . $esc_name . "', '" . $esc_orig . "', 1) "
         . "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)";

    if ($conn->query($sql)) {
        return (int) $conn->insert_id;
    }
    return null;
}

/**
 * Apply a single changelog entry using the appropriate merge strategy.
 *
 * @return string 'applied', 'skipped', 'conflict:...', or 'error:...'
 */
function _apply_entry($conn, $tbl, $op, $pk, $row_data, $version, $changed, $strategy, $aggregate_rules, $origin, $email, $this_site, $source_site) {
    $esc_tbl = $conn->real_escape_string($tbl);

    // Check if target table exists
    $tbl_check = $conn->query("SHOW TABLES LIKE '" . $esc_tbl . "'");
    if (!$tbl_check || $tbl_check->num_rows === 0) {
        return 'skipped'; // table doesn't exist on this site
    }

    // Build WHERE clause from PK
    $where_parts = array();
    foreach ($pk as $col => $val) {
        $esc_col = $conn->real_escape_string($col);
        $esc_val = $conn->real_escape_string($val);
        $where_parts[] = "`" . $esc_col . "` = '" . $esc_val . "'";
    }
    $where = implode(' AND ', $where_parts);

    // Fetch existing local row
    $local_row = null;
    $local_sql = "SELECT * FROM `" . $esc_tbl . "` WHERE " . $where . " LIMIT 1";
    $local_result = @$conn->query($local_sql);
    if ($local_result && $local_result->num_rows > 0) {
        $local_row = $local_result->fetch_assoc();
    }

    $local_version = 0;
    if ($local_row !== null && isset($local_row['sync_version'])) {
        $local_version = (int) $local_row['sync_version'];
    }

    // ── DELETE ────────────────────────────────────────────────────────────
    if ($op === 'DELETE') {
        if ($local_row === null) {
            return 'skipped'; // already gone
        }
        // DELETE wins if remote version >= local version
        if ($version >= $local_version) {
            $del = $conn->query("DELETE FROM `" . $esc_tbl . "` WHERE " . $where . " LIMIT 1");
            if ($del) {
                // Log the applied change with original origin
                log_sync_change_safe($conn, $tbl, 'DELETE', $pk, $local_row, $email, $origin);
                return 'applied';
            }
            return 'error: DELETE failed: ' . $conn->error;
        }
        return 'skipped'; // local is newer
    }

    // ── INSERT (row doesn't exist locally) ───────────────────────────────
    if ($local_row === null && ($op === 'INSERT' || $op === 'UPDATE')) {
        if (!is_array($row_data)) {
            return 'error: no row_data for INSERT';
        }

        // For users table, special handling (already done in caller)
        if ($tbl === 'users') {
            return 'skipped'; // user creation handled separately
        }

        // Build INSERT
        $cols = array();
        $vals = array();
        foreach ($row_data as $col => $val) {
            if ($col === 'id' && $tbl !== 'users') {
                // Skip auto-increment ID columns (except users which maps by email)
                $pk_defs = sync_get_primary_keys();
                $pk_cols = isset($pk_defs[$tbl]) ? $pk_defs[$tbl] : array();
                if (count($pk_cols) === 1 && $pk_cols[0] === 'id') {
                    continue; // let auto-increment generate it
                }
            }
            $cols[] = '`' . $conn->real_escape_string($col) . '`';
            if ($val === null) {
                $vals[] = 'NULL';
            } else {
                $vals[] = "'" . $conn->real_escape_string($val) . "'";
            }
        }

        // Ensure sync_version is set
        if (!isset($row_data['sync_version'])) {
            $cols[] = '`sync_version`';
            $vals[] = (string) $version;
        }

        $sql = "INSERT IGNORE INTO `" . $esc_tbl . "` (" . implode(', ', $cols) . ") "
             . "VALUES (" . implode(', ', $vals) . ")";
        if ($conn->query($sql)) {
            log_sync_change_safe($conn, $tbl, 'INSERT', $pk, $row_data, $email, $origin);
            return 'applied';
        }
        return 'error: INSERT failed: ' . $conn->error;
    }

    // ── UPDATE (row exists locally) ──────────────────────────────────────
    if ($local_row !== null && ($op === 'INSERT' || $op === 'UPDATE')) {
        if (!is_array($row_data)) {
            return 'error: no row_data for UPDATE';
        }

        // Apply strategy
        if ($strategy === 'JSON_UNION') {
            return _apply_json_union($conn, $tbl, $where, $local_row, $row_data, $version, $local_version, $pk, $email, $origin);
        }

        if ($strategy === 'AGGREGATE') {
            $rules = isset($aggregate_rules[$tbl]) ? $aggregate_rules[$tbl] : array();
            return _apply_aggregate($conn, $tbl, $where, $local_row, $row_data, $rules, $pk, $email, $origin);
        }

        if ($strategy === 'UNION' || $strategy === 'UNION_DEL') {
            // For UNION, the row already exists -- treat as LWW for updates
            // (UNION is mainly about keeping rows from both sites, handled by INSERT above)
        }

        // LWW (and fallback for UNION/UNION_DEL updates)
        if ($version > $local_version) {
            return _apply_lww_update($conn, $tbl, $where, $row_data, $version, $pk, $email, $origin);
        } elseif ($version === $local_version) {
            // Same version -- use timestamp as tiebreaker
            $local_updated = isset($local_row['updated_at']) ? $local_row['updated_at'] : '';
            if ($changed > $local_updated) {
                return _apply_lww_update($conn, $tbl, $where, $row_data, $version, $pk, $email, $origin);
            }
        }

        return 'skipped'; // local is newer or same
    }

    return 'skipped';
}

/**
 * LWW update: overwrite local row with remote data.
 */
function _apply_lww_update($conn, $tbl, $where, $row_data, $version, $pk, $email, $origin) {
    $esc_tbl = $conn->real_escape_string($tbl);
    $set_parts = array();

    $pk_defs = sync_get_primary_keys();
    $pk_cols = isset($pk_defs[$tbl]) ? $pk_defs[$tbl] : array();
    $pk_set = array();
    foreach ($pk_cols as $c) {
        $pk_set[$c] = true;
    }

    foreach ($row_data as $col => $val) {
        // Skip PK columns and auto-increment IDs
        if (isset($pk_set[$col])) continue;
        if ($col === 'id') continue;
        if ($col === 'created_at') continue; // preserve creation time

        $esc_col = $conn->real_escape_string($col);
        if ($val === null) {
            $set_parts[] = "`" . $esc_col . "` = NULL";
        } else {
            $set_parts[] = "`" . $esc_col . "` = '" . $conn->real_escape_string($val) . "'";
        }
    }

    // Set sync_version to remote version
    $set_parts[] = "`sync_version` = " . (int) $version;

    if (count($set_parts) === 0) {
        return 'skipped';
    }

    $sql = "UPDATE `" . $esc_tbl . "` SET " . implode(', ', $set_parts) . " WHERE " . $where . " LIMIT 1";
    if ($conn->query($sql)) {
        log_sync_change_safe($conn, $tbl, 'UPDATE', $pk, $row_data, $email, $origin);
        return 'applied';
    }
    return 'error: UPDATE failed: ' . $conn->error;
}

/**
 * JSON_UNION merge for user_lists.creators: union creator arrays by ID.
 */
function _apply_json_union($conn, $tbl, $where, $local_row, $remote_data, $remote_ver, $local_ver, $pk, $email, $origin) {
    $esc_tbl = $conn->real_escape_string($tbl);

    // Merge the JSON field (creators for user_lists)
    $local_json  = isset($local_row['creators'])  ? $local_row['creators']  : '[]';
    $remote_json = isset($remote_data['creators']) ? $remote_data['creators'] : '[]';

    $merged = sync_json_merge_creators($local_json, $remote_json);
    $esc_merged = $conn->real_escape_string($merged);
    $new_version = ($remote_ver > $local_ver) ? $remote_ver : $local_ver;
    $new_version = $new_version + 1;

    $sql = "UPDATE `" . $esc_tbl . "` SET creators = '" . $esc_merged . "', "
         . "sync_version = " . $new_version . " "
         . "WHERE " . $where . " LIMIT 1";

    if ($conn->query($sql)) {
        $merged_row = $local_row;
        $merged_row['creators'] = $merged;
        $merged_row['sync_version'] = $new_version;
        log_sync_change_safe($conn, $tbl, 'UPDATE', $pk, $merged_row, $email, $origin);
        return 'applied';
    }
    return 'error: JSON_UNION UPDATE failed: ' . $conn->error;
}

/**
 * AGGREGATE merge for user_visit_days: MAX/MIN per field.
 */
function _apply_aggregate($conn, $tbl, $where, $local_row, $remote_data, $rules, $pk, $email, $origin) {
    $esc_tbl = $conn->real_escape_string($tbl);
    $merged = sync_aggregate_merge($local_row, $remote_data, $rules);

    $set_parts = array();
    foreach ($rules as $field => $func) {
        $val = isset($merged[$field]) ? $merged[$field] : null;
        $esc_field = $conn->real_escape_string($field);
        if ($val === null) {
            $set_parts[] = "`" . $esc_field . "` = NULL";
        } else {
            $set_parts[] = "`" . $esc_field . "` = '" . $conn->real_escape_string($val) . "'";
        }
    }

    $new_ver = max(
        (isset($local_row['sync_version']) ? (int)$local_row['sync_version'] : 0),
        (isset($remote_data['sync_version']) ? (int)$remote_data['sync_version'] : 0)
    ) + 1;
    $set_parts[] = "`sync_version` = " . $new_ver;

    if (count($set_parts) === 0) return 'skipped';

    $sql = "UPDATE `" . $esc_tbl . "` SET " . implode(', ', $set_parts) . " WHERE " . $where . " LIMIT 1";
    if ($conn->query($sql)) {
        $merged['sync_version'] = $new_ver;
        log_sync_change_safe($conn, $tbl, 'UPDATE', $pk, $merged, $email, $origin);
        return 'applied';
    }
    return 'error: AGGREGATE UPDATE failed: ' . $conn->error;
}
