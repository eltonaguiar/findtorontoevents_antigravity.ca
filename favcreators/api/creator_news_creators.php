<?php
// Get list of creators that have content in creator_mentions
// Path: /findtorontoevents.ca/fc/api/creator_news_creators.php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

// Get user_id parameter
$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

try {
    // Get user's creator list from user_lists table (JSON format)
    $user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
    $user_list_result = $conn->query($user_list_sql);

    if (!$user_list_result || $user_list_result->num_rows === 0) {
        echo json_encode(array('creators' => array(), 'total' => 0));
        $conn->close();
        exit;
    }

    $user_list_row = $user_list_result->fetch_assoc();
    $creators_json = $user_list_row['creators'];
    $creators_data = json_decode($creators_json, true);

    if (!$creators_data || count($creators_data) === 0) {
        echo json_encode(array('creators' => array(), 'total' => 0));
        $conn->close();
        exit;
    }

    // Extract creator IDs from JSON
    $creator_ids = array();
    foreach ($creators_data as $creator) {
        if (isset($creator['id'])) {
            $creator_ids[] = $conn->real_escape_string($creator['id']);
        }
    }

    if (count($creator_ids) === 0) {
        echo json_encode(array('creators' => array(), 'total' => 0));
        $conn->close();
        exit;
    }

    // Get creators with content, filtered by 50K+ followers AND user follows
    $sql = "SELECT DISTINCT 
                c.id,
                c.name,
                c.avatar_url,
                c.follower_count,
                COUNT(cm.id) as content_count
            FROM creators c
            INNER JOIN creator_mentions cm ON c.id = cm.creator_id
            WHERE c.id IN ('" . implode("','", $creator_ids) . "')
              AND c.follower_count >= 50000
            GROUP BY c.id
            ORDER BY content_count DESC";

    $result = $conn->query($sql);

    if (!$result) {
        throw new Exception($conn->error);
    }

    $creators = array();
    while ($row = $result->fetch_assoc()) {
        $creators[] = array(
            'id' => intval($row['id']),
            'name' => $row['name'],
            'avatarUrl' => $row['avatar_url'],
            'followerCount' => intval($row['follower_count']),
            'contentCount' => intval($row['content_count'])
        );
    }

    echo json_encode(array(
        'creators' => $creators,
        'total' => count($creators)
    ));

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(array(
        'error' => 'Database error',
        'message' => $e->getMessage()
    ));
}

$conn->close();
?>