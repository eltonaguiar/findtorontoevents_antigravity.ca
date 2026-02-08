<?php
/**
 * Contact Lens Checker - Check if user has accepted the disclaimer
 * GET /CONTACTLENSES/api/check_acceptance.php?token=<user_token>
 * Returns: { accepted: true/false, accepted_at: "...", version: "..." }
 * PHP 5.2 compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    echo '{}';
    exit;
}

require_once dirname(__FILE__) . '/db_config.php';

$token = isset($_GET['token']) ? trim($_GET['token']) : '';
$version = isset($_GET['version']) ? trim($_GET['version']) : '1.0';

if ($token === '' || strlen($token) < 16 || strlen($token) > 64) {
    echo json_encode(array('accepted' => false, 'reason' => 'invalid_token'));
    exit;
}

try {
    $pdo = cl_get_pdo();

    // Ensure table exists (auto-create if first call)
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

    $stmt = $pdo->prepare("SELECT accepted_at, disclaimer_version FROM contactlens_disclaimer WHERE user_token = ? AND disclaimer_version = ? LIMIT 1");
    $stmt->execute(array($token, $version));
    $row = $stmt->fetch();

    if ($row) {
        echo json_encode(array(
            'accepted' => true,
            'accepted_at' => $row['accepted_at'],
            'version' => $row['disclaimer_version']
        ));
    } else {
        echo json_encode(array('accepted' => false));
    }
} catch (Exception $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('accepted' => false, 'error' => 'db_error'));
}
