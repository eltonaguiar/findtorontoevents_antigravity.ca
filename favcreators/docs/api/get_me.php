<?php
// get_me.php v4 — 2026-02-17
// Returns the currently logged-in user from PHP Session.
// PHP 8.3 compatible: uses try/catch for DB queries (mysqli throws exceptions).

if (function_exists('opcache_invalidate')) {
    @opcache_invalidate(__FILE__, true);
}

error_reporting(0);
ini_set('display_errors', '0');

function _gm_shutdown() {
    $err = error_get_last();
    if ($err && ($err['type'] & (E_ERROR | E_PARSE | E_CORE_ERROR | E_COMPILE_ERROR))) {
        if (!headers_sent()) {
            header('HTTP/1.1 200 OK');
            header('Content-Type: application/json');
        }
        echo json_encode(array('user' => null, 'debug_log_enabled' => false, '_v' => 4, '_recovered' => true));
    }
}
register_shutdown_function('_gm_shutdown');

session_set_cookie_params(86400, '/', null, true, true);
@session_start();

header('Content-Type: application/json');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('X-FC-Version: get_me_v4');

$out = array('user' => null, 'debug_log_enabled' => false, '_v' => 4);

if (isset($_SESSION['user'])) {
    $out['user'] = $_SESSION['user'];

    if (isset($_SESSION['user']['role']) && $_SESSION['user']['role'] === 'admin' && isset($_SESSION['debug_log_enabled'])) {
        $out['debug_log_enabled'] = (bool)$_SESSION['debug_log_enabled'];
    }

    // Fetch Discord info — wrapped in try/catch because PHP 8.3 throws
    // mysqli_sql_exception on query errors (Unknown column, etc.)
    if (isset($_SESSION['user']['id'])) {
        try {
            $f = dirname(__FILE__) . '/db_config.php';
            if (file_exists($f)) {
                require_once $f;
                if (isset($servername) && isset($username) && isset($password) && isset($dbname)) {
                    $conn = new mysqli($servername, $username, $password, $dbname);
                    if (!$conn->connect_error) {
                        $uid = intval($_SESSION['user']['id']);
                        $cols = $conn->query("SHOW COLUMNS FROM users LIKE 'discord_id'");
                        if ($cols && $cols->num_rows > 0) {
                            $result = $conn->query("SELECT discord_id, discord_username FROM users WHERE id = " . $uid);
                            if ($result && $result->num_rows > 0) {
                                $row = $result->fetch_assoc();
                                if (!empty($row['discord_id'])) {
                                    $out['user']['discord_id'] = $row['discord_id'];
                                    $out['user']['discord_username'] = $row['discord_username'];
                                }
                            }
                        }
                        $conn->close();
                    }
                }
            }
        } catch (Exception $e) {
            // Discord info is optional — never crash for it
        }
    }
}

echo json_encode($out);
exit;
