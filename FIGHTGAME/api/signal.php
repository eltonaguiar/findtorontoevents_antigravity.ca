<?php
/**
 * Shadow Arena — WebRTC Signaling Server
 * Stores room data in flat files for peer-to-peer matchmaking.
 * PHP 5.2 compatible — no closures, no short array syntax, no ?:, no ??.
 */

// CORS headers
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

// Room data directory
$roomDir = dirname(__FILE__) . '/rooms';
if (!is_dir($roomDir)) {
    @mkdir($roomDir, 0755, true);
}

// Clean up expired rooms (older than 5 minutes)
$files = glob($roomDir . '/*.json');
if ($files) {
    $now = time();
    foreach ($files as $file) {
        $mtime = filemtime($file);
        if ($mtime !== false && ($now - $mtime) > 300) {
            @unlink($file);
        }
    }
}

// Handle GET — retrieve room data
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $room = isset($_GET['room']) ? preg_replace('/[^A-Z0-9]/', '', strtoupper($_GET['room'])) : '';
    if ($room === '' || strlen($room) !== 6) {
        echo json_encode(array('error' => 'Invalid room code'));
        exit;
    }

    $roomFile = $roomDir . '/' . $room . '.json';
    if (!file_exists($roomFile)) {
        echo json_encode(array('error' => 'Room not found', 'data' => null));
        exit;
    }

    $data = @file_get_contents($roomFile);
    if ($data === false) {
        echo json_encode(array('error' => 'Failed to read room', 'data' => null));
        exit;
    }

    $roomData = json_decode($data, true);
    if (!$roomData) {
        echo json_encode(array('error' => 'Invalid room data', 'data' => null));
        exit;
    }

    echo json_encode(array('data' => $roomData));
    exit;
}

// Handle POST — create or update room
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $payload = json_decode($input, true);

    if (!$payload || !isset($payload['action']) || !isset($payload['data'])) {
        echo json_encode(array('error' => 'Invalid payload'));
        exit;
    }

    $action = $payload['action'];
    $data = $payload['data'];

    $room = isset($data['room']) ? preg_replace('/[^A-Z0-9]/', '', strtoupper($data['room'])) : '';
    if ($room === '' || strlen($room) !== 6) {
        echo json_encode(array('error' => 'Invalid room code'));
        exit;
    }

    $roomFile = $roomDir . '/' . $room . '.json';

    if ($action === 'offer') {
        // Host creates room with offer SDP
        $roomData = array(
            'room' => $room,
            'sdp' => isset($data['sdp']) ? $data['sdp'] : '',
            'answer' => null,
            'created' => time()
        );
        $written = @file_put_contents($roomFile, json_encode($roomData));
        if ($written === false) {
            echo json_encode(array('error' => 'Failed to create room'));
            exit;
        }
        echo json_encode(array('success' => true, 'room' => $room));
        exit;
    }

    if ($action === 'answer') {
        // Guest joins room with answer SDP
        if (!file_exists($roomFile)) {
            echo json_encode(array('error' => 'Room not found'));
            exit;
        }
        $existingData = @file_get_contents($roomFile);
        $roomData = json_decode($existingData, true);
        if (!$roomData) {
            echo json_encode(array('error' => 'Invalid room'));
            exit;
        }
        $roomData['answer'] = isset($data['sdp']) ? $data['sdp'] : '';
        @file_put_contents($roomFile, json_encode($roomData));
        echo json_encode(array('success' => true));
        exit;
    }

    echo json_encode(array('error' => 'Unknown action'));
    exit;
}

echo json_encode(array('error' => 'Method not allowed'));
