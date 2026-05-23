<?php
/**
 * API endpoint to get streamer last seen status.
 * PHP 5.2 compatible version (without get_result())
 */

error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

// Ensure table exists
$create_sql = "CREATE TABLE IF NOT EXISTS streamer_last_seen (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    creator_name VARCHAR(255) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(255) NOT NULL,
    account_url VARCHAR(1024) DEFAULT '',
    is_live TINYINT(1) DEFAULT 0,
    last_seen_online DATETIME,
    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    stream_title VARCHAR(512) DEFAULT '',
    viewer_count INT DEFAULT 0,
    check_count INT DEFAULT 1,
    first_seen_by VARCHAR(255) DEFAULT '',
    UNIQUE KEY uq_creator_platform (creator_id, platform),
    INDEX idx_is_live (is_live),
    INDEX idx_last_seen_online (last_seen_online),
    INDEX idx_last_checked (last_checked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
$conn->query($create_sql);

$creator_id = isset($_GET['creator_id']) ? $conn->real_escape_string($_GET['creator_id']) : null;
$platform = isset($_GET['platform']) ? $conn->real_escape_string($_GET['platform']) : null;
$live_only = isset($_GET['live_only']) && $_GET['live_only'] == '1';
$since_minutes = isset($_GET['since_minutes']) ? intval($_GET['since_minutes']) : 60;

// Use direct query for PHP 5.2 compatibility (without prepared statements for simple queries)
$where_clauses = array();
$params = array();
$types = "";

if ($creator_id) {
    $where_clauses[] = "creator_id = ?";
    $params[] = $creator_id;
    $types .= "s";
}

if ($platform) {
    $where_clauses[] = "platform = ?";
    $params[] = $platform;
    $types .= "s";
}

if ($live_only) {
    $where_clauses[] = "is_live = 1";
}

if ($since_minutes > 0) {
    $where_clauses[] = "(last_seen_online >= DATE_SUB(NOW(), INTERVAL ? MINUTE) OR last_checked >= DATE_SUB(NOW(), INTERVAL ? MINUTE))";
    $params[] = $since_minutes;
    $params[] = $since_minutes;
    $types .= "ii";
}

// Build the SQL query
$sql = "SELECT id, creator_id, creator_name, platform, username, account_url, is_live, 
        last_seen_online, last_checked, stream_title, viewer_count, check_count, first_seen_by 
        FROM streamer_last_seen";

if (count($where_clauses) > 0) {
    $sql .= " WHERE " . implode(" AND ", $where_clauses);
}

$sql .= " ORDER BY last_seen_online DESC, last_checked DESC";

$streamers = array();

// Execute with or without prepared statement based on params
if (count($params) > 0) {
    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        echo json_encode(array('ok' => false, 'error' => 'Prepare failed: ' . $conn->error, 'sql' => $sql));
        exit;
    }
    
    // Bind parameters using references for PHP 5.2
    $bind_params = array_merge(array($types), $params);
    $refs = array();
    foreach ($bind_params as $key => $value) {
        $refs[$key] = &$bind_params[$key];
    }
    call_user_func_array(array($stmt, 'bind_param'), $refs);
    
    $stmt->execute();
    
    // Bind result variables
    $stmt->bind_result($id, $creator_id_val, $creator_name, $platform_val, $username, $account_url, 
                       $is_live, $last_seen_online, $last_checked, $stream_title, $viewer_count, 
                       $check_count, $first_seen_by);
    
    // Fetch results
    while ($stmt->fetch()) {
        $streamers[] = array(
            'id' => $id,
            'creator_id' => $creator_id_val,
            'creator_name' => $creator_name,
            'platform' => $platform_val,
            'username' => $username,
            'account_url' => $account_url,
            'is_live' => $is_live == 1,
            'last_seen_online' => $last_seen_online,
            'last_checked' => $last_checked,
            'stream_title' => $stream_title,
            'viewer_count' => intval($viewer_count),
            'check_count' => intval($check_count),
            'first_seen_by' => $first_seen_by
        );
    }
    
    $stmt->close();
} else {
    // No parameters, use simple query
    $result = $conn->query($sql);
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $streamers[] = array(
                'id' => $row['id'],
                'creator_id' => $row['creator_id'],
                'creator_name' => $row['creator_name'],
                'platform' => $row['platform'],
                'username' => $row['username'],
                'account_url' => $row['account_url'],
                'is_live' => $row['is_live'] == 1,
                'last_seen_online' => $row['last_seen_online'],
                'last_checked' => $row['last_checked'],
                'stream_title' => $row['stream_title'],
                'viewer_count' => intval($row['viewer_count']),
                'check_count' => intval($row['check_count']),
                'first_seen_by' => $row['first_seen_by']
            );
        }
        $result->free();
    }
}

// Get stats
$stats_sql = "SELECT COUNT(*) as total_tracked FROM streamer_last_seen";
$stats_result = $conn->query($stats_sql);
$total_tracked = 0;
if ($stats_result) {
    $row = $stats_result->fetch_assoc();
    if ($row) {
        $total_tracked = intval($row['total_tracked']);
    }
    $stats_result->free();
}

// Build response
$response = array(
    'ok' => true,
    'streamers' => $streamers,
    'stats' => array(
        'total_tracked' => $total_tracked,
        'currently_live' => 0,
        'unique_creators' => 0,
        'last_check_time' => null
    ),
    'query' => array(
        'creator_id' => $creator_id,
        'platform' => $platform,
        'live_only' => $live_only,
        'since_minutes' => $since_minutes
    )
);

echo json_encode($response);
$conn->close();
?>
