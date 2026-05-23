<?php
/**
 * sync_log.php -- Lightweight sync logging include for favcreators API endpoints.
 * PHP 5.2-safe.
 *
 * Include this in any endpoint that writes to user-related tables, then call:
 *   sync_log_write($conn, 'user_notes', 'UPDATE', array('user_id'=>5, 'creator_id'=>'abc'), $row, 'user@email.com');
 *   sync_log_write($conn, 'user_notes', 'DELETE', array('user_id'=>5, 'creator_id'=>'abc'), $tombstone, 'user@email.com');
 *
 * If the sync_changelog table doesn't exist, all calls are silent no-ops.
 */

if (!function_exists('sync_log_write')) {

    function _sync_log_detect_site() {
        $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';
        if (strpos($host, 'torontoevent.net') !== false) {
            return 'torontoevent.net';
        }
        return 'findtorontoevents.ca';
    }

    /**
     * @param object $conn       mysqli connection
     * @param string $table      Table name
     * @param string $operation  'INSERT', 'UPDATE', or 'DELETE'
     * @param array  $pk_values  Assoc array of PK columns => values
     * @param mixed  $row_data   Full row as array (for DELETE: snapshot before deletion)
     * @param string $user_email User email for identity resolution
     * @param string $origin     Origin site override (default: auto-detect)
     */
    function sync_log_write($conn, $table, $operation, $pk_values, $row_data, $user_email, $origin) {
        if (!isset($origin) || $origin === null || $origin === '') {
            $origin = _sync_log_detect_site();
        }
        if (!isset($user_email)) {
            $user_email = '';
        }

        // Serialize PK
        $key_parts = array();
        if (is_array($pk_values)) {
            foreach ($pk_values as $col => $val) {
                $key_parts[] = urlencode($col) . '=' . urlencode($val);
            }
        }
        $row_key = implode('&', $key_parts);

        // JSON-encode row data
        $row_data_sql = 'NULL';
        if ($row_data !== null && $row_data !== false) {
            $encoded = json_encode($row_data);
            if ($encoded !== false) {
                $row_data_sql = "'" . $conn->real_escape_string($encoded) . "'";
            }
        }

        // Get sync_version from row data
        $sv = 1;
        if (is_array($row_data) && isset($row_data['sync_version'])) {
            $sv = (int) $row_data['sync_version'];
        }

        $now = gmdate('Y-m-d H:i:s');

        $sql = "INSERT INTO sync_changelog "
             . "(table_name, operation, row_key, row_data, user_email, origin_site, sync_version, changed_at) "
             . "VALUES ("
             . "'" . $conn->real_escape_string($table) . "', "
             . "'" . $conn->real_escape_string($operation) . "', "
             . "'" . $conn->real_escape_string($row_key) . "', "
             . $row_data_sql . ", "
             . "'" . $conn->real_escape_string($user_email) . "', "
             . "'" . $conn->real_escape_string($origin) . "', "
             . $sv . ", "
             . "'" . $now . "'"
             . ")";

        @$conn->query($sql);
    }

    /**
     * Look up a user's email by user_id.
     */
    function sync_get_user_email_local($conn, $user_id) {
        $uid = (int) $user_id;
        if ($uid <= 0) return '';
        $r = @$conn->query("SELECT email FROM users WHERE id = " . $uid . " LIMIT 1");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            return isset($row['email']) ? $row['email'] : '';
        }
        return '';
    }

    /**
     * Fetch a row before deletion to store as tombstone.
     */
    function sync_log_fetch_before_delete($conn, $table, $pk_values) {
        $where_parts = array();
        foreach ($pk_values as $col => $val) {
            $where_parts[] = "`" . $conn->real_escape_string($col) . "` = '" . $conn->real_escape_string($val) . "'";
        }
        $where = implode(' AND ', $where_parts);
        $sql = "SELECT * FROM `" . $conn->real_escape_string($table) . "` WHERE " . $where . " LIMIT 1";
        $r = @$conn->query($sql);
        if ($r && $r->num_rows > 0) {
            return $r->fetch_assoc();
        }
        return null;
    }
}
