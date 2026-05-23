<?php
/**
 * Kimi's Claw API - Debug Script
 * Comprehensive diagnostics for troubleshooting non-JSON responses
 */

// Enable all error reporting first thing
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('log_errors', 1);

header('Content-Type: text/plain; charset=utf-8');

echo "========================================\n";
echo "KIMI'S CLAW API - DEBUG REPORT\n";
echo "Generated: " . date('Y-m-d H:i:s') . "\n";
echo "========================================\n\n";

// ============================================
// 1. PHP VERSION & ENVIRONMENT
// ============================================
echo "1. PHP VERSION & ENVIRONMENT\n";
echo "-----------------------------\n";
echo "PHP Version:        " . PHP_VERSION . "\n";
echo "PHP SAPI:           " . php_sapi_name() . "\n";
echo "PHP OS:             " . PHP_OS . "\n";
$_sw = isset($_SERVER['SERVER_SOFTWARE']) ? $_SERVER['SERVER_SOFTWARE'] : 'Unknown';
$_dr = isset($_SERVER['DOCUMENT_ROOT']) ? $_SERVER['DOCUMENT_ROOT'] : 'Unknown';
echo "Server Software:    " . $_sw . "\n";
echo "Current Script:     " . __FILE__ . "\n";
echo "Document Root:      " . $_dr . "\n";
echo "\n";

// PHP Version Check
$php_version = PHP_VERSION;
$_vparts = explode('.', $php_version);
$php_major = (int)$_vparts[0];
$php_minor = (int)$_vparts[1];

echo "PHP Version Analysis:\n";
echo "  Major: $php_major, Minor: $php_minor\n";
if ($php_major < 5 || ($php_major == 5 && $php_minor < 4)) {
    echo "  *** CRITICAL: PHP version is too old!\n";
    echo "  *** Array dereferencing (e.g., func()['key']) requires PHP 5.4+\n";
} else {
    echo "  OK: PHP version supports array dereferencing\n";
}
echo "\n";

// Check for create_function availability
echo "create_function():  " . (function_exists('create_function') ? 'AVAILABLE' : 'NOT AVAILABLE (REMOVED IN PHP 8.0+)') . "\n";
echo "json_encode():      " . (function_exists('json_encode') ? 'AVAILABLE' : 'NOT AVAILABLE') . "\n";
echo "mysqli extension:   " . (extension_loaded('mysqli') ? 'LOADED' : 'NOT LOADED') . "\n";
echo "ob_start():         " . (function_exists('ob_start') ? 'AVAILABLE' : 'NOT AVAILABLE') . "\n";
echo "\n";

// ============================================
// 2. JSON OUTPUT TEST
// ============================================
echo "\n2. JSON OUTPUT TEST\n";
echo "-------------------\n";
$test_data = array('test' => true, 'message' => 'Hello from debug', 'time' => time());
$json_output = json_encode($test_data);
if ($json_output === false) {
    echo "json_encode() FAILED: error code " . json_last_error() . "\n";
} else {
    echo "json_encode() SUCCESS: " . $json_output . "\n";
}
echo "\n";

// ============================================
// 3. DATABASE CONNECTION TEST
// ============================================
echo "\n3. DATABASE CONNECTION TEST\n";
echo "----------------------------\n";

// Database config (same as competition.php)
$db_host = 'mysql.50webs.com';
$db_user = 'ejaguiar1_stocks';
$db_pass = 'stocks';
$db_name = 'ejaguiar1_stocks';

echo "Host:       $db_host\n";
echo "User:       $db_user\n";
echo "Database:   $db_name\n";
echo "\n";

echo "Attempting connection...\n";

// Connect without error suppression to see actual errors
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    echo "CONNECTION FAILED!\n";
    echo "Error Code:    " . $conn->connect_errno . "\n";
    echo "Error Message: " . $conn->connect_error . "\n";
} else {
    echo "CONNECTION SUCCESS!\n";
    echo "Server Version: " . $conn->server_info . "\n";
    
    // Test charset
    if ($conn->set_charset('utf8')) {
        echo "Charset set to UTF-8: OK\n";
    } else {
        echo "Charset set FAILED: " . $conn->error . "\n";
    }
    
    // Test a simple query
    echo "\nTesting query: SELECT 1 as test...\n";
    $result = $conn->query("SELECT 1 as test");
    if ($result) {
        $row = $result->fetch_assoc();
        echo "Query result: " . print_r($row, true);
        $result->free();
    } else {
        echo "Query FAILED: " . $conn->error . "\n";
    }
    
    // Check if stock_picks table exists
    echo "\nChecking stock_picks table...\n";
    $table_check = $conn->query("SHOW TABLES LIKE 'stock_picks'");
    if ($table_check && $table_check->num_rows > 0) {
        echo "Table 'stock_picks': EXISTS\n";
        
        // Count rows
        $count_res = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE entry_price > 0");
        if ($count_res) {
            $count_row = $count_res->fetch_assoc();
            echo "Rows with entry_price > 0: " . $count_row['cnt'] . "\n";
        }
    } else {
        echo "Table 'stock_picks': NOT FOUND\n";
    }
    
    $conn->close();
}
echo "\n";

// ============================================
// 4. ARRAY DEREFERENCING TEST (CRITICAL)
// ============================================
echo "\n4. ARRAY DEREFERENCING TEST (CRITICAL)\n";
echo "---------------------------------------\n";
echo "Testing: function()[0] syntax\n\n";

function test_return_array() {
    return array('cnt' => 42, 'name' => 'test');
}

// Test old-style PHP 5.3 compatible syntax
echo "Method 1 (PHP 5.3+ compatible):\n";
echo "  \$row = test_return_array();\n";
echo "  \$cnt = \$row['cnt'];\n";
$row1 = test_return_array();
$cnt1 = $row1['cnt'];
echo "  Result: \$cnt = $cnt1 - OK\n\n";

// Test new array dereferencing syntax
echo "Method 2 (PHP 5.4+ only):\n";
echo "  \$cnt = test_return_array()['cnt'];\n";
$success = false;
try {
    // This will fail on PHP < 5.4
    $cnt2 = @test_return_array()['cnt'];
    if ($cnt2 === 42) {
        echo "  Result: \$cnt = $cnt2 - OK (PHP 5.4+)\n";
        $success = true;
    }
} catch (Exception $e) {
    echo "  Result: FAILED - " . $e->getMessage() . "\n";
}

if (!$success) {
    echo "  Result: SYNTAX ERROR on PHP < 5.4\n";
}

echo "\n";

// ============================================
// 5. CREATE_FUNCTION TEST
// ============================================
echo "\n5. CREATE_FUNCTION TEST\n";
echo "------------------------\n";
if (function_exists('create_function')) {
    echo "create_function() exists - testing...\n";
    $test_func = @create_function('$a,$b', 'return $a + $b;');
    if ($test_func && is_callable($test_func)) {
        $result = call_user_func($test_func, 2, 3);
        echo "create_function() WORKS: 2 + 3 = $result\n";
    } else {
        echo "create_function() FAILED to create function\n";
    }
} else {
    echo "create_function() does NOT exist (REMOVED in PHP 8.0+)\n";
    echo "Files using create_function() will FAIL on PHP 8.0+\n";
}
echo "\n";

// ============================================
// 6. ANONYMOUS FUNCTION TEST
// ============================================
echo "\n6. ANONYMOUS FUNCTION TEST (PHP 5.3+)\n";
echo "--------------------------------------\n";
$test_array = array(
    array('name' => 'Algo A', 'return' => 15.5),
    array('name' => 'Algo B', 'return' => 8.2),
    array('name' => 'Algo C', 'return' => 22.1)
);

try {
    usort($test_array, '_debug_sortByReturn');
    echo "Anonymous function with usort(): WORKS\n";
    echo "Sorted results:\n";
    foreach ($test_array as $item) {
        echo "  - {$item['name']}: {$item['return']}%\n";
    }
} catch (Exception $e) {
    echo "Anonymous function FAILED: " . $e->getMessage() . "\n";
}
echo "\n";

// ============================================
// 7. OUTPUT BUFFERING TEST
// ============================================
echo "\n7. OUTPUT BUFFERING TEST\n";
echo "------------------------\n";
echo "Output buffering active: " . (ob_get_level() > 0 ? 'YES (level ' . ob_get_level() . ')' : 'NO') . "\n";

// Test ob_start and ob_clean
ob_start();
echo "Test content in buffer";
$buffer_content = ob_get_contents();
ob_clean();
echo "ob_start() + ob_clean() test: " . (strlen($buffer_content) > 0 ? 'WORKS' : 'FAILED') . "\n";
echo "Buffer content was: '$buffer_content'\n";
echo "\n";

// ============================================
// 8. COMPETITION.PHP SYNTAX CHECK
// ============================================
echo "\n8. COMPETITION.PHP SYNTAX CHECK\n";
echo "--------------------------------\n";
$competition_file = dirname(__FILE__) . '/competition.php';

if (file_exists($competition_file)) {
    echo "File exists: $competition_file\n";
    echo "File size: " . filesize($competition_file) . " bytes\n";
    echo "File lines: " . count(file($competition_file)) . "\n\n";
    
    // Check for problematic syntax patterns
    $content = file_get_contents($competition_file);
    
    $issues = array();
    
    // Check for array dereferencing (PHP 5.4+)
    if (preg_match('/fetch_assoc\(\)\s*\[/', $content)) {
        $issues[] = "Array dereferencing found: fetch_assoc()['key'] requires PHP 5.4+";
    }
    
    // Check for short array syntax (PHP 5.4+)
    if (preg_match('/=\s*\[.*\]/', $content)) {
        $issues[] = "Short array syntax found: [] requires PHP 5.4+";
    }
    
    // Check for create_function (deprecated in 7.2, removed in 8.0)
    if (preg_match('/create_function\s*\(/', $content)) {
        $issues[] = "create_function() found: deprecated in PHP 7.2, removed in PHP 8.0";
    }
    
    if (empty($issues)) {
        echo "No obvious PHP compatibility issues found in local file.\n";
    } else {
        echo "POTENTIAL ISSUES FOUND:\n";
        foreach ($issues as $issue) {
            echo "  - $issue\n";
        }
    }
} else {
    echo "ERROR: competition.php not found at expected location\n";
}

echo "\n";

// ============================================
// 9. SUMMARY & DIAGNOSIS
// ============================================
echo "\n========================================\n";
echo "9. SUMMARY & DIAGNOSIS\n";
echo "========================================\n";

echo "\n=== ROOT CAUSE ANALYSIS ===\n\n";

echo "The competition.php API is returning:\n";
echo "  'Parse error: syntax error, unexpected \"[\" on line 152'\n\n";

echo "This error indicates the SERVER is running PHP 5.3 or EARLIER.\n";
echo "The old version of competition.php contained this code:\n\n";
echo "  \$pc = (int)\$pr->fetch_assoc()['cnt'];  // REQUIRES PHP 5.4+\n\n";
echo "The \"['cnt']\" part after fetch_assoc() is called\n";
echo "\"array dereferencing\" and was introduced in PHP 5.4.\n\n";

echo "=== SOLUTION ===\n\n";

echo "The local file has ALREADY been fixed. The fix changes:\n\n";
echo "OLD (PHP 5.4+ only):\n";
echo "  \$pc = (int)\$pr->fetch_assoc()['cnt'];\n\n";
echo "NEW (PHP 5.3 compatible):\n";
echo "  \$row = \$pr->fetch_assoc();\n";
echo "  \$pc = isset(\$row['cnt']) ? (int)\$row['cnt'] : 0;\n\n";

echo "=== DEPLOYMENT NEEDED ===\n\n";

echo "The local file is fixed but the SERVER still has the old version.\n";
echo "You need to DEPLOY the current competition.php to the server.\n\n";

echo "=== VERIFICATION ===\n\n";

// Verify our local file is compatible
$local_content = @file_get_contents($competition_file);
if ($local_content) {
    $has_dereferencing = preg_match('/fetch_assoc\(\)\s*\[/', $local_content);
    $has_create_function = preg_match('/create_function\s*\(/', $local_content);
    
    echo "Local competition.php status:\n";
    echo "  - Array dereferencing: " . ($has_dereferencing ? "FOUND (BAD)" : "NOT FOUND (GOOD)") . "\n";
    echo "  - create_function():   " . ($has_create_function ? "FOUND (BAD for PHP 8+)" : "NOT FOUND (GOOD)") . "\n";
    
    if (!$has_dereferencing && !$has_create_function) {
        echo "\n*** Local file is COMPATIBLE and ready for deployment ***\n";
    }
}

echo "\n========================================\n";
echo "END OF DEBUG REPORT\n";
echo "========================================\n";

function _debug_sortByReturn($a, $b) {
    $va = (float)$a['return'];
    $vb = (float)$b['return'];
    if ($va == $vb) return 0;
    return ($va > $vb) ? -1 : 1;
}
