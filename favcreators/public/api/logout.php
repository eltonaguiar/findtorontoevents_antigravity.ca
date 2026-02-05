<?php
/**
 * Sign out: destroy session and return success.
 */
session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION = array();
if (ini_get('session.use_cookies')) {
    $p = session_get_cookie_params();
    setcookie(session_name(), '', time() - 3600, $p['path'], $p['domain'], $p['secure'], $p['httponly']);
}
session_destroy();

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache');
echo json_encode(array('status' => 'ok'));
