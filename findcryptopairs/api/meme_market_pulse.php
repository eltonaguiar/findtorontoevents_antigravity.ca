<?php
/**
 * Meme Market Pulse v2.0 — Real-time trending & gainers scanner
 * Scans Kraken meme coins directly for gainers, fetches CoinGecko trending,
 * and produces a #1 Top Pick recommendation.
 *
 * v2.0 Changes:
 *   - Negative momentum penalty: coins dropping 24h now capped at 5/10 max rating
 *   - Parabolic pump detection: >50% 24h change = score capped at 20
 *   - Volume gate raised from $50K to $100K minimum
 *   - Reduced negative momentum scores from 10 to 5/2/0 pts
 *
 * Actions:
 *   pulse          — full market pulse (Kraken gainers + CG trending + top pick)
 *   kraken_scan    — scan all known meme coins on Kraken for gainers
 *   trending       — CoinGecko trending coins
 *
 * PHP 5.2 compatible. No short arrays, no http_response_code().
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

error_reporting(0);
ini_set('display_errors', '0');

$action = isset($_GET['action']) ? $_GET['action'] : 'pulse';

// Simple file-based cache
$CACHE_DIR = dirname(__FILE__) . '/../../tmp';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

// ═══════════════════════════════════════════════════════════════════════
//  Known meme coins on Kraken — pair name => display symbol
//  Kraken uses special naming: DOGE→XDG, BTC→XBT
//  We try both USD and USDT variants
// ═══════════════════════════════════════════════════════════════════════
$KRAKEN_MEMES = array(
    // Format: internal_pair => array(display_name, kraken_pairs_to_try, coingecko_id)
    'DOGE' => array('DOGE', 'XDGUSD,DOGEUSD,XDGUSDT,DOGEUSDT', 'dogecoin'),
    'SHIB' => array('SHIB', 'SHIBUSD,SHIBUSDT', 'shiba-inu'),
    'PEPE' => array('PEPE', 'PEPEUSD,PEPEUSDT', 'pepe'),
    'FLOKI' => array('FLOKI', 'FLOKIUSD,FLOKIUSDT', 'floki'),
    'BONK' => array('BONK', 'BONKUSD,BONKUSDT', 'bonk'),
    'WIF' => array('WIF', 'WIFUSD,WIFUSDT', 'dogwifhat'),
    'TURBO' => array('TURBO', 'TURBOUSD,TURBOUSDT', 'turbo'),
    'NEIRO' => array('NEIRO', 'NEIROUSD,NEIROUSDT', 'neiro-3'),
    'MEME' => array('MEME', 'MEMEUSD,MEMEUSDT', 'memecoin-2'),
    'TRUMP' => array('TRUMP', 'TRUMPUSD,TRUMPUSDT', 'official-trump'),
    'FARTCOIN' => array('FARTCOIN', 'FARTCOINUSD,FARTCOINUSDT', 'fartcoin'),
    'PNUT' => array('PNUT', 'PNUTUSD,PNUTUSDT', 'peanut-the-squirrel'),
    'PENGU' => array('PENGU', 'PENGUUSD,PENGUUSDT', 'pudgy-penguins'),
    'POPCAT' => array('POPCAT', 'POPCATUSD,POPCATUSDT', 'popcat'),
    'BRETT' => array('BRETT', 'BRETTUSD,BRETTUSDT', 'brett'),
    'MOG' => array('MOG', 'MOGUSD,MOGUSDT', 'mog-coin'),
    'BOME' => array('BOME', 'BOMEUSD,BOMEUSDT', 'book-of-meme'),
    'ACT' => array('ACT', 'ACTUSD,ACTUSDT', 'act-i-the-ai-prophecy'),
    'SPX' => array('SPX6900', 'SPXUSD,SPXUSDT,SPX6900USD', 'spx6900'),
    'PONKE' => array('PONKE', 'PONKEUSD,PONKEUSDT', 'ponke'),
    'FWOG' => array('FWOG', 'FWOGUSD,FWOGUSDT', 'fwog'),
    'SLERF' => array('SLERF', 'SLERFUSD,SLERFUSDT', 'slerf'),
    'AI16Z' => array('AI16Z', 'AI16ZUSD,AI16ZUSDT', 'ai16z'),
    'VIRTUAL' => array('VIRTUAL', 'VIRTUALUSD,VIRTUALUSDT', 'virtual-protocol'),
    'MYRO' => array('MYRO', 'MYROUSD,MYROUSDT', 'myro'),
    'GOAT' => array('GOAT', 'GOATUSD,GOATUSDT', 'goatseus-maximus'),
    'MOODENG' => array('MOODENG', 'MOODENGUSD,MOODENGUSDT', 'moo-deng'),
    'GIGA' => array('GIGA', 'GIGAUSD,GIGAUSDT', 'gigachad-2'),
    'DEGEN' => array('DEGEN', 'DEGENUSD,DEGENUSDT', 'degen-base'),
    'BABYDOGE' => array('BABYDOGE', 'BABYDOGEUSD,BABYDOGEUSDT,BABYUSD', 'baby-doge-coin'),
    'WOJAK' => array('WOJAK', 'WOJAKUSD,WOJAKUSDT', 'wojak'),
    'SATS' => array('1000SATS', '1000SATSUSD,SATSUSD,1000SATSUSDT', '1000sats'),
    'COQ' => array('COQ', 'COQUSD,COQUSDT', 'coq-inu'),
    'DOG' => array('DOG', 'DOGUSD,DOGUSDT', 'dog-go-to-the-moon-runes'),
    'CHILLGUY' => array('CHILLGUY', 'CHILLGUYUSD,CHILLGUYUSDT', 'just-a-chill-guy')
);

switch ($action) {
    case 'pulse':
        _mp_action_pulse();
        break;
    case 'kraken_ranked':
        _mp_action_kraken_ranked();
        break;
    case 'kraken_pairs':
        _mp_action_kraken_pairs();
        break;
    case 'kraken_scan':
        _mp_action_kraken_scan();
        break;
    case 'trending':
        _mp_action_trending();
        break;
    case 'diag':
        _mp_action_diag();
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

// ═══════════════════════════════════════════════════════════════════════
//  DIAGNOSTICS — test Kraken API connectivity from server
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_diag()
{
    global $KRAKEN_MEMES, $CACHE_DIR;
    $result = array('ok' => true);

    // Test 1: Can we reach Kraken?
    $url = 'https://api.kraken.com/0/public/Ticker?pair=XDGUSD';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeMarketPulse/1.0');
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);

    $result['kraken_test'] = array(
        'url' => $url,
        'http_code' => $code,
        'curl_error' => $err,
        'response_length' => $resp ? strlen($resp) : 0,
        'response_preview' => $resp ? substr($resp, 0, 300) : null
    );

    // Test 2: Can we reach CoinGecko?
    $cg_url = 'https://api.coingecko.com/api/v3/ping';
    $cg_resp = _mp_curl($cg_url, 5);
    $result['coingecko_test'] = array(
        'url' => $cg_url,
        'response' => $cg_resp ? json_decode($cg_resp, true) : null
    );

    // Test 3: Cache directory writable?
    $result['cache_dir'] = $CACHE_DIR;
    $result['cache_writable'] = is_writable($CACHE_DIR) || @mkdir($CACHE_DIR, 0755, true);

    // Test 4: Kraken pairs count
    $result['kraken_memes_count'] = count($KRAKEN_MEMES);

    // Test 5: PHP curl available?
    $result['curl_available'] = function_exists('curl_init');

    echo json_encode($result);
}

// ═══════════════════════════════════════════════════════════════════════
//  KRAKEN PAIRS — return the canonical list of known Kraken meme pairs
//  Used by other files (scanner, frontend) as the single source of truth
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_kraken_pairs()
{
    global $KRAKEN_MEMES;
    $pairs = array();
    foreach ($KRAKEN_MEMES as $key => $info) {
        $pairs[] = array(
            'symbol' => $info[0],
            'key' => $key,
            'usdt_pair' => $key . '_USDT',
            'kraken_pairs_try' => $info[1],
            'coingecko_id' => $info[2]
        );
    }
    echo json_encode(array(
        'ok' => true,
        'count' => count($pairs),
        'pairs' => $pairs
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  KRAKEN RANKED — ALL Kraken meme coins ranked 1-10, always returns full list
//  This is the primary endpoint for the "What should I buy right now?" view
//
//  Score model (1-10 scale):
//    The rating combines 5 real-time factors from Kraken + CoinGecko:
//    1. Momentum (35%) — 24h price change sweet spot (3-15% ideal)
//    2. Volume (25%) — 24h USD volume on Kraken (liquidity)
//    3. Social Buzz (15%) — CoinGecko trending bonus
//    4. Entry Position (15%) — Where price sits in daily range (lower = better)
//    5. Spread (10%) — Bid/ask spread tightness (execution quality)
//
//  Urgency zones:
//    8-10: Strong buy — multiple factors aligned, act now
//    5-7:  Warming up — some momentum, watch closely
//    1-4:  Quiet — no signal, be patient
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_kraken_ranked()
{
    global $CACHE_DIR;
    $start = microtime(true);

    // Check cache (45s TTL — fast enough for real-time)
    $cache_file = $CACHE_DIR . '/mp_kraken_ranked.json';
    $force = isset($_GET['force']) && $_GET['force'] === '1';
    if ($force) {
        // Also clear batch cache so scan is truly fresh
        @unlink($CACHE_DIR . '/mp_kraken_batch.json');
    }
    if (!$force && file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 45) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached) {
                $cached['cached'] = true;
                $cached['cache_age_s'] = $age;
                echo json_encode($cached);
                return;
            }
        }
    }

    // 1. Scan all Kraken meme coins (batch ticker)
    $kraken_results = _mp_scan_kraken_memes();

    // 2. Fetch CoinGecko trending for social buzz bonus
    $cg_trending = _mp_fetch_cg_trending();

    // 3. Fetch CoinGecko meme gainers for cross-reference
    $cg_gainers = _mp_fetch_cg_meme_gainers();

    // 4. Score and rank ALL coins
    $top_pick_data = _mp_compute_top_pick($kraken_results, $cg_trending, $cg_gainers);
    $all_scored = isset($top_pick_data['all_scored']) ? $top_pick_data['all_scored'] : array();

    // 5. Convert pulse_score (0-100) to rating_10 (1-10) for each coin
    $rankings = array();
    for ($i = 0; $i < count($all_scored); $i++) {
        $coin = $all_scored[$i];
        $ps = intval($coin['pulse_score']);
        $r10 = _mp_score_to_rating($ps);
        $coin['rating_10'] = $r10;
        $coin['rating_label'] = _mp_rating_label($r10);
        $coin['rating_zone'] = _mp_rating_zone($r10);
        $coin['rank'] = $i + 1;
        $rankings[] = $coin;
    }

    // 6. Market mood
    $mood = _mp_market_mood($kraken_results);

    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    $result = array(
        'ok' => true,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'latency_ms' => $latency_ms,
        'cached' => false,
        'total_coins' => count($rankings),
        'mood' => $mood,
        'rankings' => $rankings,
        'model' => array(
            'name' => 'Meme Buy Rating',
            'version' => '3.0',
            'scale' => '1-10',
            'description' => 'Real-time buy rating for Kraken meme coins. Combines momentum, volume, social buzz, entry position, and spread quality. Higher = stronger buy signal.',
            'factors' => array(
                array('name' => 'Momentum', 'weight' => '35%', 'max_pts' => 35, 'description' => '24h price change. Sweet spot is +3% to +15% (gaining but not overextended). Over +25% = FOMO danger zone.'),
                array('name' => 'Volume', 'weight' => '25%', 'max_pts' => 25, 'description' => '24h USD volume on Kraken. Higher volume = better liquidity for entry and exit. $500K+ is ideal.'),
                array('name' => 'Social Buzz', 'weight' => '15%', 'max_pts' => 15, 'description' => 'Bonus if coin is trending on CoinGecko. Trending = social media buzz driving interest.'),
                array('name' => 'Entry Position', 'weight' => '15%', 'max_pts' => 15, 'description' => 'Where price sits in the 24h range. Near the low = better entry. Near the high = chasing.'),
                array('name' => 'Spread', 'weight' => '10%', 'max_pts' => 10, 'description' => 'Bid/ask spread on Kraken. Tighter spread = less slippage when you buy/sell.')
            ),
            'zones' => array(
                array('range' => '8-10', 'label' => 'Strong Buy', 'color' => '#22c55e', 'description' => 'Multiple factors aligned. Momentum, volume, and conditions favor a buy.'),
                array('range' => '5-7', 'label' => 'Warming Up', 'color' => '#f59e0b', 'description' => 'Some momentum building. Watch closely but conditions are not ideal yet.'),
                array('range' => '1-4', 'label' => 'Quiet', 'color' => '#6b7280', 'description' => 'No clear signal. Be patient and wait for better conditions.')
            ),
            'data_sources' => array('Kraken Ticker API (real-time)', 'CoinGecko Trending API', 'CoinGecko Meme Category API'),
            'disclaimer' => 'This is a momentum indicator, not financial advice. Meme coins can lose 50%+ in minutes. Never risk more than 1-2% of your portfolio on any single trade.'
        )
    );

    @file_put_contents($cache_file, json_encode($result));
    echo json_encode($result);
}

/**
 * Convert 0-100 pulse score to 1-10 rating.
 * Distribution designed so most coins cluster at 2-5 and only exceptional coins hit 8+.
 */
function _mp_score_to_rating($score)
{
    if ($score >= 90)
        return 10;
    if ($score >= 80)
        return 9;
    if ($score >= 70)
        return 8;
    if ($score >= 60)
        return 7;
    if ($score >= 50)
        return 6;
    if ($score >= 40)
        return 5;
    if ($score >= 30)
        return 4;
    if ($score >= 20)
        return 3;
    if ($score >= 10)
        return 2;
    return 1;
}

function _mp_rating_label($r)
{
    if ($r >= 9)
        return 'Exceptional';
    if ($r >= 8)
        return 'Strong Buy';
    if ($r >= 7)
        return 'Buy';
    if ($r >= 6)
        return 'Lean Buy';
    if ($r >= 5)
        return 'Warming Up';
    if ($r >= 4)
        return 'Mild Activity';
    if ($r >= 3)
        return 'Quiet';
    if ($r >= 2)
        return 'Very Quiet';
    return 'Dead';
}

function _mp_rating_zone($r)
{
    if ($r >= 8)
        return 'strong_buy';
    if ($r >= 5)
        return 'warming_up';
    return 'quiet';
}

// ═══════════════════════════════════════════════════════════════════════
//  PULSE — full market pulse: Kraken gainers + CG trending + Top Pick
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_pulse()
{
    global $CACHE_DIR;
    $start = microtime(true);

    // Check cache (60 second TTL for pulse — fast enough for real-time feel)
    $cache_file = $CACHE_DIR . '/mp_pulse.json';
    $force = isset($_GET['force']) && $_GET['force'] === '1';
    if (!$force && file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 60) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached) {
                $cached['cached'] = true;
                $cached['cache_age_s'] = $age;
                echo json_encode($cached);
                return;
            }
        }
    }

    // 1. Scan Kraken meme coins
    $kraken_results = _mp_scan_kraken_memes();

    // 2. Fetch CoinGecko trending
    $cg_trending = _mp_fetch_cg_trending();

    // 3. Fetch CoinGecko meme category top gainers
    $cg_gainers = _mp_fetch_cg_meme_gainers();

    // 4. Combine and produce Top Pick
    $top_pick = _mp_compute_top_pick($kraken_results, $cg_trending, $cg_gainers);

    // 5. Market mood summary
    $mood = _mp_market_mood($kraken_results);

    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    $result = array(
        'ok' => true,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'latency_ms' => $latency_ms,
        'cached' => false,
        'mood' => $mood,
        'top_pick' => $top_pick,
        'kraken_gainers' => array_slice($kraken_results, 0, 15),
        'kraken_total' => count($kraken_results),
        'trending' => array_slice($cg_trending, 0, 10),
        'cg_gainers' => array_slice($cg_gainers, 0, 10)
    );

    @file_put_contents($cache_file, json_encode($result));
    echo json_encode($result);
}

// ═══════════════════════════════════════════════════════════════════════
//  KRAKEN SCAN — scan all known meme coins on Kraken
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_kraken_scan()
{
    global $CACHE_DIR;
    $start = microtime(true);

    // Delete batch cache so we get fresh data
    $batch_cache = $CACHE_DIR . '/mp_kraken_batch.json';
    if (isset($_GET['force']) && $_GET['force'] === '1') {
        @unlink($batch_cache);
    }

    $results = _mp_scan_kraken_memes();
    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    $out = array(
        'ok' => true,
        'count' => count($results),
        'coins' => $results,
        'latency_ms' => $latency_ms,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC'
    );
    if (isset($GLOBALS['_mp_scan_debug'])) {
        $out['_debug'] = $GLOBALS['_mp_scan_debug'];
    }
    echo json_encode($out);
}

// ═══════════════════════════════════════════════════════════════════════
//  TRENDING — CoinGecko trending coins
// ═══════════════════════════════════════════════════════════════════════
function _mp_action_trending()
{
    $start = microtime(true);
    $trending = _mp_fetch_cg_trending();
    $latency_ms = round((microtime(true) - $start) * 1000, 1);

    echo json_encode(array(
        'ok' => true,
        'count' => count($trending),
        'trending' => $trending,
        'latency_ms' => $latency_ms,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  Scan all known meme coins on Kraken for gainers
//  Uses batch ticker API: one call per coin (Kraken doesn't support true batch)
//  But we cache aggressively to stay fast
// ═══════════════════════════════════════════════════════════════════════
function _mp_scan_kraken_memes()
{
    global $KRAKEN_MEMES, $CACHE_DIR;

    // Check batch cache (30s TTL)
    $batch_cache = $CACHE_DIR . '/mp_kraken_batch.json';
    if (file_exists($batch_cache)) {
        $age = time() - filemtime($batch_cache);
        if ($age < 30) {
            $cached = json_decode(file_get_contents($batch_cache), true);
            if ($cached && is_array($cached))
                return $cached;
        }
    }

    // Step 1: Discover which pairs actually exist on Kraken using AssetPairs API
    // Cache this for 5 minutes since it rarely changes
    $valid_pairs = _mp_get_valid_kraken_pairs();

    // Step 2: Match our meme list against valid Kraken pairs
    $matched_pairs = array();  // kraken_pair_name => coin_key
    $_debug_batch_info = array();

    foreach ($KRAKEN_MEMES as $key => $info) {
        $try_list = explode(',', $info[1]);
        foreach ($try_list as $kp) {
            $kp = trim($kp);
            $upper = strtoupper($kp);
            // Check if this pair exists on Kraken (exact match or normalized)
            if (isset($valid_pairs[$upper])) {
                $matched_pairs[$valid_pairs[$upper]] = $key;
                break; // found valid pair for this coin
            }
        }
    }

    $_debug_batch_info[] = array(
        'step' => 'pair_discovery',
        'valid_pairs_total' => count($valid_pairs),
        'matched_meme_pairs' => count($matched_pairs),
        'matched_keys' => array_values($matched_pairs)
    );

    if (empty($matched_pairs)) {
        $GLOBALS['_mp_scan_debug'] = array(
            'all_try_pairs_count' => 0,
            'batches_count' => 0,
            'tickers_found' => 0,
            'results_count' => 0,
            'seen_keys' => array(),
            'batch_info' => $_debug_batch_info
        );
        return array();
    }

    // Step 3: Batch-fetch tickers for valid pairs only
    $valid_pair_names = array_keys($matched_pairs);
    $batches = array_chunk($valid_pair_names, 15);
    $all_tickers = array();
    $pair_to_coin = $matched_pairs;

    foreach ($batches as $bi => $batch) {
        $pair_str = implode(',', $batch);
        $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_str;
        $resp = _mp_curl($url, 10);

        $batch_debug = array('batch' => $bi, 'pair_count' => count($batch), 'url_len' => strlen($url));

        if (!$resp) {
            $batch_debug['error'] = 'No response from curl';
            $_debug_batch_info[] = $batch_debug;
            continue;
        }

        $data = json_decode($resp, true);
        if (!$data) {
            $batch_debug['error'] = 'JSON decode failed';
            $batch_debug['resp_preview'] = substr($resp, 0, 200);
            $_debug_batch_info[] = $batch_debug;
            continue;
        }

        $kraken_errors = isset($data['error']) ? $data['error'] : array();
        $result_keys = isset($data['result']) ? array_keys($data['result']) : array();
        $batch_debug['kraken_errors'] = $kraken_errors;
        $batch_debug['result_count'] = count($result_keys);
        $batch_debug['result_pairs'] = $result_keys;
        $_debug_batch_info[] = $batch_debug;

        if (!isset($data['result']))
            continue;
        if (count($kraken_errors) > 0 && empty($data['result']))
            continue;

        foreach ($data['result'] as $kpair => $ticker) {
            $all_tickers[$kpair] = $ticker;
        }
    }

    // Process tickers into results
    $results = array();
    $seen = array(); // avoid duplicates (one coin may match multiple pair names)

    foreach ($all_tickers as $kpair => $ticker) {
        // Find which coin this is
        $coin_key = null;
        // Kraken returns internal pair names that may differ from what we queried
        // Try direct match first
        foreach ($pair_to_coin as $query_pair => $ck) {
            // Kraken might return XXDGZUSD for XDGUSD, etc. Check if the coin key matches
            if (isset($seen[$ck]))
                continue;
            // Check if query pair matches (case-insensitive)
            if (strtoupper($kpair) === strtoupper($query_pair)) {
                $coin_key = $ck;
                break;
            }
        }

        // Fallback: try to match by checking if the kraken pair contains the coin symbol
        if (!$coin_key) {
            foreach ($KRAKEN_MEMES as $ck => $info) {
                if (isset($seen[$ck]))
                    continue;
                $display = strtoupper($info[0]);
                $upper_kpair = strtoupper($kpair);
                // Check base symbol presence
                if (
                    strpos($upper_kpair, $display) !== false ||
                    ($ck === 'DOGE' && strpos($upper_kpair, 'XDG') !== false)
                ) {
                    $coin_key = $ck;
                    break;
                }
            }
        }

        if (!$coin_key || isset($seen[$coin_key]))
            continue;
        $seen[$coin_key] = true;

        $price = isset($ticker['c'][0]) ? floatval($ticker['c'][0]) : 0;
        if ($price <= 0)
            continue;

        $open = isset($ticker['o']) ? floatval($ticker['o']) : 0;
        $high24h = isset($ticker['h'][1]) ? floatval($ticker['h'][1]) : 0;
        $low24h = isset($ticker['l'][1]) ? floatval($ticker['l'][1]) : 0;
        $vol24h_units = isset($ticker['v'][1]) ? floatval($ticker['v'][1]) : 0;
        $vol24h_usd = $vol24h_units * $price;
        $vwap = isset($ticker['p'][1]) ? floatval($ticker['p'][1]) : 0;
        $trades = isset($ticker['t'][1]) ? intval($ticker['t'][1]) : 0;
        $ask = isset($ticker['a'][0]) ? floatval($ticker['a'][0]) : 0;
        $bid = isset($ticker['b'][0]) ? floatval($ticker['b'][0]) : 0;
        $spread_pct = ($ask > 0 && $bid > 0) ? round((($ask - $bid) / $ask) * 100, 3) : 0;

        $chg24h = 0;
        if ($open > 0) {
            $chg24h = round((($price - $open) / $open) * 100, 2);
        }

        // Intraday range %
        $range_pct = 0;
        if ($low24h > 0) {
            $range_pct = round((($high24h - $low24h) / $low24h) * 100, 2);
        }

        // Distance from 24h high
        $from_high_pct = 0;
        if ($high24h > 0) {
            $from_high_pct = round((($price - $high24h) / $high24h) * 100, 2);
        }

        $info = $KRAKEN_MEMES[$coin_key];
        $results[] = array(
            'symbol' => $info[0],
            'pair' => $coin_key . '_USDT',
            'kraken_pair' => $kpair,
            'coingecko_id' => $info[2],
            'price' => $price,
            'open' => $open,
            'chg_24h' => $chg24h,
            'high_24h' => $high24h,
            'low_24h' => $low24h,
            'vol_24h_usd' => round($vol24h_usd, 0),
            'vol_24h_units' => $vol24h_units,
            'vwap' => $vwap,
            'trades_24h' => $trades,
            'spread_pct' => $spread_pct,
            'range_pct' => $range_pct,
            'from_high_pct' => $from_high_pct,
            'source' => 'kraken',
            'canadian_eligible' => true
        );
    }

    // Sort by 24h change descending
    usort($results, '_mp_sort_by_change');

    @file_put_contents($batch_cache, json_encode($results));

    // Store debug info globally for diagnostics
    $GLOBALS['_mp_scan_debug'] = array(
        'all_try_pairs_count' => count($matched_pairs),
        'batches_count' => count($batches),
        'tickers_found' => count($all_tickers),
        'results_count' => count($results),
        'seen_keys' => array_keys($seen),
        'batch_info' => $_debug_batch_info
    );

    return $results;
}

// ═══════════════════════════════════════════════════════════════════════
//  Fetch CoinGecko trending coins
// ═══════════════════════════════════════════════════════════════════════
function _mp_fetch_cg_trending()
{
    global $CACHE_DIR;

    $cache_file = $CACHE_DIR . '/mp_cg_trending.json';
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 120) { // 2 min cache
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached)
                return $cached;
        }
    }

    $url = 'https://api.coingecko.com/api/v3/search/trending';
    $resp = _mp_curl($url, 8);
    if (!$resp)
        return array();

    $data = json_decode($resp, true);
    if (!$data || !isset($data['coins']))
        return array();

    $results = array();
    foreach ($data['coins'] as $c) {
        $item = isset($c['item']) ? $c['item'] : $c;
        $id = isset($item['id']) ? $item['id'] : '';
        $symbol = isset($item['symbol']) ? strtoupper($item['symbol']) : '';
        $name = isset($item['name']) ? $item['name'] : '';
        $mcap_rank = isset($item['market_cap_rank']) ? intval($item['market_cap_rank']) : 0;
        $thumb = isset($item['thumb']) ? $item['thumb'] : '';
        $price_btc = isset($item['price_btc']) ? floatval($item['price_btc']) : 0;
        $score = isset($item['score']) ? intval($item['score']) : 0;

        // Try to get USD price data if available
        $price_usd = 0;
        $chg24h = 0;
        $vol24h = 0;
        $mcap = 0;
        if (isset($item['data'])) {
            $d = $item['data'];
            $price_usd = isset($d['price']) ? floatval(str_replace(array('$', ','), '', $d['price'])) : 0;
            // price_change_percentage_24h might be in data
            if (isset($d['price_change_percentage_24h'])) {
                if (is_array($d['price_change_percentage_24h']) && isset($d['price_change_percentage_24h']['usd'])) {
                    $chg24h = round(floatval($d['price_change_percentage_24h']['usd']), 2);
                } else {
                    $chg24h = round(floatval($d['price_change_percentage_24h']), 2);
                }
            }
            $vol24h = isset($d['total_volume']) ? floatval(str_replace(array('$', ','), '', $d['total_volume'])) : 0;
            $mcap = isset($d['market_cap']) ? floatval(str_replace(array('$', ','), '', $d['market_cap'])) : 0;
        }

        // Check if this is on Kraken
        $on_kraken = _mp_is_on_kraken($symbol, $id);

        $results[] = array(
            'symbol' => $symbol,
            'name' => $name,
            'coingecko_id' => $id,
            'trending_rank' => $score + 1,
            'market_cap_rank' => $mcap_rank,
            'price_usd' => $price_usd,
            'chg_24h' => $chg24h,
            'vol_24h' => $vol24h,
            'market_cap' => $mcap,
            'thumb' => $thumb,
            'on_kraken' => $on_kraken
        );
    }

    @file_put_contents($cache_file, json_encode($results));
    return $results;
}

// ═══════════════════════════════════════════════════════════════════════
//  Fetch CoinGecko meme category top gainers
// ═══════════════════════════════════════════════════════════════════════
function _mp_fetch_cg_meme_gainers()
{
    global $CACHE_DIR;

    $cache_file = $CACHE_DIR . '/mp_cg_meme_gainers.json';
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 120) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached)
                return $cached;
        }
    }

    $url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=volume_desc&per_page=30&page=1&sparkline=false&price_change_percentage=24h';
    $resp = _mp_curl($url, 10);
    if (!$resp)
        return array();

    $data = json_decode($resp, true);
    if (!$data || !is_array($data))
        return array();

    $results = array();
    foreach ($data as $coin) {
        $symbol = isset($coin['symbol']) ? strtoupper($coin['symbol']) : '';
        $id = isset($coin['id']) ? $coin['id'] : '';
        $on_kraken = _mp_is_on_kraken($symbol, $id);

        $results[] = array(
            'symbol' => $symbol,
            'name' => isset($coin['name']) ? $coin['name'] : '',
            'coingecko_id' => $id,
            'price' => isset($coin['current_price']) ? floatval($coin['current_price']) : 0,
            'chg_24h' => isset($coin['price_change_percentage_24h']) ? round(floatval($coin['price_change_percentage_24h']), 2) : 0,
            'vol_24h' => isset($coin['total_volume']) ? floatval($coin['total_volume']) : 0,
            'market_cap' => isset($coin['market_cap']) ? floatval($coin['market_cap']) : 0,
            'high_24h' => isset($coin['high_24h']) ? floatval($coin['high_24h']) : 0,
            'low_24h' => isset($coin['low_24h']) ? floatval($coin['low_24h']) : 0,
            'mcap_rank' => isset($coin['market_cap_rank']) ? intval($coin['market_cap_rank']) : 0,
            'thumb' => isset($coin['image']) ? $coin['image'] : '',
            'on_kraken' => $on_kraken
        );
    }

    // Sort by 24h change descending
    usort($results, '_mp_sort_by_change');

    @file_put_contents($cache_file, json_encode($results));
    return $results;
}

// ═══════════════════════════════════════════════════════════════════════
//  Compute Top Pick — the #1 coin to buy right now
//  Scoring:
//   - Momentum (24h change): sweet spot 3-15% = max points, >25% = risky
//   - Volume: higher = better (liquidity for entry/exit)
//   - Kraken eligible: required for top pick
//   - Trending bonus: if on CoinGecko trending
//   - Range position: near low of day = better entry
//   - Spread: tighter = better execution
// ═══════════════════════════════════════════════════════════════════════
function _mp_compute_top_pick($kraken_coins, $trending, $cg_gainers)
{
    if (empty($kraken_coins)) {
        return array(
            'available' => false,
            'reason' => 'No Kraken meme coin data available'
        );
    }

    // Build trending set for bonus
    $trending_set = array();
    foreach ($trending as $t) {
        $sym = strtoupper($t['symbol']);
        $trending_set[$sym] = true;
        if (isset($t['coingecko_id'])) {
            $trending_set[$t['coingecko_id']] = true;
        }
    }

    // Build CG gainer set for cross-reference
    $cg_data = array();
    foreach ($cg_gainers as $g) {
        $sym = strtoupper($g['symbol']);
        $cg_data[$sym] = $g;
        if (isset($g['coingecko_id'])) {
            $cg_data[$g['coingecko_id']] = $g;
        }
    }

    $scored = array();
    foreach ($kraken_coins as $coin) {
        $chg = floatval($coin['chg_24h']);
        $vol = floatval($coin['vol_24h_usd']);
        $spread = floatval($coin['spread_pct']);
        $from_high = floatval($coin['from_high_pct']);
        $range = floatval($coin['range_pct']);
        $sym = strtoupper($coin['symbol']);

        // ── Momentum score (0-35) ──
        // Sweet spot: +3% to +15% = gaining but not overextended
        // v2.0: Negative momentum scores greatly reduced to prevent false BUYs
        $mom_score = 0;
        $is_negative_momentum = ($chg < 0);
        if ($chg >= 3 && $chg <= 8) {
            $mom_score = 35; // perfect entry zone
        } elseif ($chg > 8 && $chg <= 15) {
            $mom_score = 30; // strong but may be mid-pump
        } elseif ($chg > 15 && $chg <= 25) {
            $mom_score = 20; // risky, could retrace
        } elseif ($chg > 25 && $chg <= 50) {
            $mom_score = 10; // FOMO zone, dangerous
        } elseif ($chg > 50) {
            $mom_score = 0; // parabolic pump-and-dump territory
        } elseif ($chg >= 1 && $chg < 3) {
            $mom_score = 25; // mild momentum, early
        } elseif ($chg >= 0 && $chg < 1) {
            $mom_score = 15; // flat
        } else {
            // Negative — heavily penalized in v2.0
            if ($chg >= -1) {
                $mom_score = 5; // tiny dip, minimal score
            } elseif ($chg >= -3) {
                $mom_score = 2; // moderate dip
            } else {
                $mom_score = 0; // dumping hard
            }
        }

        // ── Volume score (0-25) ──
        // v2.0: Min $100K for consideration (raised from $50K), $500K+ ideal
        $vol_score = 0;
        if ($vol >= 5000000) {
            $vol_score = 25;
        } elseif ($vol >= 1000000) {
            $vol_score = 22;
        } elseif ($vol >= 500000) {
            $vol_score = 18;
        } elseif ($vol >= 100000) {
            $vol_score = 10;
        }
        // Below $100K = 0 volume score (too illiquid for safe entry/exit)

        // ── Trending bonus (0-15) ──
        $trend_score = 0;
        $is_trending = false;
        if (isset($trending_set[$sym]) || isset($trending_set[$coin['coingecko_id']])) {
            $trend_score = 15;
            $is_trending = true;
        }

        // ── Entry position score (0-15) ──
        // How close to the low of day? Closer = better entry
        $entry_score = 0;
        if ($range > 0) {
            $price_in_range = ($coin['price'] - $coin['low_24h']) / ($coin['high_24h'] - $coin['low_24h']);
            if ($price_in_range <= 0.3) {
                $entry_score = 15; // near bottom of range
            } elseif ($price_in_range <= 0.5) {
                $entry_score = 12; // lower half
            } elseif ($price_in_range <= 0.7) {
                $entry_score = 8; // upper half
            } else {
                $entry_score = 3; // near high
            }
        }

        // ── Spread score (0-10) ──
        // Tighter spread = better execution
        $spread_score = 0;
        if ($spread <= 0.05) {
            $spread_score = 10;
        } elseif ($spread <= 0.1) {
            $spread_score = 8;
        } elseif ($spread <= 0.3) {
            $spread_score = 5;
        } elseif ($spread <= 0.5) {
            $spread_score = 3;
        }

        $total = $mom_score + $vol_score + $trend_score + $entry_score + $spread_score;
        $liquidity_warning = ($vol < 100000);
        if ($liquidity_warning) {
            // Keep it in the rankings but force it to the bottom for top-pick selection.
            $total = 0;
        }

        // v2.0: Parabolic pump hard cap — coins that pumped >50% are dangerous
        if ($chg > 50) {
            $total = min($total, 20); // hard cap, never a BUY
        }

        // v2.0: Negative momentum cap — coins dropping should NOT be rated as BUY
        // Even with perfect volume/spread/entry, max rating = 5/10 (WARMING) when red
        if ($is_negative_momentum) {
            $total = min($total, 45); // caps at 5/10 rating max
        }

        // Confidence level
        $confidence = 'SKIP';
        $confidence_emoji = '';
        if ($total >= 75) {
            $confidence = 'STRONG';
            $confidence_emoji = 'strong';
        } elseif ($total >= 60) {
            $confidence = 'BUY';
            $confidence_emoji = 'buy';
        } elseif ($total >= 45) {
            $confidence = 'LEAN';
            $confidence_emoji = 'lean';
        }

        // Calculate suggested TP/SL based on momentum and volatility
        $tp_pct = 0;
        $sl_pct = 0;
        if ($chg >= 10) {
            $tp_pct = 5;
            $sl_pct = 3; // tight since already pumped
        } elseif ($chg >= 5) {
            $tp_pct = 6;
            $sl_pct = 3;
        } elseif ($chg >= 2) {
            $tp_pct = 8;
            $sl_pct = 4; // best R:R
        } elseif ($chg >= 0) {
            $tp_pct = 6;
            $sl_pct = 3;
        } else {
            $tp_pct = 5;
            $sl_pct = 4; // dip buy, tighter
        }

        // CG cross-reference data
        $cg_vol = 0;
        $cg_mcap = 0;
        if (isset($cg_data[$sym])) {
            $cg_vol = floatval($cg_data[$sym]['vol_24h']);
            $cg_mcap = floatval($cg_data[$sym]['market_cap']);
        } elseif (isset($cg_data[$coin['coingecko_id']])) {
            $cg_vol = floatval($cg_data[$coin['coingecko_id']]['vol_24h']);
            $cg_mcap = floatval($cg_data[$coin['coingecko_id']]['market_cap']);
        }

        $scored[] = array(
            'symbol' => $coin['symbol'],
            'pair' => $coin['pair'],
            'kraken_pair' => $coin['kraken_pair'],
            'coingecko_id' => $coin['coingecko_id'],
            'price' => $coin['price'],
            'chg_24h' => $chg,
            'vol_24h_usd' => $vol,
            'high_24h' => $coin['high_24h'],
            'low_24h' => $coin['low_24h'],
            'spread_pct' => $spread,
            'range_pct' => $range,
            'from_high_pct' => $from_high,
            'trades_24h' => $coin['trades_24h'],
            'pulse_score' => $total,
            'scores' => array(
                'momentum' => $mom_score,
                'volume' => $vol_score,
                'trending' => $trend_score,
                'entry_position' => $entry_score,
                'spread' => $spread_score
            ),
            'confidence' => $confidence,
            'is_trending' => $is_trending,
            'liquidity_warning' => $liquidity_warning,
            'tp_pct' => $tp_pct,
            'sl_pct' => $sl_pct,
            'tp_price' => round($coin['price'] * (1 + $tp_pct / 100), 10),
            'sl_price' => round($coin['price'] * (1 - $sl_pct / 100), 10),
            'rr_ratio' => $sl_pct > 0 ? round($tp_pct / $sl_pct, 2) : 0,
            'cg_vol_24h' => $cg_vol,
            'cg_market_cap' => $cg_mcap,
            'canadian_eligible' => true
        );
    }

    // Sort by pulse score descending
    usort($scored, '_mp_sort_by_pulse');

    if (empty($scored)) {
        return array(
            'available' => false,
            'reason' => 'No meme coins scored high enough'
        );
    }

    $pick = null;
    for ($i = 0; $i < count($scored); $i++) {
        if (floatval($scored[$i]['vol_24h_usd']) >= 100000) {
            $pick = $scored[$i];
            break;
        }
    }

    if (!$pick) {
        return array(
            'available' => false,
            'reason' => 'No meme coins meet the $100K liquidity floor',
            'all_scored' => $scored
        );
    }

    // Determine buy reasoning
    $reasons = array();
    if ($pick['scores']['momentum'] >= 30)
        $reasons[] = 'Strong momentum (+' . $pick['chg_24h'] . '% today)';
    elseif ($pick['scores']['momentum'] >= 20)
        $reasons[] = 'Solid momentum (+' . $pick['chg_24h'] . '% today)';
    elseif ($pick['chg_24h'] > 0)
        $reasons[] = 'Positive momentum (+' . $pick['chg_24h'] . '% today)';
    else
        $reasons[] = 'Small dip (' . $pick['chg_24h'] . '%) — potential bounce';

    if ($pick['is_trending'])
        $reasons[] = 'Trending on CoinGecko (social buzz)';
    if ($pick['scores']['volume'] >= 20)
        $reasons[] = 'High volume ($' . number_format($pick['vol_24h_usd'], 0) . ')';
    if ($pick['scores']['entry_position'] >= 12)
        $reasons[] = 'Near bottom of daily range (good entry)';
    if ($pick['scores']['spread'] >= 8)
        $reasons[] = 'Tight spread (' . $pick['spread_pct'] . '%)';
    if ($pick['cg_market_cap'] > 0)
        $reasons[] = 'Market cap: $' . _mp_format_number($pick['cg_market_cap']);

    $pick['reasons'] = $reasons;
    $pick['available'] = true;
    $pick['runner_up'] = count($scored) > 1 ? $scored[1] : null;
    $pick['all_scored'] = $scored;

    return $pick;
}

// ═══════════════════════════════════════════════════════════════════════
//  Market mood — overall meme market sentiment from Kraken data
// ═══════════════════════════════════════════════════════════════════════
function _mp_market_mood($kraken_coins)
{
    if (empty($kraken_coins)) {
        return array('mood' => 'unknown', 'label' => 'No Data', 'gainers' => 0, 'losers' => 0, 'avg_chg' => 0);
    }

    $gainers = 0;
    $losers = 0;
    $flat = 0;
    $total_chg = 0;
    $total_vol = 0;
    $big_movers = 0; // >5% change

    foreach ($kraken_coins as $c) {
        $chg = floatval($c['chg_24h']);
        $total_chg += $chg;
        $total_vol += floatval($c['vol_24h_usd']);
        if ($chg > 1)
            $gainers++;
        elseif ($chg < -1)
            $losers++;
        else
            $flat++;
        if (abs($chg) > 5)
            $big_movers++;
    }

    $n = count($kraken_coins);
    $avg_chg = round($total_chg / $n, 2);
    $gainer_ratio = $gainers / $n;

    $mood = 'neutral';
    $label = 'Mixed Market';
    if ($avg_chg > 5 && $gainer_ratio > 0.6) {
        $mood = 'euphoric';
        $label = 'Euphoric — Memes Pumping!';
    } elseif ($avg_chg > 2 && $gainer_ratio > 0.5) {
        $mood = 'bullish';
        $label = 'Bullish — Memes Gaining';
    } elseif ($avg_chg > 0 && $gainer_ratio > 0.4) {
        $mood = 'mild_bull';
        $label = 'Mildly Bullish';
    } elseif ($avg_chg < -5 && $gainer_ratio < 0.3) {
        $mood = 'panic';
        $label = 'Panic Selling — High Risk!';
    } elseif ($avg_chg < -2) {
        $mood = 'bearish';
        $label = 'Bearish — Memes Dropping';
    } elseif ($avg_chg < 0) {
        $mood = 'mild_bear';
        $label = 'Mildly Bearish';
    }

    return array(
        'mood' => $mood,
        'label' => $label,
        'gainers' => $gainers,
        'losers' => $losers,
        'flat' => $flat,
        'big_movers' => $big_movers,
        'avg_chg' => $avg_chg,
        'total_vol' => round($total_vol, 0),
        'coins_scanned' => $n
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  Helper: check if a symbol/id is on our Kraken meme list
// ═══════════════════════════════════════════════════════════════════════
function _mp_is_on_kraken($symbol, $cg_id)
{
    global $KRAKEN_MEMES;
    $upper = strtoupper($symbol);

    foreach ($KRAKEN_MEMES as $key => $info) {
        if ($upper === strtoupper($info[0]) || $upper === strtoupper($key))
            return true;
        if ($cg_id && $cg_id === $info[2])
            return true;
    }
    return false;
}

// ═══════════════════════════════════════════════════════════════════════
//  Helper: cURL fetch with timeout
// ═══════════════════════════════════════════════════════════════════════
/**
 * Fetch all valid trading pairs from Kraken's AssetPairs endpoint.
 * Returns a lookup: UPPERCASE_PAIR_NAME => actual_kraken_pair_name
 * Cached for 5 minutes.
 */
function _mp_get_valid_kraken_pairs()
{
    global $CACHE_DIR;
    $cache_file = $CACHE_DIR . '/mp_kraken_valid_pairs.json';

    // Cache for 5 minutes
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 300) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached && is_array($cached))
                return $cached;
        }
    }

    $url = 'https://api.kraken.com/0/public/AssetPairs';
    $resp = _mp_curl($url, 10);
    if (!$resp)
        return array();

    $data = json_decode($resp, true);
    if (!$data || !isset($data['result']))
        return array();

    $lookup = array();
    foreach ($data['result'] as $pair_name => $pair_info) {
        // Map both the official pair name and the altname (wsname)
        $upper = strtoupper($pair_name);
        $lookup[$upper] = $pair_name;

        // Also map the altname (e.g., XDGUSD -> XXDGZUSD)
        if (isset($pair_info['altname'])) {
            $alt_upper = strtoupper($pair_info['altname']);
            if (!isset($lookup[$alt_upper])) {
                $lookup[$alt_upper] = $pair_name;
            }
        }

        // Map wsname too (e.g., XDG/USD)
        if (isset($pair_info['wsname'])) {
            $ws = str_replace('/', '', strtoupper($pair_info['wsname']));
            if (!isset($lookup[$ws])) {
                $lookup[$ws] = $pair_name;
            }
        }
    }

    @file_put_contents($cache_file, json_encode($lookup));
    return $lookup;
}

function _mp_curl($url, $timeout)
{
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeMarketPulse/1.0');
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if (!$resp || $code < 200 || $code >= 300)
        return null;
    return $resp;
}

// ═══════════════════════════════════════════════════════════════════════
//  Sort helpers
// ═══════════════════════════════════════════════════════════════════════
function _mp_sort_by_change($a, $b)
{
    $ac = floatval($a['chg_24h']);
    $bc = floatval($b['chg_24h']);
    if ($ac == $bc)
        return 0;
    return ($ac > $bc) ? -1 : 1;
}

function _mp_sort_by_pulse($a, $b)
{
    $as = intval($a['pulse_score']);
    $bs = intval($b['pulse_score']);
    if ($as == $bs)
        return 0;
    return ($as > $bs) ? -1 : 1;
}

function _mp_format_number($n)
{
    if ($n >= 1000000000)
        return round($n / 1000000000, 1) . 'B';
    if ($n >= 1000000)
        return round($n / 1000000, 1) . 'M';
    if ($n >= 1000)
        return round($n / 1000, 0) . 'K';
    return '' . $n;
}
