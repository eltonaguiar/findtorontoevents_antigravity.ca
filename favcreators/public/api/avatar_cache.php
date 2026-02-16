<?php
/**
 * Avatar Cache API — pre-fetched avatar URLs for creators.
 *
 * GET  ?creator_id=xxx        → returns cached avatars for one creator
 * GET  ?all=1                 → returns all cached avatars (for bulk frontend load)
 * POST (JSON body)            → batch-save cached avatars (requires secret token)
 *
 * The GitHub Actions prefetch job calls POST daily. The frontend reads via GET
 * so the AvatarSelectorModal can show results instantly.
 */
error_reporting(0);
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-Avatar-Token');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 204 No Content');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

/* ── Ensure table exists ─────────────────────────────────────────────── */
$conn->query("CREATE TABLE IF NOT EXISTS avatar_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id VARCHAR(64) NOT NULL,
    source VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT '',
    username VARCHAR(255) NOT NULL DEFAULT '',
    avatar_url VARCHAR(1024) NOT NULL,
    fetched_at DATETIME NOT NULL,
    UNIQUE KEY uq_creator_source (creator_id, source)
)");


/* ── GET: read cached avatars ────────────────────────────────────────── */
if ($_SERVER['REQUEST_METHOD'] === 'GET') {

    if (isset($_GET['all']) && $_GET['all'] === '1') {
        /* Return everything, grouped by creator_id */
        $q = $conn->query("SELECT creator_id, source, platform, username, avatar_url, fetched_at FROM avatar_cache ORDER BY creator_id, platform");
        $result = array();
        if ($q) {
            while ($row = $q->fetch_assoc()) {
                $cid = $row['creator_id'];
                if (!isset($result[$cid])) {
                    $result[$cid] = array();
                }
                $result[$cid][] = array(
                    'source'     => $row['source'],
                    'platform'   => $row['platform'],
                    'username'   => $row['username'],
                    'avatar_url' => $row['avatar_url'],
                    'fetched_at' => $row['fetched_at']
                );
            }
        }
        echo json_encode(array('ok' => true, 'avatars' => $result, 'count' => count($result)));
        $conn->close();
        exit;
    }

    if (isset($_GET['creator_id'])) {
        $cid = $conn->real_escape_string($_GET['creator_id']);
        $q = $conn->query("SELECT source, platform, username, avatar_url, fetched_at FROM avatar_cache WHERE creator_id = '$cid' ORDER BY platform");
        $rows = array();
        if ($q) {
            while ($row = $q->fetch_assoc()) {
                $rows[] = array(
                    'source'     => $row['source'],
                    'platform'   => $row['platform'],
                    'username'   => $row['username'],
                    'avatar_url' => $row['avatar_url'],
                    'fetched_at' => $row['fetched_at']
                );
            }
        }
        echo json_encode(array('ok' => true, 'creator_id' => $_GET['creator_id'], 'avatars' => $rows));
        $conn->close();
        exit;
    }

    /* Summary: how many creators have cached avatars */
    $q = $conn->query("SELECT COUNT(DISTINCT creator_id) AS c FROM avatar_cache");
    $count = 0;
    if ($q) {
        $row = $q->fetch_assoc();
        $count = (int) $row['c'];
    }
    $q2 = $conn->query("SELECT COUNT(*) AS total FROM avatar_cache");
    $total = 0;
    if ($q2) {
        $row2 = $q2->fetch_assoc();
        $total = (int) $row2['total'];
    }
    echo json_encode(array('ok' => true, 'creators_with_cache' => $count, 'total_entries' => $total));
    $conn->close();
    exit;
}


/* ── POST: batch-save avatars (requires token) ───────────────────────── */
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    echo json_encode(array('error' => 'Use GET or POST'));
    exit;
}

/* Verify secret token (set in GitHub Actions secrets / .env) */
$expected_token = '';
$env_token = getenv('AVATAR_CACHE_TOKEN');
if ($env_token !== false && $env_token !== '') {
    $expected_token = $env_token;
}
/* Also check a config file */
$token_file = dirname(__FILE__) . '/avatar_cache_token.txt';
if ($expected_token === '' && file_exists($token_file)) {
    $expected_token = trim(file_get_contents($token_file));
}

if ($expected_token === '') {
    /* No token configured — allow writes (first-time setup). */
    /* After deploying, create avatar_cache_token.txt with a random secret. */
} else {
    $provided = '';
    if (isset($_SERVER['HTTP_X_AVATAR_TOKEN'])) {
        $provided = $_SERVER['HTTP_X_AVATAR_TOKEN'];
    }
    $input_check = json_decode(file_get_contents('php://input'), true);
    if ($provided === '' && is_array($input_check) && isset($input_check['token'])) {
        $provided = $input_check['token'];
    }
    if ($provided !== $expected_token) {
        header('HTTP/1.1 403 Forbidden');
        echo json_encode(array('error' => 'Invalid token'));
        $conn->close();
        exit;
    }
}

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!is_array($data) || !isset($data['avatars']) || !is_array($data['avatars'])) {
    echo json_encode(array('error' => 'Expected JSON with "avatars" array'));
    $conn->close();
    exit;
}

$saved = 0;
$errors = 0;
$now = date('Y-m-d H:i:s');

foreach ($data['avatars'] as $entry) {
    $cid      = isset($entry['creator_id']) ? $conn->real_escape_string($entry['creator_id']) : '';
    $source   = isset($entry['source'])     ? $conn->real_escape_string($entry['source']) : '';
    $platform = isset($entry['platform'])   ? $conn->real_escape_string($entry['platform']) : '';
    $username = isset($entry['username'])   ? $conn->real_escape_string($entry['username']) : '';
    $url      = isset($entry['avatar_url']) ? $conn->real_escape_string($entry['avatar_url']) : '';

    if ($cid === '' || $source === '' || $url === '') {
        $errors++;
        continue;
    }

    $sql = "INSERT INTO avatar_cache (creator_id, source, platform, username, avatar_url, fetched_at)
            VALUES ('$cid', '$source', '$platform', '$username', '$url', '$now')
            ON DUPLICATE KEY UPDATE avatar_url = '$url', platform = '$platform', username = '$username', fetched_at = '$now'";

    if ($conn->query($sql)) {
        $saved++;
    } else {
        $errors++;
    }
}

echo json_encode(array(
    'ok'     => true,
    'saved'  => $saved,
    'errors' => $errors,
    'total'  => count($data['avatars'])
));
$conn->close();
?>
