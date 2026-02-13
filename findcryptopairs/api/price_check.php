<?php
/**
 * Price Check API — Real-time price verification for BUY NOW system
 * Fetches live prices from Crypto.com Exchange + CoinGecko fallback
 * Used by the meme scanner's price verification modal
 *
 * Actions:
 *   live_price   — fetch current price for a single pair
 *   batch_price  — fetch prices for multiple pairs (up to 10)
 *   verify       — verify if a signal is still valid at current price
 *
 * PHP 5.2 compatible. No short arrays, no ?:, no ??.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');

$action = isset($_GET['action']) ? $_GET['action'] : 'live_price';

// Simple file-based cache to avoid hammering APIs (10s TTL)
$CACHE_DIR = dirname(__FILE__) . '/../../tmp';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

// CoinGecko ID map for common meme coins
$CG_ID_MAP = array(
    'DOGE_USDT'  => 'dogecoin',
    'SHIB_USDT'  => 'shiba-inu',
    'PEPE_USDT'  => 'pepe',
    'FLOKI_USDT' => 'floki',
    'BONK_USDT'  => 'bonk',
    'WIF_USDT'   => 'dogwifhat',
    'TURBO_USDT' => 'turbo',
    'NEIRO_USDT' => 'neiro-3',
    'PNUT_USDT'  => 'peanut-the-squirrel',
    'GOAT_USDT'  => 'goatseus-maximus',
    'MEME_USDT'  => 'memecoin-2',
    'MOG_USDT'   => 'mog-coin',
    'POPCAT_USDT'=> 'popcat',
    'BRETT_USDT' => 'brett',
    'MYRO_USDT'  => 'myro'
);

switch ($action) {
    case 'live_price':
        _pc_action_live_price();
        break;
    case 'batch_price':
        _pc_action_batch_price();
        break;
    case 'verify':
        _pc_action_verify();
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

// ═══════════════════════════════════════════════════════════════════════
//  LIVE PRICE — fetch real-time price for a pair
// ═══════════════════════════════════════════════════════════════════════
function _pc_action_live_price() {
    $pair = isset($_GET['pair']) ? strtoupper(trim($_GET['pair'])) : '';
    if (!$pair) {
        echo json_encode(array('ok' => false, 'error' => 'Missing pair parameter'));
        return;
    }

    $start = microtime(true);
    $result = _pc_fetch_price($pair);
    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    if ($result) {
        $result['latency_ms'] = $latency_ms;
        $result['ok'] = true;
        echo json_encode($result);
    } else {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Could not fetch price for ' . $pair,
            'latency_ms' => $latency_ms
        ));
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  BATCH PRICE — fetch prices for up to 10 pairs
// ═══════════════════════════════════════════════════════════════════════
function _pc_action_batch_price() {
    $pairs_raw = isset($_GET['pairs']) ? $_GET['pairs'] : '';
    if (!$pairs_raw) {
        echo json_encode(array('ok' => false, 'error' => 'Missing pairs parameter'));
        return;
    }

    $pairs = explode(',', strtoupper($pairs_raw));
    if (count($pairs) > 10) {
        $pairs = array_slice($pairs, 0, 10);
    }

    $start = microtime(true);
    $results = array();

    foreach ($pairs as $pair) {
        $pair = trim($pair);
        if (!$pair) continue;
        $price_data = _pc_fetch_price($pair);
        if ($price_data) {
            $price_data['pair'] = $pair;
            $results[] = $price_data;
        } else {
            $results[] = array('pair' => $pair, 'price' => null, 'error' => 'fetch_failed');
        }
    }

    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    echo json_encode(array(
        'ok' => true,
        'count' => count($results),
        'prices' => $results,
        'latency_ms' => $latency_ms
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  VERIFY — check if a signal is still valid at current price
// ═══════════════════════════════════════════════════════════════════════
function _pc_action_verify() {
    $pair = isset($_GET['pair']) ? strtoupper(trim($_GET['pair'])) : '';
    $signal_price = isset($_GET['signal_price']) ? floatval($_GET['signal_price']) : 0;
    $target_pct = isset($_GET['target_pct']) ? floatval($_GET['target_pct']) : 0;
    $risk_pct = isset($_GET['risk_pct']) ? floatval($_GET['risk_pct']) : 0;
    $user_price = isset($_GET['user_price']) ? floatval($_GET['user_price']) : 0;

    if (!$pair || $signal_price <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing pair or signal_price'));
        return;
    }

    $start = microtime(true);

    // Fetch live price or use user-supplied price
    $current_price = 0;
    $price_source = '';

    if ($user_price > 0) {
        $current_price = $user_price;
        $price_source = 'user_input';
    } else {
        $live = _pc_fetch_price($pair);
        if ($live) {
            $current_price = $live['price'];
            $price_source = $live['source'];
        }
    }

    if ($current_price <= 0) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Could not determine current price. Please enter manually.'
        ));
        return;
    }

    // Calculate drift and validity
    $price_change_pct = (($current_price - $signal_price) / $signal_price) * 100;
    $remaining_upside = $target_pct - $price_change_pct;
    $remaining_risk = $risk_pct + $price_change_pct;

    // Determine verdict
    $verdict = 'STILL_VALID';
    $verdict_detail = '';
    $verdict_color = 'green';

    if ($price_change_pct > $target_pct * 0.8) {
        $verdict = 'INVALIDATED';
        $verdict_detail = 'Price already moved ' . round($price_change_pct, 2) . '% — most upside is gone';
        $verdict_color = 'red';
    } elseif ($price_change_pct < -$risk_pct) {
        $verdict = 'INVALIDATED';
        $verdict_detail = 'Price dropped ' . round(abs($price_change_pct), 2) . '% — already past stop loss';
        $verdict_color = 'red';
    } elseif ($price_change_pct > $target_pct * 0.5) {
        $verdict = 'CAUTION';
        $verdict_detail = 'Price moved ' . round($price_change_pct, 2) . '% — reduced reward/risk ratio';
        $verdict_color = 'yellow';
    } elseif ($price_change_pct < -($risk_pct * 0.5)) {
        $verdict = 'CAUTION';
        $verdict_detail = 'Price dropped ' . round(abs($price_change_pct), 2) . '% — approaching stop loss';
        $verdict_color = 'yellow';
    } else {
        $verdict_detail = 'Signal still viable — ' . round($remaining_upside, 2) . '% potential upside remaining';
    }

    // Calculate new R:R at current price
    $new_tp_pct = $remaining_upside;
    $new_sl_pct = $remaining_risk;
    $new_rr = ($new_sl_pct > 0) ? round($new_tp_pct / $new_sl_pct, 2) : 0;

    // Adjusted TP/SL prices from current price
    $new_tp_price = $signal_price * (1 + $target_pct / 100);
    $new_sl_price = $signal_price * (1 - $risk_pct / 100);

    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    echo json_encode(array(
        'ok' => true,
        'pair' => $pair,
        'signal_price' => $signal_price,
        'current_price' => $current_price,
        'price_source' => $price_source,
        'price_change_pct' => round($price_change_pct, 4),
        'remaining_upside_pct' => round($remaining_upside, 2),
        'remaining_risk_pct' => round($remaining_risk, 2),
        'new_rr_ratio' => $new_rr,
        'target_price' => $new_tp_price,
        'stop_price' => $new_sl_price,
        'verdict' => $verdict,
        'verdict_detail' => $verdict_detail,
        'verdict_color' => $verdict_color,
        'latency_ms' => $latency_ms,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  PRICE FETCHER — Crypto.com primary, CoinGecko fallback
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_price($pair) {
    global $CACHE_DIR, $CG_ID_MAP;

    // Check cache first (10 second TTL)
    $cache_file = $CACHE_DIR . '/pc_' . md5($pair) . '.json';
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 10) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached && isset($cached['price'])) {
                $cached['cached'] = true;
                $cached['cache_age_s'] = $age;
                return $cached;
            }
        }
    }

    // Try Crypto.com Exchange first
    $cc_result = _pc_fetch_cryptocom($pair);
    if ($cc_result) {
        // Cache the result
        @file_put_contents($cache_file, json_encode($cc_result));
        return $cc_result;
    }

    // Fallback to CoinGecko
    $cg_result = _pc_fetch_coingecko($pair);
    if ($cg_result) {
        @file_put_contents($cache_file, json_encode($cg_result));
        return $cg_result;
    }

    return null;
}

function _pc_fetch_cryptocom($pair) {
    $url = 'https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=' . urlencode($pair);
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 6);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemePriceCheck/1.0');
    $resp = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if (!$resp || $http_code !== 200) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['result']['data'][0])) return null;

    $ticker = $data['result']['data'][0];
    $price = isset($ticker['a']) ? floatval($ticker['a']) : 0;
    $vol24h = isset($ticker['vv']) ? floatval($ticker['vv']) : 0;
    $chg24h = isset($ticker['c']) ? floatval($ticker['c']) * 100 : 0;
    $high24h = isset($ticker['h']) ? floatval($ticker['h']) : 0;
    $low24h = isset($ticker['l']) ? floatval($ticker['l']) : 0;

    if ($price <= 0) return null;

    return array(
        'price' => $price,
        'vol_24h' => $vol24h,
        'chg_24h' => round($chg24h, 2),
        'high_24h' => $high24h,
        'low_24h' => $low24h,
        'source' => 'crypto.com',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

function _pc_fetch_coingecko($pair) {
    global $CG_ID_MAP;

    // Map pair to CoinGecko ID
    $cg_id = isset($CG_ID_MAP[$pair]) ? $CG_ID_MAP[$pair] : null;

    if (!$cg_id) {
        // Try symbol-based lookup
        $symbol = strtolower(str_replace('_USDT', '', $pair));
        $url = 'https://api.coingecko.com/api/v3/simple/price?ids=' . urlencode($symbol) . '&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true';
    } else {
        $url = 'https://api.coingecko.com/api/v3/simple/price?ids=' . urlencode($cg_id) . '&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true';
    }

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemePriceCheck/1.0');
    $resp = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if (!$resp || $http_code !== 200) return null;

    $data = json_decode($resp, true);
    if (!is_array($data) || empty($data)) return null;

    // Get the first (and only) coin data
    $coin_data = null;
    foreach ($data as $key => $val) {
        $coin_data = $val;
        break;
    }

    if (!$coin_data || !isset($coin_data['usd'])) return null;

    $price = floatval($coin_data['usd']);
    if ($price <= 0) return null;

    $vol24h = isset($coin_data['usd_24h_vol']) ? floatval($coin_data['usd_24h_vol']) : 0;
    $chg24h = isset($coin_data['usd_24h_change']) ? floatval($coin_data['usd_24h_change']) : 0;

    return array(
        'price' => $price,
        'vol_24h' => $vol24h,
        'chg_24h' => round($chg24h, 2),
        'high_24h' => 0,
        'low_24h' => 0,
        'source' => 'coingecko',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}
?>
