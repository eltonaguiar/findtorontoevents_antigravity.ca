<?php
// PHP 5 Compatibility Test
header('Content-Type: application/json');

// Test 1: Basic array
$test = array('ok' => true, 'message' => 'PHP is working');

// Test 2: Check if http_response_code exists
$test['http_response_code_exists'] = function_exists('http_response_code');

// Test 3: Check PHP version
$test['php_version'] = phpversion();

echo json_encode($test);