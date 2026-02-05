<?php
// get_me.php - Compatible Version
// Returns the currently logged-in user from PHP Session and, for admin, debug_log_enabled.

session_set_cookie_params(86400, '/', null, true, true);
session_start();

header('Content-Type: application/json');
header('Cache-Control: no-cache, must-revalidate');

$out = array("user" => null, "debug_log_enabled" => false);
if (isset($_SESSION['user'])) {
    $out["user"] = $_SESSION['user'];
    if (isset($_SESSION['user']['role']) && $_SESSION['user']['role'] === 'admin' && isset($_SESSION['debug_log_enabled'])) {
        $out["debug_log_enabled"] = (bool)$_SESSION['debug_log_enabled'];
    }
}
echo json_encode($out);
?>