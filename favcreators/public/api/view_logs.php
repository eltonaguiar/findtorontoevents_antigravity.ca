<?php
/**
 * View the logs from get_my_creators.php. Admin only.
 */
header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

$log_file = '/tmp/get_my_creators_log.txt';

if (file_exists($log_file)) {
    echo file_get_contents($log_file);
} else {
    echo "No log file found at $log_file\n";
}
?>