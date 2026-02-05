<?php
// get_notes.php — returns notes for a user. Session-protected: only own notes (or guest) unless admin.
error_reporting(0);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Credentials: true');

$GLOBALS['_fc_get_notes_output_sent'] = false;
function _fc_get_notes_shutdown()
{
    if (!empty($GLOBALS['_fc_get_notes_output_sent']))
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
    echo json_encode(array());
}
register_shutdown_function('_fc_get_notes_shutdown');

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    $GLOBALS['_fc_get_notes_output_sent'] = true;
    ob_end_clean();
    echo json_encode(array());
    exit;
}

$requested_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;
$session_id = get_session_user_id();

// Not logged in: only allow viewing guest (user_id=0). No param or other user_id = 403.
if ($session_id === null) {
    if ($requested_id !== 0) {
        header('HTTP/1.1 403 Forbidden');
        $GLOBALS['_fc_get_notes_output_sent'] = true;
        ob_end_clean();
        echo json_encode(array('notes' => array(), 'secondaryNotes' => array()));
        exit;
    }
    $user_id = 0;
} else {
    // Logged in: admin can view any user_id (including 0). Non-admin can ONLY view their own (requested_id must equal session_id).
    if (is_session_admin()) {
        $user_id = $requested_id;
    } else {
        if ($requested_id !== $session_id) {
            header('HTTP/1.1 403 Forbidden');
            $GLOBALS['_fc_get_notes_output_sent'] = true;
            ob_end_clean();
            echo json_encode(array('notes' => array(), 'secondaryNotes' => array()));
            exit;
        }
        $user_id = $session_id;
    }
}

// 1. Fetch Global Defaults (creator_defaults table)
$notes = array();
$query = "SELECT creator_id, note FROM creator_defaults";
$result = $conn->query($query);
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $notes[(string) $row['creator_id']] = $row['note'];
    }
}

// 2. If User Logged In, Fetch User Overrides from user_notes
if ($user_id > 0) {
    $u_query = "SELECT creator_id, note FROM user_notes WHERE user_id = " . intval($user_id);
    $u_result = $conn->query($u_query);
    if ($u_result) {
        while ($row = $u_result->fetch_assoc()) {
            $notes[(string) $row['creator_id']] = $row['note'];
        }
    }
} else {
    // 3. Guest (user_id=0): where creator_defaults has no row, use one real note from user_notes per creator so guest sees actual DB content
    $fallback = @$conn->query("SELECT creator_id, note FROM user_notes ORDER BY updated_at DESC");
    if (!$fallback) {
        $fallback = @$conn->query("SELECT creator_id, note FROM user_notes ORDER BY id DESC");
    }
    if (!$fallback) {
        $fallback = @$conn->query("SELECT creator_id, note FROM user_notes");
    }
    if ($fallback) {
        while ($row = $fallback->fetch_assoc()) {
            $cid = (string) $row['creator_id'];
            if (!isset($notes[$cid])) {
                $notes[$cid] = $row['note'];
            }
        }
    }
}

// 4. Fetch Secondary Notes for user
$secondary_notes = array();
$sn_query = "SELECT creator_id, secondary_note FROM user_secondary_notes WHERE user_id = " . intval($user_id);
$sn_result = $conn->query($sn_query);
if ($sn_result) {
    while ($row = $sn_result->fetch_assoc()) {
        $secondary_notes[(string) $row['creator_id']] = $row['secondary_note'];
    }
}
// Guest fallback for secondary notes
if ($user_id === 0) {
    $sn_fallback = @$conn->query("SELECT creator_id, secondary_note FROM user_secondary_notes ORDER BY updated_at DESC");
    if (!$sn_fallback) {
        $sn_fallback = @$conn->query("SELECT creator_id, secondary_note FROM user_secondary_notes");
    }
    if ($sn_fallback) {
        while ($row = $sn_fallback->fetch_assoc()) {
            $cid = (string) $row['creator_id'];
            if (!isset($secondary_notes[$cid])) {
                $secondary_notes[$cid] = $row['secondary_note'];
            }
        }
    }
}

$conn->close();
$GLOBALS['_fc_get_notes_output_sent'] = true;
ob_end_clean();
echo json_encode(array('notes' => $notes, 'secondaryNotes' => $secondary_notes));
?>