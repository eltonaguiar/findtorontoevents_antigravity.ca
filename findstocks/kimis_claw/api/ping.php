<?php
// Simple ping test - no database, should be instant
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

echo json_encode(array(
    'ok' => true,
    'ping' => 'pong',
    'time' => date('Y-m-d H:i:s'),
    'php_version' => phpversion()
));
