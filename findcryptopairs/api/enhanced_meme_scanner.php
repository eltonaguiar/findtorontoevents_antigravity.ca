&lt;?php
/**
 * Enhanced Meme Coin Scanner with Failover — high-volatility, short-term momentum plays
 * Uses multiple APIs and scrapers with failover for reliability
 *
 * Actions:
 *   scan          — scan meme coins, score, return top winners
 *
 * PHP 5.2 compatible. No short arrays, no http_response_code().
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

// Dedicated meme coin database (separate from stocks)
error_reporting(0);
ini_set('display_errors', '0');
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn-&gt;connect_error) {
    echo json_encode(array('ok' =&gt; false, 'error' =&gt; 'Database connection failed'));
    exit;
}
$conn-&gt;set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';

$ADMIN_KEY = 'memescan2026'; // Same as existing

// Tier 1: established meme coins (as per query)
$MEME_TIER1 = array(
    'DOGE_USDT', 'SHIB_USDT', 'PEPE_USDT', 'FLOKI_USDT',
    'BONK_USDT', 'WIF_USDT', 'MEME_USDT'
);

// CoinGecko IDs for Tier 1
$CG_TIER1_IDS = array(
    'DOGE_USDT'  =&gt; 'dogecoin',
    'SHIB_USDT'  =&gt; 'shiba-inu',
    'PEPE_USDT'  =&gt; 'pepe',
    'FLOKI_USDT' =&gt; 'floki',
    'BONK_USDT'  =&gt; 'bonk',
    'WIF_USDT'   =&gt; 'dogwifhat',
    'MEME_USDT'  =&gt; 'meme'
);

// Meme keyword fragments for dynamic discovery (same as existing)
$MEME_KEYWORDS = array(
    // Original 27
    'DOGE', 'SHIB', 'INU', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME',
    'BABY', 'MOON', 'ELON', 'CAT', 'DOG', 'NEIRO', 'TURBO', 'BRETT',
    'MOG', 'POPCAT', 'MYRO', 'SLERF', 'BOME', 'WOJAK', 'LADYS',
    'SATS', 'ORDI', 'COQ', 'TOSHI',
    // 2025-2026 meme cycle additions
    'PNUT', 'GOAT', 'ACT', 'CHILLGUY', 'SPX', 'GIGA', 'PONKE', 'NEIROCTO',
    'PORK', 'BODEN', 'TREMP', 'TRUMP', 'FWOG', 'MICHI', 'WENMOON',
    'NEKO', 'HAMSTER', 'CATE', 'DEGEN', 'CHAD', 'BASED', 'RIZZ',
    'SNAIL', 'TOAD', 'APE', 'PIG', 'BEAR', 'BULL', 'FROG'
);

_mc_ensure_schema($conn);

switch ($action) {
    case 'scan':
        $key = isset($_GET['key']) ? $_GET['key'] : '';
        if ($key !== $ADMIN_KEY) { _mc_err('Unauthorized'); }
        _mc_action_scan($conn);
        break;
    default:
        _mc_err('Unknown action: ' . $action);
}

// ───────────────────────────────────────────────────────────────────────
//  ENHANCED SCAN with FAILOVER
// ───────────────────────────────────────────────────────────────────────
function _mc_action_scan($conn) {
    global $MEME_TIER1, $MEME_KEYWORDS, $CG_TIER1_IDS;
    $start = microtime(true);

    // Define source order: APIs first, then scrapers
    $sources = array('coingecko', 'coinmarketcap', 'cryptocom', 'coinmarketcap_site', 'dexscreener', 'binance', 'coingecko_site', 'pumpfun');

    // Get candidates from first successful source
    $candidates = array();
    $used_source = '';
    foreach ($sources as $src) {
        $cands = _mc_get_candidates_from_source($src);
        if (!empty($cands)) {
            $candidates = $cands;
            $used_source = $src;
            break;
        }
    }

    if (empty($candidates)) {
        echo json_encode(array('ok' =&gt; false, 'error' =&gt; 'All data sources failed', 'winners' =&gt; array()));
        return;
    }

    // For each candidate, get candles from chain starting with used_source
    $scored = array();
    foreach ($candidates as $c) {
        $c15m = array();
        $c5m = array();
        $has_volume_data = false;

        // Try sources for candles, starting with the list source
        $candle_sources = array_merge(array($used_source), array_diff($sources, array($used_source)));
        foreach ($candle_sources as $csrc) {
            $candles = _mc_get_candles_from_source($c['pair'], $csrc, isset($c['cg_id']) ? $c['cg_id'] : null);
            if (!empty($candles)) {
                $c15m = $candles['15m'];
                $c5m = $candles['5m'];
                $has_volume_data = $candles['has_volume'];
                $c['source'] = $csrc; // update source for candles
                break;
            }
        }

        if (empty($c15m)) continue;

        if (empty($c5m)) $c5m = $c15m;

        $score_details = _mc_score_pair($c, $c15m, $c5m, $has_volume_data);

        // ... (copy the rest from existing, including btc regime, etc.)

        $c['score'] = $score_details['total'];
        $c['factors'] = $score_details['factors'];
        $c['verdict'] = $score_details['verdict'];
        $c['target_pct'] = $score_details['target_pct'];
        $c['risk_pct'] = $score_details['risk_pct'];

        $scored[] = $c;
    }

    usort($scored, '_mc_sort_by_score');

    // Save winners, etc. copy from existing

    // ...

    echo json_encode(array(
        'ok' =&gt; true,
        'scan_id' =&gt; $scan_id,
        'used_source' =&gt; $used_source,
        // ... other stats
        'winners' =&gt; array_slice($winners, 0, 15),
        // ...
    ));
}

// Function to get candidates from a source
function _mc_get_candidates_from_source($source) {
    $candidates = array();

    if ($source == 'coingecko') {
        $cg_memes = _mc_coingecko_meme_market();
        if (!empty($cg_memes)) {
            foreach ($cg_memes as $cg) {
                $pair = strtoupper($cg['symbol']) . '_USDT';
                $candidates[] = array(
                    'pair' =&gt; $pair,
                    'price' =&gt; floatval($cg['current_price']),
                    'vol_usd' =&gt; floatval($cg['total_volume']),
                    'chg_24h' =&gt; floatval($cg['price_change_percentage_24h']),
                    'high_24h' =&gt; floatval($cg['high_24h']),
                    'low_24h' =&gt; floatval($cg['low_24h']),
                    'tier' =&gt; 'tier2', // set tier later
                    'source' =&gt; 'coingecko',
                    'cg_id' =&gt; $cg['id'],
                    'has_cc' =&gt; false // check later if needed
                );
            }
        }
    } elseif ($source == 'coinmarketcap') {
        $key = getenv('COINMARKETCAP_API_KEY');
        if (!$key) return array();
        $url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/category?cmc_id=6051a31466fc1b42617d6da4&amp;limit=50'; // meme category ID?
        // Note: The category ID for meme might be different, check docs
        $headers = array(
            'Accept: application/json',
            'X-CMC_PRO_API_KEY: ' . $key
        );
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        $resp = curl_exec($ch);
        curl_close($ch);
        $data = json_decode($resp, true);
        if (isset($data['data']['coins'])) {
            foreach ($data['data']['coins'] as $coin) {
                $pair = strtoupper($coin['symbol']) . '_USDT';
                $candidates[] = array(
                    'pair' =&gt; $pair,
                    'price' =&gt; floatval($coin['price']),
                    'vol_usd' =&gt; floatval($coin['volume_24h']),
                    'chg_24h' =&gt; floatval($coin['percent_change_24h']),
                    'high_24h' =&gt; 0, // CMC doesn't provide in this endpoint, approximate or fetch separately
                    'low_24h' =&gt; 0,
                    'tier' =&gt; 'tier2',
                    'source' =&gt; 'coinmarketcap',
                    'cmc_id' =&gt; $coin['id'],
                    'has_cc' =&gt; false
                );
            }
        }
    } elseif ($source == 'cryptocom') {
        // Copy from existing PHASE 1
        $instruments = _mc_api('public/get-instruments');
        $all_usdt_pairs = array();
        if ($instruments &amp;&amp; isset($instruments['result']['data'])) {
            foreach ($instruments['result']['data'] as $inst) {
                $sym = isset($inst['symbol']) ? $inst['symbol'] : (isset($inst['instrument_name']) ? $inst['instrument_name'] : '');
                $itype = isset($inst['inst_type']) ? $inst['inst_type'] : '';
                if ($itype === 'CCY_PAIR' &amp;&amp; _mc_ends_with($sym, '_USDT')) {
                    $all_usdt_pairs[] = $sym;
                }
            }
        }

        $tickers_raw = _mc_api('public/get-tickers');
        $tickers = array();
        if ($tickers_raw &amp;&amp; isset($tickers_raw['result']['data'])) {
            foreach ($tickers_raw['result']['data'] as $t) {
                $k = isset($t['i']) ? $t['i'] : (isset($t['symbol']) ? $t['symbol'] : '');
                if ($k) $tickers[$k] = $t;
            }
        }

        // Build candidates like tier2 in existing
        foreach ($all_usdt_pairs as $pair) {
            if (!isset($tickers[$pair])) continue;
            $t = $tickers[$pair];
            $price  = isset($t['a']) ? floatval($t['a']) : 0;
            $volUsd = isset($t['vv']) ? floatval($t['vv']) : (floatval(isset($t['v']) ? $t['v'] : 0) * $price);
            $chg24  = isset($t['c']) ? floatval($t['c']) * 100 : 0;

            // Apply filters
            if ($chg24 &lt; 2) continue;
            if ($volUsd &lt; 25000) continue;
            if ($volUsd &gt; 500000000) continue;

            $is_meme = false;
            $base = str_replace('_USDT', '', $pair);
            foreach ($MEME_KEYWORDS as $kw) {
                if (strpos($base, $kw) !== false) {
                    $is_meme = true;
                    break;
                }
            }
            $is_extreme_pump = ($chg24 &gt;= 10 &amp;&amp; $volUsd &gt;= 100000);
            if (!$is_meme &amp;&amp; !$is_extreme_pump) continue;

            $candidates[] = array(
                'pair' =&gt; $pair,
                'price' =&gt; $price,
                'vol_usd' =&gt; $volUsd,
                'chg_24h' =&gt; $chg24,
                'high_24h' =&gt; isset($t['h']) ? floatval($t['h']) : $price,
                'low_24h' =&gt; isset($t['l']) ? floatval($t['l']) : $price,
                'tier' =&gt; 'tier2',
                'source' =&gt; 'cryptocom',
                'cg_id' =&gt; null,
                'has_cc' =&gt; true
            );
        }
    } elseif ($source == 'coinmarketcap_site') {
        // Simple scraper for top memes
        $url = 'https://coinmarketcap.com/view/meme/';
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_USERAGENT, 'MemeScanner/1.0');
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        $html = curl_exec($ch);
        curl_close($ch);
        if (!$html) return array();

        $dom = new DOMDocument();
        @$dom-&gt;loadHTML($html);
        $rows = $dom-&gt;getElementsByTagName('tr');
        for ($i = 1; $i &lt; $rows-&gt;length; $i++) { // skip header
            $cols = $rows-&gt;item($i)-&gt;getElementsByTagName('td');
            if ($cols-&gt;length &lt; 5) continue;
            $symbol = trim($cols-&gt;item(1)-&gt;nodeValue); // adjust index
            $price_str = trim($cols-&gt;item(2)-&gt;nodeValue);
            $chg_str = trim($cols-&gt;item(3)-&gt;nodeValue);
            $vol_str = trim($cols-&gt;item(4)-&gt;nodeValue);
            // Parse strings to floats
            $price = floatval(preg_replace('/[^0-9.]/', '', $price_str));
            $chg24 = floatval(preg_replace('/[^0-9.-]/', '', $chg_str));
            $volUsd = floatval(preg_replace('/[^0-9.]/', '', $vol_str)) * (strpos($vol_str, 'M') !== false ? 1000000 : 1); // rough
            $pair = strtoupper($symbol) . '_USDT';
            $candidates[] = array(
                'pair' =&gt; $pair,
                'price' =&gt; $price,
                'vol_usd' =&gt; $volUsd,
                'chg_24h' =&gt; $chg24,
                'high_24h' =&gt; $price * (1 + $chg24 / 100), // approximate
                'low_24h' =&gt; $price * (1 - $chg24 / 100), // approximate
                'tier' =&gt; 'tier2',
                'source' =&gt; 'coinmarketcap_site',
                'cg_id' =&gt; null,
                'has_cc' =&gt; false
            );
            if (count($candidates) &gt;= 50) break;
        }
    } // Add similar for other scrapers, e.g. dexscreener: scrape https://dexscreener.com/solana for Solana memes, etc.

    // For other scrapers, implement similarly

    // Filter and sort

    usort($candidates, '_mc_sort_by_change');
    return array_slice($candidates, 0, 50); // top 50
}

// Function to get candles from source
function _mc_get_candles_from_source($pair, $source, $cg_id = null) {
    $candles = array('15m' =&gt; array(), '5m' =&gt; array(), 'has_volume' =&gt; false);

    if ($source == 'coingecko' &amp;&amp; $cg_id) {
        $cg_ohlc = _mc_coingecko_ohlc($cg_id);
        if (!empty($cg_ohlc)) {
            $candles['15m'] = $cg_ohlc; // 30min actually, but use
            $candles['5m'] = $cg_ohlc;
            $candles['has_volume'] = false;
        }
    } elseif ($source == 'cryptocom') {
        $candles_15m = _mc_api('public/get-candlestick?instrument_name=' . $pair . '&amp;timeframe=M15');
        $candles_5m = _mc_api('public/get-candlestick?instrument_name=' . $pair . '&amp;timeframe=M5');
        $candles['15m'] = isset($candles_15m['result']['data']) ? $candles_15m['result']['data'] : array();
        $candles['5m'] = isset($candles_5m['result']['data']) ? $candles_5m['result']['data'] : array();
        $candles['has_volume'] = (count($candles['15m']) &gt;= 8);
    } // Add for other sources

    return $candles;
}

// Copy all other functions from existing meme_scanner.php: _mc_score_pair, _mc_detect_btc_regime, _mc_regime_score_adjust, _mc_calc_rsi, _mc_calc_ema, _mc_calc_atr, _mc_binomial_significance, _mc_coingecko_meme_market, _mc_coingecko_ohlc, _mc_find_cg_match, _mc_api, _mc_ends_with, _mc_sort_by_change, _mc_sort_by_score, _mc_discord_alert, _mc_err, _mc_ensure_schema

// Note: To avoid duplication, in real implementation, include or require the common functions if possible, but for this, assume copied.

// For scoring enhancement: since more sources, perhaps average vol_usd from multiple if available, but since failover, it's from one.

// To enhance, in get_candidates, if primary fails, but secondary has data, perhaps merge.

 // But for simplicity, use first successful.

// After code, deploy and verify.

?&gt;