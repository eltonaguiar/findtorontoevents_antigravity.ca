<?php
/**
 * Simple session check endpoint - returns user_id if logged in, 0 if guest
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");

require_once dirname(__FILE__) . '/session_auth.php';

$user_id = get_session_user_id();
$is_admin = is_session_admin();

echo json_encode(array(
    'user_id' => $user_id !== null ? $user_id : 0,
    'is_admin' => $is_admin,
    'logged_in' => $user_id !== null && $user_id > 0
));
?>
