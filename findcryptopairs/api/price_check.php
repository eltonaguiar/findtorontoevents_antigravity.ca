<?php
/**
 * Price Check API v2 — Multi-source real-time price verification
 * 6-source failover chain: Crypto.com → Binance → KuCoin → Gate.io → MEXC → CoinGecko → DexScreener
 *
 * Actions:
 *   live_price   — fetch current price for a single pair
 *   batch_price  — fetch prices for multiple pairs (up to 10)
 *   verify       — verify if a signal is still valid at current price
 *   sources      — list all available sources and their status
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

// CoinGecko ID map — expanded with 60+ meme coins
// This is the primary lookup table; CoinGecko search API is the dynamic fallback
$CG_ID_MAP = array(
    'DOGE_USDT'     => 'dogecoin',
    'SHIB_USDT'     => 'shiba-inu',
    'PEPE_USDT'     => 'pepe',
    'FLOKI_USDT'    => 'floki',
    'BONK_USDT'     => 'bonk',
    'WIF_USDT'      => 'dogwifhat',
    'TURBO_USDT'    => 'turbo',
    'NEIRO_USDT'    => 'neiro-3',
    'PNUT_USDT'     => 'peanut-the-squirrel',
    'GOAT_USDT'     => 'goatseus-maximus',
    'MEME_USDT'     => 'memecoin-2',
    'MOG_USDT'      => 'mog-coin',
    'POPCAT_USDT'   => 'popcat',
    'BRETT_USDT'    => 'brett',
    'MYRO_USDT'     => 'myro',
    'MOODENG_USDT'  => 'moo-deng',
    'ACT_USDT'      => 'act-i-the-ai-prophecy',
    'SPX_USDT'      => 'spx6900',
    'GIGA_USDT'     => 'gigachad-2',
    'PONKE_USDT'    => 'ponke',
    'FWOG_USDT'     => 'fwog',
    'SLERF_USDT'    => 'slerf',
    'BOME_USDT'     => 'book-of-meme',
    'WOJAK_USDT'    => 'wojak',
    'COQ_USDT'      => 'coq-inu',
    'TOSHI_USDT'    => 'toshi',
    'LADYS_USDT'    => 'milady-meme-coin',
    'TRUMP_USDT'    => 'official-trump',
    'DEGEN_USDT'    => 'degen-base',
    'HIGHER_USDT'   => 'higher',
    'ANDY_USDT'     => 'andy-on-base',
    'BABYDOGE_USDT' => 'baby-doge-coin',
    'KISHU_USDT'    => 'kishu-inu',
    'SATS_USDT'     => '1000sats',
    'ORDI_USDT'     => 'ordinals',
    'RATS_USDT'     => 'rats',
    'DOG_USDT'      => 'dog-go-to-the-moon-runes',
    'NEIROCTO_USDT' => 'neiro-on-eth',
    'PORK_USDT'     => 'pepefork',
    'CATDOG_USDT'   => 'catdog',
    'MICHI_USDT'    => 'michi',
    'MEW_USDT'      => 'cat-in-a-dogs-world',
    'WEN_USDT'      => 'wen-4',
    'BODEN_USDT'    => 'jeo-boden',
    'TREMP_USDT'    => 'doland-tremp',
    'CHAD_USDT'     => 'chad-index',
    'AI16Z_USDT'    => 'ai16z',
    'GRIFFAIN_USDT' => 'griffain',
    'PENGU_USDT'    => 'pudgy-penguins',
    'VIRTUAL_USDT'  => 'virtual-protocol',
    'FARTCOIN_USDT' => 'fartcoin',
    'CHILLGUY_USDT' => 'just-a-chill-guy'
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
    case 'sources':
        _pc_action_sources();
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
            'error' => 'Could not fetch price for ' . $pair . ' from any source',
            'sources_tried' => _pc_get_source_names(),
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
            $results[] = array('pair' => $pair, 'price' => null, 'error' => 'all_sources_failed');
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
            'error' => 'Could not determine current price from any of 7 sources. Please enter manually.',
            'sources_tried' => _pc_get_source_names()
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
//  SOURCES — list all available price sources
// ═══════════════════════════════════════════════════════════════════════
function _pc_action_sources() {
    echo json_encode(array(
        'ok' => true,
        'sources' => array(
            array('name' => 'Crypto.com Exchange', 'type' => 'api', 'priority' => 1, 'pairs' => '400+ USDT pairs'),
            array('name' => 'Binance', 'type' => 'api', 'priority' => 2, 'pairs' => '600+ USDT pairs'),
            array('name' => 'KuCoin', 'type' => 'api', 'priority' => 3, 'pairs' => '800+ USDT pairs (great meme coverage)'),
            array('name' => 'Gate.io', 'type' => 'api', 'priority' => 4, 'pairs' => '1700+ USDT pairs (widest meme coverage)'),
            array('name' => 'MEXC', 'type' => 'api', 'priority' => 5, 'pairs' => '2000+ USDT pairs (lists almost everything)'),
            array('name' => 'CoinGecko', 'type' => 'api', 'priority' => 6, 'pairs' => '15000+ coins via ID or search'),
            array('name' => 'DexScreener', 'type' => 'api', 'priority' => 7, 'pairs' => 'DEX pairs across all chains (Solana, ETH, BSC, Base)')
        ),
        'failover' => 'Each source is tried in order. First successful response is returned. 10s cache per pair.'
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  MASTER PRICE FETCHER — 7-source failover chain
//  Order: Crypto.com → Binance → KuCoin → Gate.io → MEXC → CoinGecko → DexScreener
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_price($pair) {
    global $CACHE_DIR;

    // Normalize pair format: ensure FOO_USDT
    $pair = strtoupper(trim($pair));
    if (strpos($pair, '/') !== false) {
        $pair = str_replace('/', '_', $pair);
    }

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

    // Source 1: Crypto.com Exchange
    $result = _pc_fetch_cryptocom($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 2: Binance
    $result = _pc_fetch_binance($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 3: KuCoin
    $result = _pc_fetch_kucoin($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 4: Gate.io
    $result = _pc_fetch_gateio($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 5: MEXC
    $result = _pc_fetch_mexc($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 6: CoinGecko (API with expanded map + dynamic search fallback)
    $result = _pc_fetch_coingecko($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    // Source 7: DexScreener (covers DEX-only tokens)
    $result = _pc_fetch_dexscreener($pair);
    if ($result) {
        @file_put_contents($cache_file, json_encode($result));
        return $result;
    }

    return null;
}

function _pc_get_source_names() {
    return array('crypto.com', 'binance', 'kucoin', 'gate.io', 'mexc', 'coingecko', 'dexscreener');
}

// ═══════════════════════════════════════════════════════════════════════
//  Helper: extract base symbol from pair (e.g. MOODENG_USDT → MOODENG)
// ═══════════════════════════════════════════════════════════════════════
function _pc_base_symbol($pair) {
    $parts = explode('_', $pair);
    return $parts[0];
}

// ═══════════════════════════════════════════════════════════════════════
//  Helper: cURL fetch with timeout
// ═══════════════════════════════════════════════════════════════════════
function _pc_curl($url, $timeout, $headers_arr) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemePriceCheck/2.0');
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    if (!empty($headers_arr)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_arr);
    }
    $resp = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if (!$resp || $http_code < 200 || $http_code >= 300) {
        return null;
    }
    return $resp;
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 1: Crypto.com Exchange
//  Docs: https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_cryptocom($pair) {
    $url = 'https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=' . urlencode($pair);
    $resp = _pc_curl($url, 5, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['result']['data'][0])) return null;

    $ticker = $data['result']['data'][0];
    $price = isset($ticker['a']) ? floatval($ticker['a']) : 0;
    if ($price <= 0) return null;

    $vol24h = isset($ticker['vv']) ? floatval($ticker['vv']) : 0;
    $chg24h = isset($ticker['c']) ? floatval($ticker['c']) * 100 : 0;
    $high24h = isset($ticker['h']) ? floatval($ticker['h']) : 0;
    $low24h = isset($ticker['l']) ? floatval($ticker['l']) : 0;

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

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 2: Binance
//  Docs: https://binance-docs.github.io/apidocs/spot/en/
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_binance($pair) {
    // Binance uses DOGEUSDT format (no underscore)
    $symbol = str_replace('_', '', $pair);
    $url = 'https://api.binance.com/api/v3/ticker/24hr?symbol=' . urlencode($symbol);
    $resp = _pc_curl($url, 5, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['lastPrice'])) return null;

    $price = floatval($data['lastPrice']);
    if ($price <= 0) return null;

    return array(
        'price' => $price,
        'vol_24h' => isset($data['quoteVolume']) ? floatval($data['quoteVolume']) : 0,
        'chg_24h' => isset($data['priceChangePercent']) ? round(floatval($data['priceChangePercent']), 2) : 0,
        'high_24h' => isset($data['highPrice']) ? floatval($data['highPrice']) : 0,
        'low_24h' => isset($data['lowPrice']) ? floatval($data['lowPrice']) : 0,
        'source' => 'binance',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 3: KuCoin
//  Docs: https://www.kucoin.com/docs/rest/spot-trading/market-data/get-24hr-stats
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_kucoin($pair) {
    // KuCoin uses DOGE-USDT format (dash)
    $symbol = str_replace('_', '-', $pair);
    $url = 'https://api.kucoin.com/api/v1/market/stats?symbol=' . urlencode($symbol);
    $resp = _pc_curl($url, 5, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['data']['last'])) return null;

    $d = $data['data'];
    $price = floatval($d['last']);
    if ($price <= 0) return null;

    $chg_pct = 0;
    if (isset($d['changeRate'])) {
        $chg_pct = round(floatval($d['changeRate']) * 100, 2);
    }

    return array(
        'price' => $price,
        'vol_24h' => isset($d['volValue']) ? floatval($d['volValue']) : 0,
        'chg_24h' => $chg_pct,
        'high_24h' => isset($d['high']) ? floatval($d['high']) : 0,
        'low_24h' => isset($d['low']) ? floatval($d['low']) : 0,
        'source' => 'kucoin',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 4: Gate.io
//  Docs: https://www.gate.io/docs/developers/apiv4/
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_gateio($pair) {
    // Gate.io uses DOGE_USDT format (underscore — same as ours!)
    $url = 'https://api.gateio.ws/api/v4/spot/tickers?currency_pair=' . urlencode($pair);
    $resp = _pc_curl($url, 5, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!is_array($data) || empty($data) || !isset($data[0]['last'])) return null;

    $t = $data[0];
    $price = floatval($t['last']);
    if ($price <= 0) return null;

    return array(
        'price' => $price,
        'vol_24h' => isset($t['quote_volume']) ? floatval($t['quote_volume']) : 0,
        'chg_24h' => isset($t['change_percentage']) ? round(floatval($t['change_percentage']), 2) : 0,
        'high_24h' => isset($t['high_24h']) ? floatval($t['high_24h']) : 0,
        'low_24h' => isset($t['low_24h']) ? floatval($t['low_24h']) : 0,
        'source' => 'gate.io',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 5: MEXC
//  Docs: https://mexcdevelop.github.io/apidocs/spot_v3_en/
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_mexc($pair) {
    // MEXC uses MOODENGUSDT format (no separator)
    $symbol = str_replace('_', '', $pair);
    $url = 'https://api.mexc.com/api/v3/ticker/24hr?symbol=' . urlencode($symbol);
    $resp = _pc_curl($url, 5, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['lastPrice'])) return null;

    $price = floatval($data['lastPrice']);
    if ($price <= 0) return null;

    return array(
        'price' => $price,
        'vol_24h' => isset($data['quoteVolume']) ? floatval($data['quoteVolume']) : 0,
        'chg_24h' => isset($data['priceChangePercent']) ? round(floatval($data['priceChangePercent']), 2) : 0,
        'high_24h' => isset($data['highPrice']) ? floatval($data['highPrice']) : 0,
        'low_24h' => isset($data['lowPrice']) ? floatval($data['lowPrice']) : 0,
        'source' => 'mexc',
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 6: CoinGecko (free API, no key required)
//  Uses hardcoded ID map first, then falls back to search API
//  Docs: https://www.coingecko.com/api/documentation
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_coingecko($pair) {
    global $CG_ID_MAP, $CACHE_DIR;

    // Step 1: Look up in our hardcoded ID map
    $cg_id = isset($CG_ID_MAP[$pair]) ? $CG_ID_MAP[$pair] : null;

    // Step 2: If not in map, try CoinGecko search API to find the ID dynamically
    if (!$cg_id) {
        $cg_id = _pc_coingecko_search($pair);
    }

    // Step 3: If still no ID, try using symbol directly (works for some coins)
    if (!$cg_id) {
        $cg_id = strtolower(_pc_base_symbol($pair));
    }

    // Fetch price with the resolved ID
    $url = 'https://api.coingecko.com/api/v3/simple/price?ids=' . urlencode($cg_id) . '&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true';
    $resp = _pc_curl($url, 8, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!is_array($data) || empty($data)) return null;

    // Get the first coin data
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
        'coingecko_id' => $cg_id,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}

/**
 * CoinGecko search: find coin ID dynamically by searching the symbol
 * Results are cached for 1 hour to avoid rate limits
 */
function _pc_coingecko_search($pair) {
    global $CACHE_DIR;

    $symbol = _pc_base_symbol($pair);
    $symbol_lower = strtolower($symbol);

    // Check search cache (1 hour TTL)
    $search_cache = $CACHE_DIR . '/cg_search_' . md5($symbol_lower) . '.json';
    if (file_exists($search_cache)) {
        $age = time() - filemtime($search_cache);
        if ($age < 3600) {
            $cached_id = file_get_contents($search_cache);
            if ($cached_id && $cached_id !== 'NOT_FOUND') {
                return $cached_id;
            }
            if ($cached_id === 'NOT_FOUND') {
                return null;
            }
        }
    }

    $url = 'https://api.coingecko.com/api/v3/search?query=' . urlencode($symbol_lower);
    $resp = _pc_curl($url, 8, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['coins']) || empty($data['coins'])) {
        @file_put_contents($search_cache, 'NOT_FOUND');
        return null;
    }

    // Find the best match: exact symbol match preferred
    $best_id = null;
    foreach ($data['coins'] as $coin) {
        $coin_sym = isset($coin['symbol']) ? strtoupper($coin['symbol']) : '';
        if ($coin_sym === strtoupper($symbol)) {
            $best_id = $coin['id'];
            break;
        }
    }

    // If no exact match, use first result
    if (!$best_id) {
        $best_id = $data['coins'][0]['id'];
    }

    // Cache the result
    @file_put_contents($search_cache, $best_id);
    return $best_id;
}

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE 7: DexScreener (DEX aggregator — covers Solana, ETH, BSC, Base)
//  Best for: tokens not on CEXes, new launches, Solana meme coins
//  Docs: https://docs.dexscreener.com/api/reference
// ═══════════════════════════════════════════════════════════════════════
function _pc_fetch_dexscreener($pair) {
    $symbol = _pc_base_symbol($pair);
    $url = 'https://api.dexscreener.com/latest/dex/search?q=' . urlencode($symbol);
    $resp = _pc_curl($url, 8, array());
    if (!$resp) return null;

    $data = json_decode($resp, true);
    if (!$data || !isset($data['pairs']) || empty($data['pairs'])) return null;

    // Find the best USDT or USDC pair with the highest liquidity
    $best = null;
    $best_liq = 0;

    foreach ($data['pairs'] as $p) {
        if (!isset($p['baseToken']['symbol']) || !isset($p['priceUsd'])) continue;

        $base_sym = strtoupper($p['baseToken']['symbol']);
        if ($base_sym !== strtoupper($symbol)) continue;

        // Prefer USDT/USDC quote, but accept SOL/WETH too (priceUsd is always in USD)
        $price_usd = floatval($p['priceUsd']);
        if ($price_usd <= 0) continue;

        $liq = 0;
        if (isset($p['liquidity']['usd'])) {
            $liq = floatval($p['liquidity']['usd']);
        }

        // Pick the highest-liquidity match
        if (!$best || $liq > $best_liq) {
            $best = $p;
            $best_liq = $liq;
        }
    }

    if (!$best) return null;

    $price = floatval($best['priceUsd']);
    if ($price <= 0) return null;

    $vol24h = 0;
    if (isset($best['volume']['h24'])) {
        $vol24h = floatval($best['volume']['h24']);
    }
    $chg24h = 0;
    if (isset($best['priceChange']['h24'])) {
        $chg24h = floatval($best['priceChange']['h24']);
    }

    $chain = isset($best['chainId']) ? $best['chainId'] : 'unknown';
    $dex = isset($best['dexId']) ? $best['dexId'] : 'unknown';

    return array(
        'price' => $price,
        'vol_24h' => $vol24h,
        'chg_24h' => round($chg24h, 2),
        'high_24h' => 0,
        'low_24h' => 0,
        'source' => 'dexscreener',
        'chain' => $chain,
        'dex' => $dex,
        'liquidity_usd' => $best_liq,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'cached' => false
    );
}
?>
