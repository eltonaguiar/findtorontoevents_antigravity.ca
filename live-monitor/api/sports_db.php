<?php
/**
 * Sports betting DB connection (ejaguiar1_sportsbet).
 * PHP 5.2 safe. Used by sports_*.php endpoints.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once dirname(__FILE__) . '/db_config.php';

// Use same variable names that db_config.php sets (sports_servername, etc.)
// This fixes the "Sports DB connection failed" error on the live server
$sports_server = isset($sports_servername) ? $sports_servername : 'localhost';
$sports_user = isset($sports_username) ? $sports_username : 'root';
$sports_pass = isset($sports_password) ? $sports_password : '';
$sports_db = isset($sports_dbname) ? $sports_dbname : 'ejaguiar1_sportsbet';

$sports_mysqli = @new mysqli($sports_server, $sports_user, $sports_pass, $sports_db);

function sports_db_json_error($msg) {
    echo json_encode(array('ok' => false, 'error' => $msg));
    exit;
}

if ($sports_mysqli->connect_error) {
    error_log('sports_db: ' . $sports_mysqli->connect_error);
    sports_db_json_error('Sports DB connection failed');
}

$sports_mysqli->set_charset('utf8');
