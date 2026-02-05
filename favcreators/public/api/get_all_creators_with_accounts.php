<?php
/**
 * API endpoint to get all creators with their social accounts.
 * Used by GitHub Actions to check live status for all creators.
 * Fetches from all user lists and aggregates unique creators.
 * 
 * GET /api/get_all_creators_with_accounts.php
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

// Aggregate all creators from all user lists
$all_creators = array();
$seen_ids = array();

// Get all user lists
$user_lists_query = $conn->query("SELECT user_id, creators FROM user_lists");

if ($user_lists_query) {
    while ($row = $user_lists_query->fetch_assoc()) {
        $creators_json = $row['creators'];
        $creators = json_decode($creators_json, true);
        
        if (is_array($creators)) {
            foreach ($creators as $creator) {
                $id = isset($creator['id']) ? $creator['id'] : '';
                if ($id === '' || isset($seen_ids[$id])) continue;
                
                $seen_ids[$id] = true;
                $all_creators[] = $creator;
            }
        }
    }
}

// If no creators found in user_lists, try creators table (guest list)
if (empty($all_creators)) {
    $guest_query = $conn->query("SELECT id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned FROM creators WHERE in_guest_list = 1");
    
    if ($guest_query) {
        while ($row = $guest_query->fetch_assoc()) {
            $all_creators[] = array(
                'id' => $row['id'],
                'name' => $row['name'],
                'bio' => $row['bio'],
                'avatarUrl' => $row['avatar_url'],
                'category' => $row['category'],
                'reason' => $row['reason'],
                'tags' => json_decode($row['tags'], true),
                'accounts' => json_decode($row['accounts'], true),
                'isFavorite' => (bool) $row['is_favorite'],
                'isPinned' => (bool) $row['is_pinned']
            );
        }
    }
}

echo json_encode(array(
    'ok' => true,
    'count' => count($all_creators),
    'creators' => $all_creators
));

$conn->close();
