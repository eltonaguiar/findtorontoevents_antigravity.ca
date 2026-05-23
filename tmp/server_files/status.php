<?php
/**
 * Sign-of-life endpoint: verify we can reach the DB and read notes (e.g. Starfireara creator_id=6).
 * Session required. Non-admin get ok, db, read_ok, notes_count only; admin also get starfireara_note and get_notes_sample.
 * GET only. Returns JSON. PHP 5.2 compatible (no anonymous functions).
 */
error_reporting(0);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
// Don't require session - status check should work for guests too
// require_session();

$GLOBALS['_fc_status_output_sent'] = false;
function _fc_status_shutdown()
{
    if (!empty($GLOBALS['_fc_status_output_sent']))
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
register_shutdown_function('_fc_status_shutdown');

$out = array(
    'ok' => false,
    'db' => 'unknown',
    'error' => null,
    'read_ok' => false,
    'notes_count' => 0,
    'starfireara_note' => null,
    'get_notes_sample' => null,
);

try {
    require_once dirname(__FILE__) . '/db_connect.php';
    if (!isset($conn) || !$conn) {
        $out['error'] = 'db_connect did not set $conn';
        $GLOBALS['_fc_status_output_sent'] = true;
        ob_end_clean();
        echo json_encode($out);
        exit;
    }
    $out['db'] = 'connected';

    // Read test: same logic as get_notes for guest (creator_defaults + user_notes fallback for creator 6)
    $notes = array();
    $q1 = $conn->query("SELECT creator_id, note FROM creator_defaults");
    if ($q1) {
        while ($row = $q1->fetch_assoc()) {
            $notes[(string) $row['creator_id']] = $row['note'];
        }
    }
    if (!isset($notes['6'])) {
        $q2 = @$conn->query("SELECT creator_id, note FROM user_notes ORDER BY updated_at DESC");
        if (!$q2) {
            $q2 = @$conn->query("SELECT creator_id, note FROM user_notes ORDER BY id DESC");
        }
        if (!$q2) {
            $q2 = $conn->query("SELECT creator_id, note FROM user_notes");
        }
        if ($q2) {
            while ($row = $q2->fetch_assoc()) {
                $cid = (string) $row['creator_id'];
                if (!isset($notes[$cid])) {
                    $notes[$cid] = $row['note'];
                }
            }
        }
    }

    $out['read_ok'] = true;
    $out['notes_count'] = count($notes);
    $out['ok'] = true;
    // Only include note content for admin (avoid leaking any user/guest notes)
    if (get_session_user_id() !== null && is_session_admin()) {
        $out['starfireara_note'] = isset($notes['6']) ? $notes['6'] : null;
        $out['get_notes_sample'] = $notes;
    }

    $conn->close();
} catch (Exception $e) {
    $out['error'] = $e->getMessage();
}

$GLOBALS['_fc_status_output_sent'] = true;
ob_end_clean();
echo json_encode($out);
