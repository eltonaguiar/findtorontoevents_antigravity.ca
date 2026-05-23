<?php
/**
 * Comprehensive Diagnostic Script for FindStocks API
 * Tests PHP environment, extensions, and database connectivity
 * PHP 5.2 compatible
 */

ini_set('display_errors', 1);
ini_set('html_errors', 0);
error_reporting(E_ALL);

header('Content-Type: text/plain; charset=utf-8');

echo "=====================================\n";
echo "FINDSTOCKS API DIAGNOSTIC REPORT\n";
echo "Generated: " . date('Y-m-d H:i:s') . "\n";
echo "=====================================\n\n";

echo "=== PHP INFO ===\n";
echo "Version: " . phpversion() . "\n";
echo "SAPI: " . php_sapi_name() . "\n";
echo "OS: " . PHP_OS . "\n";
echo "\n";

echo "=== PHP CONFIG ===\n";
echo "display_errors: " . ini_get('display_errors') . "\n";
echo "log_errors: " . ini_get('log_errors') . "\n";
echo "error_log: " . ini_get('error_log') . "\n";
echo "memory_limit: " . ini_get('memory_limit') . "\n";
echo "max_execution_time: " . ini_get('max_execution_time') . "\n";
echo "default_charset: " . ini_get('default_charset') . "\n";
echo "\n";

echo "=== EXTENSIONS ===\n";
$required_extensions = array('mysqli', 'mysql', 'json', 'pdo', 'pdo_mysql');
$loaded_extensions = get_loaded_extensions();

foreach ($required_extensions as $ext) {
    $loaded = in_array($ext, $loaded_extensions);
    echo "$ext: " . ($loaded ? "YES" : "NO") . "\n";
}
echo "\n";

echo "=== DATABASE TEST ===\n";

$db_host = 'mysql.50webs.com';
$db_user = 'ejaguiar1_stocks';
$db_pass = 'stocks';
$db_name = 'ejaguiar1_stocks';

echo "Host: $db_host\n";
echo "User: $db_user\n";
echo "Database: $db_name\n";
echo "\n";

$mysqli = @new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($mysqli->connect_error) {
    echo "Connection: FAILED\n";
    echo "Error Code: " . $mysqli->connect_errno . "\n";
    echo "Error Message: " . $mysqli->connect_error . "\n";
    echo "\n";
    
    echo "Attempting connection without database selection...\n";
    $mysqli2 = @new mysqli($db_host, $db_user, $db_pass);
    
    if ($mysqli2->connect_error) {
        echo "Raw connection: FAILED\n";
        echo "Error: " . $mysqli2->connect_error . "\n";
    } else {
        echo "Raw connection: OK (without DB selection)\n";
        $mysqli2->close();
    }
    echo "\n";
} else {
    echo "Connection: OK\n";
    echo "Server Version: " . $mysqli->server_info . "\n";
    echo "Client Version: " . $mysqli->client_info . "\n";
    echo "Character Set: " . $mysqli->character_set_name() . "\n";
    echo "\n";

    echo "=== TABLE CHECK ===\n";
    
    $tables_to_check = array('stock_picks', 'stocks', 'signals', 'alerts');
    
    foreach ($tables_to_check as $table) {
        $result = @$mysqli->query("SHOW TABLES LIKE '$table'");
        if ($result && $result->num_rows > 0) {
            echo "$table exists: YES\n";
            
            $count_result = @$mysqli->query("SELECT COUNT(*) as count FROM $table");
            if ($count_result) {
                $row = $count_result->fetch_assoc();
                echo "  Row count: " . $row['count'] . "\n";
                $count_result->free();
            } else {
                echo "  Row count: ERROR - " . $mysqli->error . "\n";
            }
        } else {
            echo "$table exists: NO\n";
        }
        if ($result) $result->free();
    }
    echo "\n";

    echo "=== QUERY TEST ===\n";
    
    echo "Test 1 - Simple SELECT (VERSION()): ";
    $result = @$mysqli->query("SELECT VERSION() as version");
    if ($result) {
        $row = $result->fetch_assoc();
        echo "OK (MySQL " . $row['version'] . ")\n";
        $result->free();
    } else {
        echo "FAILED - " . $mysqli->error . "\n";
    }
    
    echo "Test 2 - SELECT from stock_picks: ";
    $table_check = @$mysqli->query("SHOW TABLES LIKE 'stock_picks'");
    if ($table_check && $table_check->num_rows > 0) {
        $table_check->free();
        $result = @$mysqli->query("SELECT * FROM stock_picks LIMIT 1");
        if ($result) {
            $count = $result->num_rows;
            echo "OK (fetched $count row(s))\n";
            
            if ($count > 0) {
                $row = $result->fetch_assoc();
                echo "  Columns: " . implode(', ', array_keys($row)) . "\n";
            }
            $result->free();
        } else {
            echo "FAILED - " . $mysqli->error . "\n";
        }
    } else {
        echo "SKIPPED (table does not exist)\n";
    }
    
    echo "\nTest 3 - List all tables in database:\n";
    $result = @$mysqli->query("SHOW TABLES");
    if ($result) {
        echo "Tables found: " . $result->num_rows . "\n";
        while ($row = $result->fetch_array()) {
            echo "  - " . $row[0] . "\n";
        }
        $result->free();
    } else {
        echo "FAILED - " . $mysqli->error . "\n";
    }
    
    $mysqli->close();
}

echo "\n=== ADDITIONAL INFO ===\n";
echo "Request Method: " . $_SERVER['REQUEST_METHOD'] . "\n";
$_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : 'N/A';
$_sn = isset($_SERVER['SCRIPT_NAME']) ? $_SERVER['SCRIPT_NAME'] : 'N/A';
$_ssw = isset($_SERVER['SERVER_SOFTWARE']) ? $_SERVER['SERVER_SOFTWARE'] : 'N/A';
$_ddr = isset($_SERVER['DOCUMENT_ROOT']) ? $_SERVER['DOCUMENT_ROOT'] : 'N/A';
echo "Request URI: " . $_uri . "\n";
echo "Script Name: " . $_sn . "\n";
echo "Server Software: " . $_ssw . "\n";
echo "Document Root: " . $_ddr . "\n";
echo "\n";

echo "=====================================\n";
echo "END OF DIAGNOSTIC REPORT\n";
echo "=====================================\n";
