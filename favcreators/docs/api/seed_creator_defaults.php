<?php
/**
 * One-time seed: ensure creator_defaults has a row for creator_id 6 (Starfireara)
 * so guest page shows a note. Run once after DB is configured: GET or POST this URL.
 * PHP 5.2 compatible.
 */
error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

$out = array('ok' => false, 'error' => null, 'message' => '');

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    $out['error'] = 'Database not available';
    echo json_encode($out);
    exit;
}

$default_note = 'Personal note for Starfireara (default). Edit as admin to change.';
$creator_id = '6';

// Create table if missing (optional)
$create = "CREATE TABLE IF NOT EXISTS creator_defaults (creator_id VARCHAR(32) PRIMARY KEY, note TEXT)";
if (!$conn->query($create)) {
    $out['error'] = 'Could not create table: ' . $conn->error;
    echo json_encode($out);
    exit;
}

$note_esc = $conn->real_escape_string($default_note);
$creator_esc = $conn->real_escape_string($creator_id);
$sql = "INSERT INTO creator_defaults (creator_id, note) VALUES ('$creator_esc', '$note_esc') ON DUPLICATE KEY UPDATE note = VALUES(note)";
if ($conn->query($sql)) {
    $out['ok'] = true;
    $out['message'] = 'Creator 6 default note seeded. Guest page will show it.';
} else {
    $out['error'] = $conn->error;
}
echo json_encode($out);
$conn->close();
