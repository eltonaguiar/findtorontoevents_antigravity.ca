<?php
/**
 * sync_helpers.php -- Core helper functions for bi-directional sync.
 * PHP 5.2-safe. No closures, no short array syntax, no ?:, no ??.
 *
 * Include this in any PHP endpoint that writes to user-related tables.
 * After a successful INSERT/UPDATE/DELETE, call log_sync_change().
 *
 * Usage:
 *   require_once dirname(__FILE__) . '/sync_helpers.php';
 *   // ... after successful DB write ...
 *   log_sync_change($conn, 'user_notes', 'UPDATE',
 *       array('user_id' => 5, 'creator_id' => 'abc'),
 *       $row_data_array,
 *       'user@example.com'
 *   );
 */

if (!function_exists('_sync_helpers_loaded')) {
    function _sync_helpers_loaded() { return true; }
}

require_once dirname(__FILE__) . '/sync_config.php';

// ── log_sync_change ──────────────────────────────────────────────────────────
/**
 * Record a user-data mutation in the sync_changelog table.
 *
 * @param object $conn       mysqli connection
 * @param string $table      Table name (e.g. 'user_notes')
 * @param string $operation  'INSERT', 'UPDATE', or 'DELETE'
 * @param array  $pk_values  Associative array of primary key columns => values
 * @param mixed  $row_data   Full row as associative array (or NULL). For DELETE,
 *                           pass the row snapshot BEFORE deletion (tombstone).
 * @param string $user_email The user's email for identity resolution (can be ''
 *                           for non-user-keyed tables like accountability logs).
 * @param string $origin     Override origin_site (default: auto-detect from HTTP_HOST).
 *                           Set this when applying synced changes to preserve original origin.
 * @return bool  True on success, false on failure.
 */
function log_sync_change($conn, $table, $operation, $pk_values, $row_data, $user_email, $origin) {
    if (!isset($origin) || $origin === '' || $origin === null) {
        $origin = sync_detect_site();
    }

    // Serialize primary key
    $key_parts = array();
    if (is_array($pk_values)) {
        foreach ($pk_values as $col => $val) {
            $key_parts[] = urlencode($col) . '=' . urlencode($val);
        }
    }
    $row_key = implode('&', $key_parts);

    // JSON-encode row data (NULL for tombstone-less deletes, but we prefer tombstones)
    $row_data_json = 'NULL';
    if ($row_data !== null && $row_data !== false) {
        $encoded = json_encode($row_data);
        if ($encoded !== false) {
            $row_data_json = "'" . $conn->real_escape_string($encoded) . "'";
        }
    }

    // Determine sync_version from the row data if available
    $sync_version = 1;
    if (is_array($row_data) && isset($row_data['sync_version'])) {
        $sync_version = (int) $row_data['sync_version'];
    }

    $esc_table   = $conn->real_escape_string($table);
    $esc_op      = $conn->real_escape_string($operation);
    $esc_key     = $conn->real_escape_string($row_key);
    $esc_email   = $conn->real_escape_string($user_email);
    $esc_origin  = $conn->real_escape_string($origin);
    $now         = gmdate('Y-m-d H:i:s');

    $sql = "INSERT INTO sync_changelog "
         . "(table_name, operation, row_key, row_data, user_email, origin_site, sync_version, changed_at) "
         . "VALUES ("
         . "'" . $esc_table . "', "
         . "'" . $esc_op . "', "
         . "'" . $esc_key . "', "
         . $row_data_json . ", "
         . "'" . $esc_email . "', "
         . "'" . $esc_origin . "', "
         . $sync_version . ", "
         . "'" . $now . "'"
         . ")";

    $result = @$conn->query($sql);
    if (!$result) {
        // If sync_changelog table doesn't exist yet, fail silently
        // (don't break the main application flow)
        return false;
    }
    return true;
}

// ── log_sync_change_safe ─────────────────────────────────────────────────────
/**
 * Wrapper that catches all errors. Use this in endpoints where sync logging
 * must never break the primary operation.
 */
function log_sync_change_safe($conn, $table, $operation, $pk_values, $row_data, $user_email, $origin) {
    if (!isset($origin)) {
        $origin = '';
    }
    if (!isset($user_email)) {
        $user_email = '';
    }
    try {
        return log_sync_change($conn, $table, $operation, $pk_values, $row_data, $user_email, $origin);
    } catch (Exception $e) {
        return false;
    }
}

// ── fetch_row_for_tombstone ──────────────────────────────────────────────────
/**
 * Fetch a row's current data before deleting it, so we can store a tombstone.
 *
 * @param object $conn       mysqli connection
 * @param string $table      Table name
 * @param array  $pk_values  Associative array of PK columns => values
 * @return array|null        The row data, or null if not found.
 */
function fetch_row_for_tombstone($conn, $table, $pk_values) {
    $esc_table = $conn->real_escape_string($table);
    $where_parts = array();
    foreach ($pk_values as $col => $val) {
        $esc_col = $conn->real_escape_string($col);
        $esc_val = $conn->real_escape_string($val);
        $where_parts[] = "`" . $esc_col . "` = '" . $esc_val . "'";
    }
    $where = implode(' AND ', $where_parts);
    $sql = "SELECT * FROM `" . $esc_table . "` WHERE " . $where . " LIMIT 1";

    $result = @$conn->query($sql);
    if (!$result || $result->num_rows === 0) {
        return null;
    }
    return $result->fetch_assoc();
}

// ── increment_sync_version ───────────────────────────────────────────────────
/**
 * Increment the sync_version column on a row. Call this BEFORE reading the row
 * for changelog logging, so the logged version is the new one.
 *
 * @param object $conn       mysqli connection
 * @param string $table      Table name
 * @param array  $pk_values  PK columns => values
 * @return int               The new sync_version, or 0 on failure.
 */
function increment_sync_version($conn, $table, $pk_values) {
    $esc_table = $conn->real_escape_string($table);
    $where_parts = array();
    foreach ($pk_values as $col => $val) {
        $esc_col = $conn->real_escape_string($col);
        $esc_val = $conn->real_escape_string($val);
        $where_parts[] = "`" . $esc_col . "` = '" . $esc_val . "'";
    }
    $where = implode(' AND ', $where_parts);

    // Try to increment; if column doesn't exist yet, fail silently
    $sql = "UPDATE `" . $esc_table . "` SET sync_version = sync_version + 1 WHERE " . $where;
    $ok = @$conn->query($sql);
    if (!$ok) {
        return 0;
    }

    // Read back the new version
    $sql2 = "SELECT sync_version FROM `" . $esc_table . "` WHERE " . $where . " LIMIT 1";
    $r = @$conn->query($sql2);
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return (int) $row['sync_version'];
    }
    return 0;
}

// ── serialize_pk ─────────────────────────────────────────────────────────────
/**
 * Build a URL-encoded primary key string from a row and the table's PK definition.
 *
 * @param array $row       The full row data
 * @param array $pk_cols   Array of PK column names
 * @return string          URL-encoded key string
 */
function sync_serialize_pk($row, $pk_cols) {
    $parts = array();
    foreach ($pk_cols as $col) {
        $val = isset($row[$col]) ? $row[$col] : '';
        $parts[] = urlencode($col) . '=' . urlencode($val);
    }
    return implode('&', $parts);
}

// ── deserialize_pk ───────────────────────────────────────────────────────────
/**
 * Parse a URL-encoded primary key string back into an associative array.
 *
 * @param string $row_key  The serialized key
 * @return array           Associative array of column => value
 */
function sync_deserialize_pk($row_key) {
    $result = array();
    $pairs = explode('&', $row_key);
    foreach ($pairs as $pair) {
        $kv = explode('=', $pair, 2);
        if (count($kv) === 2) {
            $result[urldecode($kv[0])] = urldecode($kv[1]);
        }
    }
    return $result;
}

// ── get_user_email_for_row ───────────────────────────────────────────────────
/**
 * Look up the user's email given a user_id. Used to denormalize email into
 * changelog entries.
 *
 * @param object $conn     mysqli connection
 * @param int    $user_id  The user ID
 * @return string          The email, or '' if not found.
 */
function sync_get_user_email($conn, $user_id) {
    $uid = (int) $user_id;
    $sql = "SELECT email FROM users WHERE id = " . $uid . " LIMIT 1";
    $r = @$conn->query($sql);
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return isset($row['email']) ? $row['email'] : '';
    }
    return '';
}

// ── json_merge_creator_lists ─────────────────────────────────────────────────
/**
 * Merge two JSON arrays of creator objects by their 'id' field.
 * Used for the JSON_UNION strategy on user_lists.creators.
 *
 * @param string $json_a  JSON array string from Site A
 * @param string $json_b  JSON array string from Site B
 * @return string          Merged JSON array
 */
function sync_json_merge_creators($json_a, $json_b) {
    $list_a = json_decode($json_a, true);
    $list_b = json_decode($json_b, true);
    if (!is_array($list_a)) $list_a = array();
    if (!is_array($list_b)) $list_b = array();

    $merged = array();
    $seen_ids = array();

    // Add all from A
    foreach ($list_a as $item) {
        $id = isset($item['id']) ? $item['id'] : null;
        if ($id !== null) {
            $merged[] = $item;
            $seen_ids[$id] = true;
        }
    }

    // Add from B only if not already in A
    foreach ($list_b as $item) {
        $id = isset($item['id']) ? $item['id'] : null;
        if ($id !== null && !isset($seen_ids[$id])) {
            $merged[] = $item;
            $seen_ids[$id] = true;
        }
    }

    return json_encode($merged);
}

// ── aggregate_merge ──────────────────────────────────────────────────────────
/**
 * Merge two rows using aggregate functions (MAX, MIN) per field.
 *
 * @param array $local_row   Row from destination
 * @param array $remote_row  Row from source changelog
 * @param array $rules       field_name => 'MAX'|'MIN'
 * @return array             Merged row
 */
function sync_aggregate_merge($local_row, $remote_row, $rules) {
    $merged = $local_row;
    foreach ($rules as $field => $func) {
        $local_val  = isset($local_row[$field])  ? $local_row[$field]  : null;
        $remote_val = isset($remote_row[$field]) ? $remote_row[$field] : null;

        if ($local_val === null) {
            $merged[$field] = $remote_val;
        } elseif ($remote_val === null) {
            $merged[$field] = $local_val;
        } elseif ($func === 'MAX') {
            $merged[$field] = ($remote_val > $local_val) ? $remote_val : $local_val;
        } elseif ($func === 'MIN') {
            $merged[$field] = ($remote_val < $local_val) ? $remote_val : $local_val;
        }
    }
    return $merged;
}
