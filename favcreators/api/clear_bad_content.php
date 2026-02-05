<?php
// Clear irrelevant YouTube content
// Path: /findtorontoevents.ca/fc/api/clear_bad_content.php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$results = array();

// Get count before deletion
$count_sql = "SELECT COUNT(*) as total FROM creator_mentions";
$count_result = $conn->query($count_sql);
$before_count = 0;
if ($count_result) {
    $row = $count_result->fetch_assoc();
    $before_count = intval($row['total']);
}
$results['before_count'] = $before_count;

// Delete irrelevant content
// 1. Content with titles that don't match our use case
$bad_titles = array(
    'Frankie and Starfire',
    'Frankie and Starfir',
    'backwards',
    'ara ara',
    'meme',
    'Teaser Trailer',
    'Pico'
);

$deleted_items = array();
foreach ($bad_titles as $bad_title) {
    $title_safe = $conn->real_escape_string($bad_title);
    $delete_sql = "DELETE FROM creator_mentions WHERE title LIKE '%$title_safe%'";
    if ($conn->query($delete_sql)) {
        if ($conn->affected_rows > 0) {
            $deleted_items[] = array(
                'pattern' => $bad_title,
                'deleted' => $conn->affected_rows
            );
        }
    }
}

$results['deleted_by_title'] = $deleted_items;

// 2. Delete content for creators with less than 50K followers
$delete_small_sql = "DELETE cm FROM creator_mentions cm 
                     INNER JOIN creators c ON cm.creator_id = c.id 
                     WHERE c.follower_count < 50000";
if ($conn->query($delete_small_sql)) {
    $results['deleted_small_creators'] = $conn->affected_rows;
}

// Get count after deletion
$count_result2 = $conn->query($count_sql);
$after_count = 0;
if ($count_result2) {
    $row = $count_result2->fetch_assoc();
    $after_count = intval($row['total']);
}
$results['after_count'] = $after_count;
$results['total_deleted'] = $before_count - $after_count;

// Get remaining content
$remaining_sql = "SELECT cm.id, cm.title, c.name as creator_name, c.follower_count 
                  FROM creator_mentions cm 
                  INNER JOIN creators c ON cm.creator_id = c.id 
                  ORDER BY cm.posted_at DESC 
                  LIMIT 10";
$remaining_result = $conn->query($remaining_sql);

$results['remaining_content'] = array();
if ($remaining_result) {
    while ($row = $remaining_result->fetch_assoc()) {
        $results['remaining_content'][] = $row;
    }
}

$results['success'] = true;
echo json_encode($results);

$conn->close();
?>