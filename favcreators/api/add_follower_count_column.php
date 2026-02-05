<?php
// Add follower_count column to creators table
// Path: /findtorontoevents.ca/fc/api/add_follower_count_column.php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$results = array();

// Check if column exists
$check_sql = "SHOW COLUMNS FROM creators LIKE 'follower_count'";
$check_result = $conn->query($check_sql);

if ($check_result->num_rows == 0) {
    // Column doesn't exist, add it
    $alter_sql = "ALTER TABLE creators ADD COLUMN follower_count INT DEFAULT 0 AFTER name";
    if ($conn->query($alter_sql)) {
        $results['column_added'] = true;
    } else {
        $results['column_added'] = false;
        $results['error'] = $conn->error;
    }
} else {
    $results['column_exists'] = true;
}

// Update known creators with follower counts
$updates = array(
    array('name' => 'Adin Ross', 'count' => 500000),
    array('name' => 'MrBeast', 'count' => 200000000),
    array('name' => 'Starfireara', 'count' => 150000),
    array('name' => 'xQc', 'count' => 2000000),
    array('name' => 'Pokimane', 'count' => 9000000),
    array('name' => 'Ninja', 'count' => 18000000),
    array('name' => 'Shroud', 'count' => 10000000),
    array('name' => 'Summit1g', 'count' => 6000000),
    array('name' => 'DrLupo', 'count' => 4500000),
    array('name' => 'TimTheTatman', 'count' => 7000000)
);

$results['updates'] = array();
foreach ($updates as $update) {
    $name = $conn->real_escape_string($update['name']);
    $count = intval($update['count']);

    $update_sql = "UPDATE creators SET follower_count = $count WHERE name = '$name'";
    if ($conn->query($update_sql)) {
        $results['updates'][] = array(
            'name' => $update['name'],
            'follower_count' => $count,
            'affected_rows' => $conn->affected_rows
        );
    }
}

// Get creators with 50K+ followers
$verify_sql = "SELECT id, name, follower_count FROM creators WHERE follower_count >= 50000 ORDER BY follower_count DESC";
$verify_result = $conn->query($verify_sql);

$results['creators_50k_plus'] = array();
if ($verify_result) {
    while ($row = $verify_result->fetch_assoc()) {
        $results['creators_50k_plus'][] = $row;
    }
}

$results['success'] = true;
echo json_encode($results);

$conn->close();
?>