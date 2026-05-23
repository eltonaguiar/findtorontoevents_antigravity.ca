<?php
/**
 * user-settings.php
 *
 * GET  /api/user-settings.php      — returns user's saved settings from DB
 * POST /api/user-settings.php      — saves settings JSON to user_settings table
 *
 * Auth: Requires a valid session_id cookie. Returns 401 if absent/invalid.
 *
 * JSON Schema:
 * {
 *   maxEventsPerDayPerSource: number(1-10),
 *   exemptEventbrite: boolean,
 *   showSourceBadges: boolean,
 *   groupByDate: boolean,
 *   deduplicate: boolean,
 *   enabledSources: string[],
 *   calendarExportFormat: string
 * }
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
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

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

function success($data): void {
    jsonResponse(200, ['success' => true, 'data' => $data, 'error' => null]);
}

function error(int $status, string $message): void {
    jsonResponse($status, ['success' => false, 'data' => null, 'error' => $message]);
}

/* ── DB connection ── */
require_once __DIR__ . '/db-config.php';

/* ── Session validation ── */
function getCurrentUserId(PDO $pdo): ?int {
    $sessionId = $_COOKIE['session_id'] ?? '';
    if (!$sessionId || !preg_match('/^[a-f0-9]{64}$/', $sessionId)) {
        return null;
    }

    $stmt = $pdo->prepare("SELECT user_id FROM sessions WHERE session_id = :sid AND expires_at > NOW() LIMIT 1");
    $stmt->execute([':sid' => $sessionId]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);

    return $row ? (int) $row['user_id'] : null;
}

/* ── Schema validator ── */
function validateSettings(array $raw): array {
    $defaults = [
        'maxEventsPerDayPerSource' => 3,
        'exemptEventbrite' => true,
        'showSourceBadges' => true,
        'groupByDate' => false,
        'deduplicate' => true,
        'enabledSources' => [],
        'calendarExportFormat' => 'both',
    ];

    $errors = [];

    // maxEventsPerDayPerSource: int 1-10
    if (isset($raw['maxEventsPerDayPerSource'])) {
        $val = (int) $raw['maxEventsPerDayPerSource'];
        if ($val < 1 || $val > 10) {
            $errors[] = 'maxEventsPerDayPerSource must be between 1 and 10';
        } else {
            $defaults['maxEventsPerDayPerSource'] = $val;
        }
    }

    // booleans
    foreach (['exemptEventbrite', 'showSourceBadges', 'groupByDate', 'deduplicate'] as $boolKey) {
        if (isset($raw[$boolKey])) {
            $defaults[$boolKey] = filter_var($raw[$boolKey], FILTER_VALIDATE_BOOLEAN);
        }
    }

    // enabledSources: array of strings
    if (isset($raw['enabledSources'])) {
        if (!is_array($raw['enabledSources'])) {
            $errors[] = 'enabledSources must be an array';
        } else {
            $defaults['enabledSources'] = array_values(array_filter($raw['enabledSources'], 'is_string'));
        }
    }

    // calendarExportFormat
    if (isset($raw['calendarExportFormat'])) {
        $fmt = (string) $raw['calendarExportFormat'];
        $allowedFormats = ['ical', 'google', 'both'];
        $defaults['calendarExportFormat'] = in_array($fmt, $allowedFormats, true) ? $fmt : 'both';
    }

    return ['errors' => $errors, 'settings' => $defaults];
}

/* ── MAIN ── */

try {
    $pdo = getDbConnection();
    $userId = getCurrentUserId($pdo);

    // GET ── fetch settings
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        if (!$userId) {
            error(401, 'Unauthorized: valid session required');
        }

        $stmt = $pdo->prepare(
            "SELECT settings_json, updated_at FROM user_settings WHERE user_id = :uid LIMIT 1"
        );
        $stmt->execute([':uid' => $userId]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$row) {
            // No saved settings yet — return defaults
            success([
                'settings' => [
                    'maxEventsPerDayPerSource' => 3,
                    'exemptEventbrite' => true,
                    'showSourceBadges' => true,
                    'groupByDate' => false,
                    'deduplicate' => true,
                    'enabledSources' => [],
                    'calendarExportFormat' => 'both',
                ],
                'updated_at' => null,
                'source' => 'default',
            ]);
        }

        $settings = json_decode($row['settings_json'], true);
        if (!is_array($settings)) {
            $settings = [];
        }

        success([
            'settings' => $settings,
            'updated_at' => $row['updated_at'],
            'source' => 'database',
        ]);
    }

    // POST ── save settings
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (!$userId) {
            error(401, 'Unauthorized: valid session required');
        }

        $input = json_decode(file_get_contents('php://input'), true);
        if (!is_array($input)) {
            error(400, 'Invalid JSON body');
        }

        $validated = validateSettings($input);
        if (!empty($validated['errors'])) {
            error(400, 'Validation failed: ' . implode('; ', $validated['errors']));
        }

        $settingsJson = json_encode($validated['settings']);

        $stmt = $pdo->prepare(
            "INSERT INTO user_settings (user_id, settings_json, created_at, updated_at)
             VALUES (:uid, :json, NOW(), NOW())
             ON DUPLICATE KEY UPDATE
             settings_json = :json,
             updated_at = NOW()"
        );
        $stmt->execute([
            ':uid' => $userId,
            ':json' => $settingsJson,
        ]);

        success([
            'settings' => $validated['settings'],
            'updated_at' => date('c'),
            'source' => 'database',
        ]);
    }

    error(405, 'Method not allowed. Use GET or POST.');

} catch (Throwable $e) {
    error_log("[user-settings.php] " . $e->getMessage());
    error(500, 'Internal server error');
}
