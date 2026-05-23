<?php
header("Content-Type: text/plain; charset=utf-8");
error_reporting(E_ALL);
ini_set('display_errors', '1');

echo "=== Full Diagnostic ===\n\n";
echo "PHP: " . phpversion() . "\n";
echo "CWD: " . getcwd() . "\n";
echo "Script: " . __FILE__ . "\n";
echo "dirname(__FILE__): " . dirname(__FILE__) . "\n";

$envPath = dirname(__FILE__) . '/.env';
echo "\n=== .env file ===\n";
echo "Path: $envPath\n";
echo "exists: " . (file_exists($envPath) ? "yes" : "NO") . "\n";
echo "readable: " . (is_readable($envPath) ? "yes" : "NO") . "\n";
if (file_exists($envPath)) {
    $perms = substr(sprintf('%o', fileperms($envPath)), -4);
    echo "perms: $perms\n";
    echo "size: " . filesize($envPath) . "\n";
    $raw = file_get_contents($envPath);
    echo "read length: " . strlen($raw) . "\n\n";
    echo "--- .env content ---\n";
    echo $raw;
    echo "--- end .env ---\n";
}

echo "\n=== Load db_config.php ===\n";
require_once dirname(__FILE__) . '/db_config.php';
echo "host: $servername\n";
echo "user: $username\n";
echo "db: $dbname\n";
echo "pass_len: " . strlen($password) . "\n";
echo "pass_empty: " . ($password === '' ? 'YES' : 'NO') . "\n";
echo "pass_first3: " . (strlen($password) > 3 ? substr($password, 0, 3) . '***' : '(empty)') . "\n";

echo "\n=== Test connection ===\n";
try {
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        echo "CONNECT ERROR: " . $conn->connect_error . "\n";
    } else {
        echo "SUCCESS: " . $conn->server_info . "\n";
        
        // Check tables
        $tables = array('user_lists', 'creator_status_updates', 'creator_mentions', 'creators', 'creator_defaults', 'user_notes');
        foreach ($tables as $t) {
            $r = $conn->query("SHOW TABLES LIKE '$t'");
            echo "  table $t: " . ($r && $r->num_rows > 0 ? "exists" : "MISSING") . "\n";
        }
        $conn->close();
    }
} catch (Exception $e) {
    echo "EXCEPTION: " . $e->getMessage() . "\n";
}

echo "\nDone.\n";
?>