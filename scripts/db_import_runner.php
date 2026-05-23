<?php
/**
 * db_import_runner.php
 * Server-side DB import helper — deployed temporarily by GitHub Actions.
 * Supports POST body or file mode (FTP-uploaded dumps read from disk).
 *
 * Usage:
 *   POST  /_db_import_tmp.php  (JSON body: token, db, dump)
 *   GET   /_db_import_tmp.php?token=X&db=NAME&file=1  (reads _sync_dumps/NAME.b64gz)
 *   GET   /_db_import_tmp.php?token=X&db=__diag__      (diagnostics)
 */

@set_time_limit(300);
@ini_set('max_execution_time', '300');

// -- Authentication --
$raw   = file_get_contents('php://input');
$_decoded = json_decode($raw, true);
$input = is_array($_decoded) ? $_decoded : array();

$expected_token = 'IMPORT_TOKEN_PLACEHOLDER';
$provided_token = isset($input['token']) ? $input['token'] : (isset($_GET['token']) ? $_GET['token'] : '');

if ($expected_token === '' || substr($expected_token, 0, 7) === 'IMPORT_' || $expected_token !== $provided_token) {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// -- Config --
$db_host = 'localhost';
$db_user = 'IMPORT_DB_USER_PLACEHOLDER';
$db_pass = 'IMPORT_DB_PASS_PLACEHOLDER';

$dbname    = isset($input['db'])   ? $input['db']   : (isset($_GET['db']) ? $_GET['db'] : '');
$dump_b64  = isset($input['dump']) ? $input['dump'] : '';
$file_mode = isset($_GET['file']) && $_GET['file'] === '1';

// -- Diagnostics mode --
if ($dbname === '__diag__') {
    $_dis_raw = explode(',', ini_get('disable_functions'));
    $_dis_fns = array();
    foreach ($_dis_raw as $_df) { $_dis_fns[] = trim($_df); }

    $dump_dir = dirname(__FILE__) . '/_sync_dumps';
    $dump_files = array();
    if (is_dir($dump_dir)) {
        $dh = opendir($dump_dir);
        if ($dh) {
            while (($f = readdir($dh)) !== false) {
                if (substr($f, -6) === '.b64gz') {
                    $dump_files[] = $f . ' (' . round(filesize($dump_dir . '/' . $f) / 1024, 1) . ' KB)';
                }
            }
            closedir($dh);
        }
    }

    header('Content-Type: application/json');
    echo json_encode(array(
        'status' => 'ok',
        'diag' => true,
        'php_version' => PHP_VERSION,
        'exec_available' => function_exists('exec') && !in_array('exec', $_dis_fns),
        'pdo_available' => class_exists('PDO'),
        'gzdecode_available' => function_exists('gzdecode'),
        'db_user' => $db_user,
        'db_host' => $db_host,
        'dump_dir_exists' => is_dir($dump_dir),
        'dump_files' => $dump_files,
        'disabled_functions' => implode(', ', array_slice($_dis_fns, 0, 20)),
    ));
    exit;
}

// -- File mode: read dump from FTP-uploaded file --
if ($file_mode && $dbname !== '') {
    $dump_file = dirname(__FILE__) . '/_sync_dumps/' . basename($dbname) . '.b64gz';
    if (file_exists($dump_file)) {
        $dump_b64 = trim(file_get_contents($dump_file));
    } else {
        header('HTTP/1.1 404 Not Found');
        header('Content-Type: application/json');
        echo json_encode(array('error' => 'Dump file not found: ' . basename($dbname) . '.b64gz'));
        exit;
    }
}

if ($dbname === '' || $dump_b64 === '') {
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Missing db or dump. file_mode=' . ($file_mode ? '1' : '0') . ' b64_len=' . strlen($dump_b64)));
    exit;
}

if (!preg_match('/^[a-zA-Z0-9_]+$/', $dbname)) {
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Invalid database name'));
    exit;
}

// -- Decode dump --
$compressed = base64_decode($dump_b64);
if ($compressed === false) {
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Invalid base64 data', 'b64_len' => strlen($dump_b64), 'b64_start' => substr($dump_b64, 0, 40)));
    exit;
}

$sql = function_exists('gzdecode') ? gzdecode($compressed) : false;
if ($sql === false) {
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'Failed to decompress (gzdecode available: ' . (function_exists('gzdecode') ? 'yes' : 'NO') . ')'));
    exit;
}

// Fix collation incompatibilities (MySQL 8.0 → MariaDB)
$sql = str_replace('utf8mb4_0900_ai_ci', 'utf8mb4_general_ci', $sql);
$sql = str_replace('utf8mb4_0900_as_cs', 'utf8mb4_general_ci', $sql);

// Strip non-SQL lines (e.g. mysqldump warnings captured from stderr)
$cleaned_lines = array();
$raw_lines = explode("\n", $sql);
foreach ($raw_lines as $line) {
    $trimmed = ltrim($line);
    if ($trimmed === '') { $cleaned_lines[] = $line; continue; }
    $first2 = substr($trimmed, 0, 2);
    if ($first2 === '--' || $first2 === '/*' || $first2 === '*/') { $cleaned_lines[] = $line; continue; }
    // Skip mysqldump/mariadb-dump warning lines that aren't SQL
    if (strpos($trimmed, 'mysqldump:') === 0 || strpos($trimmed, 'mariadb-dump:') === 0) { continue; }
    $cleaned_lines[] = $line;
}
$sql = implode("\n", $cleaned_lines);

$sql_len = strlen($sql);
$import_errors = array();

// -- Import via mysql CLI (fastest) --
$import_ok = false;
$method_used = 'none';

$_dis_raw = explode(',', ini_get('disable_functions'));
$_dis_fns = array();
foreach ($_dis_raw as $_df) { $_dis_fns[] = trim($_df); }
$exec_ok = function_exists('exec') && !in_array('exec', $_dis_fns);

if ($exec_ok) {
    $method_used = 'exec';
    $tmp_file = tempnam(sys_get_temp_dir(), 'db_import_') . '.sql';
    file_put_contents($tmp_file, "SET FOREIGN_KEY_CHECKS=0;\nSET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n" . $sql . "\nSET FOREIGN_KEY_CHECKS=1;\n");

    $escaped_pass = escapeshellarg($db_pass);
    $escaped_user = escapeshellarg($db_user);
    $escaped_db   = escapeshellarg($dbname);
    $cmd = "mysql -h " . escapeshellarg($db_host) . " -u $escaped_user -p$escaped_pass $escaped_db --force < " . escapeshellarg($tmp_file) . " 2>&1";

    $out = array();
    $exit_code = -1;
    exec($cmd, $out, $exit_code);
    @unlink($tmp_file);

    if ($exit_code === 0) {
        $import_ok = true;
    } else {
        $import_errors[] = 'exec exit=' . $exit_code . ': ' . implode(' ', array_slice($out, 0, 5));
    }
}

// -- Fallback: PDO --
if (!$import_ok) {
    $method_used = $exec_ok ? 'exec_failed_then_pdo' : 'pdo';
    try {
        $pdo = new PDO("mysql:host=$db_host;dbname=$dbname;charset=utf8mb4", $db_user, $db_pass, array(
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ));
        $pdo->setAttribute(PDO::MYSQL_ATTR_USE_BUFFERED_QUERY, true);
        $pdo->exec('SET FOREIGN_KEY_CHECKS=0');
        $pdo->exec('SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO"');
        $pdo->exec("SET NAMES 'utf8mb4'");

        $statements = preg_split('/;\s*\n/', $sql, -1, PREG_SPLIT_NO_EMPTY);
        $executed = 0;
        $skipped = 0;
        $critical_errs = array();
        $noncritical_errs = 0;
        foreach ($statements as $stmt) {
            $stmt = trim($stmt);
            if ($stmt === '' || substr($stmt, 0, 2) === '--') continue;
            // Skip non-SQL noise
            if (strpos($stmt, 'mysqldump:') !== false && strpos($stmt, 'SELECT') === false) { $skipped++; continue; }
            try {
                $pdo->exec($stmt);
                $executed++;
            } catch (PDOException $e) {
                $msg = $e->getMessage();
                $code = $e->getCode();
                // Non-critical: table exists (1050), duplicate key (1062) — expected on re-sync
                if ($code == '42S01' || $code == '23000' || strpos($msg, '1050') !== false || strpos($msg, '1062') !== false) {
                    $noncritical_errs++;
                } else {
                    if (count($critical_errs) < 5) {
                        $critical_errs[] = substr($msg, 0, 200);
                    }
                }
            }
        }
        $pdo->exec('SET FOREIGN_KEY_CHECKS=1');

        // Success if we executed statements and have no critical errors
        $import_ok = ($executed > 0 && count($critical_errs) === 0);
        if (!empty($critical_errs)) {
            $import_errors[] = 'PDO: ' . $executed . ' ok, ' . count($critical_errs) . ' critical, ' . $noncritical_errs . ' non-critical: ' . implode(' | ', $critical_errs);
        } elseif ($noncritical_errs > 0) {
            $import_errors[] = 'PDO: ' . $executed . ' ok, ' . $noncritical_errs . ' non-critical (table-exists/dup-key, expected)';
        }
    } catch (Exception $e) {
        $import_errors[] = 'PDO connect failed: ' . $e->getMessage();
    }
}

header('Content-Type: application/json');
echo json_encode(array(
    'status'    => $import_ok ? 'ok' : 'error',
    'db'        => $dbname,
    'method'    => $method_used,
    'sql_bytes' => $sql_len,
    'errors'    => $import_errors,
    'timestamp' => date('c'),
));
