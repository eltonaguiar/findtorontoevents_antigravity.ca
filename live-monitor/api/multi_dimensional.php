<?php
/**
 * multi_dimensional.php — Multi-dimensional market context for the Investment Hub.
 * Provides Fear & Greed index, market regime, VIX, and dimensional scores.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=market   — Current market context (cached 15 min)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

$action    = isset($_GET['action']) ? $_GET['action'] : 'market';
$CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($CACHE_DIR)) { @mkdir($CACHE_DIR, 0755, true); }

function _md_cache_get($key, $ttl) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'md_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}
function _md_cache_set($key, $data) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'md_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

function _md_http_get($url, $timeout = 10) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'InvestmentHub/1.0 (findtorontoevents.ca)');
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    $ctx = stream_context_create(array('http' => array('timeout' => $timeout, 'user_agent' => 'InvestmentHub/1.0')));
    return @file_get_contents($url, false, $ctx);
}

// ── market: Fear & Greed + VIX + regime ──
if ($action === 'market') {
    $cached = _md_cache_get('market', 900); // 15 min TTL
    if ($cached) { echo json_encode($cached); exit; }

    // 1. Fear & Greed index — Alternative.me (free, no key required)
    $fg_value = null;
    $fg_label = null;
    $raw = _md_http_get('https://api.alternative.me/fng/?limit=1&format=json');
    if ($raw) {
        $fng = json_decode($raw, true);
        if (isset($fng['data'][0]['value'])) {
            $fg_value = (int)$fng['data'][0]['value'];
            $fg_label = isset($fng['data'][0]['value_classification'])
                ? $fng['data'][0]['value_classification']
                : ($fg_value >= 75 ? 'Extreme Greed' : ($fg_value >= 55 ? 'Greed' : ($fg_value >= 45 ? 'Neutral' : ($fg_value >= 25 ? 'Fear' : 'Extreme Fear'))));
        }
    }

    // 2. VIX — Yahoo Finance (^VIX)
    $vix = null;
    $vix_raw = _md_http_get('https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d');
    if ($vix_raw) {
        $vix_data = json_decode($vix_raw, true);
        $close = isset($vix_data['chart']['result'][0]['indicators']['quote'][0]['close'])
            ? $vix_data['chart']['result'][0]['indicators']['quote'][0]['close']
            : null;
        if (is_array($close) && !empty($close)) {
            $last = end($close);
            if ($last !== false && $last !== null) $vix = round((float)$last, 2);
        }
    }
    // Yahoo fallback — v7 endpoint
    if ($vix === null) {
        $vix_raw2 = _md_http_get('https://query2.finance.yahoo.com/v7/finance/quote?symbols=%5EVIX');
        if ($vix_raw2) {
            $vd2 = json_decode($vix_raw2, true);
            $rp  = isset($vd2['quoteResponse']['result'][0]['regularMarketPrice'])
                ? $vd2['quoteResponse']['result'][0]['regularMarketPrice']
                : null;
            if ($rp !== null) $vix = round((float)$rp, 2);
        }
    }

    // 3. Determine market regime from VIX + Fear & Greed
    $regime = 'Unknown';
    if ($vix !== null) {
        if ($vix >= 30) {
            $regime = 'High Volatility';
        } elseif ($vix >= 20) {
            $regime = ($fg_value !== null && $fg_value >= 50) ? 'Neutral' : 'Bear Trend';
        } elseif ($vix >= 13) {
            $regime = ($fg_value !== null && $fg_value >= 55) ? 'Bull Trend' : 'Consolidation';
        } else {
            $regime = 'Bull Trend';
        }
    } elseif ($fg_value !== null) {
        $regime = $fg_value >= 60 ? 'Bull Trend' : ($fg_value <= 35 ? 'Bear Trend' : 'Consolidation');
    }

    // 4. Dimensional scores (simple heuristics from available data)
    $dimensions = array();
    if ($fg_value !== null) {
        $dimensions['sentiment']   = round($fg_value / 100, 2);
        $dimensions['momentum']    = round(min(1.0, max(0.0, ($fg_value - 30) / 70)), 2);
    }
    if ($vix !== null) {
        $dimensions['volatility']  = round(min(1.0, $vix / 40), 2);
        $dimensions['risk_on']     = round(max(0.0, 1.0 - ($vix / 40)), 2);
    }

    $result = array(
        'fear_greed'   => array(
            'value'          => $fg_value !== null ? $fg_value : '?',
            'label'          => $fg_label !== null ? $fg_label : 'Unknown',
        ),
        'regime'       => $regime,
        'vix'          => $vix !== null ? $vix : '?',
        'dimensions'   => $dimensions,
        'top_picks'    => array(),
        'generated_at' => date('Y-m-d H:i:s'),
    );

    _md_cache_set('market', $result);
    echo json_encode($result);
    exit;
}

echo json_encode(array('error' => 'Unknown action'));
