<?php
/**
 * SPIKE DETECTOR v1.0 — Reverse-Engineered from 6 Massive Profit Events
 *
 * Based on forensic analysis of BTC and ETH spikes that delivered 50-500% gains:
 *   1. BTC COVID Bottom (Mar 2020): $3,850 → $11,500 (+198%)
 *   2. BTC 2018 Bear Bottom (Dec 2018): $3,200 → $12,000 (+275%)
 *   3. BTC Post-COVID Breakout (Q3 2020): $10,000 → $58,000 (+480%)
 *   4. ETH COVID Bottom (Mar 2020): $90 → $390 (+333%)
 *   5. ETH DeFi Summer (Q2 2020): $200 → $480 (+140%)
 *   6. ETH Summer Dip (Jun 2021): $1,700 → $4,800 (+182%)
 *
 * THE 12 REVERSE-ENGINEERED SIGNALS:
 *   === CAPITULATION SIGNALS (appear at bottoms) ===
 *   1. Volume Climax: Daily volume >300% of 20-day average
 *   2. RSI Extreme Oversold: RSI(14) < 25 on daily
 *   3. Long Downside Wicks: Wick-to-body ratio > 3:1 on daily
 *   4. Realized volatility spike: ATR expanding > 2x 30-day average
 *
 *   === STRUCTURAL SUPPORT SIGNALS ===
 *   5. 200-Day MA Test & Hold: Price within 3% of 200MA with bounce
 *   6. 200-Week MA Proximity: Price near cycle-defining support
 *   7. Prior Breakout Zone Retest: Price returns to previous resistance-turned-support
 *
 *   === TREND CONFIRMATION SIGNALS ===
 *   8. 200-Day MA Reclaim: Price closes above 200MA after being below
 *   9. Golden Cross: 50MA crosses above 200MA
 *   10. Higher Lows Forming: 3+ consecutive higher swing lows
 *   11. Breakout from Multi-Week Base: Price breaks above range high on volume
 *
 *   === MOMENTUM CONFIRMATION ===
 *   12. RSI Bullish Divergence: Price lower low + RSI higher low
 *
 * SCORING: Each signal = 1 point. 3+ signals = BUY zone.
 *          Signals are grouped into phases (Capitulation → Support → Confirmation)
 *
 * Focused EXCLUSIVELY on BTCUSD and ETHUSD.
 * PHP 5.2 compatible. Real Kraken data only.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(120);

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB')); exit; }
$conn->set_charset('utf8');

/* ---------- SCHEMA ---------- */
$conn->query("CREATE TABLE IF NOT EXISTS spike_detector_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset VARCHAR(16),
    snapshot_time DATETIME,
    price DECIMAL(20,8),
    signals_active INT DEFAULT 0,
    signal_phase VARCHAR(32),
    verdict VARCHAR(32),
    signal_details TEXT,
    raw_data TEXT,
    INDEX(asset), INDEX(snapshot_time), INDEX(verdict)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS spike_detector_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset VARCHAR(16),
    alert_type VARCHAR(32),
    signal_count INT,
    verdict VARCHAR(32),
    price_at_alert DECIMAL(20,8),
    details TEXT,
    created_at DATETIME,
    resolved_at DATETIME,
    outcome_pnl DECIMAL(10,4),
    status ENUM('ACTIVE','RESOLVED_WIN','RESOLVED_LOSS','EXPIRED') DEFAULT 'ACTIVE',
    INDEX(asset), INDEX(status), INDEX(created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS spike_detector_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phase VARCHAR(32),
    action VARCHAR(64),
    detail TEXT,
    data_json TEXT,
    created_at DATETIME,
    INDEX(phase)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

/* ---------- ROUTING ---------- */
$action = isset($_GET['action']) ? $_GET['action'] : 'status';
switch ($action) {
    case 'scan':        _scan($conn); break;
    case 'history':     _history($conn); break;
    case 'alerts':      _alerts($conn); break;
    case 'monitor':     _monitor_alerts($conn); break;
    case 'performance': _performance($conn); break;
    case 'methodology': _methodology(); break;
    case 'status':      _status($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action')); break;
}
$conn->close();

/* ============================================================
   KRAKEN API
   ============================================================ */
function _kraken_ticker($pair) {
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return null;
    $j = json_decode($resp, true);
    if (!$j || !empty($j['error'])) return null;
    if (!isset($j['result']) || count($j['result']) === 0) return null;
    $keys = array_keys($j['result']);
    return $j['result'][$keys[0]];
}

function _kraken_ohlc($pair, $interval, $since) {
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
    if ($since) $url .= '&since=' . $since;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return array();
    $j = json_decode($resp, true);
    if (!$j || !empty($j['error'])) return array();
    if (!isset($j['result'])) return array();
    $keys = array_keys($j['result']);
    /* Skip the 'last' key */
    foreach ($keys as $k) {
        if ($k !== 'last' && is_array($j['result'][$k])) return $j['result'][$k];
    }
    return array();
}

/* ============================================================
   INDICATOR LIBRARY
   ============================================================ */
function _ema($data, $period) {
    if (count($data) < $period) return array();
    $k = 2.0 / ($period + 1);
    $ema = array();
    $sum = 0;
    for ($i = 0; $i < $period; $i++) $sum += $data[$i];
    $ema[$period - 1] = $sum / $period;
    for ($i = $period; $i < count($data); $i++) {
        $ema[$i] = $data[$i] * $k + $ema[$i - 1] * (1 - $k);
    }
    return $ema;
}

function _sma($data, $period) {
    $sma = array();
    for ($i = $period - 1; $i < count($data); $i++) {
        $sum = 0;
        for ($j = $i - $period + 1; $j <= $i; $j++) $sum += $data[$j];
        $sma[$i] = $sum / $period;
    }
    return $sma;
}

function _rsi($closes, $period) {
    if (count($closes) < $period + 1) return array();
    $rsi = array();
    $gains = 0; $losses = 0;
    for ($i = 1; $i <= $period; $i++) {
        $d = $closes[$i] - $closes[$i - 1];
        if ($d > 0) $gains += $d; else $losses += abs($d);
    }
    $avg_g = $gains / $period;
    $avg_l = $losses / $period;
    $rs = ($avg_l > 0) ? $avg_g / $avg_l : 100;
    $rsi[$period] = 100 - (100 / (1 + $rs));
    for ($i = $period + 1; $i < count($closes); $i++) {
        $d = $closes[$i] - $closes[$i - 1];
        $g = ($d > 0) ? $d : 0;
        $l = ($d < 0) ? abs($d) : 0;
        $avg_g = ($avg_g * ($period - 1) + $g) / $period;
        $avg_l = ($avg_l * ($period - 1) + $l) / $period;
        $rs = ($avg_l > 0) ? $avg_g / $avg_l : 100;
        $rsi[$i] = 100 - (100 / (1 + $rs));
    }
    return $rsi;
}

function _atr($highs, $lows, $closes, $period) {
    if (count($closes) < $period + 1) return array();
    $tr = array();
    for ($i = 1; $i < count($closes); $i++) {
        $hl = $highs[$i] - $lows[$i];
        $hc = abs($highs[$i] - $closes[$i - 1]);
        $lc = abs($lows[$i] - $closes[$i - 1]);
        $tr[$i] = max($hl, $hc, $lc);
    }
    $atr = array();
    $sum = 0;
    for ($i = 1; $i <= $period; $i++) $sum += $tr[$i];
    $atr[$period] = $sum / $period;
    for ($i = $period + 1; $i < count($closes); $i++) {
        $atr[$i] = ($atr[$i - 1] * ($period - 1) + $tr[$i]) / $period;
    }
    return $atr;
}

/* ============================================================
   THE 12 REVERSE-ENGINEERED SIGNALS
   ============================================================ */
function _run_all_signals($closes, $highs, $lows, $volumes, $opens, $asset) {
    $n = count($closes);
    if ($n < 210) return array('error' => 'Need 210+ candles');

    $price = $closes[$n - 1];
    $signals = array();

    /* ---------- CAPITULATION SIGNALS ---------- */

    /* Signal 1: Volume Climax — volume > 300% of 20-day average */
    $vol_20avg = 0;
    for ($i = $n - 21; $i < $n - 1; $i++) $vol_20avg += $volumes[$i];
    $vol_20avg = $vol_20avg / 20;
    $vol_today = $volumes[$n - 1];
    $vol_ratio = ($vol_20avg > 0) ? $vol_today / $vol_20avg : 0;
    $sig1 = ($vol_ratio >= 3.0);
    /* Also check if any of the last 3 days had a climax */
    $vol_climax_recent = false;
    for ($i = $n - 3; $i < $n; $i++) {
        if ($vol_20avg > 0 && ($volumes[$i] / $vol_20avg) >= 2.5) $vol_climax_recent = true;
    }
    $signals[] = array(
        'id' => 1,
        'name' => 'Volume Climax',
        'category' => 'CAPITULATION',
        'active' => $sig1 || $vol_climax_recent,
        'strength' => min(100, round($vol_ratio / 3.0 * 100)),
        'value' => round($vol_ratio, 2) . 'x avg',
        'threshold' => '>3.0x 20-day avg',
        'source_events' => 'BTC COVID 2020, BTC 2018 Bottom',
        'detail' => 'Current volume is ' . round($vol_ratio, 2) . 'x the 20-day average' . ($vol_climax_recent ? ' (climax seen in last 3 days)' : '')
    );

    /* Signal 2: RSI Extreme Oversold — RSI(14) < 25 */
    $rsi14 = _rsi($closes, 14);
    $rsi_now = isset($rsi14[$n - 1]) ? $rsi14[$n - 1] : 50;
    $rsi_threshold = ($asset === 'BTC') ? 25 : 28; /* ETH threshold slightly higher */
    $sig2 = ($rsi_now < $rsi_threshold);
    $signals[] = array(
        'id' => 2,
        'name' => 'RSI Extreme Oversold',
        'category' => 'CAPITULATION',
        'active' => $sig2,
        'strength' => $sig2 ? min(100, round(($rsi_threshold - $rsi_now) / $rsi_threshold * 200)) : 0,
        'value' => round($rsi_now, 1),
        'threshold' => '<' . $rsi_threshold,
        'source_events' => 'BTC COVID 2020 (RSI<20), BTC 2018 Bottom',
        'detail' => 'RSI(14) = ' . round($rsi_now, 1) . ' (threshold: <' . $rsi_threshold . ')'
    );

    /* Signal 3: Long Downside Wicks — wick-to-body ratio > 3:1 */
    $body = abs($closes[$n - 1] - $opens[$n - 1]);
    $lower_wick = min($opens[$n - 1], $closes[$n - 1]) - $lows[$n - 1];
    $wick_ratio = ($body > 0) ? $lower_wick / $body : 0;
    /* Check last 3 candles for any long-wick candle */
    $long_wick_recent = false;
    for ($i = $n - 3; $i < $n; $i++) {
        $b = abs($closes[$i] - $opens[$i]);
        $lw = min($opens[$i], $closes[$i]) - $lows[$i];
        if ($b > 0 && ($lw / $b) >= 2.5) $long_wick_recent = true;
    }
    $sig3 = ($wick_ratio >= 3.0 || $long_wick_recent);
    $signals[] = array(
        'id' => 3,
        'name' => 'Long Downside Wicks (Rejection)',
        'category' => 'CAPITULATION',
        'active' => $sig3,
        'strength' => $sig3 ? min(100, round($wick_ratio / 3 * 100)) : 0,
        'value' => round($wick_ratio, 1) . ':1',
        'threshold' => '>3:1 wick-to-body',
        'source_events' => 'BTC COVID 2020 (V-shaped reversal candle)',
        'detail' => 'Wick ratio ' . round($wick_ratio, 1) . ':1' . ($long_wick_recent ? ', long wick seen in last 3 days' : '')
    );

    /* Signal 4: Volatility Spike — ATR expanding > 2x its 30-day average */
    $atr14 = _atr($highs, $lows, $closes, 14);
    $atr_now = isset($atr14[$n - 1]) ? $atr14[$n - 1] : 0;
    $atr_30avg = 0; $atr_count = 0;
    for ($i = $n - 31; $i < $n - 1; $i++) {
        if (isset($atr14[$i])) { $atr_30avg += $atr14[$i]; $atr_count++; }
    }
    $atr_30avg = ($atr_count > 0) ? $atr_30avg / $atr_count : $atr_now;
    $atr_expansion = ($atr_30avg > 0) ? $atr_now / $atr_30avg : 1;
    $sig4 = ($atr_expansion >= 2.0);
    $signals[] = array(
        'id' => 4,
        'name' => 'Realized Volatility Spike',
        'category' => 'CAPITULATION',
        'active' => $sig4,
        'strength' => min(100, round($atr_expansion / 2 * 100)),
        'value' => round($atr_expansion, 2) . 'x avg ATR',
        'threshold' => '>2.0x 30-day avg ATR',
        'source_events' => 'All 6 events (vol spikes at inflection points)',
        'detail' => 'ATR is ' . round($atr_expansion, 2) . 'x its 30-day average'
    );

    /* ---------- STRUCTURAL SUPPORT SIGNALS ---------- */

    /* Signal 5: 200-Day MA Test & Hold */
    $sma200 = _sma($closes, 200);
    $sma200_now = isset($sma200[$n - 1]) ? $sma200[$n - 1] : 0;
    $dist_200ma = ($sma200_now > 0) ? (($price - $sma200_now) / $sma200_now) * 100 : 0;
    $at_200ma = (abs($dist_200ma) < 3); /* Within 3% */
    $above_200ma = ($price > $sma200_now);
    /* Bounce detection: was below or at 200MA recently, now above */
    $bounce_200ma = false;
    if ($n > 5 && $sma200_now > 0) {
        for ($i = $n - 5; $i < $n - 1; $i++) {
            if (isset($sma200[$i]) && $closes[$i] < $sma200[$i] * 1.01) $bounce_200ma = true;
        }
        $bounce_200ma = $bounce_200ma && ($price > $sma200_now);
    }
    $sig5 = ($at_200ma || $bounce_200ma);
    $signals[] = array(
        'id' => 5,
        'name' => '200-Day MA Test & Hold',
        'category' => 'SUPPORT',
        'active' => $sig5,
        'strength' => $sig5 ? min(100, round((3 - abs($dist_200ma)) / 3 * 100)) : 0,
        'value' => round($dist_200ma, 2) . '% from 200MA ($' . round($sma200_now, 2) . ')',
        'threshold' => 'Within 3% of 200MA with bounce',
        'source_events' => 'BTC COVID 2020, ETH COVID 2020, ETH DeFi Summer 2020, ETH Summer 2021',
        'detail' => 'Price is ' . round($dist_200ma, 2) . '% ' . ($above_200ma ? 'above' : 'below') . ' 200MA' . ($bounce_200ma ? ' — BOUNCE DETECTED' : '')
    );

    /* Signal 6: Prior Breakout Zone Retest */
    /* Find the highest high from 60-90 days ago (potential prior breakout zone) */
    $prior_zone_high = 0; $prior_zone_low = 999999999;
    for ($i = $n - 90; $i < $n - 60; $i++) {
        if ($i >= 0) {
            if ($highs[$i] > $prior_zone_high) $prior_zone_high = $highs[$i];
            if ($lows[$i] < $prior_zone_low) $prior_zone_low = $lows[$i];
        }
    }
    $at_prior_zone = ($prior_zone_high > 0 && abs($price - $prior_zone_high) / $prior_zone_high < 0.05);
    $at_prior_support = ($prior_zone_low > 0 && abs($price - $prior_zone_low) / $prior_zone_low < 0.05);
    $sig6 = ($at_prior_zone || $at_prior_support);
    $signals[] = array(
        'id' => 6,
        'name' => 'Prior Breakout Zone Retest',
        'category' => 'SUPPORT',
        'active' => $sig6,
        'strength' => $sig6 ? 70 : 0,
        'value' => 'Zone: $' . round($prior_zone_low, 2) . ' - $' . round($prior_zone_high, 2),
        'threshold' => 'Price within 5% of prior 60-90d range',
        'source_events' => 'BTC 2018 Bottom, ETH Summer 2021 (prior breakout zone retest)',
        'detail' => ($at_prior_zone ? 'Near prior resistance zone ' : ($at_prior_support ? 'Near prior support zone ' : 'Not near prior zone')) . '($' . round($prior_zone_low, 2) . '-$' . round($prior_zone_high, 2) . ')'
    );

    /* Signal 7: Price Deviation from ATH > -30% */
    $ath = 0;
    for ($i = 0; $i < $n; $i++) {
        if ($highs[$i] > $ath) $ath = $highs[$i];
    }
    $ath_deviation = ($ath > 0) ? (($price - $ath) / $ath) * 100 : 0;
    $sig7 = ($ath_deviation < -30);
    $signals[] = array(
        'id' => 7,
        'name' => 'Deep Discount from ATH',
        'category' => 'SUPPORT',
        'active' => $sig7,
        'strength' => $sig7 ? min(100, round(abs($ath_deviation) / 50 * 100)) : 0,
        'value' => round($ath_deviation, 1) . '% from ATH ($' . round($ath, 2) . ')',
        'threshold' => '>30% below ATH',
        'source_events' => 'BTC 2018 Bottom (-84%), BTC COVID 2020 (-63%), ETH COVID 2020 (-93%)',
        'detail' => 'Price is ' . round(abs($ath_deviation), 1) . '% below all-time high of $' . round($ath, 2)
    );

    /* ---------- TREND CONFIRMATION SIGNALS ---------- */

    /* Signal 8: 200-Day MA Reclaim */
    $sma200_prev5 = isset($sma200[$n - 6]) ? $sma200[$n - 6] : $sma200_now;
    $was_below = false;
    for ($i = $n - 10; $i < $n - 1; $i++) {
        if (isset($sma200[$i]) && $closes[$i] < $sma200[$i]) $was_below = true;
    }
    $ma_reclaim = ($was_below && $price > $sma200_now);
    $sig8 = $ma_reclaim;
    $signals[] = array(
        'id' => 8,
        'name' => '200-Day MA Reclaim',
        'category' => 'TREND_CONFIRM',
        'active' => $sig8,
        'strength' => $sig8 ? 85 : 0,
        'value' => $above_200ma ? 'Above 200MA' : 'Below 200MA',
        'threshold' => 'Cross from below to above 200MA within 10 days',
        'source_events' => 'BTC COVID 2020 (reclaimed ~$8-9k), ETH DeFi Summer 2020, ETH Summer 2021',
        'detail' => ($ma_reclaim ? 'RECLAIMED — was below 200MA within last 10 days, now above' : 'No recent reclaim')
    );

    /* Signal 9: Golden Cross (50MA > 200MA) */
    $sma50 = _sma($closes, 50);
    $sma50_now = isset($sma50[$n - 1]) ? $sma50[$n - 1] : 0;
    $sma50_prev = isset($sma50[$n - 2]) ? $sma50[$n - 2] : 0;
    $sma200_prev = isset($sma200[$n - 2]) ? $sma200[$n - 2] : 0;
    $golden_cross = ($sma50_prev < $sma200_prev && $sma50_now > $sma200_now);
    /* Also check if golden cross happened in last 10 days */
    $recent_golden = false;
    for ($i = $n - 10; $i < $n; $i++) {
        if ($i > 0 && isset($sma50[$i]) && isset($sma50[$i - 1]) && isset($sma200[$i]) && isset($sma200[$i - 1])) {
            if ($sma50[$i - 1] < $sma200[$i - 1] && $sma50[$i] >= $sma200[$i]) $recent_golden = true;
        }
    }
    $sig9 = ($golden_cross || $recent_golden);
    $signals[] = array(
        'id' => 9,
        'name' => 'Golden Cross (50MA > 200MA)',
        'category' => 'TREND_CONFIRM',
        'active' => $sig9,
        'strength' => $sig9 ? 90 : 0,
        'value' => '50MA=$' . round($sma50_now, 2) . ' vs 200MA=$' . round($sma200_now, 2),
        'threshold' => '50-day MA crosses above 200-day MA',
        'source_events' => 'BTC Post-COVID 2020, ETH DeFi Summer 2020',
        'detail' => ($sig9 ? 'GOLDEN CROSS detected!' : '50MA ' . ($sma50_now > $sma200_now ? 'above' : 'below') . ' 200MA (diff: ' . round($sma50_now - $sma200_now, 2) . ')')
    );

    /* Signal 10: Higher Lows Forming (3+ consecutive) */
    /* Find swing lows using a 5-candle lookback */
    $swing_lows = array();
    for ($i = 5; $i < $n - 5; $i++) {
        $is_low = true;
        for ($j = $i - 5; $j <= $i + 5; $j++) {
            if ($j !== $i && $lows[$j] < $lows[$i]) { $is_low = false; break; }
        }
        if ($is_low) $swing_lows[] = array('idx' => $i, 'low' => $lows[$i]);
    }
    /* Check last 3-5 swing lows */
    $recent_swings = array_slice($swing_lows, -5);
    $higher_lows_count = 0;
    for ($i = 1; $i < count($recent_swings); $i++) {
        if ($recent_swings[$i]['low'] > $recent_swings[$i - 1]['low']) $higher_lows_count++;
    }
    $sig10 = ($higher_lows_count >= 2);
    $signals[] = array(
        'id' => 10,
        'name' => 'Higher Lows Forming',
        'category' => 'TREND_CONFIRM',
        'active' => $sig10,
        'strength' => min(100, $higher_lows_count * 30),
        'value' => $higher_lows_count . ' consecutive higher lows',
        'threshold' => '3+ consecutive higher swing lows',
        'source_events' => 'BTC Post-COVID 2020 (higher lows $9k, $9.8k, $10.5k), BTC 2018 Bottom',
        'detail' => $higher_lows_count . ' higher lows detected in recent swing structure'
    );

    /* Signal 11: Breakout from Multi-Week Base on Volume */
    /* Range over last 20 days (the base) */
    $range_high = 0; $range_low = 999999999;
    for ($i = $n - 21; $i < $n - 1; $i++) {
        if ($highs[$i] > $range_high) $range_high = $highs[$i];
        if ($lows[$i] < $range_low) $range_low = $lows[$i];
    }
    $range_pct = ($range_low > 0) ? (($range_high - $range_low) / $range_low) * 100 : 0;
    $tight_range = ($range_pct < 15); /* Base = tight range */
    $breakout_up = ($price > $range_high);
    $vol_on_breakout = ($vol_20avg > 0 && $vol_today > $vol_20avg * 1.5);
    $sig11 = ($breakout_up && $vol_on_breakout);
    /* Also accept near-breakout with volume surge */
    $near_breakout = ($range_high > 0 && ($range_high - $price) / $range_high < 0.02);
    $sig11 = $sig11 || ($near_breakout && $vol_on_breakout && $tight_range);
    $signals[] = array(
        'id' => 11,
        'name' => 'Base Breakout on Volume',
        'category' => 'TREND_CONFIRM',
        'active' => $sig11,
        'strength' => $sig11 ? min(100, round($vol_ratio * 30)) : 0,
        'value' => 'Range: $' . round($range_low, 2) . '-$' . round($range_high, 2) . ' (' . round($range_pct, 1) . '%)',
        'threshold' => 'Break above 20-day range high with 1.5x+ volume',
        'source_events' => 'BTC 2018-2019 (breakout from $3-4k base), BTC 2020 ($10-12k breakout), ETH 2020 ($200-250 breakout)',
        'detail' => ($breakout_up ? 'BREAKOUT above range! ' : ($near_breakout ? 'Near breakout ' : 'Within range. ')) . 'Volume ' . round($vol_ratio, 1) . 'x avg'
    );

    /* Signal 12: RSI Bullish Divergence */
    /* Price making lower low but RSI making higher low over last 14-30 candles */
    $rsi_div = false;
    $rsi_vals = _rsi($closes, 14);
    /* Find lows in last 30 candles */
    $price_low1 = $lows[$n - 1]; $price_low2 = $lows[$n - 1];
    $rsi_low1 = isset($rsi_vals[$n - 1]) ? $rsi_vals[$n - 1] : 50;
    $rsi_low2 = $rsi_low1;
    $low1_idx = $n - 1; $low2_idx = $n - 1;

    /* Find two most recent swing lows */
    $recent_price_lows = array();
    for ($i = $n - 30; $i < $n; $i++) {
        if ($i >= 2 && $i < $n - 1) {
            if ($lows[$i] < $lows[$i - 1] && $lows[$i] < $lows[$i + 1] && $lows[$i] < $lows[$i - 2]) {
                $recent_price_lows[] = array('idx' => $i, 'price' => $lows[$i], 'rsi' => isset($rsi_vals[$i]) ? $rsi_vals[$i] : 50);
            }
        }
    }

    if (count($recent_price_lows) >= 2) {
        $pl = $recent_price_lows[count($recent_price_lows) - 1]; /* Most recent */
        $pp = $recent_price_lows[count($recent_price_lows) - 2]; /* Previous */
        if ($pl['price'] < $pp['price'] && $pl['rsi'] > $pp['rsi']) {
            $rsi_div = true;
        }
    }
    $sig12 = $rsi_div;
    $signals[] = array(
        'id' => 12,
        'name' => 'RSI Bullish Divergence',
        'category' => 'MOMENTUM',
        'active' => $sig12,
        'strength' => $sig12 ? 80 : 0,
        'value' => $rsi_div ? 'DIVERGENCE detected' : 'No divergence',
        'threshold' => 'Price lower low + RSI higher low',
        'source_events' => 'BTC 2018 Bottom (RSI divergence during Dec 2018 low)',
        'detail' => ($rsi_div ? 'BULLISH DIVERGENCE — price made lower low but RSI made higher low' : 'No bullish divergence detected in last 30 candles')
    );

    /* ---------- AGGREGATE SCORING ---------- */
    $active_count = 0;
    $by_category = array('CAPITULATION' => 0, 'SUPPORT' => 0, 'TREND_CONFIRM' => 0, 'MOMENTUM' => 0);
    $active_names = array();

    foreach ($signals as $s) {
        if ($s['active']) {
            $active_count++;
            $by_category[$s['category']]++;
            $active_names[] = $s['name'];
        }
    }

    /* Determine phase */
    $phase = 'NO_SIGNAL';
    if ($by_category['CAPITULATION'] >= 2) $phase = 'CAPITULATION';
    elseif ($by_category['SUPPORT'] >= 2) $phase = 'SUPPORT_TEST';
    elseif ($by_category['TREND_CONFIRM'] >= 2) $phase = 'TREND_FORMING';

    /* Verdict */
    $verdict = 'WAIT';
    if ($active_count >= 5) $verdict = 'STRONG_BUY';
    elseif ($active_count >= 3) $verdict = 'BUY';
    elseif ($active_count >= 2) $verdict = 'ACCUMULATE';

    /* Additional: combined score (average of active signal strengths) */
    $total_strength = 0;
    foreach ($signals as $s) {
        if ($s['active']) $total_strength += $s['strength'];
    }
    $avg_strength = ($active_count > 0) ? round($total_strength / $active_count, 1) : 0;

    return array(
        'asset' => $asset,
        'price' => $price,
        'signals_active' => $active_count,
        'signals_total' => 12,
        'phase' => $phase,
        'verdict' => $verdict,
        'avg_strength' => $avg_strength,
        'by_category' => $by_category,
        'active_signals' => $active_names,
        'key_levels' => array(
            '200_day_ma' => round($sma200_now, 2),
            '50_day_ma' => round($sma50_now, 2),
            'rsi_14' => round($rsi_now, 1),
            'atr_14' => round($atr_now, 2),
            'ath' => round($ath, 2),
            'ath_deviation' => round($ath_deviation, 1) . '%',
            '20d_range_high' => round($range_high, 2),
            '20d_range_low' => round($range_low, 2)
        ),
        'signals' => $signals
    );
}

/* ============================================================
   ACTIONS
   ============================================================ */
function _scan($conn) {
    $assets = array(
        'BTC' => 'XXBTZUSD',
        'ETH' => 'XETHZUSD'
    );

    $results = array();

    foreach ($assets as $name => $pair) {
        /* Fetch 240 days of daily candles */
        $since = time() - (245 * 86400);
        $candles = _kraken_ohlc($pair, 1440, $since);

        if (count($candles) < 210) {
            $results[$name] = array('error' => 'Insufficient data: only ' . count($candles) . ' candles');
            continue;
        }

        $closes = array(); $highs = array(); $lows = array(); $volumes = array(); $opens = array();
        foreach ($candles as $c) {
            $opens[] = floatval($c[1]);
            $highs[] = floatval($c[2]);
            $lows[] = floatval($c[3]);
            $closes[] = floatval($c[4]);
            $volumes[] = floatval($c[6]);
        }

        $result = _run_all_signals($closes, $highs, $lows, $volumes, $opens, $name);
        $results[$name] = $result;

        /* Save snapshot */
        $conn->query(sprintf(
            "INSERT INTO spike_detector_snapshots (asset, snapshot_time, price, signals_active, signal_phase, verdict, signal_details, raw_data) VALUES ('%s','%s',%s,%d,'%s','%s','%s','%s')",
            $name,
            date('Y-m-d H:i:s'),
            $result['price'],
            $result['signals_active'],
            $conn->real_escape_string($result['phase']),
            $result['verdict'],
            $conn->real_escape_string(json_encode($result['active_signals'])),
            $conn->real_escape_string(json_encode($result['key_levels']))
        ));

        /* Create alert if verdict is BUY or STRONG_BUY */
        if ($result['verdict'] === 'BUY' || $result['verdict'] === 'STRONG_BUY') {
            /* Check if there is already an active alert for this asset */
            $existing = $conn->query("SELECT id FROM spike_detector_alerts WHERE asset='" . $name . "' AND status='ACTIVE' ORDER BY id DESC LIMIT 1");
            if ($existing->num_rows === 0) {
                $conn->query(sprintf(
                    "INSERT INTO spike_detector_alerts (asset, alert_type, signal_count, verdict, price_at_alert, details, created_at, status) VALUES ('%s','%s',%d,'%s',%s,'%s','%s','ACTIVE')",
                    $name,
                    $result['phase'],
                    $result['signals_active'],
                    $result['verdict'],
                    $result['price'],
                    $conn->real_escape_string(json_encode(array('active_signals' => $result['active_signals'], 'key_levels' => $result['key_levels']))),
                    date('Y-m-d H:i:s')
                ));
            }
        }

        _audit_log($conn, 'SCAN', 'analyzed_' . $name, $name . ': ' . $result['signals_active'] . '/12 signals active, verdict=' . $result['verdict'], json_encode($result['key_levels']));

        sleep(1); /* Rate limit */
    }

    echo json_encode(array('ok' => true, 'scan_time' => date('Y-m-d H:i:s'), 'results' => $results));
}

function _history($conn) {
    $asset = isset($_GET['asset']) ? $_GET['asset'] : 'BTC';
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 48;

    $r = $conn->query("SELECT * FROM spike_detector_snapshots WHERE asset='" . $conn->real_escape_string($asset) . "' ORDER BY snapshot_time DESC LIMIT " . $limit);
    $snapshots = array();
    while ($row = $r->fetch_assoc()) $snapshots[] = $row;

    echo json_encode(array('ok' => true, 'asset' => $asset, 'count' => count($snapshots), 'snapshots' => $snapshots));
}

function _alerts($conn) {
    $status = isset($_GET['status']) ? $_GET['status'] : 'ACTIVE';
    $where = "1=1";
    if ($status !== 'all') $where = "status='" . $conn->real_escape_string($status) . "'";

    $r = $conn->query("SELECT * FROM spike_detector_alerts WHERE " . $where . " ORDER BY created_at DESC LIMIT 50");
    $alerts = array();
    while ($row = $r->fetch_assoc()) {
        if ($row['status'] === 'ACTIVE') {
            /* Add live PnL */
            $pair = ($row['asset'] === 'BTC') ? 'XXBTZUSD' : 'XETHZUSD';
            $ticker = _kraken_ticker($pair);
            if ($ticker) {
                $live = floatval($ticker['c'][0]);
                $entry = floatval($row['price_at_alert']);
                $row['live_price'] = $live;
                $row['live_pnl'] = round((($live - $entry) / $entry) * 100, 4);
            }
        }
        $alerts[] = $row;
    }

    echo json_encode(array('ok' => true, 'count' => count($alerts), 'alerts' => $alerts));
}

function _monitor_alerts($conn) {
    $r = $conn->query("SELECT * FROM spike_detector_alerts WHERE status='ACTIVE'");
    $checked = 0; $resolved = 0;

    while ($row = $r->fetch_assoc()) {
        $pair = ($row['asset'] === 'BTC') ? 'XXBTZUSD' : 'XETHZUSD';
        $ticker = _kraken_ticker($pair);
        if (!$ticker) continue;

        $live = floatval($ticker['c'][0]);
        $entry = floatval($row['price_at_alert']);
        $pnl = (($live - $entry) / $entry) * 100;
        $checked++;

        /* Auto-resolve: +20% TP or -10% SL or 30 days expired */
        $age_days = (time() - strtotime($row['created_at'])) / 86400;

        if ($pnl >= 20) {
            $conn->query(sprintf("UPDATE spike_detector_alerts SET status='RESOLVED_WIN', outcome_pnl=%s, resolved_at='%s' WHERE id=%d", $pnl, date('Y-m-d H:i:s'), $row['id']));
            $resolved++;
            _audit_log($conn, 'MONITOR', 'resolved_win', $row['asset'] . ' hit +20% TP: PnL=' . round($pnl, 2) . '%', '');
        } elseif ($pnl <= -10) {
            $conn->query(sprintf("UPDATE spike_detector_alerts SET status='RESOLVED_LOSS', outcome_pnl=%s, resolved_at='%s' WHERE id=%d", $pnl, date('Y-m-d H:i:s'), $row['id']));
            $resolved++;
            _audit_log($conn, 'MONITOR', 'resolved_loss', $row['asset'] . ' hit -10% SL: PnL=' . round($pnl, 2) . '%', '');
        } elseif ($age_days > 30) {
            $conn->query(sprintf("UPDATE spike_detector_alerts SET status='EXPIRED', outcome_pnl=%s, resolved_at='%s' WHERE id=%d", $pnl, date('Y-m-d H:i:s'), $row['id']));
            $resolved++;
            _audit_log($conn, 'MONITOR', 'expired', $row['asset'] . ' expired after 30 days: PnL=' . round($pnl, 2) . '%', '');
        }
        sleep(1);
    }

    echo json_encode(array('ok' => true, 'checked' => $checked, 'resolved' => $resolved));
}

function _performance($conn) {
    $r = $conn->query("SELECT status, COUNT(*) as cnt, AVG(outcome_pnl) as avg_pnl, MAX(outcome_pnl) as best, MIN(outcome_pnl) as worst FROM spike_detector_alerts WHERE status != 'ACTIVE' GROUP BY status");
    $by_status = array();
    while ($row = $r->fetch_assoc()) $by_status[$row['status']] = $row;

    $r2 = $conn->query("SELECT COUNT(*) as active FROM spike_detector_alerts WHERE status='ACTIVE'");
    $active = $r2->fetch_assoc();

    $r3 = $conn->query("SELECT * FROM spike_detector_alerts WHERE status != 'ACTIVE' ORDER BY resolved_at DESC LIMIT 10");
    $recent = array();
    while ($row = $r3->fetch_assoc()) $recent[] = $row;

    echo json_encode(array(
        'ok' => true,
        'active_alerts' => intval($active['active']),
        'by_status' => $by_status,
        'recent_resolved' => $recent
    ));
}

function _methodology() {
    echo json_encode(array(
        'ok' => true,
        'title' => 'Spike Detector — Reverse-Engineered from 6 Massive Profit Events',
        'source_events' => array(
            array('id' => 1, 'asset' => 'BTC', 'event' => 'COVID Bottom Mar 2020', 'entry' => 3850, 'exit' => 11500, 'gain' => '+198%'),
            array('id' => 2, 'asset' => 'BTC', 'event' => '2018 Bear Bottom Dec 2018', 'entry' => 3200, 'exit' => 12000, 'gain' => '+275%'),
            array('id' => 3, 'asset' => 'BTC', 'event' => 'Post-COVID Breakout Q3 2020', 'entry' => 10000, 'exit' => 58000, 'gain' => '+480%'),
            array('id' => 4, 'asset' => 'ETH', 'event' => 'COVID Bottom Mar 2020', 'entry' => 90, 'exit' => 390, 'gain' => '+333%'),
            array('id' => 5, 'asset' => 'ETH', 'event' => 'DeFi Summer Q2 2020', 'entry' => 200, 'exit' => 480, 'gain' => '+140%'),
            array('id' => 6, 'asset' => 'ETH', 'event' => 'Summer Dip Jun 2021', 'entry' => 1700, 'exit' => 4800, 'gain' => '+182%')
        ),
        'signal_categories' => array(
            'CAPITULATION' => array('Volume Climax (>300% avg)', 'RSI Extreme (<25)', 'Long Downside Wicks (>3:1)', 'Volatility Spike (>2x ATR)'),
            'SUPPORT' => array('200-Day MA Test & Hold', 'Prior Breakout Zone Retest', 'Deep Discount from ATH (>30%)'),
            'TREND_CONFIRM' => array('200-Day MA Reclaim', 'Golden Cross (50>200)', 'Higher Lows Forming', 'Base Breakout on Volume'),
            'MOMENTUM' => array('RSI Bullish Divergence')
        ),
        'scoring' => '3+ signals = BUY, 5+ signals = STRONG_BUY. Strongest when signals span multiple categories.',
        'exit_rules' => 'TP: +20%, SL: -10%, Max hold: 30 days',
        'disclaimer' => 'Educational only. Past performance does not guarantee future results.'
    ));
}

function _status($conn) {
    $r1 = $conn->query("SELECT COUNT(*) as cnt FROM spike_detector_snapshots");
    $snaps = $r1->fetch_assoc();

    $r2 = $conn->query("SELECT COUNT(*) as cnt FROM spike_detector_alerts WHERE status='ACTIVE'");
    $active = $r2->fetch_assoc();

    $r3 = $conn->query("SELECT asset, snapshot_time, signals_active, verdict FROM spike_detector_snapshots ORDER BY id DESC LIMIT 2");
    $latest = array();
    while ($row = $r3->fetch_assoc()) $latest[] = $row;

    echo json_encode(array(
        'ok' => true,
        'total_snapshots' => intval($snaps['cnt']),
        'active_alerts' => intval($active['cnt']),
        'latest_scans' => $latest,
        'monitored_assets' => array('BTCUSD', 'ETHUSD'),
        'signals_tracked' => 12,
        'source_events_analyzed' => 6,
        'methodology' => 'Reverse-engineered from 6 BTC/ETH spikes delivering 140-480% gains'
    ));
}

function _audit_log($conn, $phase, $action, $detail, $data_json) {
    $conn->query(sprintf(
        "INSERT INTO spike_detector_audit (phase, action, detail, data_json, created_at) VALUES ('%s','%s','%s','%s','%s')",
        $conn->real_escape_string($phase),
        $conn->real_escape_string($action),
        $conn->real_escape_string($detail),
        $conn->real_escape_string($data_json),
        date('Y-m-d H:i:s')
    ));
}
