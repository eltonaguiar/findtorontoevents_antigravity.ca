<?php
/**
 * Discord Interactions Endpoint — Standalone handler
 * Deployed at /discord-interactions.php (root level, no .htaccess restrictions)
 * Handles Discord slash commands including /fc-crypto
 */

error_reporting(0);
ini_set('display_errors', 0);

// === Signature Verification ===
$body = file_get_contents('php://input');
$signature = isset($_SERVER['HTTP_X_SIGNATURE_ED25519']) ? $_SERVER['HTTP_X_SIGNATURE_ED25519'] : '';
$timestamp = isset($_SERVER['HTTP_X_SIGNATURE_TIMESTAMP']) ? $_SERVER['HTTP_X_SIGNATURE_TIMESTAMP'] : '';

// Discord Public Key
$public_key = '276870d26bca9f11def6dd538f7c207515075f6c41a02c3d6c2161f34547ac14';

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    header('Content-Type: application/json');
    echo '{"error":"Method not allowed"}';
    exit;
}

// Verify signature
if (empty($signature) || empty($timestamp) || empty($public_key)) {
    header('HTTP/1.1 401 Unauthorized');
    header('Content-Type: application/json');
    echo '{"error":"Missing signature data"}';
    exit;
}

$verified = false;
if (function_exists('sodium_crypto_sign_verify_detached')) {
    try {
        $sig_bin = hex2bin($signature);
        $key_bin = hex2bin($public_key);
        $message = $timestamp . $body;
        $verified = sodium_crypto_sign_verify_detached($sig_bin, $message, $key_bin);
    } catch (Exception $e) {
        $verified = false;
    }
}

// Fallback: try the ed25519 pure PHP verifier
if (!$verified) {
    $ed25519_path = __DIR__ . '/favcreators/docs/api/ed25519_verify.php';
    if (!file_exists($ed25519_path)) {
        $ed25519_path = __DIR__ . '/fc/api/ed25519_verify.php';
    }
    if (file_exists($ed25519_path)) {
        require_once $ed25519_path;
        if (function_exists('verify_discord_request')) {
            $verified = verify_discord_request($body, $signature, $timestamp, $public_key);
        }
    }
}

if (!$verified) {
    header('HTTP/1.1 401 Unauthorized');
    header('Content-Type: application/json');
    echo '{"error":"Invalid request signature"}';
    exit;
}

// Parse interaction
$interaction = json_decode($body, true);
if (!$interaction) {
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo '{"error":"Invalid JSON"}';
    exit;
}

$type = isset($interaction['type']) ? intval($interaction['type']) : 0;

// Handle PING (Discord endpoint verification)
if ($type === 1) {
    header('Content-Type: application/json');
    echo '{"type":1}';
    exit;
}

// Handle Application Commands
if ($type === 2) {
    $data = isset($interaction['data']) ? $interaction['data'] : array();
    $command_name = isset($data['name']) ? $data['name'] : '';
    $options = isset($data['options']) ? $data['options'] : array();

    switch ($command_name) {
        case 'fc-crypto':
            handle_crypto($options);
            break;
        case 'fc-forex':
            respond_embed('💱 Forex Signals', "Forex signal engine is being enhanced.\n\n🔗 [Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)", 0x3b82f6);
            break;
        case 'fc-picks':
            handle_all_picks();
            break;
        case 'fc-momentum':
            handle_momentum();
            break;
        case 'fc-realtime':
            respond_embed('⚡ Real-Time Market Data', "View real-time trading signals:\n\n🔗 [Live Trading Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)\n🔗 [ML Gainer Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)\n🔗 [Crypto Pair Scanner](https://findtorontoevents.ca/findcryptopairs/)", 0x06b6d4);
            break;
        default:
            respond_embed('❓ Unknown Command', "Command `/$command_name` is not recognized.", 0xef4444);
            break;
    }
    exit;
}

header('HTTP/1.1 400 Bad Request');
header('Content-Type: application/json');
echo '{"error":"Unhandled interaction type"}';

// ═══════════════════════════════════════════════════════
//  COMMAND HANDLERS
// ═══════════════════════════════════════════════════════

function respond_embed($title, $description, $color, $fields = array(), $footer_text = 'Not financial advice')
{
    $embed = array(
        'title' => $title,
        'description' => $description,
        'color' => $color,
    );
    if (!empty($fields))
        $embed['fields'] = $fields;
    if ($footer_text)
        $embed['footer'] = array('text' => $footer_text);

    header('Content-Type: application/json');
    echo json_encode(array(
        'type' => 4,
        'data' => array(
            'embeds' => array($embed)
        )
    ));
}

function get_opt($options, $name, $default = null)
{
    foreach ($options as $opt) {
        if (isset($opt['name']) && $opt['name'] === $name) {
            return isset($opt['value']) ? $opt['value'] : $default;
        }
    }
    return $default;
}

function fmt_price($price)
{
    if ($price >= 100)
        return '$' . number_format($price, 2);
    if ($price >= 1)
        return '$' . number_format($price, 4);
    if ($price >= 0.001)
        return '$' . number_format($price, 6);
    return '$' . sprintf('%.3e', $price);
}

function load_json($path)
{
    if (!file_exists($path))
        return null;
    $raw = @file_get_contents($path);
    if (!$raw)
        return null;
    return json_decode($raw, true);
}

function handle_crypto($options)
{
    $timeline = get_opt($options, 'timeline', 'daytrader');
    $budget = get_opt($options, 'budget', 'medium');

    $active_picks = array();
    $source = '';

    // Try multiple data paths (relative to this file's location)
    $base_paths = array(
        __DIR__,                          // If deployed at root
        dirname(__DIR__),                  // One level up
    );

    $data_paths = array(
        '/updates/data/antigravity_ml_live_picks.json',
        '/updates/data/antigravity_ml_performance.json',
        '/updates/data/claude_ml_picks.json',
        '/claude_gainer_ml/tracker/claude_live_picks.json',
    );

    foreach ($base_paths as $base) {
        // Antigravity live picks (array of picks)
        $path = $base . '/updates/data/antigravity_ml_live_picks.json';
        if (file_exists($path)) {
            $data = load_json($path);
            if (is_array($data) && !empty($data) && isset($data[0])) {
                foreach ($data as $p) {
                    $p['_source'] = 'Antigravity ML';
                    $active_picks[] = $p;
                }
                $source = 'Antigravity ML';
                break;
            }
        }

        // Antigravity performance (has active_picks array)
        $path = $base . '/updates/data/antigravity_ml_performance.json';
        if (file_exists($path)) {
            $data = load_json($path);
            if (is_array($data) && isset($data['active_picks']) && !empty($data['active_picks'])) {
                foreach ($data['active_picks'] as $p) {
                    $p['_source'] = 'Antigravity ML';
                    $active_picks[] = $p;
                }
                $source = 'Antigravity ML Performance';
                break;
            }
        }

        // Claude ML picks
        $path = $base . '/updates/data/claude_ml_picks.json';
        if (file_exists($path)) {
            $data = load_json($path);
            if (is_array($data) && isset($data['picks']) && !empty($data['picks'])) {
                foreach ($data['picks'] as $p) {
                    if (!isset($p['status']) || $p['status'] === 'ACTIVE') {
                        $p['_source'] = 'Claude Code ML';
                        $active_picks[] = $p;
                    }
                }
                if (!empty($active_picks)) {
                    $source = 'Claude Code ML';
                    break;
                }
            }
        }

        // Claude tracker
        $path = $base . '/claude_gainer_ml/tracker/claude_live_picks.json';
        if (file_exists($path)) {
            $data = load_json($path);
            if (is_array($data) && isset($data['picks']) && !empty($data['picks'])) {
                foreach ($data['picks'] as $p) {
                    if (!isset($p['status']) || $p['status'] === 'ACTIVE') {
                        $p['_source'] = 'Claude Code ML';
                        $active_picks[] = $p;
                    }
                }
                if (!empty($active_picks)) {
                    $source = 'Claude Code ML';
                    break;
                }
            }
        }
    }

    // No picks found
    if (empty($active_picks)) {
        respond_embed(
            '📊 Crypto ML Picks — No Active Picks',
            "No active ML predictions currently available.\n\nThe ML scanner runs every 4 hours. Next scan should produce new picks.\n\n🔗 [View Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)\n🔗 [Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
            0xf59e0b,
            array(),
            'CLAUDE CODE ML v2.0 | Not financial advice'
        );
        return;
    }

    // Build embed fields
    $fields = array();
    $count = 0;
    foreach ($active_picks as $pick) {
        if ($count >= 8)
            break;

        $symbol = isset($pick['symbol']) ? strtoupper($pick['symbol']) : (isset($pick['coin_id']) ? strtoupper($pick['coin_id']) : '???');

        // Entry price
        $entry = 0;
        if (isset($pick['entry_price']))
            $entry = floatval($pick['entry_price']);
        elseif (isset($pick['price']))
            $entry = floatval($pick['price']);
        elseif (isset($pick['current_price']))
            $entry = floatval($pick['current_price']);

        // TP/SL
        $tp = isset($pick['tp_price']) ? floatval($pick['tp_price']) : (isset($pick['tp1_price']) ? floatval($pick['tp1_price']) : $entry * 1.10);
        $sl = isset($pick['sl_price']) ? floatval($pick['sl_price']) : $entry * 0.93;

        // Confidence
        $confidence = 'N/A';
        $prob = 0;
        if (isset($pick['pump_probability'])) {
            $prob = floatval($pick['pump_probability']);
            if ($prob >= 0.80)
                $confidence = 'VERY HIGH';
            elseif ($prob >= 0.65)
                $confidence = 'HIGH';
            elseif ($prob >= 0.50)
                $confidence = 'MEDIUM';
            else
                $confidence = 'LOW';
        } elseif (isset($pick['gainer_score'])) {
            $score = intval($pick['gainer_score']);
            $prob = $score / 100.0;
            if ($score >= 70)
                $confidence = 'HIGH';
            elseif ($score >= 50)
                $confidence = 'MEDIUM';
            else
                $confidence = 'LOW';
        } elseif (isset($pick['confidence'])) {
            $confidence = $pick['confidence'];
        }

        // Signals
        $signals = isset($pick['signals']) && is_array($pick['signals']) ? array_slice($pick['signals'], 0, 3) : array('ML Signal');
        $sig_str = implode(' | ', $signals);

        $tp_pct = $entry > 0 ? round(($tp - $entry) / $entry * 100, 1) : 0;
        $sl_pct = $entry > 0 ? round(($sl - $entry) / $entry * 100, 1) : 0;

        $src_label = isset($pick['_source']) ? $pick['_source'] : 'ML';

        $fields[] = array(
            'name' => $symbol . ' — ' . $confidence . ' (' . round($prob * 100) . '%)',
            'value' => 'Entry: ' . fmt_price($entry) . "\n" .
                'TP: ' . fmt_price($tp) . ' (+' . $tp_pct . "%)  SL: " . fmt_price($sl) . ' (' . $sl_pct . "%)\n" .
                'Signals: ' . $sig_str,
            'inline' => false,
        );

        $count++;
    }

    respond_embed(
        '📊 Crypto ML Picks — ' . count($active_picks) . ' Active',
        "**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT**\nSource: $source\n\n🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html) | [Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
        0x22c55e,
        $fields,
        "Timeline: $timeline | Budget: $budget | ⚠️ PAPER TRADE ONLY — Not financial advice"
    );
}

function handle_all_picks()
{
    $base = __DIR__;
    $total = 0;
    $lines = array();

    // Try Antigravity
    $path = $base . '/updates/data/antigravity_ml_live_picks.json';
    if (file_exists($path)) {
        $data = load_json($path);
        $cnt = is_array($data) ? count($data) : 0;
        $total += $cnt;
        $lines[] = "**Antigravity ML**: $cnt active picks";
    }

    // Try Claude
    $path = $base . '/updates/data/claude_ml_picks.json';
    if (file_exists($path)) {
        $data = load_json($path);
        $cnt = 0;
        if (is_array($data) && isset($data['picks'])) {
            foreach ($data['picks'] as $p) {
                if (isset($p['status']) && $p['status'] === 'ACTIVE')
                    $cnt++;
            }
        }
        $total += $cnt;
        $lines[] = "**Claude Code ML**: $cnt active picks";
    }

    if (empty($lines))
        $lines[] = "No scanner data available.";

    respond_embed(
        "📋 All Active Picks — $total Total",
        implode("\n", $lines) . "\n\n🔗 [Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)",
        0x6366f1
    );
}

function handle_momentum()
{
    $base = __DIR__;
    $desc = "Momentum data from the latest ML scan.\n\n";

    $path = $base . '/claude_gainer_ml/tracker/claude_scan_log.json';
    if (file_exists($path)) {
        $logs = load_json($path);
        if (is_array($logs) && !empty($logs)) {
            $latest = end($logs);
            $desc .= "**Last Scan**: " . (isset($latest['scan_time']) ? substr($latest['scan_time'], 0, 19) : 'N/A') . " UTC\n";
            $desc .= "**Coins Scanned**: " . (isset($latest['coins_scanned']) ? $latest['coins_scanned'] : 'N/A') . "\n";
            $desc .= "**Top Coin**: " . (isset($latest['top_coin']) ? strtoupper($latest['top_coin']) : 'N/A') . "\n";
            $desc .= "**Top Probability**: " . (isset($latest['top_probability']) ? round($latest['top_probability'] * 100, 1) . '%' : 'N/A') . "\n";
        }
    }

    $desc .= "\n🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)";

    respond_embed('📈 Momentum Indicators', $desc, 0x22c55e, array(), 'CLAUDE CODE ML | Not financial advice');
}
