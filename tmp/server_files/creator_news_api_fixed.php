<?php
// Creator News API - Returns aggregated content ABOUT creators
// Compatible with PHP 5.2 through 8.x
// Includes UTF-8 sanitizer for scraped content with Windows-1252 characters
// Path: /torontoevent.net/fc/api/creator_news_api.php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit();
}

/**
 * Recursively sanitize strings to valid UTF-8.
 * Replaces Windows-1252 smart quotes/special chars with UTF-8 equivalents.
 */
function _sanitize_utf8_news($data) {
    if (is_array($data)) {
        $out = array();
        foreach ($data as $k => $v) {
            $out[$k] = _sanitize_utf8_news($v);
        }
        return $out;
    }
    if (!is_string($data)) return $data;
    $win1252_map = array(
        "\x80" => "\xE2\x82\xAC",
        "\x85" => "\xE2\x80\xA6",
        "\x91" => "\xE2\x80\x98",
        "\x92" => "\xE2\x80\x99",
        "\x93" => "\xE2\x80\x9C",
        "\x94" => "\xE2\x80\x9D",
        "\x95" => "\xE2\x80\xA2",
        "\x96" => "\xE2\x80\x93",
        "\x97" => "\xE2\x80\x94",
        "\x99" => "\xE2\x84\xA2",
    );
    $data = strtr($data, $win1252_map);
    if (function_exists('mb_convert_encoding')) {
        $data = mb_convert_encoding($data, 'UTF-8', 'UTF-8');
    }
    $data = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', '', $data);
    return $data;
}

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

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

// Build query
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

if ($platform && $platform !== 'all') {
    $platform_safe = $conn->real_escape_string($platform);
    $sql .= " AND cm.platform = '$platform_safe'";
}

if ($creator_id) {
    $creator_id_safe = $conn->real_escape_string($creator_id);
    $sql .= " AND cm.creator_id = '$creator_id_safe'";
}

$sql .= " ORDER BY cm.posted_at DESC LIMIT $limit OFFSET $offset";

$result = $conn->query($sql);

if (!$result) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'error' => 'Database error',
        'message' => $conn->error
    ));
    $conn->close();
    exit;
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
        'publishedAt' => intval($row['posted_at']) * 1000
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

// Sanitize UTF-8 before encoding (fixes Windows-1252 chars in scraped content)
$response = _sanitize_utf8_news(array(
    'items' => $items,
    'total' => $total,
    'user_id' => $user_id
));

if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
    echo json_encode($response, JSON_INVALID_UTF8_SUBSTITUTE);
} else {
    echo json_encode($response);
}

$conn->close();
?>