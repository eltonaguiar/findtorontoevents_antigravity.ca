<?php
/**
 * User Preferences API
 * Manages user preferences: rewatch, autoplay, sound settings
 */

require_once 'db-config.php';

function getUserId()
{
    session_start();
    return $_SESSION['user_id'] ?? null;
}

/**
 * Get user preferences
 */
function getPreferences($pdo, $userId)
{
    $sql = "SELECT * FROM user_preferences WHERE user_id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$userId]);
    $prefs = $stmt->fetch();

    // Return defaults if not found
    if (!$prefs) {
        $prefs = [
            'user_id' => $userId,
            'rewatch_enabled' => true,
            'auto_play' => true,
            'sound_on_scroll' => true
        ];
    }

    sendJson($prefs);
}

/**
 * Update user preferences
 */
function updatePreferences($pdo, $userId)
{
    $data = getRequestBody();

    // Check if preferences exist
    $checkSql = "SELECT user_id FROM user_preferences WHERE user_id = ?";
    $checkStmt = $pdo->prepare($checkSql);
    $checkStmt->execute([$userId]);
    $exists = $checkStmt->fetch();

    if ($exists) {
        // Update
        $updates = [];
        $params = [];

        if (isset($data['rewatch_enabled'])) {
            $updates[] = "rewatch_enabled = ?";
            $params[] = $data['rewatch_enabled'] ? 1 : 0;
        }

        if (isset($data['auto_play'])) {
            $updates[] = "auto_play = ?";
            $params[] = $data['auto_play'] ? 1 : 0;
        }

        if (isset($data['sound_on_scroll'])) {
            $updates[] = "sound_on_scroll = ?";
            $params[] = $data['sound_on_scroll'] ? 1 : 0;
        }

        if (empty($updates)) {
            sendError('No updates provided', 400);
        }

        $params[] = $userId;
        $sql = "UPDATE user_preferences SET " . implode(', ', $updates) . " WHERE user_id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);

    } else {
        // Insert
        $sql = "INSERT INTO user_preferences (user_id, rewatch_enabled, auto_play, sound_on_scroll) 
                VALUES (?, ?, ?, ?)";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            $userId,
            $data['rewatch_enabled'] ?? true,
            $data['auto_play'] ?? true,
            $data['sound_on_scroll'] ?? true
        ]);
    }

    sendJson(['message' => 'Preferences updated']);
}

// Main request handler
$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$userId = getUserId();
if (!$userId) {
    sendError('Authentication required', 401);
}

$method = $_SERVER['REQUEST_METHOD'];

switch ($method) {
    case 'GET':
        getPreferences($pdo, $userId);
        break;

    case 'PUT':
    case 'POST':
        updatePreferences($pdo, $userId);
        break;

    default:
        sendError('Method not allowed', 405);
}
