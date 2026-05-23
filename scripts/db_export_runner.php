<?php
/**
 * db_export_runner.php
 * Server-side DB export helper — deployed temporarily by GitHub Actions.
 * PHP 5.2 compatible (runs on 50webs shared hosting).
 *
 * Placeholders replaced at deploy time by the workflow:
 *   Token placeholder → actual secret token (replaced at deploy time)
 *   array(); // EXPORT_DB_CRED_MAP  → array('db' => array('user','pass'), ...)
 *
 * Usage: GET /_db_export_tmp.php?token=SECRET&db=ALL
 *        GET /_db_export_tmp.php?token=SECRET&db=ejaguiar1_events
 *        GET /_db_export_tmp.php?token=SECRET&db=__ping__
 */

// -- Authentication --
$expected_token = 'EXPORT_TOKEN_PLACEHOLDER';
$provided_token = isset($_GET['token']) ? $_GET['token'] : '';

if ($expected_token === '' || substr($expected_token, 0, 7) === 'EXPORT_' || !_safe_str_equals($expected_token, $provided_token)) {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// -- Extend execution time --
@set_time_limit(300);
@ini_set('max_execution_time', '300');

// -- Config --
$db_host = 'localhost';

// Per-database credentials — injected by workflow at deploy time
$db_credentials_map = array(); // EXPORT_DB_CRED_MAP

// Fallback credentials
$db_user_default = 'ejaguiar1';
$db_pass_default = '';

$all_databases = array(
    'ejaguiar1_deals',
    'ejaguiar1_events',
    'ejaguiar1_favcreators',
    'ejaguiar1_memecoin',
    'ejaguiar1_news',
    'ejaguiar1_sportsbet',
    'ejaguiar1_stocks',
    'ejaguiar1_tvmoviestrailers'
);

$requested_db = isset($_GET['db']) ? $_GET['db'] : 'ALL';

// Health-check
if ($requested_db === '__ping__') {
    header('Content-Type: application/json');
    echo json_encode(array('status' => 'ok', 'ping' => true, 'timestamp' => date('c')));
    exit;
}

if ($requested_db === 'ALL') {
    $databases_to_export = $all_databases;
} else {
    $databases_to_export = array($requested_db);
}

// -- Detect disabled functions once --
$_disabled_raw = explode(',', ini_get('disable_functions'));
$_disabled_fns = array();
foreach ($_disabled_raw as $_dfn) {
    $_disabled_fns[] = trim($_dfn);
}
$_exec_available = function_exists('exec') && !in_array('exec', $_disabled_fns);

// -- Export --
$results = array();
$errors  = array();

foreach ($databases_to_export as $dbname) {
    @set_time_limit(120);

    if (!preg_match('/^[a-zA-Z0-9_]+$/', $dbname)) {
        $errors[] = 'Invalid database name: ' . $dbname;
        continue;
    }

    // Resolve per-DB credentials
    $cred = isset($db_credentials_map[$dbname])
        ? $db_credentials_map[$dbname]
        : array($db_user_default, $db_pass_default);
    $db_user = $cred[0];
    $db_pass = $cred[1];

    // Try mysqldump first (fastest, most complete)
    $dump_sql = '';
    if ($_exec_available) {
        $escaped_pass = escapeshellarg($db_pass);
        $escaped_user = escapeshellarg($db_user);
        $escaped_db   = escapeshellarg($dbname);
        $escaped_host = escapeshellarg($db_host);
        $cmd = 'mysqldump -h ' . $escaped_host
             . ' -u ' . $escaped_user
             . ' -p' . $escaped_pass
             . ' --single-transaction --routines --triggers'
             . ' --add-drop-table --skip-comments'
             . ' --default-character-set=utf8mb4'
             . ' ' . $escaped_db . ' 2>/dev/null';
        $lines = array();
        $exit_code = 0;
        exec($cmd, $lines, $exit_code);
        $raw_dump = implode("\n", $lines);
        if (strlen($raw_dump) > 50) {
            $dump_sql = $raw_dump;
        }
    }

    // Fallback: mysql_* row-by-row export
    if ($dump_sql === '') {
        $link = @mysql_connect($db_host, $db_user, $db_pass);
        if (!$link) {
            $errors[] = 'Connect failed for ' . $dbname . ': ' . mysql_error();
            continue;
        }
        if (!@mysql_select_db($dbname, $link)) {
            $errors[] = 'Select DB failed for ' . $dbname . ': ' . mysql_error($link);
            mysql_close($link);
            continue;
        }

        $dump_sql = '-- mysql_* export of `' . $dbname . "`\n";
        $dump_sql .= '-- Generated: ' . date('Y-m-d H:i:s') . "\n\n";
        $dump_sql .= "SET FOREIGN_KEY_CHECKS=0;\n\n";

        $tables_result = mysql_query('SHOW TABLES', $link);
        if ($tables_result) {
            while ($trow = mysql_fetch_row($tables_result)) {
                $table = $trow[0];

                // CREATE TABLE
                $create_result = mysql_query('SHOW CREATE TABLE `' . mysql_real_escape_string($table, $link) . '`', $link);
                if ($create_result) {
                    $create_row = mysql_fetch_row($create_result);
                    $dump_sql .= 'DROP TABLE IF EXISTS `' . $table . "`;\n";
                    $dump_sql .= $create_row[1] . ";\n\n";
                    mysql_free_result($create_result);
                }

                // Data
                $data_result = mysql_query('SELECT * FROM `' . mysql_real_escape_string($table, $link) . '`', $link);
                if ($data_result && mysql_num_rows($data_result) > 0) {
                    $num_fields = mysql_num_fields($data_result);
                    $cols = array();
                    for ($i = 0; $i < $num_fields; $i++) {
                        $cols[] = '`' . mysql_field_name($data_result, $i) . '`';
                    }
                    $col_str = implode(', ', $cols);

                    $batch = array();
                    $batch_count = 0;
                    while ($data_row = mysql_fetch_row($data_result)) {
                        $vals = array();
                        foreach ($data_row as $val) {
                            if ($val === null) {
                                $vals[] = 'NULL';
                            } else {
                                $vals[] = "'" . mysql_real_escape_string($val, $link) . "'";
                            }
                        }
                        $batch[] = '(' . implode(', ', $vals) . ')';
                        $batch_count++;

                        if ($batch_count >= 500) {
                            $dump_sql .= 'INSERT INTO `' . $table . '` (' . $col_str . ") VALUES\n";
                            $dump_sql .= implode(",\n", $batch) . ";\n";
                            $batch = array();
                            $batch_count = 0;
                        }
                    }
                    if ($batch_count > 0) {
                        $dump_sql .= 'INSERT INTO `' . $table . '` (' . $col_str . ") VALUES\n";
                        $dump_sql .= implode(",\n", $batch) . ";\n";
                    }
                    $dump_sql .= "\n";
                    mysql_free_result($data_result);
                }
            }
            mysql_free_result($tables_result);
        }

        $dump_sql .= "SET FOREIGN_KEY_CHECKS=1;\n";
        mysql_close($link);
    }

    // Gzip + base64 for safe JSON transport
    $compressed = gzencode($dump_sql, 9);
    $results[$dbname] = base64_encode($compressed);
}

header('Content-Type: application/json');
$response = array(
    'status'    => (count($errors) === 0) ? 'ok' : 'partial',
    'exported'  => array_keys($results),
    'errors'    => $errors,
    'dumps'     => $results,
    'timestamp' => date('c')
);
echo json_encode($response);

// -- Timing-safe string comparison (polyfill for hash_equals) --
function _safe_str_equals($a, $b) {
    if (strlen($a) !== strlen($b)) {
        return false;
    }
    $result = 0;
    for ($i = 0; $i < strlen($a); $i++) {
        $result = $result | (ord($a[$i]) ^ ord($b[$i]));
    }
    return ($result === 0);
}
