<?php
// Creator News API - Returns aggregated content ABOUT creators
// Simplified version for PHP 5.2 compatibility

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

try {
    // Get parameters
    $user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;
    $limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 100) : 50;
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
    $platform = isset($_GET['platform']) ? $_GET['platform'] : null;
    $creator_id = isset($_GET['creator_id']) ? intval($_GET['creator_id']) : null;

    // Get user's creator list from user_lists table (JSON format)
    $user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
    $user_list_result = $conn->query($user_list_sql);

    if (!$user_list_result || $user_list_result->num_rows === 0) {
        // User has no creators, return empty
        echo json_encode(array(
            'items' => array(),
            'total' => 0,
            'user_id' => $user_id
        ));
        $conn->close();
        exit;
    }

    $user_list_row = $user_list_result->fetch_assoc();
    $creators_json = $user_list_row['creators'];
    $creators_data = json_decode($creators_json, true);

    if (!$creators_data || count($creators_data) === 0) {
        // No creators in list
        echo json_encode(array(
            'items' => array(),
            'total' => 0,
            'user_id' => $user_id
        ));
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
        echo json_encode(array(
            'items' => array(),
            'total' => 0,
            'user_id' => $user_id
        ));
        $conn->close();
        exit;
    }

    // Build simple query without prepared statements for now
    $sql = "SELECT 
                cm.id,
                cm.platform,
                cm.content_type,
                cm.content_url,
                cm.title,
                cm.description,
                cm.thumbnail_url,
                cm.author,
                cm.engagement_count,
                cm.posted_at,
                c.id as creator_id,
                c.name as creator_name,
                c.avatar_url as creator_avatar
            FROM creator_mentions cm
            INNER JOIN creators c ON cm.creator_id = c.id
            WHERE c.id IN ('" . implode("','", $creator_ids) . "')
              AND c.follower_count >= 50000";

    // Add platform filter
    if ($platform && $platform !== 'all') {
        $platform_safe = $conn->real_escape_string($platform);
        $sql .= " AND cm.platform = '$platform_safe'";
    }

    // Add creator filter
    if ($creator_id) {
        $creator_id_safe = $conn->real_escape_string($creator_id);
        $sql .= " AND cm.creator_id = '$creator_id_safe'";
    }

    $sql .= " ORDER BY cm.posted_at DESC LIMIT $limit OFFSET $offset";

    $result = $conn->query($sql);

    if (!$result) {
        throw new Exception($conn->error);
    }

    // Format results
    $items = array();
    while ($row = $result->fetch_assoc()) {
        $items[] = array(
            'id' => intval($row['id']),
            'creator' => array(
                'id' => intval($row['creator_id']),
                'name' => $row['creator_name'],
                'avatarUrl' => $row['creator_avatar']
            ),
            'platform' => $row['platform'],
            'contentType' => $row['content_type'],
            'contentUrl' => $row['content_url'],
            'title' => $row['title'],
            'description' => $row['description'],
            'thumbnailUrl' => $row['thumbnail_url'],
            'author' => $row['author'],
            'engagementCount' => intval($row['engagement_count']),
            'publishedAt' => intval($row['posted_at']) * 1000  // Convert to milliseconds for JavaScript
        );
    }

    // Get total count
    $count_sql = "SELECT COUNT(*) as total
                  FROM creator_mentions cm
                  INNER JOIN creators c ON cm.creator_id = c.id
                  WHERE c.id IN ('" . implode("','", $creator_ids) . "')
                    AND c.follower_count >= 50000";
    if ($platform && $platform !== 'all') {
        $platform_safe = $conn->real_escape_string($platform);
        $count_sql .= " AND cm.platform = '$platform_safe'";
    }
    if ($creator_id) {
        $creator_id_safe = $conn->real_escape_string($creator_id);
        $count_sql .= " AND cm.creator_id = '$creator_id_safe'";
    }

    $count_result = $conn->query($count_sql);
    $total = 0;
    if ($count_result) {
        $count_row = $count_result->fetch_assoc();
        $total = intval($count_row['total']);
    }

    echo json_encode(array(
        'items' => $items,
        'total' => $total,
        'user_id' => $user_id
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