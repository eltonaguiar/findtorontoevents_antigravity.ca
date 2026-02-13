<?php
/**
 * Kraken Meme Coin Scanner - Real-time BUY NOW recommendations
 * Fetches trending/gainers from Kraken and provides specific buy recommendations
 * PHP 5.2 compatible
 *
 * v2.0 FIXES (Feb 2026):
 *  - Unified pair list (scan + buynow use same coins)
 *  - Scoring redesigned: penalizes already-pumped coins, rewards setups
 *  - RSI fixed: momentum zone 60-80 rewarded, overbought >80 penalized
 *  - Pump-and-dump detection: parabolic rise + exhaustion filter
 *  - ATR extended to 24 candles for better volatility estimation
 *  - USD volume hard gate: require $100K+ 24h volume
 *  - BTC regime bear-market filter
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, must-revalidate');

error_reporting(0);
ini_set('display_errors', '0');

// Database connection
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';

switch ($action) {
    case 'scan':
        _kraken_meme_scan($conn);
        break;
    case 'buynow':
        _kraken_buy_now_recommendation($conn);
        break;
    case 'verify':
        _kraken_verify_price();
        break;
    case 'trending':
        _kraken_trending_memes();
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

/**
 * Main scanning function - fetches Kraken data and scores meme coins
 */
function _kraken_meme_scan($conn)
{
    $start_time = microtime(true);

    // UNIFIED pair list (Flaw #3/#5 fix) - single source of truth
    $meme_pairs = _kraken_get_meme_pairs();

    // BTC regime gate (Flaw #10 fix) — skip scan during bear markets
    $btc_regime = _kraken_detect_btc_regime();
    if ($btc_regime['regime'] === 'bear') {
        echo json_encode(array(
            'ok' => true,
            'timestamp' => date('c'),
            'btc_regime' => $btc_regime,
            'signals_found' => 0,
            'buy_now_candidates' => 0,
            'top_pick' => null,
            'message' => 'BTC in bear regime (' . $btc_regime['btc_change_24h'] . '%). Meme coin entries paused.',
            'disclaimer' => 'NOT FINANCIAL ADVICE. MEME COINS ARE EXTREMELY RISKY.'
        ));
        return;
    }

    $signals = array();
    $buy_now_candidates = array();

    foreach ($meme_pairs as $pair => $info) {
        $signal = _kraken_analyze_pair($pair, $info);
        if ($signal && $signal['score'] >= 60) {
            $signals[] = $signal;

            // Track high-confidence BUY NOW candidates
            if ($signal['score'] >= 75 && $signal['safety_score'] >= 7) {
                $buy_now_candidates[] = $signal;
            }
        }
    }

    // Sort by score descending
    usort($signals, '_kraken_sort_by_score');
    usort($buy_now_candidates, '_kraken_sort_by_score');

    // Select TOP BUY NOW recommendation
    $top_pick = null;
    if (!empty($buy_now_candidates)) {
        $top_pick = $buy_now_candidates[0];
        $top_pick['recommendation'] = 'BUY NOW';
        $top_pick['confidence'] = $top_pick['score'] >= 85 ? 'EXTREMELY HIGH' : ($top_pick['score'] >= 80 ? 'HIGH' : 'MODERATE');
        $top_pick['max_position_pct'] = $top_pick['safety_score'] >= 8 ? '2%' : '1%';
    }

    $elapsed = round(microtime(true) - $start_time, 3);

    // Save scan to database
    _kraken_save_scan($conn, $signals, $top_pick);

    echo json_encode(array(
        'ok' => true,
        'timestamp' => date('c'),
        'scanner_version' => '2.0',
        'data_freshness_seconds' => round($elapsed, 3),
        'btc_regime' => $btc_regime,
        'total_memes_analyzed' => count($meme_pairs),
        'signals_found' => count($signals),
        'buy_now_candidates' => count($buy_now_candidates),
        'top_pick' => $top_pick,
        'all_signals' => array_slice($signals, 0, 10),
        'disclaimer' => 'NOT FINANCIAL ADVICE. MEME COINS ARE EXTREMELY RISKY. NEVER INVEST MORE THAN YOU CAN AFFORD TO LOSE.'
    ));
}

/**
 * Analyze a specific pair from Kraken
 */
function _kraken_analyze_pair($pair, $info)
{
    // Fetch OHLC data from Kraken (last 24h, 1h intervals)
    $ohlc = _kraken_api('OHLC', array('pair' => $pair, 'interval' => 60));

    if (!$ohlc || !isset($ohlc['result'][$pair])) {
        return null;
    }

    $candles = $ohlc['result'][$pair];
    if (count($candles) < 7) {
        return null;
    }

    // Get latest ticker
    $ticker = _kraken_api('Ticker', array('pair' => $pair));
    if (!$ticker || !isset($ticker['result'][$pair])) {
        return null;
    }

    $tick = $ticker['result'][$pair];
    $current_price = floatval($tick['c'][0]);
    $volume_24h_units = floatval($tick['v'][1]);
    $volume_24h = $volume_24h_units * $current_price; // USD-denominated (Flaw #7 confirmed OK)

    // USD volume hard gate (Flaw #7 fix) — reject illiquid coins
    if ($volume_24h < 100000) {
        return null; // Skip coins with < $100K 24h USD volume
    }
    $high_24h = floatval($tick['h'][0]);
    $low_24h = floatval($tick['l'][0]);

    // Calculate price changes
    $price_1h_ago = floatval($candles[count($candles) - 2][4]);
    $price_6h_ago = floatval($candles[count($candles) - 7][4]);
    $price_24h_ago = floatval($candles[0][4]);

    $change_1h = (($current_price - $price_1h_ago) / $price_1h_ago) * 100;
    $change_6h = (($current_price - $price_6h_ago) / $price_6h_ago) * 100;
    $change_24h = (($current_price - $price_24h_ago) / $price_24h_ago) * 100;

    // Calculate volatility (ATR-like)
    $atr = _kraken_calc_atr($candles);
    $atr_pct = ($current_price > 0) ? ($atr / $current_price) * 100 : 0;

    // Calculate momentum
    $momentum = _kraken_calc_momentum($candles);

    // Volume analysis
    $vol_trend = _kraken_volume_trend($candles);

    // RSI calculation
    $rsi = _kraken_calc_rsi($candles);

    // ====================================================================
    // SCORING v2.0 — Detect SETUPS, not chasing pumps (Flaw #1 fix)
    // ====================================================================
    $score = 0;
    $factors = array();

    // --- Pump-and-dump detection (Flaw #8 fix) ---
    $is_parabolic = ($change_24h > 50 || ($change_1h > 15 && $change_6h > 25));
    $is_exhausting = ($rsi > 85 && $change_1h < 0); // RSI extreme + price turning
    $pump_dump_flag = $is_parabolic || $is_exhausting;
    $factors['pump_dump_detected'] = $pump_dump_flag ? 1 : 0;

    if ($pump_dump_flag) {
        // Hard reject pump-and-dump patterns
        return null;
    }

    // 1. Setup momentum (0-25 pts) — reward BUILDING momentum, not completed pumps
    $trend_score = 0;
    // Ideal: positive 1h with moderate (not extreme) 6h = momentum building
    if ($change_1h > 0.5 && $change_1h <= 5)
        $trend_score += 10;  // Active but not exhausted
    elseif ($change_1h > 5 && $change_1h <= 10)
        $trend_score += 5; // Getting hot, riskier
    // Penalize if 1h is negative (momentum fading) or too explosive (>10%)

    if ($change_6h > 2 && $change_6h <= 15)
        $trend_score += 10;   // Building over hours
    elseif ($change_6h > 0 && $change_6h <= 2)
        $trend_score += 7;  // Early move
    // 6h > 15% = likely already extended

    if ($change_24h > 5 && $change_24h <= 25)
        $trend_score += 5;   // Healthy daily move
    elseif ($change_24h > 0 && $change_24h <= 5)
        $trend_score += 3; // Quiet accumulation
    // 24h > 25% = extended move, don't reward
    $score += $trend_score;
    $factors['trend'] = $trend_score;

    // 2. Volume confirmation (0-20 pts) — volume rising = interest building
    $vol_conf_score = 0;
    if ($vol_trend > 1.5)
        $vol_conf_score = 20;
    elseif ($vol_trend > 1.2)
        $vol_conf_score = 15;
    elseif ($vol_trend > 1.0)
        $vol_conf_score = 10;
    $score += $vol_conf_score;
    $factors['volume'] = $vol_conf_score;

    // 3. RSI momentum zone (0-20 pts) — Flaw #6 fix: reward 60-80, not 50-70
    $rsi_score = 0;
    if ($rsi >= 60 && $rsi <= 75)
        $rsi_score = 20;   // Strong momentum, not overbought
    elseif ($rsi >= 50 && $rsi < 60)
        $rsi_score = 15; // Building momentum
    elseif ($rsi >= 75 && $rsi <= 80)
        $rsi_score = 10; // Getting hot
    elseif ($rsi > 80)
        $rsi_score = -10;               // OVERBOUGHT penalty
    elseif ($rsi < 40)
        $rsi_score = 5;                  // Oversold bounce potential
    $score += $rsi_score;
    $factors['rsi'] = $rsi_score;
    $factors['rsi_value'] = round($rsi, 1);

    // 4. Volatility bonus (0-15 pts) - moderate volatility means trade opportunity
    $vol_score = 0;
    if ($atr_pct >= 3 && $atr_pct <= 8)
        $vol_score = 15;
    elseif ($atr_pct >= 2 && $atr_pct < 3)
        $vol_score = 10;
    elseif ($atr_pct > 8 && $atr_pct <= 12)
        $vol_score = 8;
    // ATR > 12% = too chaotic, no bonus
    $score += $vol_score;
    $factors['volatility'] = $vol_score;

    // 5. Breakout positioning (0-20 pts) — reward approaching high, NOT at high
    $breakout_score = 0;
    $distance_from_high = (($high_24h - $current_price) / $high_24h) * 100;
    // Best entry: 3-8% below high (room to run without chasing the top)
    if ($distance_from_high >= 3 && $distance_from_high < 8)
        $breakout_score = 20;
    elseif ($distance_from_high >= 1 && $distance_from_high < 3)
        $breakout_score = 15;
    elseif ($distance_from_high >= 8 && $distance_from_high < 15)
        $breakout_score = 10;
    // At the high (<1%) or too far from high (>15%) = less attractive
    if ($distance_from_high < 1 && $rsi > 75)
        $breakout_score = -5; // At high + overbought = trap
    $score += $breakout_score;
    $factors['breakout'] = $breakout_score;
    $factors['distance_from_high_pct'] = round($distance_from_high, 2);

    // --- Overbought combo penalty (Flaw #1 continuation) ---
    if ($change_24h > 30 && $rsi > 75 && $distance_from_high < 2) {
        $score -= 15; // Heavy penalty: extended + overbought + at high = buying the top
        $factors['overbought_penalty'] = -15;
    }

    // Clamp score to 0-100
    $score = max(0, min(100, $score));

    // Safety score (0-10) - independent of buy score
    $safety_score = 5;
    if ($volume_24h > 1000000)
        $safety_score += 2; // $1M+ USD volume
    if ($atr_pct < 10)
        $safety_score += 1;          // Not too volatile
    if ($info['tier'] == 1)
        $safety_score += 2;     // Established meme
    if ($change_24h < 30)
        $safety_score += 1;       // Not parabolic (tightened from 50%)
    if ($change_1h > 0 && $change_1h < 10)
        $safety_score += 1; // Moving up but not exploded

    // Calculate targets based on volatility
    $target_pct = min(15, max(3, $atr_pct * 1.5));
    $stop_pct = min(8, max(2, $atr_pct * 0.8));

    $target_price = $current_price * (1 + $target_pct / 100);
    $stop_price = $current_price * (1 - $stop_pct / 100);

    // Signal rating
    $rating = 'HOLD';
    if ($score >= 85)
        $rating = 'EXTREMELY STRONG BUY';
    elseif ($score >= 75)
        $rating = 'STRONG BUY';
    elseif ($score >= 65)
        $rating = 'BUY';
    elseif ($score >= 60)
        $rating = 'LEAN BUY';

    return array(
        'pair' => $pair,
        'name' => $info['name'],
        'tier' => $info['tier'],
        'risk_level' => $info['risk'],
        'price' => round($current_price, 10),
        'price_formatted' => _kraken_format_price($current_price),
        'score' => $score,
        'safety_score' => $safety_score,
        'rating' => $rating,
        'change_1h' => round($change_1h, 2),
        'change_6h' => round($change_6h, 2),
        'change_24h' => round($change_24h, 2),
        'volume_24h' => round($volume_24h, 2),
        'atr_pct' => round($atr_pct, 2),
        'rsi' => round($rsi, 1),
        'factors' => $factors,
        'target_price' => round($target_price, 10),
        'target_price_formatted' => _kraken_format_price($target_price),
        'stop_price' => round($stop_price, 10),
        'stop_price_formatted' => _kraken_format_price($stop_price),
        'target_pct' => round($target_pct, 1),
        'stop_pct' => round($stop_pct, 1),
        'timestamp' => time()
    );
}

/**
 * Get specific BUY NOW recommendation
 */
function _kraken_buy_now_recommendation($conn)
{
    // UNIFIED pair list (Flaw #3/#5 fix)
    $meme_pairs = _kraken_get_meme_pairs();

    // BTC regime gate (Flaw #10 fix)
    $btc_regime = _kraken_detect_btc_regime();
    if ($btc_regime['regime'] === 'bear') {
        echo json_encode(array(
            'ok' => true,
            'has_recommendation' => false,
            'btc_regime' => $btc_regime,
            'message' => 'BTC bear regime - meme entries paused.',
            'timestamp' => date('c'),
            'disclaimer' => 'NOT FINANCIAL ADVICE.'
        ));
        return;
    }

    $candidates = array();

    foreach ($meme_pairs as $pair => $info) {
        $signal = _kraken_analyze_pair($pair, $info);
        if ($signal && $signal['score'] >= 70 && $signal['safety_score'] >= 6) {
            $candidates[] = $signal;
        }
    }

    usort($candidates, '_kraken_sort_by_score');

    if (empty($candidates)) {
        echo json_encode(array(
            'ok' => true,
            'has_recommendation' => false,
            'btc_regime' => $btc_regime,
            'message' => 'No BUY NOW candidates meet safety criteria. Market may be unfavorable for meme coin entries.',
            'timestamp' => date('c'),
            'disclaimer' => 'NOT FINANCIAL ADVICE.'
        ));
        return;
    }

    $pick = $candidates[0];
    $pick['recommendation'] = 'BUY NOW';
    $pick['confidence'] = $pick['score'] >= 85 ? 'EXTREMELY HIGH' : ($pick['score'] >= 80 ? 'HIGH' : 'MODERATE');
    $pick['position_size'] = $pick['safety_score'] >= 8 ? 'Up to 2% of portfolio' : 'Up to 1% of portfolio';
    $pick['time_horizon'] = '2-24 hours';
    $pick['rationale'] = _kraken_build_rationale($pick);

    echo json_encode(array(
        'ok' => true,
        'has_recommendation' => true,
        'scanner_version' => '2.0',
        'btc_regime' => $btc_regime,
        'timestamp' => date('c'),
        'pick' => $pick,
        'alternatives' => array_slice($candidates, 1, 2),
        'disclaimer' => 'NOT FINANCIAL ADVICE. MEME COINS ARE EXTREMELY RISKY. THIS SIGNAL CAN CHANGE RAPIDLY.',
        'warning' => 'Prices can move >10% in minutes. Verify current price before buying.'
    ));
}

/**
 * Verify current price in real-time
 */
function _kraken_verify_price()
{
    $pair = isset($_GET['pair']) ? strtoupper($_GET['pair']) : 'PEPEUSD';

    $ticker = _kraken_api('Ticker', array('pair' => $pair));

    if (!$ticker || !isset($ticker['result'][$pair])) {
        echo json_encode(array('ok' => false, 'error' => 'Could not fetch price'));
        return;
    }

    $tick = $ticker['result'][$pair];
    $price = floatval($tick['c'][0]);
    $bid = floatval($tick['b'][0]);
    $ask = floatval($tick['a'][0]);
    $spread = (($ask - $bid) / $bid) * 100;

    echo json_encode(array(
        'ok' => true,
        'pair' => $pair,
        'price' => $price,
        'price_formatted' => _kraken_format_price($price),
        'bid' => $bid,
        'ask' => $ask,
        'spread_pct' => round($spread, 3),
        'timestamp' => time(),
        'iso_time' => date('c')
    ));
}

/**
 * Get trending meme coins
 */
function _kraken_trending_memes()
{
    $meme_pairs = array_keys(_kraken_get_meme_pairs()); // Unified pair list

    $trending = array();

    foreach ($meme_pairs as $pair) {
        $ticker = _kraken_api('Ticker', array('pair' => $pair));
        if ($ticker && isset($ticker['result'][$pair])) {
            $tick = $ticker['result'][$pair];
            $price = floatval($tick['c'][0]);
            $open = isset($tick['o']) ? floatval($tick['o']) : 0;
            $change_24h = $open > 0 ? (($price - $open) / $open) * 100 : 0;
            $volume = floatval($tick['v'][1]);

            $trending[] = array(
                'pair' => $pair,
                'price' => $price,
                'price_formatted' => _kraken_format_price($price),
                'change_24h_pct' => round($change_24h, 2),
                'volume_24h' => round($volume, 2),
                'trend' => $change_24h > 10 ? 'STRONG_UP' : ($change_24h > 0 ? 'UP' : ($change_24h > -10 ? 'DOWN' : 'STRONG_DOWN'))
            );
        }
    }

    // Sort by 24h change
    usort($trending, function ($a, $b) {
        return $b['change_24h_pct'] - $a['change_24h_pct'];
    });

    echo json_encode(array(
        'ok' => true,
        'timestamp' => date('c'),
        'trending' => $trending,
        'top_gainer' => $trending[0],
        'top_loser' => $trending[count($trending) - 1]
    ));
}

/**
 * Kraken API wrapper
 */
function _kraken_api($method, $params = array())
{
    $base_url = 'https://api.kraken.com/0/public/' . $method;

    if (!empty($params)) {
        $query_string = '';
        foreach ($params as $key => $val) {
            if ($query_string != '')
                $query_string .= '&';
            $query_string .= urlencode($key) . '=' . urlencode($val);
        }
        $base_url .= '?' . $query_string;
    }

    $ch = curl_init($base_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'KrakenMemeScanner/1.0');

    $response = curl_exec($ch);
    curl_close($ch);

    if (!$response)
        return null;

    $data = json_decode($response, true);
    if (isset($data['error']) && !empty($data['error'])) {
        return null;
    }

    return $data;
}

/**
 * Calculate ATR from candles
 */
function _kraken_calc_atr($candles, $period = 24)
{ // Flaw #9 fix: extended from 14 to 24
    if (count($candles) < $period + 1) {
        $period = max(1, count($candles) - 1); // Use what we have
    }

    $tr_sum = 0;
    $count = 0;

    for ($i = max(1, count($candles) - $period); $i < count($candles); $i++) {
        $high = floatval($candles[$i][2]);
        $low = floatval($candles[$i][3]);
        $prev_close = floatval($candles[$i - 1][4]);

        $tr = max($high - $low, abs($high - $prev_close), abs($low - $prev_close));
        $tr_sum += $tr;
        $count++;
    }

    return $count > 0 ? $tr_sum / $count : 0;
}

/**
 * Calculate momentum
 */
function _kraken_calc_momentum($candles)
{
    if (count($candles) < 10)
        return 0;

    $recent = floatval($candles[count($candles) - 1][4]);
    $past = floatval($candles[count($candles) - 6][4]);

    return (($recent - $past) / $past) * 100;
}

/**
 * Volume trend analysis
 */
function _kraken_volume_trend($candles)
{
    if (count($candles) < 10)
        return 1;

    $recent_vol = 0;
    $past_vol = 0;

    for ($i = count($candles) - 5; $i < count($candles); $i++) {
        $recent_vol += floatval($candles[$i][6]);
    }

    for ($i = count($candles) - 10; $i < count($candles) - 5; $i++) {
        $past_vol += floatval($candles[$i][6]);
    }

    return $past_vol > 0 ? $recent_vol / $past_vol : 1;
}

/**
 * Calculate RSI
 */
function _kraken_calc_rsi($candles, $period = 14)
{
    if (count($candles) < $period + 1)
        return 50;

    $gains = 0;
    $losses = 0;
    $count = 0;

    for ($i = count($candles) - $period; $i < count($candles); $i++) {
        $change = floatval($candles[$i][4]) - floatval($candles[$i - 1][4]);
        if ($change > 0) {
            $gains += $change;
        } else {
            $losses += abs($change);
        }
        $count++;
    }

    if ($count == 0)
        return 50;

    $avg_gain = $gains / $period;
    $avg_loss = $losses / $period;

    if ($avg_loss == 0)
        return 100;

    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

/**
 * Format price with appropriate decimals
 */
function _kraken_format_price($price)
{
    if ($price >= 1)
        return number_format($price, 4);
    if ($price >= 0.01)
        return number_format($price, 6);
    if ($price >= 0.0001)
        return number_format($price, 8);
    return number_format($price, 10);
}

/**
 * Build rationale string
 */
function _kraken_build_rationale($pick)
{
    $parts = array();

    if ($pick['change_1h'] > 2)
        $parts[] = 'Strong 1h momentum (+' . $pick['change_1h'] . '%)';
    elseif ($pick['change_1h'] > 0)
        $parts[] = 'Positive 1h trend (+' . $pick['change_1h'] . '%)';

    if ($pick['factors']['volume'] >= 15)
        $parts[] = 'High volume confirmation';
    if ($pick['factors']['rsi'] >= 15)
        $parts[] = 'RSI in optimal zone (' . $pick['rsi'] . ')';
    if ($pick['factors']['breakout'] >= 15)
        $parts[] = 'Near 24h high (breakout potential)';

    if ($pick['tier'] == 1)
        $parts[] = 'Established meme coin (Tier 1)';
    else
        $parts[] = 'Emerging meme (Tier 2 - higher risk/reward)';

    return implode('; ', $parts);
}

/**
 * Sort by score
 */
function _kraken_sort_by_score($a, $b)
{
    return $b['score'] - $a['score'];
}

/**
 * UNIFIED meme pair list — single source of truth (Flaw #3/#5 fix)
 * Both scan() and buynow() use this same list.
 */
function _kraken_get_meme_pairs()
{
    return array(
        'PEPEUSD' => array('name' => 'PEPE', 'tier' => 2, 'risk' => 'high'),
        'FLOKIUSD' => array('name' => 'FLOKI', 'tier' => 2, 'risk' => 'high'),
        'BONKUSD' => array('name' => 'BONK', 'tier' => 2, 'risk' => 'high'),
        'SHIBUSD' => array('name' => 'SHIB', 'tier' => 1, 'risk' => 'medium'),
        'DOGEUSD' => array('name' => 'DOGE', 'tier' => 1, 'risk' => 'medium'),
        'WIFUSD' => array('name' => 'WIF', 'tier' => 2, 'risk' => 'high'),
        'MOGUSD' => array('name' => 'MOG', 'tier' => 2, 'risk' => 'extreme'),
        'POPCATUSD' => array('name' => 'POPCAT', 'tier' => 2, 'risk' => 'high'),
        'NEIROUSD' => array('name' => 'NEIRO', 'tier' => 2, 'risk' => 'extreme'),
        'GIGAUSD' => array('name' => 'GIGA', 'tier' => 2, 'risk' => 'extreme'),
        'SPXUSD' => array('name' => 'SPX', 'tier' => 2, 'risk' => 'extreme'),
        'PONKEUSD' => array('name' => 'PONKE', 'tier' => 2, 'risk' => 'extreme'),
    );
}

/**
 * BTC regime detector (Flaw #10 fix) — hard gate for bear markets
 * Checks BTC 24h change to determine market environment.
 */
function _kraken_detect_btc_regime()
{
    $ticker = _kraken_api('Ticker', array('pair' => 'XBTUSD'));

    if (!$ticker || !isset($ticker['result']['XXBTZUSD'])) {
        // If we can't get BTC data, allow scan but flag it
        return array('regime' => 'unknown', 'btc_change_24h' => null, 'note' => 'Could not fetch BTC data');
    }

    $btc = $ticker['result']['XXBTZUSD'];
    $btc_price = floatval($btc['c'][0]);
    $btc_open = isset($btc['o']) ? floatval($btc['o']) : 0;
    $btc_change = $btc_open > 0 ? (($btc_price - $btc_open) / $btc_open) * 100 : 0;

    $regime = 'chop';
    if ($btc_change < -5) {
        $regime = 'bear';    // BTC dumping >5% = meme coins will follow
    } elseif ($btc_change < -2) {
        $regime = 'caution'; // BTC softening, proceed with extra care
    } elseif ($btc_change > 3) {
        $regime = 'bull';    // BTC pumping = good for memes
    }

    return array(
        'regime' => $regime,
        'btc_price' => round($btc_price, 2),
        'btc_change_24h' => round($btc_change, 2),
    );
}

/**
 * Save scan to database
 */
function _kraken_save_scan($conn, $signals, $top_pick)
{
    $scan_id = 'kraken_' . date('YmdHis');

    foreach ($signals as $sig) {
        $esc_pair = $conn->real_escape_string($sig['pair']);
        $esc_name = $conn->real_escape_string($sig['name']);
        $factors_json = $conn->real_escape_string(json_encode($sig['factors']));
        $is_pick = ($top_pick && $sig['pair'] == $top_pick['pair']) ? 1 : 0;

        $sql = "INSERT INTO kraken_meme_scans 
                (scan_id, pair, name, tier, price, score, safety_score, rating, change_1h, change_24h, volume_24h, atr_pct, rsi, factors_json, target_price, stop_price, is_top_pick, created_at)
                VALUES 
                ('$scan_id', '$esc_pair', '$esc_name', '{$sig['tier']}', {$sig['price']}, {$sig['score']}, {$sig['safety_score']}, '{$sig['rating']}', {$sig['change_1h']}, {$sig['change_24h']}, {$sig['volume_24h']}, {$sig['atr_pct']}, {$sig['rsi']}, '$factors_json', {$sig['target_price']}, {$sig['stop_price']}, $is_pick, NOW())";

        $conn->query($sql);
    }
}

// Ensure table exists
$conn->query("CREATE TABLE IF NOT EXISTS kraken_meme_scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(30) NOT NULL,
    pair VARCHAR(20) NOT NULL,
    name VARCHAR(20) NOT NULL,
    tier INT NOT NULL DEFAULT 2,
    price DECIMAL(20,10) NOT NULL,
    score INT NOT NULL,
    safety_score INT NOT NULL,
    rating VARCHAR(30) NOT NULL,
    change_1h DECIMAL(8,2) NOT NULL,
    change_24h DECIMAL(8,2) NOT NULL,
    volume_24h DECIMAL(20,2) NOT NULL,
    atr_pct DECIMAL(6,2) NOT NULL,
    rsi DECIMAL(5,2) NOT NULL,
    factors_json TEXT,
    target_price DECIMAL(20,10) NOT NULL,
    stop_price DECIMAL(20,10) NOT NULL,
    is_top_pick TINYINT DEFAULT 0,
    created_at DATETIME NOT NULL,
    INDEX idx_scan (scan_id),
    INDEX idx_pair (pair),
    INDEX idx_created (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->close();

?>