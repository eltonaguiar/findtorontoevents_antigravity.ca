<?php
/**
 * Contact Lens Checker - Save disclaimer acceptance
 * POST /CONTACTLENSES/api/save_acceptance.php
 * Body (JSON): { token: "...", version: "1.0" }
 * Saves: user_token, IP, user-agent, timestamp, version
 * Returns: { success: true, accepted_at: "...", record_id: N }
 * PHP 5.2 compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    echo '{}';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    echo json_encode(array('success' => false, 'error' => 'POST required'));
    exit;
}

require_once dirname(__FILE__) . '/db_config.php';

// Read JSON body
$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
$token = isset($input['token']) ? trim($input['token']) : '';
$version = isset($input['version']) ? trim($input['version']) : '1.0';

if ($token === '' || strlen($token) < 16 || strlen($token) > 64) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('success' => false, 'error' => 'Invalid token (must be 16-64 chars)'));
    exit;
}

// Get user info for evidence
$ip = '';
if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
    $parts = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
    $ip = $parts[0];
} elseif (!empty($_SERVER['REMOTE_ADDR'])) {
    $ip = $_SERVER['REMOTE_ADDR'];
}
$ip = trim($ip);
$ua = isset($_SERVER['HTTP_USER_AGENT']) ? substr($_SERVER['HTTP_USER_AGENT'], 0, 500) : '';

try {
    $pdo = cl_get_pdo();

    // Ensure table exists
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS contactlens_disclaimer (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_token VARCHAR(64) NOT NULL,
            ip_address VARCHAR(45) DEFAULT NULL,
            user_agent TEXT DEFAULT NULL,
            accepted_at DATETIME NOT NULL,
            disclaimer_version VARCHAR(10) NOT NULL DEFAULT '1.0',
            UNIQUE KEY idx_token_version (user_token, disclaimer_version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    // Check if already accepted
    $check = $pdo->prepare("SELECT id, accepted_at FROM contactlens_disclaimer WHERE user_token = ? AND disclaimer_version = ? LIMIT 1");
    $check->execute(array($token, $version));
    $existing = $check->fetch();

    if ($existing) {
        echo json_encode(array(
            'success' => true,
            'already_accepted' => true,
            'accepted_at' => $existing['accepted_at'],
            'record_id' => (int) $existing['id']
        ));
        exit;
    }

    // Insert new acceptance record
    $now = gmdate('Y-m-d H:i:s');
    $stmt = $pdo->prepare("INSERT INTO contactlens_disclaimer (user_token, ip_address, user_agent, accepted_at, disclaimer_version) VALUES (?, ?, ?, ?, ?)");
    $stmt->execute(array($token, $ip, $ua, $now, $version));
    $id = (int) $pdo->lastInsertId();

    echo json_encode(array(
        'success' => true,
        'already_accepted' => false,
        'accepted_at' => $now,
        'record_id' => $id
    ));
} catch (Exception $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('success' => false, 'error' => 'db_error: ' . $e->getMessage()));
}
