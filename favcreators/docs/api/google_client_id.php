<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 204 No Content');
    exit;
}

$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}

$client_id = getenv('GOOGLE_CLIENT_ID');
if (($client_id === false || $client_id === null || $client_id === '') && defined('GOOGLE_CLIENT_ID')) {
    $client_id = GOOGLE_CLIENT_ID;
}
if ($client_id === false || $client_id === null) {
    $client_id = '';
}

echo json_encode(array('client_id' => $client_id));
