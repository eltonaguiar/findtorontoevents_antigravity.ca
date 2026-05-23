<?php
/**
 * Discord Interactions Endpoint - Debug version
 */

error_reporting(0);
ini_set('display_errors', 0);

// Log function
function debug_log($msg) {
    $file = dirname(__FILE__) . '/discord_debug.log';
    $time = date('Y-m-d H:i:s');
    file_put_contents($file, "[$time] $msg\n", FILE_APPEND);
}

debug_log("=== New request ===");
debug_log("Method: " . $_SERVER['REQUEST_METHOD']);

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    header('Content-Type: application/json');
    echo '{"error":"Method not allowed"}';
    exit;
}

// Get request data
$body = file_get_contents('php://input');
$signature = isset($_SERVER['HTTP_X_SIGNATURE_ED25519']) ? $_SERVER['HTTP_X_SIGNATURE_ED25519'] : '';
$timestamp = isset($_SERVER['HTTP_X_SIGNATURE_TIMESTAMP']) ? $_SERVER['HTTP_X_SIGNATURE_TIMESTAMP'] : '';

debug_log("Body length: " . strlen($body));
debug_log("Body: " . $body);
debug_log("Signature: " . $signature);
debug_log("Timestamp: " . $timestamp);

// Load config
require_once dirname(__FILE__) . '/discord_config.php';
$config = get_discord_config();
$public_key = isset($config['public_key']) ? $config['public_key'] : '';

debug_log("Public key from config: " . $public_key);
debug_log("Public key length: " . strlen($public_key));

// Check if we have all required data
if (empty($signature) || empty($timestamp) || empty($public_key)) {
    debug_log("Missing required data - sig empty: " . (empty($signature) ? 'yes' : 'no') . 
              ", ts empty: " . (empty($timestamp) ? 'yes' : 'no') . 
              ", pk empty: " . (empty($public_key) ? 'yes' : 'no'));
    header('HTTP/1.1 401 Unauthorized');
    header('Content-Type: application/json');
    echo '{"error":"Missing signature data"}';
    exit;
}

// Try to verify using sodium if available
$verified = false;
if (function_exists('sodium_crypto_sign_verify_detached')) {
    debug_log("Using sodium for verification");
    try {
        $sig_bin = hex2bin($signature);
        $key_bin = hex2bin($public_key);
        $message = $timestamp . $body;
        debug_log("Message to verify: " . $message);
        $verified = sodium_crypto_sign_verify_detached($sig_bin, $message, $key_bin);
        debug_log("Sodium verification result: " . ($verified ? 'true' : 'false'));
    } catch (Exception $e) {
        debug_log("Sodium error: " . $e->getMessage());
    }
} else {
    debug_log("Sodium not available, trying pure PHP");
    require_once dirname(__FILE__) . '/ed25519_verify.php';
    $verified = verify_discord_request($body, $signature, $timestamp, $public_key);
    debug_log("Pure PHP verification result: " . ($verified ? 'true' : 'false'));
}

if (!$verified) {
    debug_log("Verification FAILED");
    header('HTTP/1.1 401 Unauthorized');
    header('Content-Type: application/json');
    echo '{"error":"Invalid request signature"}';
    exit;
}

debug_log("Verification PASSED");

// Parse interaction
$interaction = json_decode($body, true);
if (!$interaction) {
    debug_log("JSON parse failed");
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo '{"error":"Invalid JSON"}';
    exit;
}

$type = isset($interaction['type']) ? intval($interaction['type']) : 0;
debug_log("Interaction type: " . $type);

// Handle PING
if ($type === 1) {
    debug_log("Responding with PONG");
    header('Content-Type: application/json');
    echo '{"type":1}';
    exit;
}

// Handle commands
if ($type === 2) {
    debug_log("Handling command");
    require_once dirname(__FILE__) . '/discord_interactions_full.php';
    handle_interaction($interaction);
    exit;
}

debug_log("Unknown type: $type");
header('HTTP/1.1 400 Bad Request');
header('Content-Type: application/json');
echo '{"error":"Unhandled interaction type"}';
