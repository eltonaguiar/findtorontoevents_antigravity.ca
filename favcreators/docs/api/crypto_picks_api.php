<?php
/**
 * Crypto Picks API — Serves ML prediction data as JSON
 * Used by Discord bot, Cloudflare Worker, and external integrations
 * Bypasses ModSecurity restrictions on direct .json file access
 * 
 * Usage: GET /fc/api/crypto_picks_api.php?source=all
 *   ?source=antigravity — Antigravity ML picks only
 *   ?source=claude — Claude Code ML picks only
 *   ?source=all — All sources combined (default)
 *   ?format=discord — Format for Discord embed response
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Cache-Control: public, max-age=300'); // 5 min cache

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$source = isset($_GET['source']) ? $_GET['source'] : 'all';
$format = isset($_GET['format']) ? $_GET['format'] : 'raw';

// Use DOCUMENT_ROOT (confirmed: /home/www/findtorontoevents.ca on 50webs)
$base = $_SERVER['DOCUMENT_ROOT'];
if (!file_exists($base . '/updates/data')) {
    $base = '/home/www/findtorontoevents.ca'; // absolute fallback
}

// Data sources configuration
$sources = array(
    'antigravity_live' => $base . '/updates/data/antigravity_ml_live_picks.json',
    'antigravity_perf' => $base . '/updates/data/antigravity_ml_performance.json',
    'claude_picks' => $base . '/updates/data/claude_ml_picks.json',
    'claude_tracker' => $base . '/claude_gainer_ml/tracker/claude_live_picks.json',
    'claude_scan_log' => $base . '/claude_gainer_ml/tracker/claude_scan_log.json',
    'claude_performance' => $base . '/updates/data/claude_ml_performance.json',
);

$result = array(
    'status' => 'ok',
    'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
    'source_requested' => $source,
    'active_picks' => array(),
    'resolved_picks' => array(),
    'scan_info' => array(),
    'scorecard' => array(),
);

// Load Antigravity ML data
if ($source === 'all' || $source === 'antigravity') {
    // Live picks
    if (file_exists($sources['antigravity_live'])) {
        $raw = file_get_contents($sources['antigravity_live']);
        $data = json_decode($raw, true);
        if (is_array($data)) {
            foreach ($data as $pick) {
                $pick['_source'] = 'Antigravity ML';
                $result['active_picks'][] = $pick;
            }
        }
    }

    // Performance data
    if (file_exists($sources['antigravity_perf'])) {
        $raw = file_get_contents($sources['antigravity_perf']);
        $perf = json_decode($raw, true);
        if (is_array($perf)) {
            if (isset($perf['scorecard'])) {
                $result['scorecard']['antigravity'] = $perf['scorecard'];
            }
            if (isset($perf['active_picks']) && is_array($perf['active_picks'])) {
                foreach ($perf['active_picks'] as $pick) {
                    $pick['_source'] = 'Antigravity ML';
                    // Avoid duplicates
                    $exists = false;
                    foreach ($result['active_picks'] as $existing) {
                        if (isset($existing['coin_id']) && isset($pick['coin_id']) && $existing['coin_id'] === $pick['coin_id']) {
                            $exists = true;
                            break;
                        }
                    }
                    if (!$exists) {
                        $result['active_picks'][] = $pick;
                    }
                }
            }
            if (isset($perf['resolved_picks']) && is_array($perf['resolved_picks'])) {
                $result['resolved_picks'] = array_merge($result['resolved_picks'], $perf['resolved_picks']);
            }
            $result['scan_info']['antigravity'] = array(
                'last_run' => isset($perf['last_run']) ? $perf['last_run'] : 'unknown',
                'model_version' => isset($perf['model_version']) ? $perf['model_version'] : 'unknown',
            );
        }
    }
}

// Load Claude Code ML data
if ($source === 'all' || $source === 'claude') {
    // Claude picks
    $claude_file = file_exists($sources['claude_picks']) ? $sources['claude_picks'] : $sources['claude_tracker'];
    if (file_exists($claude_file)) {
        $raw = file_get_contents($claude_file);
        $data = json_decode($raw, true);
        if (is_array($data) && isset($data['picks'])) {
            foreach ($data['picks'] as $pick) {
                $pick['_source'] = 'Claude Code ML';
                if (isset($pick['status']) && $pick['status'] === 'ACTIVE') {
                    $exists = false;
                    foreach ($result['active_picks'] as $existing) {
                        $existing_sym = isset($existing['symbol']) ? $existing['symbol'] : '';
                        $pick_sym = isset($pick['symbol']) ? $pick['symbol'] : '';
                        if ($existing_sym === $pick_sym && $existing_sym !== '') {
                            $exists = true;
                            break;
                        }
                    }
                    if (!$exists) {
                        $result['active_picks'][] = $pick;
                    }
                } else {
                    $result['resolved_picks'][] = $pick;
                }
            }
        }
    }

    // Claude scan log
    if (file_exists($sources['claude_scan_log'])) {
        $raw = file_get_contents($sources['claude_scan_log']);
        $logs = json_decode($raw, true);
        if (is_array($logs) && !empty($logs)) {
            $latest = end($logs);
            $result['scan_info']['claude'] = $latest;
        }
    }

    // Claude performance
    if (file_exists($sources['claude_performance'])) {
        $raw = file_get_contents($sources['claude_performance']);
        $perf = json_decode($raw, true);
        if (is_array($perf) && isset($perf['scorecard'])) {
            $result['scorecard']['claude'] = $perf['scorecard'];
        }
    }
}

// Summary stats
$result['summary'] = array(
    'total_active' => count($result['active_picks']),
    'total_resolved' => count($result['resolved_picks']),
    'sources_loaded' => array_keys($result['scan_info']),
);

// Discord format
if ($format === 'discord') {
    $fields = array();
    foreach ($result['active_picks'] as $pick) {
        $symbol = isset($pick['symbol']) ? strtoupper($pick['symbol']) : (isset($pick['coin_id']) ? strtoupper($pick['coin_id']) : '???');

        $entry = 0;
        if (isset($pick['entry_price']))
            $entry = floatval($pick['entry_price']);
        elseif (isset($pick['price']))
            $entry = floatval($pick['price']);
        elseif (isset($pick['current_price']))
            $entry = floatval($pick['current_price']);

        $tp = isset($pick['tp_price']) ? floatval($pick['tp_price']) : (isset($pick['tp1_price']) ? floatval($pick['tp1_price']) : $entry * 1.10);
        $sl = isset($pick['sl_price']) ? floatval($pick['sl_price']) : $entry * 0.93;

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

        $signals = array();
        if (isset($pick['signals']) && is_array($pick['signals'])) {
            $signals = array_slice($pick['signals'], 0, 3);
        }
        $sig_str = !empty($signals) ? implode(' | ', $signals) : 'ML Signal';

        $source_name = isset($pick['_source']) ? $pick['_source'] : 'ML';

        $fields[] = array(
            'name' => $symbol . ' — ' . $confidence . ' (' . round($prob * 100) . '%)',
            'value' => 'Entry: $' . number_format($entry, $entry >= 1 ? 4 : 6) . "\n" .
                'TP: $' . number_format($tp, $tp >= 1 ? 4 : 6) . "\n" .
                'SL: $' . number_format($sl, $sl >= 1 ? 4 : 6) . "\n" .
                'Signals: ' . $sig_str . "\n" .
                'Source: ' . $source_name,
            'inline' => false,
        );
    }

    $result['discord_embed'] = array(
        'title' => 'Crypto ML Picks — ' . count($result['active_picks']) . ' Active',
        'description' => "**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT**\n\n" .
            "[Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html) | " .
            "[Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
        'color' => 0x22c55e,
        'fields' => $fields,
        'footer' => array('text' => 'PAPER TRADE ONLY — Not financial advice'),
    );
}

echo json_encode($result);
