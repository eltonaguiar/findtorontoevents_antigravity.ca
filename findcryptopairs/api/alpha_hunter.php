<?php
/**
 * Alpha Hunter v1.0 — Reverse-Engineer Past Winners
 * ==================================================
 * 1. Find extreme gainers on Kraken (coins that pumped hard recently)
 * 2. Pull their OHLCV BEFORE the pump
 * 3. Compute what the indicators looked like pre-pump
 * 4. Find common patterns (the "alpha fingerprint")
 * 5. Scan ALL pairs for that fingerprint NOW
 *
 * This is what paid Discord groups actually do — study winners,
 * extract the pattern, then find the next one.
 *
 * Actions:
 *   find_pumps     — Scan Kraken for recent extreme gainers
 *   analyze_pumps  — Reverse-engineer what happened before each pump
 *   fingerprint    — Extract common pre-pump patterns
 *   scan           — Scan all pairs for the fingerprint NOW
 *   signals        — Get current alpha signals
 *   audit          — Full audit trail
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(120);

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

$conn->query("CREATE TABLE IF NOT EXISTS ah_pump_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    pump_pct DECIMAL(10,4) NOT NULL,
    pump_start_time INT NOT NULL,
    pump_peak_time INT NOT NULL,
    pre_rsi DECIMAL(8,4),
    pre_macd_hist DECIMAL(20,10),
    pre_bb_position DECIMAL(8,4),
    pre_vol_ratio DECIMAL(8,4),
    pre_obv_trend DECIMAL(8,4),
    pre_adx DECIMAL(8,4),
    pre_atr_pct DECIMAL(8,4),
    pre_squeeze INT DEFAULT 0,
    pre_higher_lows INT DEFAULT 0,
    pre_vol_accumulation INT DEFAULT 0,
    pre_price_near_support INT DEFAULT 0,
    pre_ema_alignment VARCHAR(20),
    pre_stoch DECIMAL(8,4),
    pre_mfi DECIMAL(8,4),
    fingerprint_score DECIMAL(8,4) DEFAULT 0,
    analyzed_at DATETIME,
    INDEX idx_pair (pair),
    INDEX idx_pump (pump_pct)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS ah_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    price DECIMAL(20,10) NOT NULL,
    fingerprint_score DECIMAL(8,4) NOT NULL,
    matching_traits TEXT,
    tp_price DECIMAL(20,10),
    sl_price DECIMAL(20,10),
    tp_pct DECIMAL(8,4),
    sl_pct DECIMAL(8,4),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    current_price DECIMAL(20,10),
    pnl_pct DECIMAL(8,4),
    exit_reason VARCHAR(50),
    created_at DATETIME,
    resolved_at DATETIME,
    INDEX idx_status (status),
    INDEX idx_score (fingerprint_score)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// All Kraken USD pairs to scan
$ALL_PAIRS = array(
    'SOLUSD','XETHZUSD','XXBTZUSD','SUIUSD','XXRPZUSD','COMPUSD','SNXUSD',
    'BCHUSD','LINKUSD','ADAUSD','XDGUSD','FARTCOINUSD','MOODENGUSD','DASHUSD',
    'PEPEUSD','XZECZUSD','XXMRZUSD','XXLMZUSD','XLTCZUSD','PENGUUSD','SPXUSD',
    'UNIUSD','DOTUSD','AVAXUSD','BONKUSD','SHIBUSD','WIFUSD','FLOKIUSD',
    'VIRTUALUSD','AAVEUSD','CRVUSD','FETUSD','NEARUSD','ATOMUSD','FTMUSD',
    'INJUSD','APTUSD','OPUSD','ARBUSD','GRTUSD','SANDUSD','MANAUSD','AXSUSD',
    'GALAUSD','DYDXUSD','LPTUSD','FLOWUSD','TOSHIUSD','PONKEUSD','TURBOUSD',
    'MOGUSD','DOGUSD','TRUMPUSD','POPCATUSD','LRCUSD','LDOUSD'
);

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';

switch ($action) {
    case 'find_pumps':    action_find_pumps($conn); break;
    case 'analyze_pumps': action_analyze_pumps($conn); break;
    case 'fingerprint':   action_fingerprint($conn); break;
    case 'scan':          action_scan($conn); break;
    case 'signals':       action_signals($conn); break;
    case 'monitor':       action_monitor($conn); break;
    case 'full_run':      action_full_run($conn); break;
    case 'audit':         action_audit($conn); break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════════
//  FIND PUMPS — Identify extreme recent gainers from OHLCV history
// ═══════════════════════════════════════════════════════════════════
function action_find_pumps($conn)
{
    global $ALL_PAIRS;
    $start = microtime(true);
    $min_pump_pct = isset($_GET['min_pct']) ? floatval($_GET['min_pct']) : 15;

    // Fetch 4h OHLCV for all pairs
    $all_ohlcv = fetch_ohlcv_batch($ALL_PAIRS, 240);

    $pumps = array();
    foreach ($all_ohlcv as $pair => $candles) {
        if (count($candles) < 50) continue;

        // Scan for pump events: find candles where price rose >min_pump_pct in 3-5 candles
        for ($i = 5; $i < count($candles) - 1; $i++) {
            // Check 3-candle pump
            $low_before = min(floatval($candles[$i-3][3]), floatval($candles[$i-2][3]), floatval($candles[$i-1][3]));
            $high_now = floatval($candles[$i][2]);
            if ($low_before <= 0) continue;
            $pump_pct = (($high_now - $low_before) / $low_before) * 100;

            if ($pump_pct >= $min_pump_pct) {
                $pumps[] = array(
                    'pair' => $pair,
                    'pump_pct' => round($pump_pct, 2),
                    'pump_start_idx' => $i - 3,
                    'pump_peak_idx' => $i,
                    'pump_start_time' => intval($candles[$i-3][0]),
                    'pump_peak_time' => intval($candles[$i][0]),
                    'low_before' => $low_before,
                    'high_peak' => $high_now,
                    'candle_count' => count($candles)
                );
                $i += 5; // Skip ahead to avoid double-counting
            }
        }
    }

    // Sort by pump size
    usort($pumps, 'sort_pump_desc');

    // Deduplicate per pair (keep top pump per pair)
    $seen = array();
    $unique = array();
    foreach ($pumps as $p) {
        if (!isset($seen[$p['pair']])) {
            $seen[$p['pair']] = 0;
        }
        if ($seen[$p['pair']] < 3) { // Keep top 3 pumps per pair
            $unique[] = $p;
            $seen[$p['pair']]++;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'find_pumps',
        'min_pump_pct' => $min_pump_pct,
        'pairs_scanned' => count($all_ohlcv),
        'pump_events_found' => count($unique),
        'pumps' => array_slice($unique, 0, 50),
        'elapsed_ms' => $elapsed
    ));
}

function sort_pump_desc($a, $b)
{
    if ($a['pump_pct'] == $b['pump_pct']) return 0;
    return ($a['pump_pct'] > $b['pump_pct']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  ANALYZE PUMPS — What did indicators look like BEFORE each pump?
// ═══════════════════════════════════════════════════════════════════
function action_analyze_pumps($conn)
{
    global $ALL_PAIRS;
    $start = microtime(true);
    $min_pump_pct = isset($_GET['min_pct']) ? floatval($_GET['min_pct']) : 15;

    $all_ohlcv = fetch_ohlcv_batch($ALL_PAIRS, 240);

    // Clear previous analysis
    $conn->query("DELETE FROM ah_pump_analysis");

    $analyses = array();

    foreach ($all_ohlcv as $pair => $candles) {
        if (count($candles) < 60) continue;

        $closes = array(); $highs = array(); $lows = array(); $volumes = array(); $opens = array();
        foreach ($candles as $c) {
            $opens[] = floatval($c[1]);
            $highs[] = floatval($c[2]);
            $lows[] = floatval($c[3]);
            $closes[] = floatval($c[4]);
            $volumes[] = floatval($c[6]);
        }

        // Pre-compute indicators
        $rsi14 = arr_rsi($closes, 14);
        $ema9 = arr_ema($closes, 9);
        $ema21 = arr_ema($closes, 21);
        $ema55 = arr_ema($closes, 55);
        $bb = arr_bb($closes, 20, 2);
        $atr = arr_atr($highs, $lows, $closes, 14);
        $obv = arr_obv($closes, $volumes);
        $macd = arr_macd($closes);
        $adx = arr_adx($highs, $lows, $closes, 14);
        $stoch = arr_stoch($highs, $lows, $closes, 14, 3);
        $mfi = arr_mfi($highs, $lows, $closes, $volumes, 14);
        $vol_sma = arr_sma($volumes, 20);

        $n = count($closes);

        // Find pump events
        for ($i = 8; $i < $n - 1; $i++) {
            $low3 = min($lows[$i-3], $lows[$i-2], $lows[$i-1]);
            if ($low3 <= 0) continue;
            $pump = (($highs[$i] - $low3) / $low3) * 100;

            if ($pump >= $min_pump_pct) {
                // Analyze PRE-PUMP state (3-5 candles before the pump started)
                $pre = $i - 5; // 5 candles before pump
                if ($pre < 20) { $i += 5; continue; }

                // RSI before pump
                $pre_rsi = $rsi14[$pre];

                // MACD histogram before pump
                $pre_macd_h = $macd['histogram'][$pre];

                // BB position: where was price relative to bands? (0=lower, 0.5=middle, 1=upper)
                $bb_range = $bb['upper'][$pre] - $bb['lower'][$pre];
                $pre_bb_pos = ($bb_range > 0) ? ($closes[$pre] - $bb['lower'][$pre]) / $bb_range : 0.5;

                // Volume ratio vs 20-period average
                $pre_vol_ratio = ($vol_sma[$pre] > 0) ? $volumes[$pre] / $vol_sma[$pre] : 1;

                // OBV trend (5-bar slope)
                $obv_change = ($pre >= 5 && abs($obv[$pre-5]) > 0) ? (($obv[$pre] - $obv[$pre-5]) / abs($obv[$pre-5])) * 100 : 0;

                // ADX
                $pre_adx = $adx['adx'][$pre];

                // ATR as % of price
                $pre_atr_pct = ($closes[$pre] > 0) ? ($atr[$pre] / $closes[$pre]) * 100 : 0;

                // BB squeeze? (bandwidth < recent avg)
                $bw_now = $bb['bandwidth'][$pre];
                $bw_avg = 0;
                for ($j = $pre - 10; $j < $pre; $j++) { $bw_avg += $bb['bandwidth'][$j]; }
                $bw_avg /= 10;
                $pre_squeeze = ($bw_now < $bw_avg * 0.8) ? 1 : 0;

                // Higher lows pattern? (accumulation)
                $hl = 0;
                if ($pre >= 4 && $lows[$pre] > $lows[$pre-2] && $lows[$pre-2] > $lows[$pre-4]) $hl = 1;

                // Volume accumulation? (rising volume with flat/rising price)
                $vol_acc = 0;
                $vol_rising = ($volumes[$pre] > $volumes[$pre-2] && $volumes[$pre-2] > $volumes[$pre-4]);
                $price_flat = (abs($closes[$pre] - $closes[$pre-4]) / $closes[$pre-4]) < 0.03;
                if ($vol_rising && $price_flat) $vol_acc = 1;

                // Price near support? (price within 2% of 20-period low)
                $period_low = $lows[$pre];
                for ($j = $pre - 20; $j < $pre; $j++) { if ($lows[$j] < $period_low) $period_low = $lows[$j]; }
                $near_support = (($closes[$pre] - $period_low) / $period_low < 0.05) ? 1 : 0;

                // EMA alignment
                $ema_align = 'none';
                if ($ema9[$pre] > $ema21[$pre] && $ema21[$pre] > $ema55[$pre]) $ema_align = 'bullish';
                elseif ($ema9[$pre] < $ema21[$pre] && $ema21[$pre] < $ema55[$pre]) $ema_align = 'bearish';
                else $ema_align = 'mixed';

                $pre_stoch = $stoch['k'][$pre];
                $pre_mfi = $mfi[$pre];

                $analysis = array(
                    'pair' => $pair,
                    'pump_pct' => round($pump, 2),
                    'pump_start_time' => intval($candles[$i-3][0]),
                    'pump_peak_time' => intval($candles[$i][0]),
                    'pre_rsi' => round($pre_rsi, 2),
                    'pre_macd_hist' => $pre_macd_h,
                    'pre_bb_position' => round($pre_bb_pos, 4),
                    'pre_vol_ratio' => round($pre_vol_ratio, 4),
                    'pre_obv_trend' => round($obv_change, 4),
                    'pre_adx' => round($pre_adx, 2),
                    'pre_atr_pct' => round($pre_atr_pct, 4),
                    'pre_squeeze' => $pre_squeeze,
                    'pre_higher_lows' => $hl,
                    'pre_vol_accumulation' => $vol_acc,
                    'pre_price_near_support' => $near_support,
                    'pre_ema_alignment' => $ema_align,
                    'pre_stoch' => round($pre_stoch, 2),
                    'pre_mfi' => round($pre_mfi, 2)
                );

                // Store in DB
                $sql = sprintf(
                    "INSERT INTO ah_pump_analysis (pair,pump_pct,pump_start_time,pump_peak_time,pre_rsi,pre_macd_hist,pre_bb_position,pre_vol_ratio,pre_obv_trend,pre_adx,pre_atr_pct,pre_squeeze,pre_higher_lows,pre_vol_accumulation,pre_price_near_support,pre_ema_alignment,pre_stoch,pre_mfi,analyzed_at) VALUES ('%s','%.4f',%d,%d,'%.4f','%.10f','%.4f','%.4f','%.4f','%.4f','%.4f',%d,%d,%d,%d,'%s','%.4f','%.4f','%s')",
                    $conn->real_escape_string($pair), $pump,
                    intval($candles[$i-3][0]), intval($candles[$i][0]),
                    $pre_rsi, $pre_macd_h, $pre_bb_pos, $pre_vol_ratio, $obv_change,
                    $pre_adx, $pre_atr_pct, $pre_squeeze, $hl, $vol_acc, $near_support,
                    $conn->real_escape_string($ema_align), $pre_stoch, $pre_mfi,
                    date('Y-m-d H:i:s')
                );
                $conn->query($sql);
                $analyses[] = $analysis;
                $i += 5;
            }
        }
    }

    usort($analyses, 'sort_pump_desc');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'analyze_pumps',
        'pump_events_analyzed' => count($analyses),
        'top_pumps' => array_slice($analyses, 0, 30),
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  FINGERPRINT — Extract the common pre-pump pattern
// ═══════════════════════════════════════════════════════════════════
function action_fingerprint($conn)
{
    $res = $conn->query("SELECT * FROM ah_pump_analysis ORDER BY pump_pct DESC");
    if (!$res || $res->num_rows == 0) {
        echo json_encode(array('ok' => false, 'error' => 'No pump analyses found. Run analyze_pumps first.'));
        return;
    }

    $all = array();
    while ($r = $res->fetch_assoc()) { $all[] = $r; }
    $total = count($all);

    // Compute averages and distributions for each pre-pump metric
    $sum_rsi = 0; $sum_bb = 0; $sum_vol = 0; $sum_adx = 0; $sum_atr = 0;
    $sum_stoch = 0; $sum_mfi = 0; $sum_obv = 0;
    $cnt_squeeze = 0; $cnt_hl = 0; $cnt_vol_acc = 0; $cnt_support = 0;
    $cnt_bull_ema = 0; $cnt_bear_ema = 0; $cnt_mixed_ema = 0;
    $cnt_macd_neg = 0; $cnt_macd_pos = 0;

    foreach ($all as $a) {
        $sum_rsi += floatval($a['pre_rsi']);
        $sum_bb += floatval($a['pre_bb_position']);
        $sum_vol += floatval($a['pre_vol_ratio']);
        $sum_adx += floatval($a['pre_adx']);
        $sum_atr += floatval($a['pre_atr_pct']);
        $sum_stoch += floatval($a['pre_stoch']);
        $sum_mfi += floatval($a['pre_mfi']);
        $sum_obv += floatval($a['pre_obv_trend']);
        if (intval($a['pre_squeeze'])) $cnt_squeeze++;
        if (intval($a['pre_higher_lows'])) $cnt_hl++;
        if (intval($a['pre_vol_accumulation'])) $cnt_vol_acc++;
        if (intval($a['pre_price_near_support'])) $cnt_support++;
        if ($a['pre_ema_alignment'] === 'bullish') $cnt_bull_ema++;
        elseif ($a['pre_ema_alignment'] === 'bearish') $cnt_bear_ema++;
        else $cnt_mixed_ema++;
        if (floatval($a['pre_macd_hist']) < 0) $cnt_macd_neg++;
        else $cnt_macd_pos++;
    }

    $fingerprint = array(
        'sample_size' => $total,
        'avg_pre_rsi' => round($sum_rsi / $total, 2),
        'avg_pre_bb_position' => round($sum_bb / $total, 4),
        'avg_pre_vol_ratio' => round($sum_vol / $total, 4),
        'avg_pre_adx' => round($sum_adx / $total, 2),
        'avg_pre_atr_pct' => round($sum_atr / $total, 4),
        'avg_pre_stoch' => round($sum_stoch / $total, 2),
        'avg_pre_mfi' => round($sum_mfi / $total, 2),
        'avg_pre_obv_trend' => round($sum_obv / $total, 4),
        'pct_in_squeeze' => round(($cnt_squeeze / $total) * 100, 1),
        'pct_higher_lows' => round(($cnt_hl / $total) * 100, 1),
        'pct_vol_accumulation' => round(($cnt_vol_acc / $total) * 100, 1),
        'pct_near_support' => round(($cnt_support / $total) * 100, 1),
        'pct_bullish_ema' => round(($cnt_bull_ema / $total) * 100, 1),
        'pct_bearish_ema' => round(($cnt_bear_ema / $total) * 100, 1),
        'pct_macd_negative' => round(($cnt_macd_neg / $total) * 100, 1),
        'interpretation' => array()
    );

    // Generate interpretation
    $interp = array();
    if ($fingerprint['avg_pre_rsi'] < 45) $interp[] = 'RSI tends to be below 45 before pumps (oversold/neutral territory)';
    if ($fingerprint['avg_pre_rsi'] >= 45) $interp[] = 'RSI is neutral-to-bullish before pumps';
    if ($fingerprint['avg_pre_bb_position'] < 0.4) $interp[] = 'Price tends to be in lower half of BB before pump (value zone)';
    if ($fingerprint['pct_in_squeeze'] > 30) $interp[] = 'BB squeeze present ' . $fingerprint['pct_in_squeeze'] . '% of the time — volatility compression precedes pumps';
    if ($fingerprint['pct_higher_lows'] > 25) $interp[] = 'Higher lows pattern (accumulation) seen ' . $fingerprint['pct_higher_lows'] . '% of the time';
    if ($fingerprint['pct_vol_accumulation'] > 15) $interp[] = 'Volume accumulation (rising vol + flat price) in ' . $fingerprint['pct_vol_accumulation'] . '% of cases';
    if ($fingerprint['pct_near_support'] > 30) $interp[] = 'Price near support in ' . $fingerprint['pct_near_support'] . '% of cases — smart money buys at support';
    if ($fingerprint['pct_macd_negative'] > 50) $interp[] = 'MACD histogram negative before ' . $fingerprint['pct_macd_negative'] . '% of pumps — turns positive during pump';
    if ($fingerprint['avg_pre_adx'] < 25) $interp[] = 'Low ADX (' . $fingerprint['avg_pre_adx'] . ') — pumps start from ranging/consolidation, not trending';
    $fingerprint['interpretation'] = $interp;

    echo json_encode(array('ok' => true, 'action' => 'fingerprint', 'fingerprint' => $fingerprint));
}

// ═══════════════════════════════════════════════════════════════════
//  SCAN — Find pairs matching the fingerprint RIGHT NOW
// ═══════════════════════════════════════════════════════════════════
function action_scan($conn)
{
    global $ALL_PAIRS;
    $start = microtime(true);

    // Load the fingerprint averages
    $res = $conn->query("SELECT
        AVG(pre_rsi) as avg_rsi, AVG(pre_bb_position) as avg_bb,
        AVG(pre_vol_ratio) as avg_vol, AVG(pre_adx) as avg_adx,
        AVG(pre_atr_pct) as avg_atr, AVG(pre_stoch) as avg_stoch,
        AVG(pre_mfi) as avg_mfi,
        AVG(pre_squeeze) as avg_squeeze, AVG(pre_higher_lows) as avg_hl,
        AVG(pre_vol_accumulation) as avg_vol_acc, AVG(pre_price_near_support) as avg_support
    FROM ah_pump_analysis");

    if (!$res || !($fp = $res->fetch_assoc())) {
        echo json_encode(array('ok' => false, 'error' => 'No fingerprint data. Run analyze_pumps first.'));
        return;
    }

    // Fetch current OHLCV for all pairs
    $all_ohlcv = fetch_ohlcv_batch($ALL_PAIRS, 240);
    $now = date('Y-m-d H:i:s');

    // Clear old signals (>48h) and deduplicate (keep oldest per pair)
    $conn->query("DELETE FROM ah_signals WHERE status='ACTIVE' AND created_at < DATE_SUB(NOW(), INTERVAL 48 HOUR)");
    // Remove duplicate active signals (keep the one with lowest id per pair)
    $conn->query("DELETE s1 FROM ah_signals s1 INNER JOIN ah_signals s2 ON s1.pair = s2.pair AND s1.status = 'ACTIVE' AND s2.status = 'ACTIVE' AND s1.id > s2.id");

    $matches = array();

    foreach ($all_ohlcv as $pair => $candles) {
        if (count($candles) < 60) continue;

        $closes = array(); $highs = array(); $lows = array(); $volumes = array(); $opens = array();
        foreach ($candles as $c) {
            $opens[] = floatval($c[1]);
            $highs[] = floatval($c[2]);
            $lows[] = floatval($c[3]);
            $closes[] = floatval($c[4]);
            $volumes[] = floatval($c[6]);
        }

        $n = count($closes);
        $idx = $n - 1;
        if ($closes[$idx] <= 0) continue;

        // Compute current indicators
        $rsi = arr_rsi($closes, 14);
        $ema9 = arr_ema($closes, 9);
        $ema21 = arr_ema($closes, 21);
        $ema55 = arr_ema($closes, 55);
        $bb = arr_bb($closes, 20, 2);
        $atr = arr_atr($highs, $lows, $closes, 14);
        $obv = arr_obv($closes, $volumes);
        $macd = arr_macd($closes);
        $adx = arr_adx($highs, $lows, $closes, 14);
        $stoch = arr_stoch($highs, $lows, $closes, 14, 3);
        $mfi = arr_mfi($highs, $lows, $closes, $volumes, 14);
        $vol_sma = arr_sma($volumes, 20);

        // Score how well current state matches the pre-pump fingerprint
        $score = 0;
        $traits = array();

        // 1. RSI in pre-pump range (within 15 of average)
        $cur_rsi = $rsi[$idx];
        if (abs($cur_rsi - floatval($fp['avg_rsi'])) < 15) { $score += 10; $traits[] = 'RSI=' . round($cur_rsi, 1) . ' (pre-pump range)'; }

        // 2. BB position in lower half (accumulation zone)
        $bb_range = $bb['upper'][$idx] - $bb['lower'][$idx];
        $bb_pos = ($bb_range > 0) ? ($closes[$idx] - $bb['lower'][$idx]) / $bb_range : 0.5;
        if ($bb_pos < 0.4) { $score += 12; $traits[] = 'BB position ' . round($bb_pos, 2) . ' (lower half = value zone)'; }

        // 3. BB squeeze (volatility compression)
        $bw = $bb['bandwidth'][$idx];
        $bw_avg = 0;
        for ($j = $idx - 10; $j < $idx; $j++) { $bw_avg += $bb['bandwidth'][$j]; }
        $bw_avg /= 10;
        if ($bw < $bw_avg * 0.8) { $score += 15; $traits[] = 'BB SQUEEZE active (volatility compressed ' . round(($bw / $bw_avg) * 100) . '% of avg)'; }

        // 4. Higher lows (accumulation)
        if ($idx >= 4 && $lows[$idx] > $lows[$idx-2] && $lows[$idx-2] > $lows[$idx-4]) {
            $score += 12; $traits[] = 'Higher lows pattern (accumulation)';
        }

        // 5. Volume accumulation (rising vol + flat price)
        $vol_rising = ($volumes[$idx] > $volumes[$idx-2] && $volumes[$idx-2] > $volumes[$idx-4]);
        $price_flat = (abs($closes[$idx] - $closes[$idx-4]) / $closes[$idx-4]) < 0.03;
        if ($vol_rising && $price_flat) { $score += 15; $traits[] = 'Volume accumulation (whale loading?)'; }

        // 6. Near support
        $period_low = $lows[$idx];
        for ($j = $idx - 20; $j < $idx; $j++) { if ($lows[$j] < $period_low) $period_low = $lows[$j]; }
        if (($closes[$idx] - $period_low) / $period_low < 0.05) {
            $score += 10; $traits[] = 'Price near 20-period support';
        }

        // 7. Low ADX (consolidation before expansion)
        if ($adx['adx'][$idx] < 25) { $score += 8; $traits[] = 'Low ADX=' . round($adx['adx'][$idx], 1) . ' (consolidation)'; }

        // 8. MACD about to cross up
        if ($macd['histogram'][$idx] > $macd['histogram'][$idx-1] && $macd['histogram'][$idx-1] < 0) {
            $score += 12; $traits[] = 'MACD histogram turning positive (momentum shift)';
        }

        // 9. OBV divergence (OBV rising while price flat/down)
        $obv_5 = ($idx >= 5 && abs($obv[$idx-5]) > 0) ? (($obv[$idx] - $obv[$idx-5]) / abs($obv[$idx-5])) * 100 : 0;
        if ($obv_5 > 5 && $closes[$idx] <= $closes[$idx-5]) {
            $score += 15; $traits[] = 'OBV DIVERGENCE (hidden accumulation! OBV +' . round($obv_5, 1) . '% while price flat/down)';
        }

        // 10. Stochastic oversold
        if ($stoch['k'][$idx] < 30) { $score += 8; $traits[] = 'Stochastic oversold K=' . round($stoch['k'][$idx], 1); }

        // 11. MFI showing accumulation
        if ($mfi[$idx] < 35) { $score += 8; $traits[] = 'MFI=' . round($mfi[$idx], 1) . ' (money flow into accumulation)'; }

        // 12. ATR high (volatile pair = bigger potential move)
        $atr_pct = ($closes[$idx] > 0) ? ($atr[$idx] / $closes[$idx]) * 100 : 0;
        if ($atr_pct > 3) { $score += 5; $traits[] = 'High volatility ATR=' . round($atr_pct, 2) . '% (big move potential)'; }

        if ($score >= 40) {
            $atr_val = $atr[$idx];
            if ($atr_val <= 0) $atr_val = $closes[$idx] * 0.03;
            $tp_price = $closes[$idx] + ($atr_val * 3.0);
            $sl_price = $closes[$idx] - ($atr_val * 1.5);
            $tp_pct = (($tp_price - $closes[$idx]) / $closes[$idx]) * 100;
            $sl_pct = (($closes[$idx] - $sl_price) / $closes[$idx]) * 100;

            $matches[] = array(
                'pair' => $pair,
                'price' => $closes[$idx],
                'score' => $score,
                'traits' => $traits,
                'trait_count' => count($traits),
                'tp_price' => round($tp_price, 10),
                'sl_price' => round($sl_price, 10),
                'tp_pct' => round($tp_pct, 2),
                'sl_pct' => round($sl_pct, 2)
            );

            // Store signal — only if no active signal already exists for this pair
            $chk = $conn->query(sprintf(
                "SELECT id FROM ah_signals WHERE pair='%s' AND status='ACTIVE'",
                $conn->real_escape_string($pair)
            ));
            if (!$chk || $chk->num_rows == 0) {
                $sql = sprintf(
                    "INSERT INTO ah_signals (pair,price,fingerprint_score,matching_traits,tp_price,sl_price,tp_pct,sl_pct,status,created_at) VALUES ('%s','%.10f','%.4f','%s','%.10f','%.10f','%.4f','%.4f','ACTIVE','%s')",
                    $conn->real_escape_string($pair), $closes[$idx], $score,
                    $conn->real_escape_string(implode(' | ', $traits)),
                    $tp_price, $sl_price, $tp_pct, $sl_pct, $now
                );
                $conn->query($sql);
            }
        }
    }

    // Sort by fingerprint score
    usort($matches, 'sort_score_desc');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'scan',
        'pairs_scanned' => count($all_ohlcv),
        'matches_found' => count($matches),
        'signals' => $matches,
        'elapsed_ms' => $elapsed
    ));
}

function sort_score_desc($a, $b)
{
    if ($a['score'] == $b['score']) return 0;
    return ($a['score'] > $b['score']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  FULL RUN — Find pumps, analyze, fingerprint, scan in one call
// ═══════════════════════════════════════════════════════════════════
function action_full_run($conn)
{
    global $ALL_PAIRS;
    $start = microtime(true);

    // Step 1: Analyze pumps + store fingerprint
    ob_start();
    action_analyze_pumps($conn);
    $analyze_result = json_decode(ob_get_clean(), true);

    // Step 2: Get fingerprint
    ob_start();
    action_fingerprint($conn);
    $fp_result = json_decode(ob_get_clean(), true);

    // Step 3: Scan for matches
    ob_start();
    action_scan($conn);
    $scan_result = json_decode(ob_get_clean(), true);

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'full_run',
        'pump_events' => isset($analyze_result['pump_events_analyzed']) ? $analyze_result['pump_events_analyzed'] : 0,
        'fingerprint' => isset($fp_result['fingerprint']) ? $fp_result['fingerprint'] : null,
        'matches' => isset($scan_result['matches_found']) ? $scan_result['matches_found'] : 0,
        'signals' => isset($scan_result['signals']) ? $scan_result['signals'] : array(),
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  SIGNALS + MONITOR + AUDIT
// ═══════════════════════════════════════════════════════════════════
function action_signals($conn)
{
    $res = $conn->query("SELECT * FROM ah_signals WHERE status='ACTIVE' ORDER BY fingerprint_score DESC");
    $active = array();
    if ($res) { while ($r = $res->fetch_assoc()) { $active[] = $r; } }

    $res2 = $conn->query("SELECT * FROM ah_signals WHERE status='RESOLVED' ORDER BY resolved_at DESC LIMIT 30");
    $history = array();
    if ($res2) { while ($r = $res2->fetch_assoc()) { $history[] = $r; } }

    echo json_encode(array('ok' => true, 'active' => $active, 'history' => $history));
}

function action_monitor($conn)
{
    $res = $conn->query("SELECT * FROM ah_signals WHERE status='ACTIVE'");
    if (!$res || $res->num_rows == 0) {
        echo json_encode(array('ok' => true, 'message' => 'No active signals'));
        return;
    }

    $signals = array();
    $pairs = array();
    while ($r = $res->fetch_assoc()) { $signals[] = $r; $pairs[$r['pair']] = true; }

    $tickers = fetch_kraken_tickers_simple(array_keys($pairs));
    $now = date('Y-m-d H:i:s');
    $resolved = 0;

    foreach ($signals as $sig) {
        $cur = isset($tickers[$sig['pair']]) ? $tickers[$sig['pair']] : 0;
        if ($cur <= 0) continue;

        $entry = floatval($sig['price']);
        $tp = floatval($sig['tp_price']);
        $sl = floatval($sig['sl_price']);
        $pnl = (($cur - $entry) / $entry) * 100;

        $done = false;
        $reason = '';
        if ($cur >= $tp) { $done = true; $reason = 'TP_HIT'; }
        elseif ($cur <= $sl) { $done = true; $reason = 'SL_HIT'; }
        $hours = (time() - strtotime($sig['created_at'])) / 3600;
        if (!$done && $hours >= 72) { $done = true; $reason = 'EXPIRED'; }

        if ($done) {
            $conn->query(sprintf(
                "UPDATE ah_signals SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',exit_reason='%s',resolved_at='%s' WHERE id=%d",
                $cur, $pnl, $conn->real_escape_string($reason), $now, intval($sig['id'])
            ));
            $resolved++;
        } else {
            $conn->query(sprintf(
                "UPDATE ah_signals SET current_price='%.10f',pnl_pct='%.4f' WHERE id=%d",
                $cur, $pnl, intval($sig['id'])
            ));
        }
    }

    echo json_encode(array('ok' => true, 'checked' => count($signals), 'resolved' => $resolved));
}

function action_audit($conn)
{
    $res = $conn->query("SELECT pair, pump_pct, pre_rsi, pre_bb_position, pre_vol_ratio, pre_adx, pre_atr_pct,
        pre_squeeze, pre_higher_lows, pre_vol_accumulation, pre_price_near_support, pre_ema_alignment,
        pre_stoch, pre_mfi FROM ah_pump_analysis ORDER BY pump_pct DESC LIMIT 50");
    $pumps = array();
    if ($res) { while ($r = $res->fetch_assoc()) { $pumps[] = $r; } }

    $res2 = $conn->query("SELECT * FROM ah_signals ORDER BY created_at DESC LIMIT 50");
    $sigs = array();
    if ($res2) { while ($r = $res2->fetch_assoc()) { $sigs[] = $r; } }

    echo json_encode(array('ok' => true, 'pump_analyses' => $pumps, 'signals' => $sigs));
}

// ═══════════════════════════════════════════════════════════════════
//  DATA HELPERS
// ═══════════════════════════════════════════════════════════════════
function fetch_ohlcv_batch($pairs, $interval)
{
    $results = array();
    $batches = array_chunk($pairs, 5);
    foreach ($batches as $batch) {
        $mh = curl_multi_init();
        $handles = array();
        foreach ($batch as $pair) {
            $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'AlphaHunter/1.0');
            curl_multi_add_handle($mh, $ch);
            $handles[$pair] = $ch;
        }
        $running = null;
        do { curl_multi_exec($mh, $running); curl_multi_select($mh, 1); } while ($running > 0);
        foreach ($handles as $pair => $ch) {
            $resp = curl_multi_getcontent($ch);
            curl_multi_remove_handle($mh, $ch);
            curl_close($ch);
            if ($resp) {
                $data = json_decode($resp, true);
                if ($data && isset($data['result'])) {
                    foreach ($data['result'] as $k => $v) {
                        if ($k !== 'last') { $results[$pair] = $v; break; }
                    }
                }
            }
        }
        curl_multi_close($mh);
    }
    return $results;
}

function fetch_kraken_tickers_simple($pairs)
{
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . implode(',', $pairs);
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'AlphaHunter/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    $out = array();
    foreach ($data['result'] as $k => $v) {
        $out[$k] = floatval($v['c'][0]);
    }
    return $out;
}

// ═══════════════════════════════════════════════════════════════════
//  INDICATOR FUNCTIONS (self-contained)
// ═══════════════════════════════════════════════════════════════════
function arr_ema($data, $p) { $n=count($data); if($n<$p) return array_fill(0,$n,$data[$n-1]); $k=2.0/($p+1); $e=array_fill(0,$p-1,0); $s=array_sum(array_slice($data,0,$p))/$p; $e[$p-1]=$s; for($i=$p;$i<$n;$i++){$e[$i]=($data[$i]*$k)+($e[$i-1]*(1-$k));} for($i=0;$i<$p-1;$i++){$e[$i]=$e[$p-1];} return $e; }
function arr_sma($data, $p) { $n=count($data); $s=array_fill(0,$n,0); $sum=0; for($i=0;$i<$n;$i++){$sum+=$data[$i]; if($i>=$p){$sum-=$data[$i-$p];} $s[$i]=($i>=$p-1)?$sum/$p:$sum/($i+1);} return $s; }
function arr_rsi($c, $p) { $n=count($c); $r=array_fill(0,$n,50); if($n<$p+1)return $r; $g=array(); $l=array(); for($i=1;$i<$n;$i++){$d=$c[$i]-$c[$i-1]; $g[$i]=($d>0)?$d:0; $l[$i]=($d<0)?abs($d):0;} $ag=0;$al=0; for($i=1;$i<=$p;$i++){$ag+=$g[$i];$al+=$l[$i];} $ag/=$p;$al/=$p; $r[$p]=($al==0)?100:100-(100/(1+$ag/$al)); for($i=$p+1;$i<$n;$i++){$ag=(($ag*($p-1))+$g[$i])/$p;$al=(($al*($p-1))+$l[$i])/$p;$r[$i]=($al==0)?100:100-(100/(1+$ag/$al));} return $r; }
function arr_atr($h,$l,$c,$p) { $n=count($c); $a=array_fill(0,$n,0); if($n<$p+1)return $a; $t=array(0); for($i=1;$i<$n;$i++){$t[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));} $s=0; for($i=1;$i<=$p;$i++){$s+=$t[$i];} $a[$p]=$s/$p; for($i=$p+1;$i<$n;$i++){$a[$i]=(($a[$i-1]*($p-1))+$t[$i])/$p;} for($i=0;$i<$p;$i++){$a[$i]=$a[$p];} return $a; }
function arr_bb($c,$p,$m) { $n=count($c); $u=array_fill(0,$n,0);$mid=array_fill(0,$n,0);$lo=array_fill(0,$n,0);$bw=array_fill(0,$n,0); $sma=arr_sma($c,$p); for($i=$p-1;$i<$n;$i++){$sl=array_slice($c,$i-$p+1,$p);$mn=$sma[$i];$sq=0;foreach($sl as $v){$sq+=($v-$mn)*($v-$mn);}$sd=sqrt($sq/$p);$mid[$i]=$mn;$u[$i]=$mn+($m*$sd);$lo[$i]=$mn-($m*$sd);$bw[$i]=($mn>0)?($sd*$m*2)/$mn*100:0;} return array('upper'=>$u,'middle'=>$mid,'lower'=>$lo,'bandwidth'=>$bw); }
function arr_macd($c) { $e12=arr_ema($c,12);$e26=arr_ema($c,26);$n=count($c);$ml=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$ml[$i]=$e12[$i]-$e26[$i];}$sig=arr_ema($ml,9);$hist=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$hist[$i]=$ml[$i]-$sig[$i];}return array('line'=>$ml,'signal'=>$sig,'histogram'=>$hist); }
function arr_obv($c,$v) { $n=count($c);$o=array_fill(0,$n,0);for($i=1;$i<$n;$i++){if($c[$i]>$c[$i-1])$o[$i]=$o[$i-1]+$v[$i];elseif($c[$i]<$c[$i-1])$o[$i]=$o[$i-1]-$v[$i];else $o[$i]=$o[$i-1];}return $o; }
function arr_stoch($h,$l,$c,$kp,$dp) { $n=count($c);$sk=array_fill(0,$n,50);for($i=$kp-1;$i<$n;$i++){$hh=0;$ll=999999999;for($j=$i-$kp+1;$j<=$i;$j++){if($h[$j]>$hh)$hh=$h[$j];if($l[$j]<$ll)$ll=$l[$j];}$r=$hh-$ll;$sk[$i]=($r>0)?(($c[$i]-$ll)/$r)*100:50;}$sd=arr_sma($sk,$dp);return array('k'=>$sk,'d'=>$sd); }
function arr_adx($h,$l,$c,$p) { $n=count($c);$adx=array_fill(0,$n,25);$pdi=array_fill(0,$n,0);$mdi=array_fill(0,$n,0);if($n<$p*2)return array('adx'=>$adx,'plus_di'=>$pdi,'minus_di'=>$mdi);$tr=array(0);$pdm=array(0);$mdm=array(0);for($i=1;$i<$n;$i++){$tr[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[$i]=($up>$dn&&$up>0)?$up:0;$mdm[$i]=($dn>$up&&$dn>0)?$dn:0;}$a14=0;$p14=0;$m14=0;for($i=1;$i<=$p;$i++){$a14+=$tr[$i];$p14+=$pdm[$i];$m14+=$mdm[$i];}$dx_arr=array();for($i=$p;$i<$n;$i++){if($i>$p){$a14=$a14-($a14/$p)+$tr[$i];$p14=$p14-($p14/$p)+$pdm[$i];$m14=$m14-($m14/$p)+$mdm[$i];}$pd=($a14>0)?($p14/$a14)*100:0;$md=($a14>0)?($m14/$a14)*100:0;$pdi[$i]=$pd;$mdi[$i]=$md;$ds=$pd+$md;$dx=($ds>0)?abs($pd-$md)/$ds*100:0;$dx_arr[]=$dx;}if(count($dx_arr)>=$p){$av=array_sum(array_slice($dx_arr,0,$p))/$p;$adx[$p*2-1]=$av;for($i=$p;$i<count($dx_arr);$i++){$av=(($av*($p-1))+$dx_arr[$i])/$p;$ix=$i+$p;if($ix<$n)$adx[$ix]=$av;}}return array('adx'=>$adx,'plus_di'=>$pdi,'minus_di'=>$mdi); }
function arr_mfi($h,$l,$c,$v,$p) { $n=count($c);$mfi=array_fill(0,$n,50);$tp=array();for($i=0;$i<$n;$i++){$tp[$i]=($h[$i]+$l[$i]+$c[$i])/3;}for($i=$p;$i<$n;$i++){$pos=0;$neg=0;for($j=$i-$p+1;$j<=$i;$j++){$mf=$tp[$j]*$v[$j];if($j>0&&$tp[$j]>$tp[$j-1])$pos+=$mf;else $neg+=$mf;}$mfi[$i]=($neg>0)?100-(100/(1+$pos/$neg)):100;}return $mfi; }
?>
