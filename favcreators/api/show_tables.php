<?php
// Show all tables and their structure
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Database Tables ===\n\n";

// Show all tables
$result = $conn->query("SHOW TABLES");
if ($result) {
    while ($row = $result->fetch_array()) {
        $table = $row[0];
        echo "Table: $table\n";

        // Show structure
        $desc = $conn->query("DESCRIBE $table");
        if ($desc) {
            while ($col = $desc->fetch_assoc()) {
                echo "  - " . $col['Field'] . " (" . $col['Type'] . ")\n";
            }
        }
        echo "\n";
    }
}

$conn->close();
?>