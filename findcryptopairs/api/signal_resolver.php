<?php
/**
 * Universal Signal Resolver v1.0
 * ==============================
 * Resolves stale ACTIVE signals across ALL engines by checking current
 * prices against TP/SL levels. This fills the gap where individual engine
 * monitors don't run frequently enough.
 *
 * Actions:
 *   ?action=resolve_all  — Check all active UA predictions, resolve hits
 *   ?action=status       — Show resolution stats
 *
 * PHP 5.2 compatible.
 */
error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}

$action = isset($_GET['action']) ? $_GET['action'] : 'resolve_all';

switch ($action) {
    case 'resolve_all':  _sr_resolve_all($conn); break;
    case 'status':       _sr_status($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  RESOLVE ALL: Check current prices against TP/SL for all active
// ═══════════════════════════════════════════════════════════════
function _sr_resolve_all($conn) {
    $start = microtime(true);
    $resolved = 0;
    $expired = 0;
    $checked = 0;
    $errors = array();

    // Get all active predictions with TP/SL info
    $actives = array();
    $r = $conn->query("SELECT id, engine_name, pair, direction, entry_price, tp_pct, sl_pct, signal_time
        FROM ua_predictions WHERE status='ACTIVE' ORDER BY signal_time ASC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $actives[] = $row;
        }
    }

    if (count($actives) == 0) {
        echo json_encode(array('ok' => true, 'message' => 'No active signals', 'resolved' => 0));
        return;
    }

    // Get unique pairs
    $pairs = array();
    foreach ($actives as $a) {
        $pairs[$a['pair']] = true;
    }

    // Fetch current prices from Kraken
    $prices = array();
    $pair_list = implode(',', array_keys($pairs));
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_list;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $resp = curl_exec($ch);
    curl_close($ch);

    if ($resp) {
        $data = json_decode($resp, true);
        if (is_array($data) && isset($data['result'])) {
            foreach ($data['result'] as $kpair => $info) {
                // Kraken returns data with internal pair names
                $price = isset($info['c']) ? (float)$info['c'][0] : 0;
                if ($price > 0) {
                    $prices[$kpair] = $price;
                    // Also map common aliases
                    $clean = str_replace(array('XBT', 'XDG', 'XXBT', 'XXRP', 'XETH', 'XLTC'), array('BTC', 'DOGE', 'BTC', 'XRP', 'ETH', 'LTC'), $kpair);
                    $prices[$clean] = $price;
                }
            }
        }
    }

    // Also try pairs individually for those not in batch
    foreach (array_keys($pairs) as $p) {
        if (isset($prices[$p])) continue;
        // Try fetching individually
        $url2 = 'https://api.kraken.com/0/public/Ticker?pair=' . $p;
        $ch2 = curl_init($url2);
        curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch2, CURLOPT_TIMEOUT, 8);
        curl_setopt($ch2, CURLOPT_SSL_VERIFYPEER, false);
        $r2 = curl_exec($ch2);
        curl_close($ch2);
        if ($r2) {
            $d2 = json_decode($r2, true);
            if (is_array($d2) && isset($d2['result'])) {
                foreach ($d2['result'] as $kp => $info) {
                    $price = isset($info['c']) ? (float)$info['c'][0] : 0;
                    if ($price > 0) {
                        $prices[$p] = $price;
                        $prices[$kp] = $price;
                    }
                }
            }
        }
    }

    $now = time();

    foreach ($actives as $sig) {
        $checked++;
        $pair = $sig['pair'];
        $entry = (float)$sig['entry_price'];
        $tp_pct = (float)$sig['tp_pct'];
        $sl_pct = (float)$sig['sl_pct'];
        $direction = strtoupper($sig['direction']);
        $sig_time = strtotime($sig['signal_time']);

        if ($entry <= 0) continue;

        // Get current price
        $current = 0;
        if (isset($prices[$pair])) {
            $current = $prices[$pair];
        }

        if ($current <= 0) continue;

        // Calculate TP/SL prices
        if ($direction === 'LONG') {
            $tp_price = $entry * (1 + $tp_pct / 100);
            $sl_price = $entry * (1 - $sl_pct / 100);
        } else {
            $tp_price = $entry * (1 - $tp_pct / 100);
            $sl_price = $entry * (1 + $sl_pct / 100);
        }

        $pnl = 0;
        $status = '';
        $reason = '';

        // Check TP hit
        if ($direction === 'LONG' && $current >= $tp_price) {
            $status = 'RESOLVED';
            $reason = 'TP_HIT';
            $pnl = round(($current - $entry) / $entry * 100, 4);
        } elseif ($direction === 'SHORT' && $current <= $tp_price) {
            $status = 'RESOLVED';
            $reason = 'TP_HIT';
            $pnl = round(($entry - $current) / $entry * 100, 4);
        }
        // Check SL hit
        elseif ($direction === 'LONG' && $current <= $sl_price) {
            $status = 'RESOLVED';
            $reason = 'SL_HIT';
            $pnl = round(($current - $entry) / $entry * 100, 4);
        } elseif ($direction === 'SHORT' && $current >= $sl_price) {
            $status = 'RESOLVED';
            $reason = 'SL_HIT';
            $pnl = round(($entry - $current) / $entry * 100, 4);
        }

        // Check expiry (signals older than 7 days)
        if ($status === '' && $sig_time > 0 && ($now - $sig_time) > 7 * 86400) {
            $status = 'EXPIRED';
            $reason = 'EXPIRED_7D';
            if ($direction === 'LONG') {
                $pnl = round(($current - $entry) / $entry * 100, 4);
            } else {
                $pnl = round(($entry - $current) / $entry * 100, 4);
            }
        }

        if ($status !== '') {
            $conn->query(sprintf(
                "UPDATE ua_predictions SET status='%s', exit_price=%.8f, pnl_pct=%.4f, exit_reason='%s', resolved_at='%s'
                 WHERE id=%d AND status='ACTIVE'",
                $conn->real_escape_string($status),
                $current, $pnl,
                $conn->real_escape_string($reason),
                date('Y-m-d H:i:s'),
                (int)$sig['id']
            ));
            if ($conn->affected_rows > 0) {
                if ($status === 'EXPIRED') { $expired++; } else { $resolved++; }
            }
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'checked' => $checked,
        'resolved' => $resolved,
        'expired' => $expired,
        'prices_fetched' => count($prices),
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════
//  STATUS: Resolution stats
// ═══════════════════════════════════════════════════════════════
function _sr_status($conn) {
    $stats = array();

    $r = $conn->query("SELECT status, COUNT(*) as cnt FROM ua_predictions GROUP BY status");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $stats[$row['status']] = (int)$row['cnt'];
        }
    }

    $r2 = $conn->query("SELECT exit_reason, COUNT(*) as cnt FROM ua_predictions WHERE status != 'ACTIVE' GROUP BY exit_reason");
    $reasons = array();
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $reasons[$row['exit_reason']] = (int)$row['cnt'];
        }
    }

    echo json_encode(array(
        'ok' => true,
        'status_counts' => $stats,
        'resolution_reasons' => $reasons
    ));
}
