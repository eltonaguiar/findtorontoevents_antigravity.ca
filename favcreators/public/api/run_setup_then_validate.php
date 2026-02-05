<?php
/**
 * Run setup_tables (create + seed) then validate_tables. One URL to create and verify.
 * Run via: https://yoursite.com/fc/api/run_setup_then_validate.php
 *
 * Or run separately:
 *   GET https://yoursite.com/fc/api/setup_tables.php   — create tables + seed
 *   GET https://yoursite.com/fc/api/validate_tables.php — check structure
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

$base = dirname(__FILE__);

// 1) Run setup (create tables + seed)
ob_start();
include $base . '/setup_tables.php';
$setup_output = ob_get_clean();
$setup = json_decode($setup_output, true);
if (!is_array($setup)) $setup = array('ok' => false, 'error' => 'setup did not return JSON');

// 2) Run validate
ob_start();
include $base . '/validate_tables.php';
$validate_output = ob_get_clean();
$validate = json_decode($validate_output, true);
if (!is_array($validate)) $validate = array('ok' => false, 'error' => 'validate did not return JSON');

$out = array(
    'setup' => $setup,
    'validate' => $validate,
    'ok' => !empty($setup['ok']) && !empty($validate['ok']),
);
echo json_encode($out);
