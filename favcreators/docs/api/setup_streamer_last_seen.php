<?php
/**
 * Setup script for streamer_last_seen tracking feature.
 * Run this once to create the necessary database tables.
 * 
 * GET /api/setup_streamer_last_seen.php
 * GET /api/setup_streamer_last_seen.php?debug=1
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';
require_once 'streamer_last_seen_schema.php';

$debug = isset($_GET['debug']) && $_GET['debug'] == '1';

// Verify tables exist
$tables_to_check = array('streamer_last_seen', 'streamer_check_log');
$results = array();

foreach ($tables_to_check as $table) {
    $result = $conn->query("SHOW TABLES LIKE '$table'");
    $exists = $result && $result->num_rows > 0;
    
    $results[$table] = array(
        'exists' => $exists,
        'row_count' => 0
    );
    
    if ($exists && $debug) {
        $count_result = $conn->query("SELECT COUNT(*) as cnt FROM $table");
        if ($count_result) {
            $row = $count_result->fetch_assoc();
            $results[$table]['row_count'] = $row['cnt'];
        }
        
        // Get table structure
        $structure_result = $conn->query("DESCRIBE $table");
        if ($structure_result) {
            $columns = array();
            while ($col = $structure_result->fetch_assoc()) {
                $columns[] = $col['Field'] . ' (' . $col['Type'] . ')';
            }
            $results[$table]['columns'] = $columns;
        }
    }
}

echo json_encode(array(
    'ok' => true,
    'message' => 'Streamer last seen tracking tables setup complete',
    'tables' => $results,
    'endpoints' => array(
        'get_streamer_last_seen' => '/api/get_streamer_last_seen.php',
        'update_streamer_last_seen' => '/api/update_streamer_last_seen.php (POST)',
        'batch_update_streamer_last_seen' => '/api/batch_update_streamer_last_seen.php (POST)',
        'cleanup_old_records' => '/api/cleanup_streamer_last_seen.php'
    ),
    'usage' => array(
        'get_recent' => 'GET /api/get_streamer_last_seen.php?since_minutes=60',
        'get_live_now' => 'GET /api/get_streamer_last_seen.php?live_only=1',
        'update_single' => 'POST /api/update_streamer_last_seen.php with JSON body',
        'batch_update' => 'POST /api/batch_update_streamer_last_seen.php with JSON body'
    )
));

$conn->close();
?>