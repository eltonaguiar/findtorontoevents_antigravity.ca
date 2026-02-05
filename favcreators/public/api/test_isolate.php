<?php
header('Content-Type: application/json');
$tests = array();

// Test 1: Basic PHP
$tests['php_works'] = true;

// Test 2: Check if files exist
$tests['db_config_exists'] = file_exists(dirname(__FILE__) . '/db_config.php');
$tests['db_connect_exists'] = file_exists(dirname(__FILE__) . '/db_connect.php');
$tests['session_auth_exists'] = file_exists(dirname(__FILE__) . '/session_auth.php');

// Test 3: Try to include db_config
if ($tests['db_config_exists']) {
    try {
        require_once dirname(__FILE__) . '/db_config.php';
        $tests['db_config_loads'] = true;
    } catch (Exception $e) {
        $tests['db_config_loads'] = false;
        $tests['db_config_error'] = $e->getMessage();
    }
}

// Test 4: Try to include session_auth
if ($tests['session_auth_exists']) {
    try {
        require_once dirname(__FILE__) . '/session_auth.php';
        $tests['session_auth_loads'] = true;
    } catch (Exception $e) {
        $tests['session_auth_loads'] = false;
        $tests['session_auth_error'] = $e->getMessage();
    }
}

echo json_encode($tests);