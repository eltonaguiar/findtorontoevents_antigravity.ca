<?php
error_reporting(0);
ini_set('display_errors', '0');

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    // PHP 5.4+ only; 50webs runs 5.2.17, so send the raw status line too.
    if (function_exists('http_response_code')) { http_response_code(204); }
    header('HTTP/1.1 204 No Content');
    exit;
}

// Session support not yet implemented — return empty response
echo json_encode(array('user' => null));
?>
