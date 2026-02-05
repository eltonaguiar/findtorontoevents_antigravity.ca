<?php
/**
 * Toggle debug logging on/off. Admin only.
 * POST body: { "enabled": true|false }
 * Returns: { "debug_log_enabled": true|false }
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(array('error' => 'Use POST'));
    exit;
}

session_set_cookie_params(86400, '/', null, true, true);
session_start();

$user = isset($_SESSION['user']) ? $_SESSION['user'] : null;
if (!$user || !isset($user['role']) || $user['role'] !== 'admin') {
    echo json_encode(array('error' => 'Admin only'));
    exit;
}

$input = file_get_contents('php://input');
$data = json_decode($input, true);
$enabled = isset($data['enabled']) ? (bool)$data['enabled'] : false;
$_SESSION['debug_log_enabled'] = $enabled;

echo json_encode(array('debug_log_enabled' => $enabled));
