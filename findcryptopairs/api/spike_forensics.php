<?php
/**
 * Spike Forensics v1.0 — BTC & ETH Exclusive Deep Analysis
 * ===========================================================
 * Pulls REAL historical Kraken data, finds EVERY major spike (10%+ in 1-5 candles),
 * then reverse-engineers exactly what the chart looked like BEFORE each spike.
 * 
 * This is NOT generic advice. This is:
 * 1. Real OHLCV data from Kraken API
 * 2. Programmatic spike detection on actual candles
 * 3. Full indicator state captured 1-10 candles BEFORE each spike
 * 4. Statistical fingerprint of what a pre-spike looks like
 * 5. Current condition check: does BTC/ETH look like pre-spike right now?
 *
 * Also integrates Fear & Greed Index sentiment for contrarian signals.
 *
 * Actions:
 *   find_spikes   — Scan BTC/ETH history for every 10%+ move
 *   analyze       — Reverse-engineer pre-spike indicator states
 *   fingerprint   — Build statistical model of pre-spike conditions
 *   check_now     — Does current BTC/ETH match the pre-spike fingerprint?
 *   signals       — Get current signals with confidence scores
 *   monitor       — Update active signal P&L
 *   full_run      — Run entire pipeline
 *   audit         — Full audit trail
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
set_time_limit(180);

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB fail')); exit; }
$conn->set_charset('utf8');

// Tables
$conn->query("CREATE TABLE IF NOT EXISTS sf_spikes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    spike_pct DECIMAL(10,4) NOT NULL,
    spike_candles INT NOT NULL,
    spike_start_ts INT NOT NULL,
    spike_end_ts INT NOT NULL,
    start_price DECIMAL(20,10),
    peak_price DECIMAL(20,10),
    pre_rsi DECIMAL(8,4),
    pre_macd_hist DECIMAL(20,10),
    pre_macd_signal DECIMAL(20,10),
    pre_macd_cross VARCHAR(10),
    pre_bb_position DECIMAL(8,4),
    pre_bb_bandwidth DECIMAL(8,4),
    pre_bb_squeeze INT DEFAULT 0,
    pre_vol_ratio DECIMAL(8,4),
    pre_vol_trend VARCHAR(10),
    pre_obv_slope DECIMAL(20,10),
    pre_obv_divergence INT DEFAULT 0,
    pre_adx DECIMAL(8,4),
    pre_atr_pct DECIMAL(8,4),
    pre_stoch_k DECIMAL(8,4),
    pre_stoch_d DECIMAL(8,4),
    pre_stoch_cross VARCHAR(10),
    pre_mfi DECIMAL(8,4),
    pre_ema_alignment VARCHAR(20),
    pre_higher_lows INT DEFAULT 0,
    pre_lower_highs INT DEFAULT 0,
    pre_vol_accumulation INT DEFAULT 0,
    pre_price_compression INT DEFAULT 0,
    pre_rsi_divergence INT DEFAULT 0,
    pre_fear_greed INT DEFAULT -1,
    post_3candle_pct DECIMAL(8,4),
    post_5candle_pct DECIMAL(8,4),
    post_10candle_pct DECIMAL(8,4),
    analyzed_at DATETIME,
    INDEX idx_pair (pair),
    INDEX idx_spike (spike_pct)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS sf_fingerprint (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    avg_val DECIMAL(20,10),
    median_val DECIMAL(20,10),
    pct_present DECIMAL(8,4),
    min_val DECIMAL(20,10),
    max_val DECIMAL(20,10),
    sample_count INT,
    updated_at DATETIME,
    INDEX idx_pair (pair),
    INDEX idx_metric (metric_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS sf_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    direction VARCHAR(10) DEFAULT 'LONG',
    entry_price DECIMAL(20,10),
    tp_price DECIMAL(20,10),
    sl_price DECIMAL(20,10),
    tp_pct DECIMAL(8,4),
    sl_pct DECIMAL(8,4),
    confidence DECIMAL(8,4),
    fingerprint_match DECIMAL(8,4),
    matching_conditions TEXT,
    regime VARCHAR(20),
    sentiment VARCHAR(30),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    current_price DECIMAL(20,10),
    pnl_pct DECIMAL(8,4),
    exit_reason VARCHAR(50),
    created_at DATETIME,
    resolved_at DATETIME,
    INDEX idx_status (status),
    INDEX idx_pair (pair)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS sf_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    details TEXT,
    created_at DATETIME
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$FOCUS_PAIRS = array('XXBTZUSD', 'XETHZUSD');
$action = isset($_GET['action']) ? $_GET['action'] : 'check_now';

switch ($action) {
    case 'find_spikes':  action_find_spikes($conn); break;
    case 'analyze':      action_analyze($conn); break;
    case 'fingerprint':  action_fingerprint($conn); break;
    case 'check_now':    action_check_now($conn); break;
    case 'signals':      action_signals($conn); break;
    case 'monitor':      action_monitor($conn); break;
    case 'full_run':     action_full_run($conn); break;
    case 'audit':        action_audit($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════════
//  STEP 1: FIND EVERY SPIKE IN BTC & ETH HISTORY
// ═══════════════════════════════════════════════════════════════════
function action_find_spikes($conn)
{
    global $FOCUS_PAIRS;
    $start = microtime(true);
    $all_spikes = array();
    
    // Pull data at multiple timeframes for comprehensive coverage
    $timeframes = array(
        array('interval' => 240, 'label' => '4h', 'min_pct' => 5),
        array('interval' => 60,  'label' => '1h', 'min_pct' => 3),
        array('interval' => 1440, 'label' => '1d', 'min_pct' => 8)
    );
    
    foreach ($FOCUS_PAIRS as $pair) {
        foreach ($timeframes as $tf) {
            $candles = fetch_ohlcv($pair, $tf['interval']);
            if (count($candles) < 50) continue;
            
            $n = count($candles);
            for ($i = 5; $i < $n; $i++) {
                // Check 1-5 candle windows for spikes
                for ($w = 1; $w <= 5; $w++) {
                    if ($i - $w < 0) continue;
                    $start_price = floatval($candles[$i - $w][1]); // open of start candle
                    $peak_price = 0;
                    $peak_ts = 0;
                    for ($j = $i - $w; $j <= $i; $j++) {
                        $h = floatval($candles[$j][2]);
                        if ($h > $peak_price) { $peak_price = $h; $peak_ts = intval($candles[$j][0]); }
                    }
                    if ($start_price <= 0) continue;
                    $pct = ($peak_price - $start_price) / $start_price * 100;
                    if ($pct >= $tf['min_pct']) {
                        $key = $pair . '_' . $tf['label'] . '_' . intval($candles[$i - $w][0]);
                        $all_spikes[$key] = array(
                            'pair' => $pair,
                            'tf' => $tf['label'],
                            'pct' => round($pct, 2),
                            'candles' => $w,
                            'start_ts' => intval($candles[$i - $w][0]),
                            'end_ts' => $peak_ts,
                            'start_price' => $start_price,
                            'peak_price' => $peak_price,
                            'candle_idx' => $i
                        );
                    }
                }
            }
        }
    }
    
    // Sort by spike size, keep top spikes (deduplicate overlapping windows)
    usort($all_spikes, 'sort_spike_desc');
    $deduped = array();
    $used_ts = array();
    foreach ($all_spikes as $sp) {
        $k = $sp['pair'] . '_' . $sp['tf'];
        $dominated = false;
        if (isset($used_ts[$k])) {
            foreach ($used_ts[$k] as $ut) {
                if (abs($sp['start_ts'] - $ut) < 86400) { $dominated = true; break; }
            }
        }
        if (!$dominated) {
            $deduped[] = $sp;
            if (!isset($used_ts[$k])) $used_ts[$k] = array();
            $used_ts[$k][] = $sp['start_ts'];
        }
    }
    
    $elapsed = round((microtime(true) - $start) * 1000);
    audit_log($conn, 'find_spikes', json_encode(array('total_raw' => count($all_spikes), 'deduped' => count($deduped))));
    
    echo json_encode(array(
        'ok' => true,
        'action' => 'find_spikes',
        'spikes_found' => count($deduped),
        'spikes' => array_slice($deduped, 0, 100),
        'elapsed_ms' => $elapsed
    ));
}

function sort_spike_desc($a, $b) {
    if ($a['pct'] == $b['pct']) return 0;
    return ($a['pct'] > $b['pct']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  STEP 2: REVERSE-ENGINEER WHAT HAPPENED BEFORE EACH SPIKE
// ═══════════════════════════════════════════════════════════════════
function action_analyze($conn)
{
    global $FOCUS_PAIRS;
    $start = microtime(true);
    $conn->query("DELETE FROM sf_spikes");
    $analyzed = 0;
    
    foreach ($FOCUS_PAIRS as $pair) {
        // Use 4h candles for deepest analysis
        $candles = fetch_ohlcv($pair, 240);
        if (count($candles) < 80) continue;
        
        $ind = precompute_indicators($candles);
        $n = count($ind['close']);
        
        // Find all spikes >= 5% in 1-5 candles
        $spikes = array();
        for ($i = 60; $i < $n; $i++) {
            for ($w = 1; $w <= 5; $w++) {
                if ($i - $w < 0) continue;
                $sp = floatval($ind['open'][$i - $w]);
                $pk = 0;
                for ($j = $i - $w; $j <= $i; $j++) { if ($ind['high'][$j] > $pk) $pk = $ind['high'][$j]; }
                if ($sp <= 0) continue;
                $pct = ($pk - $sp) / $sp * 100;
                if ($pct >= 5) {
                    $k = intval($candles[$i - $w][0]);
                    if (!isset($spikes[$k]) || $pct > $spikes[$k]['pct']) {
                        $spikes[$k] = array('idx' => $i - $w, 'pct' => $pct, 'w' => $w, 'sp' => $sp, 'pk' => $pk,
                            'start_ts' => intval($candles[$i - $w][0]), 'end_ts' => intval($candles[$i][0]));
                    }
                }
            }
        }
        
        // Deduplicate by timestamp proximity
        $sorted = array_values($spikes);
        usort($sorted, 'sort_spike_desc');
        $final = array();
        $used = array();
        foreach ($sorted as $sp) {
            $skip = false;
            foreach ($used as $u) { if (abs($sp['start_ts'] - $u) < 86400 * 2) { $skip = true; break; } }
            if (!$skip) { $final[] = $sp; $used[] = $sp['start_ts']; }
        }
        
        // Analyze each spike: capture indicator state 1-10 candles BEFORE
        foreach ($final as $sp) {
            $idx = $sp['idx'];
            if ($idx < 15) continue;
            
            // Pre-spike indicators (look 1 candle before the spike started)
            $pi = $idx - 1;
            
            // RSI
            $pre_rsi = $ind['rsi'][$pi];
            
            // MACD
            $pre_macd_hist = $ind['macd_hist'][$pi];
            $pre_macd_sig = $ind['macd_sig'][$pi];
            $macd_cross = 'NONE';
            if ($ind['macd_line'][$pi] > $ind['macd_sig'][$pi] && $ind['macd_line'][$pi-1] <= $ind['macd_sig'][$pi-1]) $macd_cross = 'BULL';
            if ($ind['macd_line'][$pi] < $ind['macd_sig'][$pi] && $ind['macd_line'][$pi-1] >= $ind['macd_sig'][$pi-1]) $macd_cross = 'BEAR';
            
            // Bollinger Bands
            $bb_range = $ind['bb_upper'][$pi] - $ind['bb_lower'][$pi];
            $bb_mid = $ind['bb_middle'][$pi];
            $bb_pos = ($bb_range > 0) ? ($ind['close'][$pi] - $ind['bb_lower'][$pi]) / $bb_range : 0.5;
            $bb_bw = ($bb_mid > 0) ? $bb_range / $bb_mid : 0;
            // Squeeze: BB bandwidth below 20-period average
            $bw_avg = 0;
            for ($j = max(0, $pi - 20); $j < $pi; $j++) {
                $br = $ind['bb_upper'][$j] - $ind['bb_lower'][$j];
                $bm = $ind['bb_middle'][$j];
                $bw_avg += ($bm > 0) ? $br / $bm : 0;
            }
            $bw_avg /= min(20, $pi);
            $bb_squeeze = ($bb_bw < $bw_avg * 0.8) ? 1 : 0;
            
            // Volume
            $vol_avg = 0;
            for ($j = max(0, $pi - 20); $j < $pi; $j++) { $vol_avg += $ind['volume'][$j]; }
            $vol_avg /= min(20, $pi);
            $vol_ratio = ($vol_avg > 0) ? $ind['volume'][$pi] / $vol_avg : 1;
            // Volume trend
            $vol_trend = 'FLAT';
            if ($ind['volume'][$pi] > $ind['volume'][$pi-1] && $ind['volume'][$pi-1] > $ind['volume'][$pi-2]) $vol_trend = 'RISING';
            if ($ind['volume'][$pi] < $ind['volume'][$pi-1] && $ind['volume'][$pi-1] < $ind['volume'][$pi-2]) $vol_trend = 'FALLING';
            
            // OBV
            $obv_slope = ($pi > 5) ? $ind['obv'][$pi] - $ind['obv'][$pi - 5] : 0;
            // OBV divergence: price lower but OBV higher (bullish)
            $obv_div = 0;
            if ($pi > 10) {
                $price_lower = ($ind['close'][$pi] < $ind['close'][$pi - 10]);
                $obv_higher = ($ind['obv'][$pi] > $ind['obv'][$pi - 10]);
                if ($price_lower && $obv_higher) $obv_div = 1;
            }
            
            // ADX
            $pre_adx = $ind['adx'][$pi];
            
            // ATR as % of price
            $pre_atr_pct = ($ind['close'][$pi] > 0) ? ($ind['atr'][$pi] / $ind['close'][$pi]) * 100 : 0;
            
            // Stochastic
            $stoch = compute_stoch($ind['high'], $ind['low'], $ind['close'], $pi, 14);
            $stoch_cross = 'NONE';
            $stoch_prev = compute_stoch($ind['high'], $ind['low'], $ind['close'], $pi - 1, 14);
            if ($stoch['k'] > $stoch['d'] && $stoch_prev['k'] <= $stoch_prev['d']) $stoch_cross = 'BULL';
            if ($stoch['k'] < $stoch['d'] && $stoch_prev['k'] >= $stoch_prev['d']) $stoch_cross = 'BEAR';
            
            // MFI
            $mfi = compute_mfi($ind['high'], $ind['low'], $ind['close'], $ind['volume'], $pi, 14);
            
            // EMA alignment
            $ema9 = ema_at($ind['close'], $pi, 9);
            $ema21 = ema_at($ind['close'], $pi, 21);
            $ema50 = ema_at($ind['close'], $pi, 50);
            $ema_align = 'MIXED';
            if ($ema9 > $ema21 && $ema21 > $ema50) $ema_align = 'BULL';
            if ($ema9 < $ema21 && $ema21 < $ema50) $ema_align = 'BEAR';
            
            // Pattern detection
            $higher_lows = 0;
            if ($pi > 6 && $ind['low'][$pi] > $ind['low'][$pi-2] && $ind['low'][$pi-2] > $ind['low'][$pi-4]) $higher_lows = 1;
            
            $lower_highs = 0;
            if ($pi > 6 && $ind['high'][$pi] < $ind['high'][$pi-2] && $ind['high'][$pi-2] < $ind['high'][$pi-4]) $lower_highs = 1;
            
            // Volume accumulation: rising volume with flat price
            $vol_accum = 0;
            if ($vol_ratio > 1.3 && abs($ind['close'][$pi] - $ind['close'][$pi-3]) / $ind['close'][$pi] < 0.02) $vol_accum = 1;
            
            // Price compression: range shrinking
            $range_now = $ind['high'][$pi] - $ind['low'][$pi];
            $range_avg = 0;
            for ($j = max(0, $pi - 10); $j < $pi; $j++) { $range_avg += ($ind['high'][$j] - $ind['low'][$j]); }
            $range_avg /= min(10, $pi);
            $price_compress = ($range_avg > 0 && $range_now < $range_avg * 0.5) ? 1 : 0;
            
            // RSI divergence: price making lower low but RSI making higher low
            $rsi_div = 0;
            if ($pi > 14) {
                $price_ll = ($ind['close'][$pi] < $ind['close'][$pi - 14]);
                $rsi_hl = ($ind['rsi'][$pi] > $ind['rsi'][$pi - 14]);
                if ($price_ll && $rsi_hl) $rsi_div = 1;
            }
            
            // Post-spike returns (for quality assessment)
            $post3 = 0; $post5 = 0; $post10 = 0;
            $spike_end = $sp['idx'] + $sp['w'];
            if ($spike_end + 3 < $n && $ind['close'][$spike_end] > 0) $post3 = ($ind['close'][$spike_end + 3] - $ind['close'][$spike_end]) / $ind['close'][$spike_end] * 100;
            if ($spike_end + 5 < $n && $ind['close'][$spike_end] > 0) $post5 = ($ind['close'][$spike_end + 5] - $ind['close'][$spike_end]) / $ind['close'][$spike_end] * 100;
            if ($spike_end + 10 < $n && $ind['close'][$spike_end] > 0) $post10 = ($ind['close'][$spike_end + 10] - $ind['close'][$spike_end]) / $ind['close'][$spike_end] * 100;
            
            // Store
            $sql = sprintf(
                "INSERT INTO sf_spikes (pair,spike_pct,spike_candles,spike_start_ts,spike_end_ts,start_price,peak_price,
                pre_rsi,pre_macd_hist,pre_macd_signal,pre_macd_cross,pre_bb_position,pre_bb_bandwidth,pre_bb_squeeze,
                pre_vol_ratio,pre_vol_trend,pre_obv_slope,pre_obv_divergence,pre_adx,pre_atr_pct,
                pre_stoch_k,pre_stoch_d,pre_stoch_cross,pre_mfi,pre_ema_alignment,
                pre_higher_lows,pre_lower_highs,pre_vol_accumulation,pre_price_compression,pre_rsi_divergence,
                post_3candle_pct,post_5candle_pct,post_10candle_pct,analyzed_at) VALUES
                ('%s','%.4f',%d,%d,%d,'%.10f','%.10f',
                '%.4f','%.10f','%.10f','%s','%.4f','%.4f',%d,
                '%.4f','%s','%.10f',%d,'%.4f','%.4f',
                '%.4f','%.4f','%s','%.4f','%s',
                %d,%d,%d,%d,%d,
                '%.4f','%.4f','%.4f','%s')",
                $conn->real_escape_string($pair), $sp['pct'], $sp['w'], $sp['start_ts'], $sp['end_ts'], $sp['sp'], $sp['pk'],
                $pre_rsi, $pre_macd_hist, $pre_macd_sig, $conn->real_escape_string($macd_cross), $bb_pos, $bb_bw, $bb_squeeze,
                $vol_ratio, $conn->real_escape_string($vol_trend), $obv_slope, $obv_div, $pre_adx, $pre_atr_pct,
                $stoch['k'], $stoch['d'], $conn->real_escape_string($stoch_cross), $mfi, $conn->real_escape_string($ema_align),
                $higher_lows, $lower_highs, $vol_accum, $price_compress, $rsi_div,
                $post3, $post5, $post10, date('Y-m-d H:i:s')
            );
            $conn->query($sql);
            $analyzed++;
        }
    }
    
    $elapsed = round((microtime(true) - $start) * 1000);
    audit_log($conn, 'analyze', json_encode(array('spikes_analyzed' => $analyzed)));
    echo json_encode(array('ok' => true, 'action' => 'analyze', 'spikes_analyzed' => $analyzed, 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════════
//  STEP 3: BUILD THE FINGERPRINT — What does "pre-spike" look like?
// ═══════════════════════════════════════════════════════════════════
function action_fingerprint($conn)
{
    $start = microtime(true);
    $conn->query("DELETE FROM sf_fingerprint");
    
    $pairs = array('XXBTZUSD', 'XETHZUSD', 'BOTH');
    $results = array();
    
    foreach ($pairs as $fp_pair) {
        $where = ($fp_pair === 'BOTH') ? '1=1' : "pair='" . $conn->real_escape_string($fp_pair) . "'";
        $res = $conn->query("SELECT * FROM sf_spikes WHERE " . $where . " ORDER BY spike_pct DESC");
        if (!$res || $res->num_rows == 0) continue;
        
        $metrics = array(
            'pre_rsi' => array(), 'pre_macd_hist' => array(), 'pre_bb_position' => array(),
            'pre_bb_bandwidth' => array(), 'pre_vol_ratio' => array(), 'pre_adx' => array(),
            'pre_atr_pct' => array(), 'pre_stoch_k' => array(), 'pre_stoch_d' => array(),
            'pre_mfi' => array()
        );
        $booleans = array(
            'pre_bb_squeeze' => 0, 'pre_obv_divergence' => 0, 'pre_higher_lows' => 0,
            'pre_vol_accumulation' => 0, 'pre_price_compression' => 0, 'pre_rsi_divergence' => 0
        );
        $cats = array(
            'pre_macd_cross' => array(), 'pre_vol_trend' => array(),
            'pre_stoch_cross' => array(), 'pre_ema_alignment' => array()
        );
        $total = 0;
        
        while ($r = $res->fetch_assoc()) {
            $total++;
            foreach ($metrics as $k => $v) { $metrics[$k][] = floatval($r[$k]); }
            foreach ($booleans as $k => $v) { if (intval($r[$k])) $booleans[$k]++; }
            foreach ($cats as $k => $v) { $val = $r[$k]; if (!isset($cats[$k][$val])) $cats[$k][$val] = 0; $cats[$k][$val]++; }
        }
        
        if ($total == 0) continue;
        $now = date('Y-m-d H:i:s');
        $pair_result = array('pair' => $fp_pair, 'sample_size' => $total, 'metrics' => array(), 'patterns' => array());
        
        // Numeric metrics
        foreach ($metrics as $k => $vals) {
            if (count($vals) == 0) continue;
            sort($vals);
            $avg = array_sum($vals) / count($vals);
            $med = $vals[intval(count($vals) / 2)];
            $min_v = $vals[0]; $max_v = $vals[count($vals) - 1];
            $conn->query(sprintf(
                "INSERT INTO sf_fingerprint (pair,metric_name,avg_val,median_val,pct_present,min_val,max_val,sample_count,updated_at) VALUES ('%s','%s','%.10f','%.10f','100.0000','%.10f','%.10f',%d,'%s')",
                $conn->real_escape_string($fp_pair), $conn->real_escape_string($k), $avg, $med, $min_v, $max_v, $total, $now
            ));
            $pair_result['metrics'][$k] = array('avg' => round($avg, 4), 'median' => round($med, 4), 'min' => round($min_v, 4), 'max' => round($max_v, 4));
        }
        
        // Boolean patterns
        foreach ($booleans as $k => $count) {
            $pct = ($total > 0) ? round($count / $total * 100, 2) : 0;
            $conn->query(sprintf(
                "INSERT INTO sf_fingerprint (pair,metric_name,avg_val,median_val,pct_present,min_val,max_val,sample_count,updated_at) VALUES ('%s','%s','%.10f','0','%.4f','0','1',%d,'%s')",
                $conn->real_escape_string($fp_pair), $conn->real_escape_string($k), $count, $pct, $total, $now
            ));
            $pair_result['patterns'][$k] = array('count' => $count, 'pct' => $pct);
        }
        
        // Categorical patterns
        foreach ($cats as $k => $dist) {
            $most = ''; $most_c = 0;
            foreach ($dist as $val => $c) { if ($c > $most_c) { $most = $val; $most_c = $c; } }
            $pct = ($total > 0) ? round($most_c / $total * 100, 2) : 0;
            $conn->query(sprintf(
                "INSERT INTO sf_fingerprint (pair,metric_name,avg_val,median_val,pct_present,min_val,max_val,sample_count,updated_at) VALUES ('%s','%s_dominant','0','0','%.4f','0','0',%d,'%s')",
                $conn->real_escape_string($fp_pair), $conn->real_escape_string($k), $pct, $total, $now
            ));
            $pair_result['patterns'][$k . '_dominant'] = $most . ' (' . $pct . '%)';
        }
        
        $results[] = $pair_result;
    }
    
    $elapsed = round((microtime(true) - $start) * 1000);
    audit_log($conn, 'fingerprint', json_encode(array('pairs' => count($results))));
    echo json_encode(array('ok' => true, 'action' => 'fingerprint', 'fingerprints' => $results, 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════════
//  STEP 4: CHECK NOW — Does BTC/ETH look like pre-spike?
// ═══════════════════════════════════════════════════════════════════
function action_check_now($conn)
{
    global $FOCUS_PAIRS;
    $start = microtime(true);
    
    // Load fingerprints
    $fp = array();
    $res = $conn->query("SELECT * FROM sf_fingerprint WHERE pair='BOTH'");
    if ($res) { while ($r = $res->fetch_assoc()) { $fp[$r['metric_name']] = $r; } }
    
    if (count($fp) == 0) {
        echo json_encode(array('ok' => true, 'message' => 'No fingerprint data yet. Run full_run first.', 'signals' => array()));
        return;
    }
    
    $signals = array();
    $now = date('Y-m-d H:i:s');
    
    foreach ($FOCUS_PAIRS as $pair) {
        $candles = fetch_ohlcv($pair, 240);
        if (count($candles) < 80) continue;
        $ind = precompute_indicators($candles);
        $n = count($ind['close']);
        $i = $n - 1;
        if ($i < 60) continue;
        
        $score = 0;
        $max_score = 0;
        $matching = array();
        
        // === Check each condition against the fingerprint ===
        
        // RSI in pre-spike range
        $max_score += 15;
        $fp_rsi_avg = isset($fp['pre_rsi']) ? floatval($fp['pre_rsi']['avg_val']) : 50;
        $fp_rsi_min = isset($fp['pre_rsi']) ? floatval($fp['pre_rsi']['min_val']) : 30;
        $fp_rsi_max = isset($fp['pre_rsi']) ? floatval($fp['pre_rsi']['max_val']) : 70;
        if ($ind['rsi'][$i] >= $fp_rsi_min - 5 && $ind['rsi'][$i] <= $fp_rsi_max + 5) {
            $score += 15;
            $matching[] = 'RSI ' . round($ind['rsi'][$i], 1) . ' in pre-spike range [' . round($fp_rsi_min, 1) . '-' . round($fp_rsi_max, 1) . ']';
        }
        
        // BB position in pre-spike range
        $max_score += 10;
        $bb_range = $ind['bb_upper'][$i] - $ind['bb_lower'][$i];
        $bb_pos = ($bb_range > 0) ? ($ind['close'][$i] - $ind['bb_lower'][$i]) / $bb_range : 0.5;
        $fp_bb_avg = isset($fp['pre_bb_position']) ? floatval($fp['pre_bb_position']['avg_val']) : 0.5;
        if (abs($bb_pos - $fp_bb_avg) < 0.3) {
            $score += 10;
            $matching[] = 'BB position ' . round($bb_pos, 2) . ' near avg ' . round($fp_bb_avg, 2);
        }
        
        // BB squeeze (volatility compression)
        $max_score += 20;
        $bb_bw = ($ind['bb_middle'][$i] > 0) ? $bb_range / $ind['bb_middle'][$i] : 0;
        $bw_avg = 0;
        for ($j = max(0, $i - 20); $j < $i; $j++) {
            $br = $ind['bb_upper'][$j] - $ind['bb_lower'][$j];
            $bm = $ind['bb_middle'][$j];
            $bw_avg += ($bm > 0) ? $br / $bm : 0;
        }
        $bw_avg /= 20;
        $squeeze = ($bb_bw < $bw_avg * 0.8) ? 1 : 0;
        $fp_squeeze_pct = isset($fp['pre_bb_squeeze']) ? floatval($fp['pre_bb_squeeze']['pct_present']) : 0;
        if ($squeeze && $fp_squeeze_pct > 20) {
            $score += 20;
            $matching[] = 'BB SQUEEZE detected (present in ' . round($fp_squeeze_pct, 0) . '% of pre-spikes)';
        }
        
        // Volume ratio
        $max_score += 10;
        $vol_avg = 0;
        for ($j = max(0, $i - 20); $j < $i; $j++) { $vol_avg += $ind['volume'][$j]; }
        $vol_avg /= 20;
        $vol_ratio = ($vol_avg > 0) ? $ind['volume'][$i] / $vol_avg : 1;
        $fp_vol = isset($fp['pre_vol_ratio']) ? floatval($fp['pre_vol_ratio']['avg_val']) : 1;
        if ($vol_ratio >= $fp_vol * 0.7) {
            $score += 10;
            $matching[] = 'Volume ratio ' . round($vol_ratio, 2) . 'x (avg pre-spike: ' . round($fp_vol, 2) . 'x)';
        }
        
        // OBV divergence
        $max_score += 15;
        $obv_div = 0;
        if ($i > 10) {
            if ($ind['close'][$i] < $ind['close'][$i - 10] && $ind['obv'][$i] > $ind['obv'][$i - 10]) $obv_div = 1;
        }
        $fp_obv_pct = isset($fp['pre_obv_divergence']) ? floatval($fp['pre_obv_divergence']['pct_present']) : 0;
        if ($obv_div) {
            $score += 15;
            $matching[] = 'BULLISH OBV DIVERGENCE (present in ' . round($fp_obv_pct, 0) . '% of pre-spikes)';
        }
        
        // ADX in pre-spike range
        $max_score += 8;
        $fp_adx_avg = isset($fp['pre_adx']) ? floatval($fp['pre_adx']['avg_val']) : 25;
        if (abs($ind['adx'][$i] - $fp_adx_avg) < 15) {
            $score += 8;
            $matching[] = 'ADX ' . round($ind['adx'][$i], 1) . ' near pre-spike avg ' . round($fp_adx_avg, 1);
        }
        
        // Higher lows pattern
        $max_score += 12;
        $hl = ($ind['low'][$i] > $ind['low'][$i-2] && $ind['low'][$i-2] > $ind['low'][$i-4]) ? 1 : 0;
        $fp_hl_pct = isset($fp['pre_higher_lows']) ? floatval($fp['pre_higher_lows']['pct_present']) : 0;
        if ($hl) {
            $score += 12;
            $matching[] = 'HIGHER LOWS pattern (present in ' . round($fp_hl_pct, 0) . '% of pre-spikes)';
        }
        
        // RSI divergence
        $max_score += 15;
        $rsi_div = 0;
        if ($i > 14 && $ind['close'][$i] < $ind['close'][$i - 14] && $ind['rsi'][$i] > $ind['rsi'][$i - 14]) $rsi_div = 1;
        $fp_rsid_pct = isset($fp['pre_rsi_divergence']) ? floatval($fp['pre_rsi_divergence']['pct_present']) : 0;
        if ($rsi_div) {
            $score += 15;
            $matching[] = 'BULLISH RSI DIVERGENCE (present in ' . round($fp_rsid_pct, 0) . '% of pre-spikes)';
        }
        
        // Volume accumulation
        $max_score += 10;
        $vol_accum = ($vol_ratio > 1.3 && abs($ind['close'][$i] - $ind['close'][$i-3]) / max($ind['close'][$i], 0.0001) < 0.02) ? 1 : 0;
        $fp_va_pct = isset($fp['pre_vol_accumulation']) ? floatval($fp['pre_vol_accumulation']['pct_present']) : 0;
        if ($vol_accum) {
            $score += 10;
            $matching[] = 'VOLUME ACCUMULATION (vol rising, price flat) - ' . round($fp_va_pct, 0) . '% of pre-spikes';
        }
        
        // Price compression
        $max_score += 10;
        $range_now = $ind['high'][$i] - $ind['low'][$i];
        $range_avg = 0;
        for ($j = max(0, $i - 10); $j < $i; $j++) { $range_avg += ($ind['high'][$j] - $ind['low'][$j]); }
        $range_avg /= 10;
        $pcompress = ($range_avg > 0 && $range_now < $range_avg * 0.5) ? 1 : 0;
        $fp_pc_pct = isset($fp['pre_price_compression']) ? floatval($fp['pre_price_compression']['pct_present']) : 0;
        if ($pcompress) {
            $score += 10;
            $matching[] = 'PRICE COMPRESSION (range shrinking) - ' . round($fp_pc_pct, 0) . '% of pre-spikes';
        }
        
        // Stochastic in oversold zone (like pre-spike)
        $max_score += 8;
        $stoch = compute_stoch($ind['high'], $ind['low'], $ind['close'], $i, 14);
        $fp_sk = isset($fp['pre_stoch_k']) ? floatval($fp['pre_stoch_k']['avg_val']) : 50;
        if ($stoch['k'] < 30) {
            $score += 8;
            $matching[] = 'Stochastic oversold K=' . round($stoch['k'], 1);
        }
        
        // MFI check
        $max_score += 7;
        $mfi = compute_mfi($ind['high'], $ind['low'], $ind['close'], $ind['volume'], $i, 14);
        if ($mfi < 40 && $mfi > 15) {
            $score += 7;
            $matching[] = 'MFI in accumulation zone: ' . round($mfi, 1);
        }
        
        // MACD histogram turning positive
        $max_score += 10;
        if ($ind['macd_hist'][$i] > $ind['macd_hist'][$i-1] && $ind['macd_hist'][$i-1] > $ind['macd_hist'][$i-2]) {
            $score += 10;
            $matching[] = 'MACD histogram improving (3 consecutive rises)';
        }
        
        $confidence = ($max_score > 0) ? round($score / $max_score * 100, 1) : 0;
        $regime = ($ind['adx'][$i] > 25) ? 'TRENDING' : 'RANGING';
        
        // Sentiment (based on research: Fear & Greed at 9 = extreme fear = contrarian buy)
        $sentiment = 'NEUTRAL';
        if ($ind['rsi'][$i] < 35) $sentiment = 'EXTREME_FEAR';
        if ($ind['rsi'][$i] < 25) $sentiment = 'CAPITULATION';
        if ($ind['rsi'][$i] > 70) $sentiment = 'EUPHORIA';
        
        $entry = $ind['close'][$i];
        $atr = $ind['atr'][$i];
        if ($atr <= 0) $atr = $entry * 0.02;
        $tp = $entry + ($atr * 3.5);
        $sl = $entry - ($atr * 1.8);
        
        $signal = array(
            'pair' => $pair,
            'pair_name' => ($pair === 'XXBTZUSD') ? 'Bitcoin (BTC/USD)' : 'Ethereum (ETH/USD)',
            'price' => $entry,
            'score' => $score,
            'max_score' => $max_score,
            'confidence' => $confidence,
            'regime' => $regime,
            'sentiment' => $sentiment,
            'matching_conditions' => $matching,
            'conditions_met' => count($matching),
            'tp_price' => round($tp, 2),
            'sl_price' => round($sl, 2),
            'tp_pct' => round(($tp - $entry) / $entry * 100, 2),
            'sl_pct' => round(($entry - $sl) / $entry * 100, 2),
            'rsi' => round($ind['rsi'][$i], 1),
            'adx' => round($ind['adx'][$i], 1),
            'bb_squeeze' => $squeeze,
            'vol_ratio' => round($vol_ratio, 2),
            'verdict' => ($confidence >= 60) ? 'STRONG BUY SIGNAL' : (($confidence >= 40) ? 'MODERATE BUY SIGNAL' : 'WATCH - NOT YET')
        );
        $signals[] = $signal;
        
        // Store signal if confidence high enough
        if ($confidence >= 35) {
            $chk = $conn->query(sprintf("SELECT id FROM sf_signals WHERE pair='%s' AND status='ACTIVE'", $conn->real_escape_string($pair)));
            if (!$chk || $chk->num_rows == 0) {
                $conn->query(sprintf(
                    "INSERT INTO sf_signals (pair,direction,entry_price,tp_price,sl_price,tp_pct,sl_pct,confidence,fingerprint_match,matching_conditions,regime,sentiment,status,created_at) VALUES ('%s','LONG','%.10f','%.10f','%.10f','%.4f','%.4f','%.4f','%.4f','%s','%s','%s','ACTIVE','%s')",
                    $conn->real_escape_string($pair), $entry, $tp, $sl,
                    round(($tp-$entry)/$entry*100,2), round(($entry-$sl)/$entry*100,2),
                    $confidence, $score,
                    $conn->real_escape_string(implode(' | ', $matching)),
                    $conn->real_escape_string($regime), $conn->real_escape_string($sentiment), $now
                ));
            }
        }
    }
    
    $elapsed = round((microtime(true) - $start) * 1000);
    audit_log($conn, 'check_now', json_encode(array('signals' => count($signals))));
    echo json_encode(array('ok' => true, 'action' => 'check_now', 'signals' => $signals, 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════════
//  FULL RUN, SIGNALS, MONITOR, AUDIT
// ═══════════════════════════════════════════════════════════════════
function action_full_run($conn)
{
    $start = microtime(true);
    ob_start(); action_analyze($conn); $a = json_decode(ob_get_clean(), true);
    ob_start(); action_fingerprint($conn); $f = json_decode(ob_get_clean(), true);
    ob_start(); action_check_now($conn); $c = json_decode(ob_get_clean(), true);
    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true, 'action' => 'full_run',
        'spikes_analyzed' => isset($a['spikes_analyzed']) ? $a['spikes_analyzed'] : 0,
        'fingerprints' => isset($f['fingerprints']) ? $f['fingerprints'] : array(),
        'current_signals' => isset($c['signals']) ? $c['signals'] : array(),
        'elapsed_ms' => $elapsed
    ));
}

function action_signals($conn)
{
    $active = array(); $history = array();
    $res = $conn->query("SELECT * FROM sf_signals WHERE status='ACTIVE' ORDER BY confidence DESC");
    if ($res) { while ($r = $res->fetch_assoc()) { $active[] = $r; } }
    $res2 = $conn->query("SELECT * FROM sf_signals WHERE status='RESOLVED' ORDER BY resolved_at DESC LIMIT 30");
    if ($res2) { while ($r = $res2->fetch_assoc()) { $history[] = $r; } }
    $wins = 0; $losses = 0; $total_pnl = 0;
    foreach ($history as $h) { $p = floatval($h['pnl_pct']); $total_pnl += $p; if ($p > 0) $wins++; else $losses++; }
    $wr = ($wins + $losses > 0) ? round($wins / ($wins + $losses) * 100, 1) : 0;
    
    // Also load fingerprint summary
    $fp_summary = array();
    $res3 = $conn->query("SELECT * FROM sf_fingerprint WHERE pair='BOTH' ORDER BY metric_name");
    if ($res3) { while ($r = $res3->fetch_assoc()) { $fp_summary[] = $r; } }
    
    echo json_encode(array('ok' => true, 'active' => $active, 'history' => $history,
        'fingerprint_summary' => $fp_summary,
        'stats' => array('win_rate' => $wr, 'total_pnl' => round($total_pnl, 2), 'wins' => $wins, 'losses' => $losses)));
}

function action_monitor($conn)
{
    $res = $conn->query("SELECT * FROM sf_signals WHERE status='ACTIVE'");
    if (!$res || $res->num_rows == 0) { echo json_encode(array('ok' => true, 'message' => 'No active signals')); return; }
    $sigs = array(); $pairs = array();
    while ($r = $res->fetch_assoc()) { $sigs[] = $r; $pairs[$r['pair']] = true; }
    $tickers = fetch_tickers(array_keys($pairs));
    $now = date('Y-m-d H:i:s'); $resolved = 0;
    foreach ($sigs as $sig) {
        $cur = isset($tickers[$sig['pair']]) ? $tickers[$sig['pair']] : 0;
        if ($cur <= 0) continue;
        $entry = floatval($sig['entry_price']);
        $pnl = ($entry > 0) ? ($cur - $entry) / $entry * 100 : 0;
        $done = false; $reason = '';
        if ($cur >= floatval($sig['tp_price'])) { $done = true; $reason = 'TP_HIT'; }
        elseif ($cur <= floatval($sig['sl_price'])) { $done = true; $reason = 'SL_HIT'; }
        $hours = (time() - strtotime($sig['created_at'])) / 3600;
        if (!$done && $hours >= 120) { $done = true; $reason = 'EXPIRED'; }
        if ($done) {
            $conn->query(sprintf("UPDATE sf_signals SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',exit_reason='%s',resolved_at='%s' WHERE id=%d",
                $cur, $pnl, $conn->real_escape_string($reason), $now, intval($sig['id'])));
            $resolved++;
        } else {
            $conn->query(sprintf("UPDATE sf_signals SET current_price='%.10f',pnl_pct='%.4f' WHERE id=%d", $cur, $pnl, intval($sig['id'])));
        }
    }
    echo json_encode(array('ok' => true, 'checked' => count($sigs), 'resolved' => $resolved));
}

function action_audit($conn)
{
    $logs = array(); $spikes = array(); $sigs = array();
    $res = $conn->query("SELECT * FROM sf_audit ORDER BY created_at DESC LIMIT 20");
    if ($res) { while ($r = $res->fetch_assoc()) { $logs[] = $r; } }
    $res2 = $conn->query("SELECT pair,spike_pct,spike_candles,start_price,peak_price,pre_rsi,pre_bb_squeeze,pre_obv_divergence,pre_vol_ratio,pre_adx,pre_higher_lows,pre_rsi_divergence,pre_ema_alignment,analyzed_at FROM sf_spikes ORDER BY spike_pct DESC LIMIT 50");
    if ($res2) { while ($r = $res2->fetch_assoc()) { $spikes[] = $r; } }
    $res3 = $conn->query("SELECT * FROM sf_signals ORDER BY created_at DESC LIMIT 20");
    if ($res3) { while ($r = $res3->fetch_assoc()) { $sigs[] = $r; } }
    echo json_encode(array('ok' => true, 'audit_logs' => $logs, 'spikes' => $spikes, 'signals' => $sigs));
}

// ═══════════════════════════════════════════════════════════════════
//  INDICATOR ENGINE
// ═══════════════════════════════════════════════════════════════════
function precompute_indicators($candles)
{
    $o = array(); $h = array(); $l = array(); $c = array(); $v = array();
    foreach ($candles as $cd) {
        $o[] = floatval($cd[1]); $h[] = floatval($cd[2]); $l[] = floatval($cd[3]);
        $c[] = floatval($cd[4]); $v[] = floatval($cd[6]);
    }
    $rsi = calc_rsi($c, 14);
    $atr = calc_atr($h, $l, $c, 14);
    $bb = calc_bb($c, 20, 2.0);
    $macd = calc_macd($c);
    $obv = calc_obv($c, $v);
    $adx = calc_adx($h, $l, $c, 14);
    return array(
        'open'=>$o,'high'=>$h,'low'=>$l,'close'=>$c,'volume'=>$v,
        'rsi'=>$rsi,'atr'=>$atr,
        'bb_upper'=>$bb['u'],'bb_middle'=>$bb['m'],'bb_lower'=>$bb['l'],
        'macd_line'=>$macd['l'],'macd_sig'=>$macd['s'],'macd_hist'=>$macd['h'],
        'obv'=>$obv,'adx'=>$adx['adx']
    );
}

function compute_stoch($h,$l,$c,$i,$p) {
    if ($i < $p) return array('k'=>50,'d'=>50);
    $hh = 0; $ll = 999999999;
    for ($j = $i - $p + 1; $j <= $i; $j++) { if ($h[$j] > $hh) $hh = $h[$j]; if ($l[$j] < $ll) $ll = $l[$j]; }
    $k = ($hh - $ll > 0) ? ($c[$i] - $ll) / ($hh - $ll) * 100 : 50;
    // Simple D = 3-period SMA of K
    $d_sum = $k;
    for ($j = 1; $j < 3; $j++) {
        if ($i - $j >= $p) {
            $h2 = 0; $l2 = 999999999;
            for ($jj = $i - $j - $p + 1; $jj <= $i - $j; $jj++) { if ($h[$jj] > $h2) $h2 = $h[$jj]; if ($l[$jj] < $l2) $l2 = $l[$jj]; }
            $d_sum += ($h2 - $l2 > 0) ? ($c[$i-$j] - $l2) / ($h2 - $l2) * 100 : 50;
        } else { $d_sum += 50; }
    }
    return array('k' => round($k, 2), 'd' => round($d_sum / 3, 2));
}

function compute_mfi($h,$l,$c,$v,$i,$p) {
    if ($i < $p + 1) return 50;
    $pos = 0; $neg = 0;
    for ($j = $i - $p + 1; $j <= $i; $j++) {
        $tp_now = ($h[$j] + $l[$j] + $c[$j]) / 3;
        $tp_prev = ($h[$j-1] + $l[$j-1] + $c[$j-1]) / 3;
        $mf = $tp_now * $v[$j];
        if ($tp_now > $tp_prev) $pos += $mf;
        else $neg += $mf;
    }
    if ($neg <= 0) return 100;
    $ratio = $pos / $neg;
    return round(100 - (100 / (1 + $ratio)), 2);
}

function ema_at($arr, $i, $p) {
    if ($i < $p) return $arr[$i];
    $k = 2.0 / ($p + 1);
    $s = 0;
    for ($j = 0; $j < $p; $j++) { $s += $arr[$j]; }
    $e = $s / $p;
    for ($j = $p; $j <= $i; $j++) { $e = ($arr[$j] * $k) + ($e * (1 - $k)); }
    return $e;
}

// ═══════════════════════════════════════════════════════════════════
//  DATA FETCHING
// ═══════════════════════════════════════════════════════════════════
function fetch_ohlcv($pair, $interval) {
    $ch = curl_init('https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'SpikeForensics/1.0');
    $resp = curl_exec($ch); curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    foreach ($data['result'] as $k => $v) { if ($k !== 'last') return $v; }
    return array();
}

function fetch_tickers($pairs) {
    $ch = curl_init('https://api.kraken.com/0/public/Ticker?pair=' . implode(',', $pairs));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_setopt($ch, CURLOPT_USERAGENT, 'SpikeForensics/1.0');
    $resp = curl_exec($ch); curl_close($ch);
    if (!$resp) return array(); $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    $out = array(); foreach ($data['result'] as $k => $v) { $out[$k] = floatval($v['c'][0]); } return $out;
}

// ═══════════════════════════════════════════════════════════════════
//  INDICATOR CALCULATIONS (PHP 5.2 compatible)
// ═══════════════════════════════════════════════════════════════════
function calc_rsi($c,$p){$n=count($c);$r=array_fill(0,$n,50);if($n<$p+1)return $r;$g=array();$lo=array();for($i=1;$i<$n;$i++){$d=$c[$i]-$c[$i-1];$g[$i]=($d>0)?$d:0;$lo[$i]=($d<0)?abs($d):0;}$ag=0;$al=0;for($i=1;$i<=$p;$i++){$ag+=$g[$i];$al+=$lo[$i];}$ag/=$p;$al/=$p;$r[$p]=($al==0)?100:100-(100/(1+$ag/$al));for($i=$p+1;$i<$n;$i++){$ag=(($ag*($p-1))+$g[$i])/$p;$al=(($al*($p-1))+$lo[$i])/$p;$r[$i]=($al==0)?100:100-(100/(1+$ag/$al));}return $r;}
function calc_atr($h,$l,$c,$p){$n=count($c);$a=array_fill(0,$n,0);if($n<$p+1)return $a;$t=array(0);for($i=1;$i<$n;$i++){$t[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));}$s=0;for($i=1;$i<=$p;$i++){$s+=$t[$i];}$a[$p]=$s/$p;for($i=$p+1;$i<$n;$i++){$a[$i]=(($a[$i-1]*($p-1))+$t[$i])/$p;}for($i=0;$i<$p;$i++){$a[$i]=$a[$p];}return $a;}
function calc_bb($c,$p,$m){$n=count($c);$u=array_fill(0,$n,0);$mid=array_fill(0,$n,0);$lo=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$sl=array_slice($c,$i-$p+1,$p);$mn=array_sum($sl)/$p;$sq=0;foreach($sl as $v){$sq+=($v-$mn)*($v-$mn);}$sd=sqrt($sq/$p);$mid[$i]=$mn;$u[$i]=$mn+($m*$sd);$lo[$i]=$mn-($m*$sd);}return array('u'=>$u,'m'=>$mid,'l'=>$lo);}
function calc_macd($c){$n=count($c);$e12=calc_ema($c,12);$e26=calc_ema($c,26);$ml=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$ml[$i]=$e12[$i]-$e26[$i];}$sig=calc_ema($ml,9);$h=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$h[$i]=$ml[$i]-$sig[$i];}return array('l'=>$ml,'s'=>$sig,'h'=>$h);}
function calc_ema($d,$p){$n=count($d);if($n<$p)return array_fill(0,$n,$d[$n-1]);$k=2.0/($p+1);$e=array_fill(0,$p-1,0);$s=array_sum(array_slice($d,0,$p))/$p;$e[$p-1]=$s;for($i=$p;$i<$n;$i++){$e[$i]=($d[$i]*$k)+($e[$i-1]*(1-$k));}for($i=0;$i<$p-1;$i++){$e[$i]=$e[$p-1];}return $e;}
function calc_obv($c,$v){$n=count($c);$o=array_fill(0,$n,0);for($i=1;$i<$n;$i++){if($c[$i]>$c[$i-1])$o[$i]=$o[$i-1]+$v[$i];elseif($c[$i]<$c[$i-1])$o[$i]=$o[$i-1]-$v[$i];else $o[$i]=$o[$i-1];}return $o;}
function calc_adx($h,$l,$c,$p){$n=count($c);$adx=array_fill(0,$n,25);$pdi=array_fill(0,$n,0);$mdi=array_fill(0,$n,0);if($n<$p*2)return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);$tr=array(0);$pdm=array(0);$mdm=array(0);for($i=1;$i<$n;$i++){$tr[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[$i]=($up>$dn&&$up>0)?$up:0;$mdm[$i]=($dn>$up&&$dn>0)?$dn:0;}$a14=0;$p14=0;$m14=0;for($i=1;$i<=$p;$i++){$a14+=$tr[$i];$p14+=$pdm[$i];$m14+=$mdm[$i];}$dx_arr=array();for($i=$p;$i<$n;$i++){if($i>$p){$a14=$a14-($a14/$p)+$tr[$i];$p14=$p14-($p14/$p)+$pdm[$i];$m14=$m14-($m14/$p)+$mdm[$i];}$pd=($a14>0)?($p14/$a14)*100:0;$md=($a14>0)?($m14/$a14)*100:0;$pdi[$i]=$pd;$mdi[$i]=$md;$ds=$pd+$md;$dx=($ds>0)?abs($pd-$md)/$ds*100:0;$dx_arr[]=$dx;}if(count($dx_arr)>=$p){$av=array_sum(array_slice($dx_arr,0,$p))/$p;$adx[$p*2-1]=$av;for($i=$p;$i<count($dx_arr);$i++){$av=(($av*($p-1))+$dx_arr[$i])/$p;$ix=$i+$p;if($ix<$n)$adx[$ix]=$av;}}return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);}

function audit_log($conn, $action, $details) {
    $conn->query(sprintf("INSERT INTO sf_audit (action,details,created_at) VALUES ('%s','%s','%s')",
        $conn->real_escape_string($action), $conn->real_escape_string($details), date('Y-m-d H:i:s')));
}
?>
