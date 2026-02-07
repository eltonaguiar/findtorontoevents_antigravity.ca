<?php
// get_me.php - Compatible Version
// Returns the currently logged-in user from PHP Session and, for admin, debug_log_enabled.
// Also includes Discord link status if available.

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
    
    // Fetch Discord info from database if user has an id
    if (isset($_SESSION['user']['id'])) {
        require_once dirname(__FILE__) . '/db_connect.php';
        if (isset($conn) && $conn) {
            $user_id = intval($_SESSION['user']['id']);
            $result = $conn->query("SELECT discord_id, discord_username FROM users WHERE id = $user_id");
            if ($result && $result->num_rows > 0) {
                $row = $result->fetch_assoc();
                if (!empty($row['discord_id'])) {
                    $out["user"]["discord_id"] = $row['discord_id'];
                    $out["user"]["discord_username"] = $row['discord_username'];
                }
            }
            $conn->close();
        }
    }
}
echo json_encode($out);
?>