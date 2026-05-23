<?php
/**
 * FriendTracker: Get all friends and hangouts for the logged-in user.
 * Returns friends array with nested hangouts.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Pragma: no-cache");

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
    exit;
}

// Ensure tables exist
require_once dirname(__FILE__) . '/ensure_tables.php';

$response = array('friends' => array(), 'hangouts' => array());

// Get all friends for this user
$friends_query = $conn->query("
    SELECT 
        id, name, nickname, birthday, how_met, notes,
        phone, email, instagram, tiktok, twitter, snapchat, linkedin, other_social,
        tags, cadence_days, created_at, updated_at
    FROM friendt_friends 
    WHERE user_id = $user_id 
    ORDER BY name ASC
");

if ($friends_query) {
    while ($row = $friends_query->fetch_assoc()) {
        $friend = array(
            'id' => $row['id'],
            'name' => $row['name'],
            'nickname' => $row['nickname'],
            'birthday' => $row['birthday'],
            'howMet' => $row['how_met'],
            'notes' => $row['notes'],
            'phone' => $row['phone'],
            'email' => $row['email'],
            'instagram' => $row['instagram'],
            'tiktok' => $row['tiktok'],
            'twitter' => $row['twitter'],
            'snapchat' => $row['snapchat'],
            'linkedin' => $row['linkedin'],
            'otherSocial' => $row['other_social'],
            'tags' => json_decode($row['tags'], true) ?: array(),
            'cadenceDays' => $row['cadence_days'] ? (int)$row['cadence_days'] : null,
            'createdAt' => $row['created_at'],
            'updatedAt' => $row['updated_at'],
            'hangouts' => array()
        );
        
        // Get hangouts for this friend
        $friend_id = $conn->real_escape_string($row['id']);
        $hangouts_query = $conn->query("
            SELECT id, date, activity, notes, created_at
            FROM friendt_hangouts 
            WHERE friend_id = '$friend_id' AND user_id = $user_id 
            ORDER BY date DESC
        ");
        
        if ($hangouts_query) {
            while ($hangout = $hangouts_query->fetch_assoc()) {
                $friend['hangouts'][] = array(
                    'id' => $hangout['id'],
                    'date' => $hangout['date'],
                    'activity' => $hangout['activity'],
                    'notes' => $hangout['notes'],
                    'createdAt' => $hangout['created_at']
                );
            }
        }
        
        $response['friends'][] = $friend;
    }
}

// Also provide hangouts aggregated by friend ID for easy lookup
$response['hangouts'] = array();
foreach ($response['friends'] as $friend) {
    $response['hangouts'][$friend['id']] = $friend['hangouts'];
}

echo json_encode($response, JSON_PRETTY_PRINT);
$conn->close();
?>