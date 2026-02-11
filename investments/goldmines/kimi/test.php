<?php
header('Content-Type: application/json');
error_reporting(0);

// Test PHP version
echo json_encode(array(
    'php_version' => phpversion(),
    'ok' => true,
    'message' => 'Basic PHP test works'
));
