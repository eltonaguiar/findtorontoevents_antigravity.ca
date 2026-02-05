<?php
/**
 * CLI-only: fix user_lists for user_id=2 (zerounderscore@gmail.com) so they see ALL creators.
 * Run on the server via SSH: php fix_user2_list_cli.php
 * Uses same .env as the API (this folder). Does NOT go through the web server.
 */
if (php_sapi_name() !== 'cli') {
    die("Run from command line only: php fix_user2_list_cli.php\n");
}

error_reporting(E_ALL);
ini_set('display_errors', '1');

$api_dir = dirname(__FILE__);
require_once $api_dir . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    fwrite(STDERR, "DB connection failed: " . $conn->connect_error . "\n");
    exit(1);
}

// Default notes (creator_id => note)
$default_notes = array();
$dn = $conn->query("SELECT creator_id, note FROM creator_defaults");
if ($dn) {
    while ($r = $dn->fetch_assoc()) {
        $default_notes[$r['creator_id']] = isset($r['note']) ? $r['note'] : '';
    }
}

function build_one($row, $note) {
    $tags = $row['tags'];
    if (is_string($tags)) $tags = json_decode($tags, true);
    if (!is_array($tags)) $tags = array();
    $accounts = $row['accounts'];
    if (is_string($accounts)) $accounts = json_decode($accounts, true);
    if (!is_array($accounts)) $accounts = array();
    return array(
        'id' => $row['id'],
        'name' => $row['name'],
        'bio' => isset($row['bio']) ? $row['bio'] : '',
        'avatarUrl' => isset($row['avatar_url']) ? $row['avatar_url'] : '',
        'category' => isset($row['category']) ? $row['category'] : '',
        'reason' => isset($row['reason']) ? $row['reason'] : '',
        'tags' => $tags,
        'accounts' => $accounts,
        'isFavorite' => (bool)(isset($row['is_favorite']) ? $row['is_favorite'] : 0),
        'isPinned' => (bool)(isset($row['is_pinned']) ? $row['is_pinned'] : 0),
        'note' => $note,
        'addedAt' => 0,
        'lastChecked' => 0
    );
}

$q = $conn->query("SELECT id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned FROM creators ORDER BY id");
if (!$q) {
    fwrite(STDERR, "Query failed: " . $conn->error . "\n");
    exit(1);
}

$all = array();
while ($row = $q->fetch_assoc()) {
    $note = isset($default_notes[$row['id']]) ? $default_notes[$row['id']] : '';
    $all[] = build_one($row, $note);
}

$json = json_encode($all);
$esc = $conn->real_escape_string($json);
$sql = "INSERT INTO user_lists (user_id, creators) VALUES (2, '$esc') ON DUPLICATE KEY UPDATE creators = '$esc'";
if (!$conn->query($sql)) {
    fwrite(STDERR, "UPDATE failed: " . $conn->error . "\n");
    exit(1);
}

echo "OK: user_id=2 now has " . count($all) . " creators in user_lists.\n";
$conn->close();
exit(0);
