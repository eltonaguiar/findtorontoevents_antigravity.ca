<?php
/**
 * Sign-of-life endpoint: verify we can reach the Events DB.
 * No auth required. GET only. Returns JSON.
 * 
 * GET: https://findtorontoevents.ca/fc/api/events_status.php
 */
error_reporting(0);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$GLOBALS['_events_status_output_sent'] = false;
function _events_status_shutdown()
{
    if (!empty($GLOBALS['_events_status_output_sent']))
        return;
    $level = ob_get_level();
    if ($level > 0) {
        $buf = ob_get_contents();
        ob_end_clean();
        if ($buf !== false && $buf !== '' && isset($buf[0]) && $buf[0] === '{') {
            echo $buf;
            return;
        }
    }
    echo json_encode(array('ok' => false, 'error' => 'script_exited_early', 'db' => 'unknown'));
}
register_shutdown_function('_events_status_shutdown');

$out = array(
    'ok' => false,
    'db' => 'unknown',
    'error' => null,
    'tables_exist' => false,
    'events_count' => 0,
    'pulls_count' => 0,
    'last_pull' => null
);

try {
    require_once dirname(__FILE__) . '/events_db_config.php';
    $conn = @new mysqli($events_servername, $events_username, $events_password, $events_dbname);
    if ($conn->connect_error) {
        $out['error'] = 'Database connection failed: ' . $conn->connect_error;
        $GLOBALS['_events_status_output_sent'] = true;
        ob_end_clean();
        echo json_encode($out);
        exit;
    }
    $out['db'] = 'connected';

    // Check if tables exist
    $tables_ok = true;
    $tables = array('event_pulls', 'events_log', 'stats_summary');
    foreach ($tables as $t) {
        $r = $conn->query("SHOW TABLES LIKE '$t'");
        if (!$r || $r->num_rows === 0) {
            $tables_ok = false;
            break;
        }
    }
    $out['tables_exist'] = $tables_ok;

    if ($tables_ok) {
        // Get event count
        $r = $conn->query("SELECT COUNT(*) as cnt FROM events_log");
        if ($r) {
            $row = $r->fetch_assoc();
            $out['events_count'] = (int) $row['cnt'];
        }

        // Get pulls count
        $r = $conn->query("SELECT COUNT(*) as cnt FROM event_pulls");
        if ($r) {
            $row = $r->fetch_assoc();
            $out['pulls_count'] = (int) $row['cnt'];
        }

        // Get last pull
        $r = $conn->query("SELECT pull_timestamp, events_count, source, status FROM event_pulls ORDER BY pull_timestamp DESC LIMIT 1");
        if ($r && $r->num_rows > 0) {
            $out['last_pull'] = $r->fetch_assoc();
        }
    }

    $out['ok'] = true;
    $conn->close();
} catch (Exception $e) {
    $out['error'] = $e->getMessage();
}

$GLOBALS['_events_status_output_sent'] = true;
ob_end_clean();
echo json_encode($out);
?>