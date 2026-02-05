<?php
/**
 * Return the creator list for a user. Session-protected: only own list or guest (0) unless admin.
 */

header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Pragma: no-cache");

$log_file = '/tmp/get_my_creators_log.txt';
$log = "=== " . date('Y-m-d H:i:s') . " ===\n";

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    $log .= "ERROR: Database not available\n";
    file_put_contents($log_file, $log, FILE_APPEND);
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$requested_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;
$session_id = get_session_user_id();

if ($session_id === null) {
    if ($requested_id !== 0) {
        header('HTTP/1.1 403 Forbidden');
        echo json_encode(array('error' => 'Access denied', 'creators' => array()));
        exit;
    }
    $user_id = 0;
} else {
    // Admin can view any user_id (including 0). Non-admin can ONLY view their own.
    if (is_session_admin()) {
        $user_id = $requested_id;
    } else {
        // Non-admin logged-in user: allow their own list OR guest list (0)
        if ($requested_id !== $session_id && $requested_id !== 0) {
            header('HTTP/1.1 403 Forbidden');
            echo json_encode(array('error' => 'Access denied', 'creators' => array()));
            exit;
        }
        $user_id = $requested_id;
    }
}
$log .= "Request: user_id=$user_id (session=$session_id)\n";

// Check if user exists
if ($user_id > 0) {
    $user_check = $conn->query("SELECT email FROM users WHERE id = $user_id");
    if ($user_check && $user_check->num_rows > 0) {
        $user_row = $user_check->fetch_assoc();
        $log .= "User found: " . $user_row['email'] . "\n";
    } else {
        $log .= "WARNING: User ID $user_id not found in users table\n";
    }
}

// Try to get from user_lists first
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");

if ($query && $query->num_rows > 0) {
    $log .= "Found in user_lists table\n";
    $row = $query->fetch_assoc();
    $creators_json = $row['creators'];
    $creators = json_decode($creators_json, true);

    if (!is_array($creators)) {
        $log .= "ERROR: JSON decode failed\n";
        $creators = array();
    } else {
        $log .= "Decoded " . count($creators) . " creators from user_lists\n";
        // Deduplicate by id (keep first occurrence) - PHP 5.x safe
        $seen = array();
        $deduped = array();
        foreach ($creators as $c) {
            $id = isset($c['id']) ? $c['id'] : '';
            if ($id === '' || isset($seen[$id])) continue;
            $seen[$id] = true;
            $deduped[] = $c;
        }
        $creators = $deduped;

        // Exclude starfireara (data is incorrect)
        $filtered_creators = array();
        foreach ($creators as $c) {
            $name = isset($c['name']) ? strtolower(trim($c['name'])) : '';
            if ($name === 'starfireara') continue;
            $filtered_creators[] = $c;
        }
        $creators = $filtered_creators;
        $log .= "After starfireara exclusion: " . count($creators) . " creators\n";
        // Also dedupe by name so same person with different ids (e.g. duplicate Tony Robbins) appears once
        $seen_names = array();
        $by_name = array();
        foreach ($creators as $c) {
            $name = isset($c['name']) ? trim($c['name']) : '';
            if ($name === '') { $by_name[] = $c; continue; }
            $key = strtolower($name);
            if (isset($seen_names[$key])) continue;
            $seen_names[$key] = true;
            $by_name[] = $c;
        }
        $creators = $by_name;
        $log .= "After dedupe: " . count($creators) . " creators\n";

        // Check for Brunitarte
        $has_brunitarte = false;
        foreach ($creators as $c) {
            if (isset($c['name']) && $c['name'] === 'Brunitarte') {
                $has_brunitarte = true;
                break;
            }
        }
        $log .= "Has Brunitarte: " . ($has_brunitarte ? 'YES' : 'NO') . "\n";

        // Safeguard: user_id=2 (zerounderscore@gmail.com) must always have Brunitarte. If missing, inject and persist.
        if ($user_id === 2 && !$has_brunitarte) {
            $brunitarte = array(
                'id' => 'brunitarte-tiktok',
                'name' => 'Brunitarte',
                'bio' => '',
                'avatarUrl' => '',
                'avatar_url' => '',
                'category' => 'other',
                'reason' => '',
                'tags' => array(),
                'accounts' => array(array('platform' => 'tiktok', 'username' => 'brunitarte', 'url' => 'https://www.tiktok.com/@brunitarte')),
                'isFavorite' => false,
                'is_favorite' => 0,
                'isPinned' => false,
                'is_pinned' => 0,
                'note' => '',
                'addedAt' => 0,
                'lastChecked' => 0
            );
            $creators[] = $brunitarte;
            $has_brunitarte = true;
            $log .= "Injected Brunitarte for user 2 (was missing)\n";
            $fixed_json = $conn->real_escape_string(json_encode($creators));
            $conn->query("UPDATE user_lists SET creators = '$fixed_json' WHERE user_id = 2");
        }
    }

    file_put_contents($log_file, $log, FILE_APPEND);

    header("X-Source: user_lists");
    header("X-User-Id: $user_id");
    header("X-Creator-Count: " . count($creators));
    header("X-Has-Brunitarte: " . (isset($has_brunitarte) && $has_brunitarte ? 'true' : 'false'));

    echo json_encode(array('creators' => $creators));
    $conn->close();
    exit;
}

// Logged-in user with no list: copy default (user_id=0) to them so they get default list and can then customize
if ($user_id > 0) {
    $default_row = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($default_row && $default_row->num_rows > 0) {
        $dr = $default_row->fetch_assoc();
        $default_creators = $dr['creators'];
        $default_esc = $conn->real_escape_string($default_creators);
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$default_esc') ON DUPLICATE KEY UPDATE creators = '$default_esc'");
        if ($conn->affected_rows >= 0) {
            $creators = json_decode($default_creators, true);
            if (is_array($creators)) {
                $seen = array();
                $deduped = array();
                foreach ($creators as $c) {
                    $id = isset($c['id']) ? $c['id'] : '';
                    if ($id === '' || isset($seen[$id])) continue;
                    $seen[$id] = true;
                    $deduped[] = $c;
                }
                $creators = $deduped;
                $log .= "Initialized user $user_id from default list (" . count($creators) . " creators)\n";
                file_put_contents($log_file, $log, FILE_APPEND);
                header("X-Source: user_lists");
                header("X-User-Id: $user_id");
                header("X-Creator-Count: " . count($creators));
                echo json_encode(array('creators' => $creators));
                $conn->close();
                exit;
            }
        }
    }
}

// Fallback to creators table (guest list)
$log .= "NOT found in user_lists, falling back to creators table (guest list)\n";

$guest_query = $conn->query("SELECT id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned FROM creators WHERE in_guest_list = 1 ORDER BY guest_sort_order ASC");

$creators = array();
$seen_ids = array();
if ($guest_query) {
    while ($row = $guest_query->fetch_assoc()) {
        $cid = isset($row['id']) ? $row['id'] : '';
        if ($cid !== '' && isset($seen_ids[$cid])) continue;
        if ($cid !== '') $seen_ids[$cid] = true;
    // Skip starfireara (data is incorrect)
        if (strtolower(trim($row['name'])) === 'starfireara') continue;
        
        $creators[] = array(
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

$log .= "Loaded " . count($creators) . " creators from creators table\n";
file_put_contents($log_file, $log, FILE_APPEND);

header("X-Source: creators_table");
header("X-User-Id: $user_id");
header("X-Creator-Count: " . count($creators));

echo json_encode(array('creators' => $creators));
$conn->close();
?>