<?php
/**
 * db_sync_mark.php -- Mark changelog entries as synced to a destination site.
 * Called after db_sync_apply.php successfully applies entries on the remote site.
 *
 * Protected by DB_SCRIPT_TOKEN. PHP 5.2-safe.
 *
 * Usage: POST /db_sync_mark.php
 *   Body (JSON): {
 *     "token": "SECRET",
 *     "db": "ejaguiar1_favcreators",
 *     "dest": "torontoevent.net",
 *     "entry_ids": [1, 2, 3, ...]
 *   }
 */

header('Content-Type: application/json');

$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!is_array($input)) $input = array();

// ── Auth ─────────────────────────────────────────────────────────────────────
$provided_token   = isset($input['token']) ? $input['token'] : '';
$configured_token = 'SYNC_TOKEN_PLACEHOLDER';

if ($configured_token === '' || $provided_token === '' || $provided_token !== $configured_token) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Forbidden'));
    exit;
}

// ── Params ───────────────────────────────────────────────────────────────────
$db_host   = 'localhost';
$db_user   = 'DB_USER_PLACEHOLDER';
$db_pass   = 'DB_PASS_PLACEHOLDER';
$dbname    = isset($input['db'])        ? $input['db']        : '';
$dest      = isset($input['dest'])      ? $input['dest']      : '';
$entry_ids = isset($input['entry_ids']) ? $input['entry_ids'] : array();

if ($dbname === '' || $dest === '' || !is_array($entry_ids) || count($entry_ids) === 0) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Missing db, dest, or entry_ids'));
    exit;
}

require_once dirname(__FILE__) . '/sync_config.php';
$_allowed_dbs = array_keys(sync_get_user_tables());
if (!in_array($dbname, $_allowed_dbs)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Database not in allowed list'));
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

// ── Mark entries as synced ───────────────────────────────────────────────────
// synced_to is a JSON array of site names. We append the dest if not already there.
$esc_dest = $conn->real_escape_string($dest);
$marked = 0;
$errors = array();

foreach ($entry_ids as $eid) {
    $eid = (int) $eid;
    if ($eid <= 0) continue;

    // Read current synced_to
    $r = $conn->query("SELECT synced_to FROM sync_changelog WHERE id = " . $eid . " LIMIT 1");
    if (!$r || $r->num_rows === 0) continue;

    $row = $r->fetch_assoc();
    $current = $row['synced_to'];
    $sites = array();

    if ($current !== null && $current !== '') {
        $decoded = json_decode($current, true);
        if (is_array($decoded)) {
            $sites = $decoded;
        }
    }

    // Only add if not already there
    if (!in_array($dest, $sites)) {
        $sites[] = $dest;
    }

    $new_synced = $conn->real_escape_string(json_encode($sites));
    $upd = $conn->query("UPDATE sync_changelog SET synced_to = '" . $new_synced . "' WHERE id = " . $eid);
    if ($upd) {
        $marked++;
    } else {
        $errors[] = 'id ' . $eid . ': ' . $conn->error;
    }
}

// ── Also update sync_table_config last_synced_at ─────────────────────────────
$now = gmdate('Y-m-d H:i:s');
$conn->query("UPDATE sync_table_config SET last_synced_at = '" . $now . "' WHERE enabled = 1");

$conn->close();

echo json_encode(array(
    'status'    => (count($errors) === 0) ? 'ok' : 'partial',
    'marked'    => $marked,
    'errors'    => $errors,
    'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
));
