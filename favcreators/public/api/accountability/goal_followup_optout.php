<?php
/**
 * Accountability Coach — Goal Follow-Up Opt-Out — PHP 5.2 compatible
 *
 * GET  ?discord_id=ID&token=TOKEN  — Opt out via web link (shown in DM)
 * POST { "discord_id": "ID", "action": "optout"|"optin" }  — Toggle from dashboard
 * GET  ?discord_id=ID&check=1  — Check current opt-out status (for dashboard)
 * GET  ?app_user_id=ID&check=1 — Check status by app user ID
 * POST { "app_user_id": ID, "action": "optout"|"optin" }  — Toggle by app user ID
 */
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/../db_connect.php';
require_once dirname(__FILE__) . '/../discord_config.php';

if (!isset($conn) || !$conn) {
    header('Content-Type: application/json');
    echo json_encode(array('success' => false, 'error' => 'Database not available'));
    exit;
}

// Ensure table exists
$conn->query("CREATE TABLE IF NOT EXISTS accountability_followup_optouts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_user_id VARCHAR(32) DEFAULT NULL,
    app_user_id INT DEFAULT NULL,
    opted_out_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_discord (discord_user_id),
    INDEX idx_app_user (app_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

// Secret for token verification
$optout_secret = _discord_read_env('ACCOUNTABILITY_FOLLOWUP_SECRET', '');
if (!$optout_secret) $optout_secret = _discord_read_env('EVENT_NOTIFY_API_KEY', 'fallback_secret_key');

// ──────── GET: Opt-out via link OR check status ────────
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $discord_id = isset($_GET['discord_id']) ? trim($_GET['discord_id']) : '';
    $app_user_id = isset($_GET['app_user_id']) ? intval($_GET['app_user_id']) : 0;
    $token = isset($_GET['token']) ? trim($_GET['token']) : '';
    $check = isset($_GET['check']) && $_GET['check'] === '1';

    // Status check mode (for dashboard polling)
    if ($check) {
        header('Content-Type: application/json');

        // Resolve discord_id from app_user_id if needed
        if (!$discord_id && $app_user_id) {
            $discord_id = _resolve_discord_id($conn, $app_user_id);
        }

        if (!$discord_id && !$app_user_id) {
            echo json_encode(array('success' => false, 'error' => 'Provide discord_id or app_user_id'));
            exit;
        }

        $isOptedOut = _is_opted_out($conn, $discord_id, $app_user_id);
        echo json_encode(array('success' => true, 'opted_out' => $isOptedOut));
        exit;
    }

    // Opt-out via web link (requires valid token)
    if (!$discord_id || !$token) {
        header('Content-Type: text/html; charset=utf-8');
        echo _render_optout_page('error', 'Missing parameters. Please use the link from your Discord DM.');
        exit;
    }

    // Verify token
    $expectedToken = substr(hash_hmac('sha256', 'optout:' . $discord_id, $optout_secret), 0, 32);
    if ($token !== $expectedToken) {
        header('Content-Type: text/html; charset=utf-8');
        echo _render_optout_page('error', 'Invalid or expired opt-out link. Use the button in your Discord DM or toggle it in your dashboard.');
        exit;
    }

    // Perform opt-out
    $esc_id = $conn->real_escape_string($discord_id);
    $conn->query("INSERT IGNORE INTO accountability_followup_optouts (discord_user_id) VALUES ('" . $esc_id . "')");

    header('Content-Type: text/html; charset=utf-8');
    echo _render_optout_page('success', '');
    $conn->close();
    exit;
}

// ──────── POST: Toggle from dashboard or API ────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    header('Content-Type: application/json');
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) {
        echo json_encode(array('success' => false, 'error' => 'Invalid JSON'));
        exit;
    }

    $discord_id = isset($input['discord_id']) ? trim($input['discord_id']) : '';
    $app_user_id = isset($input['app_user_id']) ? intval($input['app_user_id']) : 0;
    $action = isset($input['action']) ? trim($input['action']) : '';

    // Resolve discord_id from app_user_id if needed
    if (!$discord_id && $app_user_id) {
        $discord_id = _resolve_discord_id($conn, $app_user_id);
    }

    if (!$discord_id && !$app_user_id) {
        echo json_encode(array('success' => false, 'error' => 'Provide discord_id or app_user_id'));
        exit;
    }

    if ($action !== 'optout' && $action !== 'optin') {
        echo json_encode(array('success' => false, 'error' => 'action must be optout or optin'));
        exit;
    }

    if ($action === 'optout') {
        if ($discord_id) {
            $esc_id = $conn->real_escape_string($discord_id);
            $conn->query("INSERT IGNORE INTO accountability_followup_optouts (discord_user_id) VALUES ('" . $esc_id . "')");
        }
        if ($app_user_id && !$discord_id) {
            $conn->query("INSERT IGNORE INTO accountability_followup_optouts (app_user_id) VALUES (" . $app_user_id . ")");
        }
        echo json_encode(array('success' => true, 'opted_out' => true, 'message' => 'Morning follow-ups stopped.'));
    } else {
        // optin — remove the opt-out record
        $conditions = array();
        if ($discord_id) {
            $conditions[] = "discord_user_id = '" . $conn->real_escape_string($discord_id) . "'";
        }
        if ($app_user_id) {
            $conditions[] = "app_user_id = " . $app_user_id;
        }
        if (count($conditions) > 0) {
            $conn->query("DELETE FROM accountability_followup_optouts WHERE " . implode(' OR ', $conditions));
        }
        echo json_encode(array('success' => true, 'opted_out' => false, 'message' => 'Morning follow-ups re-enabled!'));
    }
    $conn->close();
    exit;
}

header('Content-Type: application/json');
echo json_encode(array('success' => false, 'error' => 'Method not allowed'));

// ── Helper: Check if user is opted out ──
function _is_opted_out($conn, $discord_id, $app_user_id) {
    $conditions = array();
    if ($discord_id) {
        $conditions[] = "discord_user_id = '" . $conn->real_escape_string($discord_id) . "'";
    }
    if ($app_user_id) {
        $conditions[] = "app_user_id = " . intval($app_user_id);
    }
    if (count($conditions) === 0) return false;

    $sql = "SELECT id FROM accountability_followup_optouts WHERE " . implode(' OR ', $conditions) . " LIMIT 1";
    $result = $conn->query($sql);
    return ($result && $result->num_rows > 0);
}

// ── Helper: Resolve discord_user_id from app_user_id ──
function _resolve_discord_id($conn, $app_user_id) {
    $sql = "SELECT discord_user_id FROM accountability_tasks WHERE app_user_id = " . intval($app_user_id) . " AND discord_user_id IS NOT NULL AND discord_user_id != '' LIMIT 1";
    $result = $conn->query($sql);
    if ($result && $row = $result->fetch_assoc()) {
        return $row['discord_user_id'];
    }
    // Also check accountability_users table
    $sql2 = "SELECT discord_user_id FROM accountability_users WHERE app_user_id = " . intval($app_user_id) . " AND discord_user_id IS NOT NULL AND discord_user_id != '' LIMIT 1";
    $result2 = $conn->query($sql2);
    if ($result2 && $row2 = $result2->fetch_assoc()) {
        return $row2['discord_user_id'];
    }
    return '';
}

// ── Helper: Render opt-out HTML page ──
function _render_optout_page($status, $errorMessage) {
    $html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">';
    $html .= '<meta name="viewport" content="width=device-width, initial-scale=1">';
    $html .= '<title>Accountability Follow-Up — Opt Out</title>';
    $html .= '<style>';
    $html .= 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; ';
    $html .= 'background: #0f172a; color: #e2e8f0; display: flex; align-items: center; justify-content: center; ';
    $html .= 'min-height: 100vh; margin: 0; padding: 20px; }';
    $html .= '.card { background: #1e293b; border-radius: 16px; padding: 40px; max-width: 480px; ';
    $html .= 'text-align: center; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }';
    $html .= '.icon { font-size: 3rem; margin-bottom: 16px; }';
    $html .= 'h1 { font-size: 1.5rem; margin: 0 0 12px; }';
    $html .= 'p { color: #94a3b8; line-height: 1.6; margin: 0 0 20px; }';
    $html .= '.btn { display: inline-block; padding: 12px 24px; border-radius: 8px; text-decoration: none; ';
    $html .= 'font-weight: 600; font-size: 0.9rem; transition: opacity 0.2s; }';
    $html .= '.btn:hover { opacity: 0.85; }';
    $html .= '.btn-primary { background: linear-gradient(135deg, #60a5fa, #a78bfa); color: #fff; }';
    $html .= '.btn-secondary { background: rgba(255,255,255,0.08); color: #94a3b8; margin-left: 8px; }';
    $html .= '.error { color: #f87171; }';
    $html .= '</style></head><body><div class="card">';

    if ($status === 'success') {
        $html .= '<div class="icon">🔕</div>';
        $html .= '<h1>Morning Follow-Ups Stopped</h1>';
        $html .= '<p>You will no longer receive daily morning goal follow-ups from the Accountability Coach bot.</p>';
        $html .= '<p>You can re-enable them anytime from your Accountability Dashboard.</p>';
        $html .= '<a class="btn btn-primary" href="https://findtorontoevents.ca/fc/#/accountability">Open Dashboard</a>';
    } else {
        $html .= '<div class="icon">⚠️</div>';
        $html .= '<h1 class="error">Something Went Wrong</h1>';
        $html .= '<p>' . htmlspecialchars($errorMessage) . '</p>';
        $html .= '<a class="btn btn-primary" href="https://findtorontoevents.ca/fc/#/accountability">Go to Dashboard</a>';
    }

    $html .= '</div></body></html>';
    return $html;
}
