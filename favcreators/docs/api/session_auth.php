<?php
/**
 * Session auth helper for APIs that must act on behalf of the logged-in user.
 * Starts session (if not already). Provides get_session_user_id() and is_session_admin().
 * Use: require_once this file, then $uid = get_session_user_id(); if ($uid === null) { 401; exit; }
 * For endpoints that accept user_id param: only allow if session user matches, or is_session_admin().
 */
if (!session_id()) {
    session_set_cookie_params(86400, '/', null, true, true);
    session_start();
}

/**
 * @return int|null Authenticated user id from session, or null if not logged in.
 */
function get_session_user_id() {
    if (!isset($_SESSION['user']['id'])) {
        return null;
    }
    return (int) $_SESSION['user']['id'];
}

/**
 * @return bool True if the session user is admin (can view/edit any user's data).
 */
function is_session_admin() {
    if (!isset($_SESSION['user'])) return false;
    $u = $_SESSION['user'];
    return (isset($u['role']) && $u['role'] === 'admin')
        || (isset($u['provider']) && $u['provider'] === 'admin');
}

/**
 * Require a valid session. Sends 401 and exits if not logged in.
 * Use for endpoints that must act on behalf of the current user.
 */
function require_session() {
    if (get_session_user_id() === null) {
        header('HTTP/1.1 401 Unauthorized');
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
        exit;
    }
}

/**
 * Require admin. Sends 401 if not logged in, 403 if not admin, then exits.
 * Use for maintenance/diagnostic endpoints that must not be callable by normal users.
 */
function require_session_admin() {
    if (get_session_user_id() === null) {
        header('HTTP/1.1 401 Unauthorized');
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
        exit;
    }
    if (!is_session_admin()) {
        header('HTTP/1.1 403 Forbidden');
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(array('error' => 'Forbidden', 'require' => 'admin'));
        exit;
    }
}
