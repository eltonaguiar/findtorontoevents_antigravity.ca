<?php
header("Content-Type: text/plain");
error_reporting(E_ALL);
ini_set('display_errors', '1');

echo "=== DB Config Diagnosis ===\n\n";

// Load db_config.php
require_once dirname(__FILE__) . '/db_config.php';

echo "host: " . $servername . "\n";
echo "user: " . $username . "\n";
echo "db: " . $dbname . "\n";
echo "pass length: " . strlen($password) . "\n";
echo "pass empty: " . ($password === '' ? 'YES' : 'NO') . "\n";
echo "pass first 3: " . (strlen($password) > 3 ? substr($password, 0, 3) . '***' : '(short/empty)') . "\n";
echo "\n";

// Try connect
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo "CONNECTION FAILED: " . $conn->connect_error . "\n";
} else {
    echo "CONNECTION SUCCESS! Server: " . $conn->server_info . "\n";
    $conn->close();
}
?>