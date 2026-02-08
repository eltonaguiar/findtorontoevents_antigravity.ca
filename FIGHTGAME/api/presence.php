<?php
/**
 * Shadow Arena — Cross-Game Presence API
 * Tracks online players across all game sections.
 * File-based storage in /presence/ directory.
 *
 * PHP 5.2 compatible — no closures, no short array, no ?:, no ??.
 *
 * GET  — list all online players
 * POST action=heartbeat — register/update player presence
 * POST action=leave     — remove player presence
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

$presenceDir = dirname(__FILE__) . '/presence';
if (!is_dir($presenceDir)) {
    @mkdir($presenceDir, 0755, true);
}

// ── Cleanup expired players (no heartbeat for >30s) ──
$files = glob($presenceDir . '/*.json');
$now = time();
if ($files) {
    foreach ($files as $file) {
        $mtime = filemtime($file);
        if ($mtime !== false && ($now - $mtime) > 30) {
            @unlink($file);
        }
    }
}

// ── GET: list all online players ──
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $players = array();
    $freshFiles = glob($presenceDir . '/*.json');
    if ($freshFiles) {
        foreach ($freshFiles as $file) {
            $raw = @file_get_contents($file);
            if ($raw !== false) {
                $player = json_decode($raw, true);
                if ($player && isset($player['id'])) {
                    $players[] = $player;
                }
            }
        }
    }
    echo json_encode(array('players' => $players, 'count' => count($players)));
    exit;
}

// ── POST: heartbeat or leave ──
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $payload = json_decode($input, true);

    if (!$payload || !isset($payload['action'])) {
        echo json_encode(array('error' => 'Invalid payload'));
        exit;
    }

    $action = $payload['action'];

    // — Heartbeat: create or update player presence —
    if ($action === 'heartbeat') {
        $pid = isset($payload['player_id']) ? $payload['player_id'] : '';
        $pid = preg_replace('/[^a-zA-Z0-9_]/', '', $pid);
        if ($pid === '') {
            echo json_encode(array('error' => 'Missing player_id'));
            exit;
        }

        $pName = isset($payload['player_name']) ? $payload['player_name'] : 'Guest';
        $pName = substr($pName, 0, 30);

        $pGame = isset($payload['game']) ? $payload['game'] : 'Unknown';
        $pGame = substr($pGame, 0, 50);

        $pUrl = isset($payload['game_url']) ? $payload['game_url'] : '';
        $pUrl = substr($pUrl, 0, 200);

        $pStatus = isset($payload['status']) ? $payload['status'] : 'online';
        $pStatus = substr($pStatus, 0, 30);

        $pRoom = isset($payload['room_code']) ? $payload['room_code'] : '';
        $pRoom = preg_replace('/[^A-Z0-9]/', '', strtoupper(substr($pRoom, 0, 10)));

        $pJoin = false;
        if (isset($payload['joinable']) && $payload['joinable']) {
            $pJoin = true;
        }

        $pSpec = false;
        if (isset($payload['spectatable']) && $payload['spectatable']) {
            $pSpec = true;
        }

        $playerData = array(
            'id'          => $pid,
            'name'        => $pName,
            'game'        => $pGame,
            'game_url'    => $pUrl,
            'status'      => $pStatus,
            'room_code'   => $pRoom,
            'joinable'    => $pJoin,
            'spectatable' => $pSpec,
            'updated'     => $now
        );

        $file = $presenceDir . '/' . $pid . '.json';
        $written = @file_put_contents($file, json_encode($playerData));
        if ($written === false) {
            echo json_encode(array('error' => 'Write failed'));
            exit;
        }
        echo json_encode(array('success' => true));
        exit;
    }

    // — Leave: remove player file —
    if ($action === 'leave') {
        $pid = isset($payload['player_id']) ? $payload['player_id'] : '';
        $pid = preg_replace('/[^a-zA-Z0-9_]/', '', $pid);
        if ($pid !== '') {
            $file = $presenceDir . '/' . $pid . '.json';
            @unlink($file);
        }
        echo json_encode(array('success' => true));
        exit;
    }

    echo json_encode(array('error' => 'Unknown action'));
    exit;
}

echo json_encode(array('error' => 'Method not allowed'));
