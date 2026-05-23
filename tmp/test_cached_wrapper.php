<?php
error_reporting(E_ALL);
ini_set('display_errors', '1');
ini_set('log_errors', '1');
ini_set('error_log', dirname(__FILE__) . '/error_log_cached.txt');

// Override the output handler to capture any fatal errors
register_shutdown_function('_check_for_fatal');
function _check_for_fatal() {
    $error = error_get_last();
    if ($error !== null && in_array($error['type'], array(E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR))) {
        header('Content-Type: text/plain');
        echo "\n\n=== FATAL ERROR ===\n";
        echo "Type: " . $error['type'] . "\n";
        echo "Message: " . $error['message'] . "\n";
        echo "File: " . $error['file'] . "\n";
        echo "Line: " . $error['line'] . "\n";
    }
}

// Set custom error handler to catch warnings too
set_error_handler('_custom_error_handler');
function _custom_error_handler($errno, $errstr, $errfile, $errline) {
    $log = date('Y-m-d H:i:s') . " [$errno] $errstr in $errfile:$errline\n";
    file_put_contents(dirname(__FILE__) . '/error_log_cached.txt', $log, FILE_APPEND);
    // Don't suppress the error
    return false;
}

$_GET['user_id'] = '0';
include dirname(__FILE__) . '/get_cached_updates.php';
?>