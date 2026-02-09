<?php
/**
 * Cross-Game Presence API — Database-backed
 * Tracks online players across all game sections with "recently online" support.
 *
 * PHP 5.2 compatible — no closures, no short array, no ?:, no ??.
 *
 * GET             — list all online + recently online players
 * POST heartbeat  — register/update player presence
 * POST leave      — mark player as offline
 * POST setup      — create/migrate the game_presence table (one-time)
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

/* ── Database connection (reuse favcreators db_config) ── */
/* Server layout: /findtorontoevents.ca/FIGHTGAME/api/presence.php
                  /findtorontoevents.ca/fc/api/db_config.php          */
$_presence_config_path = dirname(__FILE__) . '/../../fc/api/db_config.php';
if (!file_exists($_presence_config_path)) {
    /* Local dev: favcreators/public/api or favcreators/docs/api */
    $_presence_config_path = dirname(__FILE__) . '/../../favcreators/public/api/db_config.php';
}
if (!file_exists($_presence_config_path)) {
    $_presence_config_path = dirname(__FILE__) . '/../../favcreators/docs/api/db_config.php';
}
if (!file_exists($_presence_config_path)) {
    echo json_encode(array('error' => 'Database config not found'));
    exit;
}
require_once $_presence_config_path;

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

/* ── Ensure table exists ── */
_presence_ensure_table($conn);

/* ── Constants ── */
$HEARTBEAT_TIMEOUT = 30;    /* seconds — no heartbeat = offline */
$RECENTLY_ONLINE   = 300;   /* 5 minutes — show as "recently online" */

/* ── Mark expired players as offline ── */
$cutoff = date('Y-m-d H:i:s', time() - $HEARTBEAT_TIMEOUT);
$conn->query("UPDATE game_presence SET is_online = 0 WHERE is_online = 1 AND last_heartbeat < '" . $conn->real_escape_string($cutoff) . "'");


/* ─────── GET: list all online + recently online ─────── */
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $onlinePlayers  = array();
    $recentPlayers  = array();

    /* Online players: heartbeat within last 30s */
    $sql = "SELECT player_id, player_name, game, game_url, status, room_code, joinable, spectatable, last_heartbeat, first_seen_at
            FROM game_presence
            WHERE is_online = 1
            ORDER BY game ASC, player_name ASC";
    $result = $conn->query($sql);
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $onlinePlayers[] = array(
                'id'          => $row['player_id'],
                'name'        => $row['player_name'],
                'game'        => $row['game'],
                'game_url'    => $row['game_url'],
                'status'      => $row['status'],
                'room_code'   => $row['room_code'],
                'joinable'    => ($row['joinable'] == 1),
                'spectatable' => ($row['spectatable'] == 1),
                'updated'     => strtotime($row['last_heartbeat'])
            );
        }
        $result->free();
    }

    /* Recently online: went offline within the last 5 minutes */
    $recentCutoff = date('Y-m-d H:i:s', time() - $RECENTLY_ONLINE);
    $sql2 = "SELECT player_id, player_name, game, game_url, status, last_heartbeat
             FROM game_presence
             WHERE is_online = 0
               AND last_heartbeat >= '" . $conn->real_escape_string($recentCutoff) . "'
             ORDER BY last_heartbeat DESC";
    $result2 = $conn->query($sql2);
    if ($result2) {
        while ($row = $result2->fetch_assoc()) {
            $recentPlayers[] = array(
                'id'             => $row['player_id'],
                'name'           => $row['player_name'],
                'game'           => $row['game'],
                'game_url'       => $row['game_url'],
                'last_status'    => $row['status'],
                'last_seen'      => strtotime($row['last_heartbeat']),
                'last_seen_ago'  => time() - strtotime($row['last_heartbeat'])
            );
        }
        $result2->free();
    }

    echo json_encode(array(
        'players'        => $onlinePlayers,
        'count'          => count($onlinePlayers),
        'recently_online'=> $recentPlayers,
        'recent_count'   => count($recentPlayers)
    ));
    $conn->close();
    exit;
}


/* ─────── POST: heartbeat / leave / setup ─────── */
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input   = file_get_contents('php://input');
    $payload = json_decode($input, true);

    if (!$payload || !isset($payload['action'])) {
        echo json_encode(array('error' => 'Invalid payload'));
        $conn->close();
        exit;
    }

    $action = $payload['action'];

    /* ── Heartbeat: upsert player presence ── */
    if ($action === 'heartbeat') {
        $pid = isset($payload['player_id']) ? $payload['player_id'] : '';
        $pid = preg_replace('/[^a-zA-Z0-9_]/', '', $pid);
        if ($pid === '') {
            echo json_encode(array('error' => 'Missing player_id'));
            $conn->close();
            exit;
        }

        $pName   = isset($payload['player_name']) ? substr($payload['player_name'], 0, 30) : 'Guest';
        $pGame   = isset($payload['game']) ? substr($payload['game'], 0, 50) : 'Unknown';
        $pUrl    = isset($payload['game_url']) ? substr($payload['game_url'], 0, 200) : '';
        $pStatus = isset($payload['status']) ? substr($payload['status'], 0, 30) : 'online';
        $pRoom   = isset($payload['room_code']) ? preg_replace('/[^A-Z0-9]/', '', strtoupper(substr($payload['room_code'], 0, 10))) : '';
        $pJoin   = (isset($payload['joinable']) && $payload['joinable']) ? 1 : 0;
        $pSpec   = (isset($payload['spectatable']) && $payload['spectatable']) ? 1 : 0;

        $ip = '';
        if (isset($_SERVER['HTTP_X_FORWARDED_FOR'])) {
            $parts = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
            $ip = trim($parts[0]);
        }
        if ($ip === '' && isset($_SERVER['REMOTE_ADDR'])) {
            $ip = $_SERVER['REMOTE_ADDR'];
        }
        $ip = substr($ip, 0, 45);

        $nowStr = date('Y-m-d H:i:s');

        /* Upsert: INSERT ... ON DUPLICATE KEY UPDATE */
        $sql = sprintf(
            "INSERT INTO game_presence (player_id, player_name, ip_address, game, game_url, status, room_code, joinable, spectatable, first_seen_at, last_heartbeat, is_online)
             VALUES ('%s','%s','%s','%s','%s','%s','%s',%d,%d,'%s','%s',1)
             ON DUPLICATE KEY UPDATE
               player_name = '%s',
               ip_address = '%s',
               game = '%s',
               game_url = '%s',
               status = '%s',
               room_code = '%s',
               joinable = %d,
               spectatable = %d,
               last_heartbeat = '%s',
               is_online = 1",
            $conn->real_escape_string($pid),
            $conn->real_escape_string($pName),
            $conn->real_escape_string($ip),
            $conn->real_escape_string($pGame),
            $conn->real_escape_string($pUrl),
            $conn->real_escape_string($pStatus),
            $conn->real_escape_string($pRoom),
            $pJoin, $pSpec,
            $conn->real_escape_string($nowStr),
            $conn->real_escape_string($nowStr),
            /* ON DUPLICATE KEY UPDATE values: */
            $conn->real_escape_string($pName),
            $conn->real_escape_string($ip),
            $conn->real_escape_string($pGame),
            $conn->real_escape_string($pUrl),
            $conn->real_escape_string($pStatus),
            $conn->real_escape_string($pRoom),
            $pJoin, $pSpec,
            $conn->real_escape_string($nowStr)
        );

        if ($conn->query($sql)) {
            echo json_encode(array('success' => true));
        } else {
            echo json_encode(array('error' => 'DB write failed: ' . $conn->error));
        }
        $conn->close();
        exit;
    }

    /* ── Leave: mark player as offline ── */
    if ($action === 'leave') {
        $pid = isset($payload['player_id']) ? $payload['player_id'] : '';
        $pid = preg_replace('/[^a-zA-Z0-9_]/', '', $pid);
        if ($pid !== '') {
            $conn->query("UPDATE game_presence SET is_online = 0 WHERE player_id = '" . $conn->real_escape_string($pid) . "'");
        }
        echo json_encode(array('success' => true));
        $conn->close();
        exit;
    }

    /* ── Setup: create table (one-time endpoint) ── */
    if ($action === 'setup') {
        _presence_ensure_table($conn);
        echo json_encode(array('success' => true, 'message' => 'game_presence table ready'));
        $conn->close();
        exit;
    }

    echo json_encode(array('error' => 'Unknown action'));
    $conn->close();
    exit;
}

echo json_encode(array('error' => 'Method not allowed'));
$conn->close();
/* ─────── Table creation (PHP 5.2 compatible) ─────── */
function _presence_ensure_table($db) {
    $sql = "CREATE TABLE IF NOT EXISTS game_presence (
        id INT AUTO_INCREMENT PRIMARY KEY,
        player_id VARCHAR(50) NOT NULL,
        player_name VARCHAR(30) NOT NULL DEFAULT 'Guest',
        ip_address VARCHAR(45) NOT NULL DEFAULT '',
        game VARCHAR(50) NOT NULL DEFAULT 'Unknown',
        game_url VARCHAR(200) DEFAULT '',
        status VARCHAR(30) NOT NULL DEFAULT 'online',
        room_code VARCHAR(10) DEFAULT '',
        joinable TINYINT(1) NOT NULL DEFAULT 0,
        spectatable TINYINT(1) NOT NULL DEFAULT 0,
        first_seen_at DATETIME NOT NULL,
        last_heartbeat DATETIME NOT NULL,
        is_online TINYINT(1) NOT NULL DEFAULT 1,
        UNIQUE KEY uq_player (player_id),
        INDEX idx_online (is_online, last_heartbeat),
        INDEX idx_game (game),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
    $db->query($sql);
}
?>