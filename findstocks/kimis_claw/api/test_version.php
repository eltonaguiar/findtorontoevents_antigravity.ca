<?php
header('Content-Type: text/plain');
echo "PHP Version: " . PHP_VERSION . "\n";
echo "PHP Major Version: " . PHP_MAJOR_VERSION . "\n";
echo "Server Software: " . ($_SERVER['SERVER_SOFTWARE'] ?? 'unknown') . "\n";

// Test array dereferencing
function test_array() {
    return array('test' => 123);
}

// This syntax requires PHP 5.4+
$value = test_array()['test'];
echo "Array dereferencing test: " . $value . "\n";

// Test create_function
if (function_exists('create_function')) {
    echo "create_function: EXISTS\n";
} else {
    echo "create_function: NOT EXISTS (PHP 8.0+)\n";
}

echo "All tests passed!\n";
