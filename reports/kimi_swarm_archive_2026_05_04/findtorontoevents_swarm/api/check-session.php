<?php
/**
 * check-session.php
 *
 * Lightweight session check endpoint.
 * Returns { loggedIn: boolean, userId?: string }
 *
 * Used by the frontend to determine whether to sync gear settings
 * to the backend (logged in) or fall back to localStorage only.
 */

header('Content-Type: application/json; charset=utf-8');

/* ── CORS ── */
$allowedOrigins = [
    'https://findtorontoevents.ca',
    'https://www.findtorontoevents.ca',
    'http://localhost',
    'http://localhost:3000',
];

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (in_array($origin, $allowedOrigins, true)) {
    header("Access-Control-Allow-Origin: $origin");
} else {
    header("Access-Control-Allow-Origin: https://findtorontoevents.ca");
}
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

/* ── Preflight ── */
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

/* ── Response helper ── */
function jsonResponse(int $status, array $payload): void {
    http_response_code($status);
    echo json_encode($payload, JSON_PRETTY_PRINT);
    exit;
}

try {
    require_once __DIR__ . '/db-config.php';
    $pdo = getDbConnection();

    $sessionId = $_COOKIE['session_id'] ?? '';

    if (!$sessionId || !preg_match('/^[a-f0-9]{64}$/', $sessionId)) {
        jsonResponse(200, [
            'loggedIn' => false,
            'userId' => null,
        ]);
    }

    $stmt = $pdo->prepare(
        "SELECT user_id FROM sessions WHERE session_id = :sid AND expires_at > NOW() LIMIT 1"
    );
    $stmt->execute([':sid' => $sessionId]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($row) {
        jsonResponse(200, [
            'loggedIn' => true,
            'userId' => (string) $row['user_id'],
        ]);
    } else {
        jsonResponse(200, [
            'loggedIn' => false,
            'userId' => null,
        ]);
    }

} catch (Throwable $e) {
    error_log("[check-session.php] " . $e->getMessage());
    jsonResponse(500, [
        'loggedIn' => false,
        'userId' => null,
        'error' => 'Internal server error',
    ]);
}
