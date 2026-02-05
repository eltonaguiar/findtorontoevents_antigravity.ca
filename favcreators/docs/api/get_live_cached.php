<?php
/**
 * Get cached live status from database
 * Returns cached live creator data for quick display
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');
header('Access-Control-Allow-Headers: Content-Type');

require_once __DIR__ . '/../db_config.php';

try {
    $pdo = getDBConnection();
    
    // Get creators who are currently live (checked within last 5 minutes)
    $fiveMinutesAgo = date('Y-m-d H:i:s', strtotime('-5 minutes'));
    
    $stmt = $pdo->prepare("
        SELECT 
            creator_id,
            creator_name,
            avatar_url,
            platform,
            username,
            is_live,
            stream_title,
            viewer_count,
            started_at,
            checked_at
        FROM streamer_live_cache
        WHERE is_live = 1 
        AND checked_at >= :fiveMinutesAgo
        ORDER BY started_at DESC
    ");
    
    $stmt->execute(array(':fiveMinutesAgo' => $fiveMinutesAgo));
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // Group by creator
    $creators = array();
    foreach ($rows as $row) {
        $id = $row['creator_id'];
        if (!isset($creators[$id])) {
            $creators[$id] = array(
                'id' => $id,
                'name' => $row['creator_name'],
                'avatarUrl' => $row['avatar_url'],
                'platforms' => array()
            );
        }
        $creators[$id]['platforms'][] = array(
            'platform' => $row['platform'],
            'username' => $row['username'],
            'isLive' => (bool)$row['is_live'],
            'streamTitle' => $row['stream_title'],
            'viewerCount' => $row['viewer_count'] ? (int)$row['viewer_count'] : null,
            'startedAt' => $row['started_at'],
            'checkedAt' => $row['checked_at']
        );
    }
    
    echo json_encode(array(
        'ok' => true,
        'liveNow' => array_values($creators),
        'count' => count($creators),
        'cachedAt' => date('Y-m-d H:i:s')
    ));
    
} catch (PDOException $e) {
    error_log("Database error in get_live_cached.php: " . $e->getMessage());
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'ok' => false,
        'error' => 'Database error',
        'liveNow' => array()
    ));
} catch (Exception $e) {
    error_log("Error in get_live_cached.php: " . $e->getMessage());
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'ok' => false,
        'error' => 'Server error',
        'liveNow' => array()
    ));
}