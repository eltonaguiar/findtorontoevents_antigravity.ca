<?php
/**
 * Database connection for the findstocks/portfolio2 API surface.
 * PHP 5.2 compatible.
 *
 * Created 2026-11-23 because stock_intel.php requires this exact path and it did
 * not exist in the repo or on the live host (HTTP 404), so the endpoint could
 * never have executed. Mirrors findforex2/api/db_connect.php, which is deployed
 * and connects successfully.
 *
 * Sets $conn for the caller. On failure it emits JSON and exits, because every
 * consumer of this file is a JSON API.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_config.php';

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');
?>
