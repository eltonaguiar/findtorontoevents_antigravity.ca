<?php
// Database connection for predictions dashboard
// Using simplified connection for testing

$host = 'localhost';
$dbname = 'antigravity';  // Default database name
$user = 'root';  // Default username
$pass = '';      // Default password

// Try to connect
try {
    $conn = new mysqli($host, $user, $pass, $dbname);
    if ($conn->connect_error) {
        // Log connection error
        file_put_contents('db_connect_error.log', date('Y-m-d H:i:s') . " - Connection failed: " . $conn->connect_error . "\n", FILE_APPEND);
        
        // Create a mock connection object for fallback
        class MockConnection {
            public function query($sql) { 
                file_put_contents('db_query.log', date('Y-m-d H:i:s') . " - Mock query: " . substr($sql, 0, 100) . "\n", FILE_APPEND);
                return new MockResult();
            }
            public function set_charset($charset) { return true; }
        }
        
        class MockResult {
            public function fetch_assoc() { return false; }
        }
        
        $conn = new MockConnection();
    } else {
        $conn->set_charset('utf8');
        file_put_contents('db_connect_success.log', date('Y-m-d H:i:s') . " - Connection successful\n", FILE_APPEND);
    }
} catch (Exception $e) {
    file_put_contents('db_connect_error.log', date('Y-m-d H:i:s') . " - Exception: " . $e->getMessage() . "\n", FILE_APPEND);
    
    // Create mock connection
    class MockConnection {
        public function query($sql) { 
            file_put_contents('db_query.log', date('Y-m-d H:i:s') . " - Mock query: " . substr($sql, 0, 100) . "\n", FILE_APPEND);
            return new MockResult();
        }
        public function set_charset($charset) { return true; }
    }
    
    class MockResult {
        public function fetch_assoc() { return false; }
    }
    
    $conn = new MockConnection();
}
?>