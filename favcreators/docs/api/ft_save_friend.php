<?php
/**
 * FriendTracker: Create or update a friend.
 * Accepts POST with friend data, validates, saves to friendt_friends.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once dirname(__FILE__) . '/session_auth.php';
$user_id = get_session_user_id();
if ($user_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized', 'require' => 'login'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['name']) || trim($data['name']) === '') {
    echo json_encode(array('error' => 'Invalid input: name is required'));
    exit;
}

// Extract and validate friend data
$friend_id = isset($data['id']) ? $conn->real_escape_string($data['id']) : '';
if ($friend_id === '') {
    // Generate new ID if not provided
    $friend_id = 'ft_' . time() . '_' . rand(1000, 9999);
}

// Map JS camelCase to DB snake_case
$name = $conn->real_escape_string(trim($data['name']));
$nickname = isset($data['nickname']) ? $conn->real_escape_string(trim($data['nickname'])) : '';
$birthday = isset($data['birthday']) && $data['birthday'] ? $conn->real_escape_string($data['birthday']) : null;
$how_met = isset($data['howMet']) ? $conn->real_escape_string(trim($data['howMet'])) : '';
$notes = isset($data['notes']) ? $conn->real_escape_string(trim($data['notes'])) : '';
$phone = isset($data['phone']) ? $conn->real_escape_string(trim($data['phone'])) : '';
$email = isset($data['email']) ? $conn->real_escape_string(trim($data['email'])) : '';
$instagram = isset($data['instagram']) ? $conn->real_escape_string(trim($data['instagram'])) : '';
$tiktok = isset($data['tiktok']) ? $conn->real_escape_string(trim($data['tiktok'])) : '';
$twitter = isset($data['twitter']) ? $conn->real_escape_string(trim($data['twitter'])) : '';
$snapchat = isset($data['snapchat']) ? $conn->real_escape_string(trim($data['snapchat'])) : '';
$linkedin = isset($data['linkedin']) ? $conn->real_escape_string(trim($data['linkedin'])) : '';
$other_social = isset($data['otherSocial']) ? $conn->real_escape_string(trim($data['otherSocial'])) : '';

// Tags: array to JSON
$tags = isset($data['tags']) && is_array($data['tags']) ? $conn->real_escape_string(json_encode($data['tags'])) : '[]';

// Cadence days
$cadence_days = isset($data['cadenceDays']) && $data['cadenceDays'] ? (int)$data['cadenceDays'] : null;

// Determine if this is an update or insert
$existing_check = $conn->query("SELECT id FROM friendt_friends WHERE id = '$friend_id' AND user_id = $user_id");
$is_update = ($existing_check && $existing_check->num_rows > 0);

if ($is_update) {
    // Update existing friend
    $sql = "UPDATE friendt_friends SET
        name = '$name',
        nickname = '$nickname',
        birthday = " . ($birthday ? "'$birthday'" : "NULL") . ",
        how_met = '$how_met',
        notes = '$notes',
        phone = '$phone',
        email = '$email',
        instagram = '$instagram',
        tiktok = '$tiktok',
        twitter = '$twitter',
        snapchat = '$snapchat',
        linkedin = '$linkedin',
        other_social = '$other_social',
        tags = '$tags',
        cadence_days = " . ($cadence_days ? $cadence_days : "NULL") . ",
        updated_at = CURRENT_TIMESTAMP
        WHERE id = '$friend_id' AND user_id = $user_id";
} else {
    // Insert new friend
    $sql = "INSERT INTO friendt_friends (
        id, user_id, name, nickname, birthday, how_met, notes,
        phone, email, instagram, tiktok, twitter, snapchat, linkedin, other_social,
        tags, cadence_days, created_at, updated_at
    ) VALUES (
        '$friend_id',
        $user_id,
        '$name',
        '$nickname',
        " . ($birthday ? "'$birthday'" : "NULL") . ",
        '$how_met',
        '$notes',
        '$phone',
        '$email',
        '$instagram',
        '$tiktok',
        '$twitter',
        '$snapchat',
        '$linkedin',
        '$other_social',
        '$tags',
        " . ($cadence_days ? $cadence_days : "NULL") . ",
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )";
}

if (!$conn->query($sql)) {
    $error_msg = $conn->error;
    echo json_encode(array('error' => 'Database error: ' . $error_msg, 'sql' => $sql));
    $conn->close();
    exit;
}

// Retrieve the saved friend to return
$result = $conn->query("SELECT * FROM friendt_friends WHERE id = '$friend_id' AND user_id = $user_id");
if (!$result || $result->num_rows === 0) {
    echo json_encode(array('error' => 'Friend saved but could not retrieve'));
    $conn->close();
    exit;
}

$row = $result->fetch_assoc();
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

// Also fetch hangouts for this friend
$hangouts_query = $conn->query("SELECT id, date, activity, notes, created_at FROM friendt_hangouts WHERE friend_id = '$friend_id' AND user_id = $user_id ORDER BY date DESC");
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

echo json_encode(array(
    'status' => 'success',
    'friend' => $friend,
    'isUpdate' => $is_update,
    'message' => $is_update ? 'Friend updated successfully' : 'Friend added successfully'
));

$conn->close();
?>