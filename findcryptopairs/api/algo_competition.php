<?php
/**
 * Algorithm Competition Engine v1.0
 * 11 algorithms compete head-to-head on the same meme coins.
 * Consensus layer tracks whether multi-algo agreement = better outcomes.
 *
 * ALGORITHMS (5 Academic + 5 Reddit + 1 Baseline):
 *   1. pulse_baseline     — Our existing momentum+volume+social scorer
 *   2. vwap_momentum      — Volume-weighted momentum (SSRN paper)
 *   3. bb_mean_reversion  — Bollinger Band mean reversion (Springer 2025)
 *   4. rsi_oversold       — RSI oversold bounce (Academic + Reddit)
 *   5. ema_trend          — Triple EMA alignment (9/21/55)
 *   6. obv_accumulation   — On-Balance Volume divergence (Academic)
 *   7. whale_volume       — Volume spike detection (Reddit)
 *   8. atr_breakout       — ATR volatility breakout (Reddit)
 *   9. social_momentum    — CoinGecko trending + momentum combo
 *  10. scalper            — Tight TP/SL Reddit scalping approach
 *  11. anti_dump          — Manipulation filter + clean chart only
 *
 * Actions:
 *   run_round    — Fetch live data, run all 11 algos, seed predictions (key required)
 *   leaderboard  — All algos ranked by win rate + P&L
 *   consensus    — Consensus analysis: do multi-algo picks outperform?
 *   current      — Current open predictions by algo
 *   monitor      — Check live prices against all open competition predictions
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
set_time_limit(60);

$API_KEY = 'compete2026';

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// Ensure table
$conn->query("CREATE TABLE IF NOT EXISTS algo_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    round_id VARCHAR(50) NOT NULL,
    algo_name VARCHAR(40) NOT NULL,
    algo_type VARCHAR(20) NOT NULL DEFAULT 'technical',
    symbol VARCHAR(20) NOT NULL,
    kraken_pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20,10) NOT NULL,
    current_price DECIMAL(20,10) DEFAULT NULL,
    tp_price DECIMAL(20,10) NOT NULL,
    sl_price DECIMAL(20,10) NOT NULL,
    tp_pct DECIMAL(8,4) NOT NULL,
    sl_pct DECIMAL(8,4) NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    reason TEXT,
    consensus_count INT DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    peak_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    trough_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    exit_price DECIMAL(20,10) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    checks_count INT DEFAULT 0,
    last_check DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    INDEX idx_round (round_id),
    INDEX idx_algo (algo_name),
    INDEX idx_status (status),
    INDEX idx_symbol (symbol),
    INDEX idx_consensus (consensus_count)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'leaderboard';

switch ($action) {
    case 'run_round':
        _require_key();
        _run_competition_round($conn);
        break;
    case 'leaderboard':
        _leaderboard($conn);
        break;
    case 'consensus':
        _consensus_analysis($conn);
        break;
    case 'current':
        _current_round($conn);
        break;
    case 'monitor':
        _monitor_competition($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();

// ═══════════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════════
function _require_key()
{
    global $API_KEY;
    $k = isset($_GET['key']) ? $_GET['key'] : '';
    if ($k !== $API_KEY) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TECHNICAL INDICATORS (PHP 5.2 safe)
// ═══════════════════════════════════════════════════════════════════

function _calc_rsi($closes, $period)
{
    if (count($closes) < $period + 1) return 50;
    $gains = array();
    $losses = array();
    for ($i = 1; $i < count($closes); $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) {
            $gains[] = $diff;
            $losses[] = 0;
        } else {
            $gains[] = 0;
            $losses[] = abs($diff);
        }
    }
    $avg_gain = array_sum(array_slice($gains, 0, $period)) / $period;
    $avg_loss = array_sum(array_slice($losses, 0, $period)) / $period;
    for ($i = $period; $i < count($gains); $i++) {
        $avg_gain = (($avg_gain * ($period - 1)) + $gains[$i]) / $period;
        $avg_loss = (($avg_loss * ($period - 1)) + $losses[$i]) / $period;
    }
    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _calc_ema($data, $period)
{
    if (count($data) < $period) return array();
    $k = 2.0 / ($period + 1);
    $ema = array();
    $sma = array_sum(array_slice($data, 0, $period)) / $period;
    $ema[] = $sma;
    for ($i = $period; $i < count($data); $i++) {
        $val = ($data[$i] * $k) + ($ema[count($ema) - 1] * (1 - $k));
        $ema[] = $val;
    }
    return $ema;
}

function _calc_sma($data, $period)
{
    if (count($data) < $period) return array();
    $sma = array();
    for ($i = $period - 1; $i < count($data); $i++) {
        $slice = array_slice($data, $i - $period + 1, $period);
        $sma[] = array_sum($slice) / $period;
    }
    return $sma;
}

function _calc_bollinger($closes, $period, $num_std)
{
    if (count($closes) < $period) return null;
    $sma = array_sum(array_slice($closes, -$period)) / $period;
    $sum_sq = 0;
    $slice = array_slice($closes, -$period);
    foreach ($slice as $c) {
        $sum_sq += pow($c - $sma, 2);
    }
    $std = sqrt($sum_sq / $period);
    return array(
        'middle' => $sma,
        'upper' => $sma + ($num_std * $std),
        'lower' => $sma - ($num_std * $std),
        'std' => $std,
        'bandwidth' => ($std * $num_std * 2) / $sma * 100
    );
}

function _calc_atr($highs, $lows, $closes, $period)
{
    if (count($closes) < $period + 1) return 0;
    $trs = array();
    for ($i = 1; $i < count($closes); $i++) {
        $tr1 = $highs[$i] - $lows[$i];
        $tr2 = abs($highs[$i] - $closes[$i - 1]);
        $tr3 = abs($lows[$i] - $closes[$i - 1]);
        $trs[] = max($tr1, $tr2, $tr3);
    }
    $atr = array_sum(array_slice($trs, 0, $period)) / $period;
    for ($i = $period; $i < count($trs); $i++) {
        $atr = (($atr * ($period - 1)) + $trs[$i]) / $period;
    }
    return $atr;
}

function _calc_obv($closes, $volumes)
{
    if (count($closes) < 2) return array(0);
    $obv = array(0);
    for ($i = 1; $i < count($closes); $i++) {
        $prev = $obv[count($obv) - 1];
        if ($closes[$i] > $closes[$i - 1]) {
            $obv[] = $prev + $volumes[$i];
        } elseif ($closes[$i] < $closes[$i - 1]) {
            $obv[] = $prev - $volumes[$i];
        } else {
            $obv[] = $prev;
        }
    }
    return $obv;
}

function _calc_macd($closes)
{
    $ema12 = _calc_ema($closes, 12);
    $ema26 = _calc_ema($closes, 26);
    if (count($ema12) < 1 || count($ema26) < 1) return null;
    $offset = count($ema12) - count($ema26);
    $macd_line = array();
    for ($i = 0; $i < count($ema26); $i++) {
        $macd_line[] = $ema12[$i + $offset] - $ema26[$i];
    }
    $signal = _calc_ema($macd_line, 9);
    if (count($signal) < 1) return null;
    $hist_offset = count($macd_line) - count($signal);
    $histogram = $macd_line[count($macd_line) - 1] - $signal[count($signal) - 1];
    return array(
        'macd' => $macd_line[count($macd_line) - 1],
        'signal' => $signal[count($signal) - 1],
        'histogram' => $histogram,
        'bullish_cross' => count($macd_line) >= 2 && $macd_line[count($macd_line) - 2] < $signal[count($signal) - 1] && $macd_line[count($macd_line) - 1] >= $signal[count($signal) - 1]
    );
}

// ═══════════════════════════════════════════════════════════════════
//  COMPUTE ALL INDICATORS FOR A COIN
// ═══════════════════════════════════════════════════════════════════
function _compute_indicators($candles)
{
    $closes = array();
    $highs = array();
    $lows = array();
    $volumes = array();
    foreach ($candles as $c) {
        $closes[] = floatval($c[4]);   // close
        $highs[] = floatval($c[2]);    // high
        $lows[] = floatval($c[3]);     // low
        $volumes[] = floatval($c[6]);  // volume
    }

    $ema9 = _calc_ema($closes, 9);
    $ema21 = _calc_ema($closes, 21);
    $ema55 = _calc_ema($closes, 55);

    $vol_sma20 = _calc_sma($volumes, 20);
    $current_vol = count($volumes) > 0 ? $volumes[count($volumes) - 1] : 0;
    $avg_vol = count($vol_sma20) > 0 ? $vol_sma20[count($vol_sma20) - 1] : 1;
    $vol_ratio = ($avg_vol > 0) ? $current_vol / $avg_vol : 1;

    $obv = _calc_obv($closes, $volumes);
    $obv_now = $obv[count($obv) - 1];
    $obv_5ago = (count($obv) > 5) ? $obv[count($obv) - 6] : $obv_now;
    $obv_trend = ($obv_5ago != 0) ? (($obv_now - $obv_5ago) / abs($obv_5ago)) * 100 : 0;

    $recent_high = (count($highs) >= 20) ? max(array_slice($highs, -20)) : (count($highs) > 0 ? max($highs) : 0);

    return array(
        'rsi' => _calc_rsi($closes, 14),
        'ema9' => count($ema9) > 0 ? $ema9[count($ema9) - 1] : 0,
        'ema21' => count($ema21) > 0 ? $ema21[count($ema21) - 1] : 0,
        'ema55' => count($ema55) > 0 ? $ema55[count($ema55) - 1] : 0,
        'bb' => _calc_bollinger($closes, 20, 2),
        'atr' => _calc_atr($highs, $lows, $closes, 14),
        'obv_trend' => $obv_trend,
        'macd' => _calc_macd($closes),
        'vol_ratio' => $vol_ratio,
        'avg_vol' => $avg_vol,
        'price' => count($closes) > 0 ? $closes[count($closes) - 1] : 0,
        'recent_high_20' => $recent_high,
        'closes' => $closes,
        'volumes' => $volumes
    );
}

// ═══════════════════════════════════════════════════════════════════
//  11 ALGORITHM IMPLEMENTATIONS
// ═══════════════════════════════════════════════════════════════════

/** 1. Pulse Baseline — our existing scoring model */
function _algo_pulse_baseline($ticker, $ind, $is_trending)
{
    $chg = floatval($ticker['chg_24h']);
    $vol = floatval($ticker['vol_24h_usd']);
    $spread = floatval($ticker['spread_pct']);

    // Momentum score (35 pts)
    $mom = 0;
    if ($chg >= 3 && $chg <= 15) $mom = 35;
    elseif ($chg >= 1 && $chg < 3) $mom = 25;
    elseif ($chg >= 15 && $chg <= 25) $mom = 15;
    elseif ($chg > 0) $mom = 10;

    // Volume score (25 pts)
    $vs = 0;
    if ($vol >= 500000) $vs = 25;
    elseif ($vol >= 200000) $vs = 18;
    elseif ($vol >= 100000) $vs = 10;

    // Social (15 pts)
    $social = $is_trending ? 15 : 0;

    // Spread (10 pts)
    $sp = 0;
    if ($spread < 0.05) $sp = 10;
    elseif ($spread < 0.1) $sp = 8;
    elseif ($spread < 0.3) $sp = 5;

    $score = $mom + $vs + $social + $sp;
    if ($score < 50) return null;

    $tp = ($chg > 10) ? 6 : 8;
    $sl = ($chg > 10) ? 3 : 4;
    $conf = ($score >= 70) ? 'HIGH' : (($score >= 55) ? 'MEDIUM' : 'LEAN');

    return array('pick' => true, 'tp_pct' => $tp, 'sl_pct' => $sl,
        'confidence' => $conf, 'score' => $score,
        'reason' => 'Pulse=' . $score . ' mom=' . $mom . ' vol=' . $vs . ' social=' . $social);
}

/** 2. Volume-Weighted Momentum (SSRN: 0.94% daily, Sharpe 2.17) */
function _algo_vwap_momentum($ticker, $ind, $is_trending)
{
    $chg = floatval($ticker['chg_24h']);
    $vol_ratio = $ind['vol_ratio'];

    // Core signal: momentum * volume_ratio
    $signal = $chg * $vol_ratio;

    if ($signal < 3) return null;  // Need positive momentum with above-avg volume
    if ($chg < 1) return null;     // Must be gaining

    $conf = 'LEAN';
    if ($signal >= 15) $conf = 'HIGH';
    elseif ($signal >= 8) $conf = 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 8, 'sl_pct' => 4,
        'confidence' => $conf, 'score' => round($signal, 2),
        'reason' => 'VWAP-Mom signal=' . round($signal, 2) . ' (chg=' . $chg . '% * volR=' . round($vol_ratio, 2) . ')');
}

/** 3. Bollinger Band Mean Reversion (Springer 2025 — BB outperforms on 1h crypto) */
function _algo_bb_mean_reversion($ticker, $ind, $is_trending)
{
    $bb = $ind['bb'];
    if (!$bb) return null;

    $price = $ind['price'];
    $lower = $bb['lower'];
    $middle = $bb['middle'];
    $upper = $bb['upper'];

    if ($price <= 0 || $lower <= 0) return null;

    // Buy when price is at or below lower band (oversold bounce expected)
    $dist_to_lower = (($price - $lower) / $price) * 100;

    if ($dist_to_lower > 1.5) return null;  // Only buy near/below lower band

    // Target = middle band
    $tp_pct = (($middle - $price) / $price) * 100;
    if ($tp_pct < 2) $tp_pct = 3;  // Minimum 3%
    if ($tp_pct > 12) $tp_pct = 10; // Cap at 10%

    $sl_pct = $tp_pct / 2;  // 2:1 R:R
    if ($sl_pct < 2) $sl_pct = 2;

    $conf = ($dist_to_lower <= 0) ? 'HIGH' : 'MEDIUM';  // Below band = strongest

    return array('pick' => true, 'tp_pct' => round($tp_pct, 1), 'sl_pct' => round($sl_pct, 1),
        'confidence' => $conf, 'score' => round(-$dist_to_lower + 2, 2),
        'reason' => 'BB revert: price ' . round($dist_to_lower, 2) . '% from lower band, target middle');
}

/** 4. RSI Oversold Bounce (Academic + Reddit consensus) */
function _algo_rsi_oversold($ticker, $ind, $is_trending)
{
    $rsi = $ind['rsi'];

    if ($rsi >= 40) return null;  // Only buy oversold

    $conf = 'LEAN';
    if ($rsi < 25) $conf = 'HIGH';
    elseif ($rsi < 30) $conf = 'MEDIUM';

    // Tighter targets for bounces
    $tp = 6;
    $sl = 3;

    return array('pick' => true, 'tp_pct' => $tp, 'sl_pct' => $sl,
        'confidence' => $conf, 'score' => round(40 - $rsi, 2),
        'reason' => 'RSI oversold at ' . round($rsi, 1) . ' (buy < 40, ideal < 30)');
}

/** 5. Triple EMA Trend Alignment (9 > 21 > 55 = strong uptrend) */
function _algo_ema_trend($ticker, $ind, $is_trending)
{
    $ema9 = $ind['ema9'];
    $ema21 = $ind['ema21'];
    $ema55 = $ind['ema55'];

    if ($ema9 <= 0 || $ema21 <= 0 || $ema55 <= 0) return null;

    // Perfect alignment: 9 > 21 > 55
    $aligned = ($ema9 > $ema21) && ($ema21 > $ema55);
    if (!$aligned) return null;

    // Measure trend strength: how far apart are the EMAs?
    $spread_pct = (($ema9 - $ema55) / $ema55) * 100;

    $conf = 'LEAN';
    if ($spread_pct > 5) $conf = 'HIGH';
    elseif ($spread_pct > 2) $conf = 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 8, 'sl_pct' => 4,
        'confidence' => $conf, 'score' => round($spread_pct, 2),
        'reason' => 'EMA aligned 9>' . round($ema9, 8) . ' 21>' . round($ema21, 8) . ' 55>' . round($ema55, 8) . ' spread=' . round($spread_pct, 2) . '%');
}

/** 6. OBV Accumulation (Academic: volume precedes price) */
function _algo_obv_accumulation($ticker, $ind, $is_trending)
{
    $obv_trend = $ind['obv_trend'];
    $chg = floatval($ticker['chg_24h']);

    // Looking for: OBV rising while price is flat or slightly down
    // This = accumulation (smart money buying before price moves)
    $accumulating = ($obv_trend > 5) && ($chg < 5);

    if (!$accumulating) return null;

    $conf = 'LEAN';
    if ($obv_trend > 20 && $chg < 2) $conf = 'HIGH';
    elseif ($obv_trend > 10) $conf = 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 6, 'sl_pct' => 3,
        'confidence' => $conf, 'score' => round($obv_trend, 2),
        'reason' => 'OBV accumulation: OBV trending +' . round($obv_trend, 1) . '% while price only +' . $chg . '%');
}

/** 7. Whale Volume Spike (Reddit: 2.5x avg vol = institutional entry) */
function _algo_whale_volume($ticker, $ind, $is_trending)
{
    $vol_ratio = $ind['vol_ratio'];
    $chg = floatval($ticker['chg_24h']);

    // Need volume spike + price moving up (not a dump)
    if ($vol_ratio < 2.0) return null;
    if ($chg < 0) return null;

    $conf = 'LEAN';
    if ($vol_ratio > 4 && $chg > 3) $conf = 'HIGH';
    elseif ($vol_ratio > 2.5 && $chg > 1) $conf = 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 6, 'sl_pct' => 3,
        'confidence' => $conf, 'score' => round($vol_ratio, 2),
        'reason' => 'Whale spike: vol ' . round($vol_ratio, 1) . 'x average with +' . $chg . '% price');
}

/** 8. ATR Breakout (Reddit: price breaks above range with volatility expansion) */
function _algo_atr_breakout($ticker, $ind, $is_trending)
{
    $atr = $ind['atr'];
    $price = $ind['price'];
    $recent_high = $ind['recent_high_20'];

    if ($atr <= 0 || $price <= 0 || $recent_high <= 0) return null;

    // Breakout = price within 0.5 ATR of 20-period high
    $breakout_level = $recent_high - (0.5 * $atr);
    $is_breaking = ($price >= $breakout_level);

    if (!$is_breaking) return null;

    // ATR-based TP and SL
    $atr_pct = ($atr / $price) * 100;
    $tp_pct = $atr_pct * 2;
    $sl_pct = $atr_pct;
    if ($tp_pct < 3) $tp_pct = 3;
    if ($tp_pct > 12) $tp_pct = 10;
    if ($sl_pct < 1.5) $sl_pct = 2;
    if ($sl_pct > 6) $sl_pct = 5;

    $conf = ($price >= $recent_high) ? 'HIGH' : 'MEDIUM';

    return array('pick' => true, 'tp_pct' => round($tp_pct, 1), 'sl_pct' => round($sl_pct, 1),
        'confidence' => $conf, 'score' => round($atr_pct, 2),
        'reason' => 'ATR breakout: price near 20-period high, ATR=' . round($atr_pct, 2) . '% of price');
}

/** 9. Social Momentum Combo (arxiv: CG trending + momentum = amplified returns) */
function _algo_social_momentum($ticker, $ind, $is_trending)
{
    // MUST be trending on CoinGecko
    if (!$is_trending) return null;

    $chg = floatval($ticker['chg_24h']);
    $vol = floatval($ticker['vol_24h_usd']);

    // Trending + positive momentum + decent volume
    if ($chg < 1) return null;
    if ($vol < 50000) return null;

    $score = $chg * 2;  // Amplify because social momentum
    if ($vol > 500000) $score += 10;
    if ($vol > 100000) $score += 5;

    $conf = 'LEAN';
    if ($score > 25) $conf = 'HIGH';
    elseif ($score > 15) $conf = 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 6, 'sl_pct' => 3,
        'confidence' => $conf, 'score' => round($score, 2),
        'reason' => 'Social+Mom: CG trending + ' . $chg . '% gain + $' . number_format($vol) . ' vol');
}

/** 10. Scalper (Reddit: tight targets, high frequency, 2:1 R:R) */
function _algo_scalper($ticker, $ind, $is_trending)
{
    $chg = floatval($ticker['chg_24h']);
    $spread = floatval($ticker['spread_pct']);
    $price = floatval($ticker['price']);
    $low = floatval($ticker['low_24h']);
    $high = floatval($ticker['high_24h']);

    // Tight spread required for scalping
    if ($spread > 0.2) return null;

    // Price in bottom 40% of daily range = good scalp entry
    $range = $high - $low;
    if ($range <= 0) return null;
    $position_in_range = ($price - $low) / $range;
    if ($position_in_range > 0.4) return null;  // Only buy near support

    // Need some positive momentum
    if ($chg < 0.5) return null;

    $conf = ($position_in_range < 0.2) ? 'HIGH' : 'MEDIUM';

    return array('pick' => true, 'tp_pct' => 3, 'sl_pct' => 1.5,
        'confidence' => $conf, 'score' => round((0.4 - $position_in_range) * 100, 2),
        'reason' => 'Scalp: price at ' . round($position_in_range * 100) . '% of range, spread=' . $spread . '%');
}

/** 11. Anti-Dump Filter (arxiv: only trade clean charts, reject manipulation) */
function _algo_anti_dump($ticker, $ind, $is_trending)
{
    $chg = floatval($ticker['chg_24h']);
    $vol = floatval($ticker['vol_24h_usd']);
    $spread = floatval($ticker['spread_pct']);
    $range_pct = floatval($ticker['range_pct']);
    $vol_ratio = $ind['vol_ratio'];
    $rsi = $ind['rsi'];

    // REJECT if any manipulation signals
    if ($chg > 25) return null;      // Parabolic pump
    if ($range_pct > 20) return null; // Extreme range = manipulation
    if ($vol_ratio > 5) return null;  // Abnormal volume spike
    if ($spread > 0.5) return null;   // Wide spread = illiquid
    if ($vol < 100000) return null;   // Min liquidity

    // Only accept clean uptrends
    if ($chg < 2) return null;
    if ($rsi > 75) return null;       // Overbought = risky
    if ($rsi < 30) return null;       // Too beaten up

    $macd = $ind['macd'];
    $macd_ok = ($macd && $macd['histogram'] > 0);

    $safety_score = 0;
    if ($spread < 0.1) $safety_score += 3;
    if ($range_pct < 10) $safety_score += 2;
    if ($vol_ratio > 0.8 && $vol_ratio < 3) $safety_score += 2;
    if ($macd_ok) $safety_score += 2;
    if ($rsi > 40 && $rsi < 65) $safety_score += 1;

    if ($safety_score < 5) return null;

    $conf = ($safety_score >= 8) ? 'HIGH' : (($safety_score >= 6) ? 'MEDIUM' : 'LEAN');

    return array('pick' => true, 'tp_pct' => 8, 'sl_pct' => 4,
        'confidence' => $conf, 'score' => $safety_score,
        'reason' => 'Clean chart: safety=' . $safety_score . '/10 spread=' . $spread . '% range=' . $range_pct . '% RSI=' . round($rsi));
}

// ═══════════════════════════════════════════════════════════════════
//  RUN A COMPETITION ROUND
// ═══════════════════════════════════════════════════════════════════
function _run_competition_round($conn)
{
    $start = microtime(true);
    $round_id = 'R' . date('Ymd_Hi');

    // --- STEP 1: Fetch Kraken tickers ---
    $meme_pairs = array(
        'XDGUSD' => 'DOGE', 'SHIBUSD' => 'SHIB', 'PEPEUSD' => 'PEPE',
        'BONKUSD' => 'BONK', 'WIFUSD' => 'WIF', 'FLOKIUSD' => 'FLOKI',
        'PENGUUSD' => 'PENGU', 'TRUMPUSD' => 'TRUMP', 'FARTCOINUSD' => 'FARTCOIN',
        'SPXUSD' => 'SPX6900', 'PONKEUSD' => 'PONKE', 'POPCATUSD' => 'POPCAT',
        'MOODENGUSD' => 'MOODENG', 'GIGAUSD' => 'GIGA', 'VIRTUALUSD' => 'VIRTUAL',
        'TURBOUSD' => 'TURBO', 'MOGUSD' => 'MOG', 'DOGUSD' => 'DOG'
    );

    $pair_list = implode(',', array_keys($meme_pairs));
    $tickers = _fetch_kraken_tickers($pair_list);
    if (empty($tickers)) {
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch Kraken tickers'));
        return;
    }

    // Build ticker info with computed fields
    $coins = array();
    foreach ($tickers as $kp => $t) {
        $sym = isset($meme_pairs[$kp]) ? $meme_pairs[$kp] : $kp;
        $price = floatval($t['c'][0]);
        $high = floatval($t['h'][1]);
        $low = floatval($t['l'][1]);
        $vol = floatval($t['v'][1]) * $price;
        $open24 = floatval($t['o']);
        $chg = ($open24 > 0) ? (($price - $open24) / $open24) * 100 : 0;
        $ask = floatval($t['a'][0]);
        $bid = floatval($t['b'][0]);
        $spread = ($ask > 0) ? (($ask - $bid) / $ask) * 100 : 0;
        $range_pct = ($low > 0) ? (($high - $low) / $low) * 100 : 0;

        $coins[$kp] = array(
            'symbol' => $sym,
            'kraken_pair' => $kp,
            'price' => $price,
            'chg_24h' => round($chg, 2),
            'vol_24h_usd' => round($vol),
            'high_24h' => $high,
            'low_24h' => $low,
            'spread_pct' => round($spread, 3),
            'range_pct' => round($range_pct, 2)
        );
    }

    // Sort by volume, take top 10 for OHLCV (API call budget)
    $vol_sorted = $coins;
    usort($vol_sorted, '_sort_by_vol_desc');
    $top_pairs = array_slice($vol_sorted, 0, 10);

    // --- STEP 2: Fetch OHLCV for top pairs (parallel via curl_multi) ---
    $ohlcv_data = _fetch_ohlcv_parallel($top_pairs);

    // --- STEP 3: Get CoinGecko trending ---
    $trending = _fetch_cg_trending();

    // --- STEP 4: Run all 11 algorithms on each coin ---
    $algo_names = array(
        'pulse_baseline', 'vwap_momentum', 'bb_mean_reversion', 'rsi_oversold',
        'ema_trend', 'obv_accumulation', 'whale_volume', 'atr_breakout',
        'social_momentum', 'scalper', 'anti_dump'
    );
    $algo_types = array(
        'pulse_baseline' => 'baseline',
        'vwap_momentum' => 'academic', 'bb_mean_reversion' => 'academic',
        'rsi_oversold' => 'academic', 'ema_trend' => 'academic', 'obv_accumulation' => 'academic',
        'whale_volume' => 'reddit', 'atr_breakout' => 'reddit',
        'social_momentum' => 'reddit', 'scalper' => 'reddit', 'anti_dump' => 'reddit'
    );

    $all_picks = array();       // algo_name => array of picks
    $coin_consensus = array();  // symbol => count of algos that picked it

    foreach ($algo_names as $algo) {
        $all_picks[$algo] = array();
    }

    foreach ($top_pairs as $coin) {
        $kp = $coin['kraken_pair'];
        $sym = $coin['symbol'];
        $is_trending = in_array(strtolower($sym), $trending);

        // Compute indicators if OHLCV available
        $ind = null;
        if (isset($ohlcv_data[$kp]) && count($ohlcv_data[$kp]) > 55) {
            $ind = _compute_indicators($ohlcv_data[$kp]);
        } else {
            // Minimal indicators from ticker only
            $ind = array(
                'rsi' => 50, 'ema9' => $coin['price'], 'ema21' => $coin['price'],
                'ema55' => $coin['price'], 'bb' => null, 'atr' => 0,
                'obv_trend' => 0, 'macd' => null, 'vol_ratio' => 1,
                'avg_vol' => $coin['vol_24h_usd'], 'price' => $coin['price'],
                'recent_high_20' => $coin['high_24h'],
                'closes' => array(), 'volumes' => array()
            );
        }

        if (!isset($coin_consensus[$sym])) {
            $coin_consensus[$sym] = 0;
        }

        // Run each algorithm
        $algo_funcs = array(
            'pulse_baseline' => '_algo_pulse_baseline',
            'vwap_momentum' => '_algo_vwap_momentum',
            'bb_mean_reversion' => '_algo_bb_mean_reversion',
            'rsi_oversold' => '_algo_rsi_oversold',
            'ema_trend' => '_algo_ema_trend',
            'obv_accumulation' => '_algo_obv_accumulation',
            'whale_volume' => '_algo_whale_volume',
            'atr_breakout' => '_algo_atr_breakout',
            'social_momentum' => '_algo_social_momentum',
            'scalper' => '_algo_scalper',
            'anti_dump' => '_algo_anti_dump'
        );

        foreach ($algo_funcs as $algo_name => $func) {
            $result = call_user_func($func, $coin, $ind, $is_trending);
            if ($result && isset($result['pick']) && $result['pick']) {
                $result['symbol'] = $sym;
                $result['kraken_pair'] = $kp;
                $result['entry_price'] = $coin['price'];
                $all_picks[$algo_name][] = $result;
                $coin_consensus[$sym] = $coin_consensus[$sym] + 1;
            }
        }
    }

    // --- STEP 5: Insert predictions + consensus counts ---
    $total_inserted = 0;
    $round_summary = array();

    foreach ($all_picks as $algo_name => $picks) {
        $count = 0;
        foreach ($picks as $pick) {
            $sym = $pick['symbol'];
            $entry = $pick['entry_price'];
            $tp_pct = $pick['tp_pct'];
            $sl_pct = $pick['sl_pct'];
            $tp_price = $entry * (1 + $tp_pct / 100);
            $sl_price = $entry * (1 - $sl_pct / 100);
            $consensus = isset($coin_consensus[$sym]) ? $coin_consensus[$sym] : 0;

            $sql = sprintf(
                "INSERT INTO algo_predictions (round_id, algo_name, algo_type, symbol, kraken_pair, direction, entry_price, tp_price, sl_price, tp_pct, sl_pct, confidence, reason, consensus_count, status, created_at)
                 VALUES ('%s','%s','%s','%s','%s','LONG','%.10f','%.10f','%.10f','%.4f','%.4f','%s','%s',%d,'OPEN','%s')",
                $conn->real_escape_string($round_id),
                $conn->real_escape_string($algo_name),
                $conn->real_escape_string(isset($algo_types[$algo_name]) ? $algo_types[$algo_name] : 'unknown'),
                $conn->real_escape_string($sym),
                $conn->real_escape_string($pick['kraken_pair']),
                $entry, $tp_price, $sl_price, $tp_pct, $sl_pct,
                $conn->real_escape_string($pick['confidence']),
                $conn->real_escape_string($pick['reason']),
                $consensus,
                date('Y-m-d H:i:s')
            );

            if ($conn->query($sql)) {
                $count++;
                $total_inserted++;
            }
        }
        $round_summary[] = array(
            'algo' => $algo_name,
            'type' => isset($algo_types[$algo_name]) ? $algo_types[$algo_name] : 'unknown',
            'picks_count' => $count,
            'picks' => $picks
        );
    }

    // Build consensus view
    arsort($coin_consensus);
    $consensus_view = array();
    foreach ($coin_consensus as $sym => $cnt) {
        if ($cnt > 0) {
            $which_algos = array();
            foreach ($all_picks as $an => $pp) {
                foreach ($pp as $p) {
                    if ($p['symbol'] === $sym) {
                        $which_algos[] = $an;
                        break;
                    }
                }
            }
            $consensus_view[] = array(
                'symbol' => $sym,
                'algo_count' => $cnt,
                'label' => ($cnt >= 6) ? 'STRONG' : (($cnt >= 4) ? 'MODERATE' : 'WEAK'),
                'algos' => $which_algos
            );
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);

    echo json_encode(array(
        'ok' => true,
        'round_id' => $round_id,
        'timestamp' => date('Y-m-d H:i:s T'),
        'latency_ms' => $elapsed,
        'coins_analyzed' => count($top_pairs),
        'total_predictions' => $total_inserted,
        'algorithms' => $round_summary,
        'consensus' => $consensus_view
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  LEADERBOARD
// ═══════════════════════════════════════════════════════════════════
function _leaderboard($conn)
{
    $res = $conn->query("SELECT algo_name, algo_type,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN exit_reason = 'EXPIRED_48H' THEN 1 ELSE 0 END) as expired,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as best,
        MIN(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as worst,
        AVG(CASE WHEN status = 'OPEN' THEN pnl_pct ELSE NULL END) as avg_open_pnl
    FROM algo_predictions GROUP BY algo_name ORDER BY avg_pnl DESC");

    $algos = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $resolved = intval($r['wins']) + intval($r['losses']) + intval($r['expired']);
            $r['resolved'] = $resolved;
            $r['win_rate'] = ($resolved > 0) ? round((intval($r['wins']) / $resolved) * 100, 1) : 0;
            $algos[] = $r;
        }
    }

    echo json_encode(array('ok' => true, 'leaderboard' => $algos));
}

// ═══════════════════════════════════════════════════════════════════
//  CONSENSUS ANALYSIS
// ═══════════════════════════════════════════════════════════════════
function _consensus_analysis($conn)
{
    // Performance by consensus level
    $res = $conn->query("SELECT
        CASE
            WHEN consensus_count >= 6 THEN 'STRONG (6+)'
            WHEN consensus_count >= 4 THEN 'MODERATE (4-5)'
            WHEN consensus_count >= 2 THEN 'WEAK (2-3)'
            ELSE 'SOLO (1)'
        END as consensus_level,
        consensus_count,
        COUNT(*) as total,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as still_open,
        AVG(CASE WHEN status = 'OPEN' THEN pnl_pct ELSE NULL END) as avg_open_pnl
    FROM algo_predictions GROUP BY consensus_count ORDER BY consensus_count DESC");

    $by_count = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $resolved = intval($r['wins']) + intval($r['losses']);
            $r['win_rate'] = ($resolved > 0) ? round((intval($r['wins']) / $resolved) * 100, 1) : 0;
            $by_count[] = $r;
        }
    }

    // Grouped summary
    $res2 = $conn->query("SELECT
        CASE WHEN consensus_count >= 6 THEN 'strong'
             WHEN consensus_count >= 4 THEN 'moderate'
             WHEN consensus_count >= 2 THEN 'weak'
             ELSE 'solo' END as tier,
        COUNT(*) as total_picks,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl
    FROM algo_predictions GROUP BY tier ORDER BY avg_pnl DESC");

    $by_tier = array();
    if ($res2) {
        while ($r = $res2->fetch_assoc()) {
            $resolved = intval($r['wins']) + intval($r['losses']);
            $r['win_rate'] = ($resolved > 0) ? round((intval($r['wins']) / $resolved) * 100, 1) : 0;
            $by_tier[] = $r;
        }
    }

    // Per-coin consensus detail (current round)
    $res3 = $conn->query("SELECT symbol, consensus_count,
        GROUP_CONCAT(DISTINCT algo_name) as algos,
        COUNT(*) as pick_count,
        AVG(pnl_pct) as avg_pnl,
        MIN(pnl_pct) as worst_pnl,
        MAX(pnl_pct) as best_pnl
    FROM algo_predictions WHERE status = 'OPEN'
    GROUP BY symbol ORDER BY consensus_count DESC");

    $coin_detail = array();
    if ($res3) {
        while ($r = $res3->fetch_assoc()) {
            $coin_detail[] = $r;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'by_consensus_count' => $by_count,
        'by_tier' => $by_tier,
        'current_coins' => $coin_detail,
        'insight' => 'Compare win rates across consensus tiers. If STRONG consensus coins consistently beat SOLO picks, multi-algo agreement is a valid signal.'
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  CURRENT ROUND
// ═══════════════════════════════════════════════════════════════════
function _current_round($conn)
{
    $res = $conn->query("SELECT * FROM algo_predictions WHERE status = 'OPEN' ORDER BY algo_name, symbol");
    $preds = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $preds[] = $r;
        }
    }

    // Group by algo
    $by_algo = array();
    foreach ($preds as $p) {
        $an = $p['algo_name'];
        if (!isset($by_algo[$an])) {
            $by_algo[$an] = array();
        }
        $by_algo[$an][] = $p;
    }

    echo json_encode(array('ok' => true, 'open_count' => count($preds), 'by_algo' => $by_algo));
}

// ═══════════════════════════════════════════════════════════════════
//  MONITOR — check live prices, resolve TP/SL
// ═══════════════════════════════════════════════════════════════════
function _monitor_competition($conn)
{
    $start = microtime(true);

    $res = $conn->query("SELECT * FROM algo_predictions WHERE status = 'OPEN'");
    if (!$res || $res->num_rows === 0) {
        echo json_encode(array('ok' => true, 'message' => 'No open predictions', 'open' => 0, 'resolved' => 0));
        return;
    }

    $pairs_needed = array();
    $open = array();
    while ($row = $res->fetch_assoc()) {
        $open[] = $row;
        $pairs_needed[$row['kraken_pair']] = true;
    }

    $pair_list = implode(',', array_keys($pairs_needed));
    $prices = _fetch_kraken_tickers($pair_list);

    $just_resolved = 0;
    $still_open = 0;
    $now = date('Y-m-d H:i:s');

    foreach ($open as $pred) {
        $kp = $pred['kraken_pair'];
        if (!isset($prices[$kp])) { $still_open++; continue; }

        $current = floatval($prices[$kp]['c'][0]);
        $entry = floatval($pred['entry_price']);
        $tp = floatval($pred['tp_price']);
        $sl = floatval($pred['sl_price']);

        $pnl = (($current - $entry) / $entry) * 100;
        $peak = max(floatval($pred['peak_pnl_pct']), $pnl);
        $trough = min(floatval($pred['trough_pnl_pct']), $pnl);
        $checks = intval($pred['checks_count']) + 1;

        $resolved = false;
        $exit_reason = '';

        if ($current >= $tp) { $resolved = true; $exit_reason = 'TP_HIT'; }
        elseif ($current <= $sl) { $resolved = true; $exit_reason = 'SL_HIT'; }

        $hours = (time() - strtotime($pred['created_at'])) / 3600;
        if (!$resolved && $hours >= 48) { $resolved = true; $exit_reason = 'EXPIRED_48H'; }

        if ($resolved) {
            $conn->query(sprintf(
                "UPDATE algo_predictions SET status='RESOLVED', current_price='%.10f', pnl_pct='%.4f',
                 peak_pnl_pct='%.4f', trough_pnl_pct='%.4f', exit_price='%.10f', exit_reason='%s',
                 checks_count=%d, last_check='%s', resolved_at='%s' WHERE id=%d",
                $current, $pnl, $peak, $trough, $current,
                $conn->real_escape_string($exit_reason), $checks, $now, $now, intval($pred['id'])
            ));
            $just_resolved++;
        } else {
            $conn->query(sprintf(
                "UPDATE algo_predictions SET current_price='%.10f', pnl_pct='%.4f',
                 peak_pnl_pct='%.4f', trough_pnl_pct='%.4f',
                 checks_count=%d, last_check='%s' WHERE id=%d",
                $current, $pnl, $peak, $trough, $checks, $now, intval($pred['id'])
            ));
            $still_open++;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true, 'timestamp' => $now, 'latency_ms' => $elapsed,
        'checked' => count($open), 'still_open' => $still_open, 'just_resolved' => $just_resolved
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  DATA FETCHING HELPERS
// ═══════════════════════════════════════════════════════════════════

function _fetch_kraken_tickers($pair_list)
{
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_list;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'AlgoCompetition/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    return $data['result'];
}

function _fetch_ohlcv_parallel($coins)
{
    $mh = curl_multi_init();
    $handles = array();

    foreach ($coins as $coin) {
        $kp = $coin['kraken_pair'];
        $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $kp . '&interval=60';
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 8);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'AlgoCompetition/1.0');
        curl_multi_add_handle($mh, $ch);
        $handles[$kp] = $ch;
    }

    $running = null;
    do {
        curl_multi_exec($mh, $running);
        curl_multi_select($mh, 1);
    } while ($running > 0);

    $results = array();
    foreach ($handles as $kp => $ch) {
        $resp = curl_multi_getcontent($ch);
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
        if ($resp) {
            $data = json_decode($resp, true);
            if ($data && isset($data['result'])) {
                foreach ($data['result'] as $key => $candles) {
                    if ($key !== 'last') {
                        $results[$kp] = $candles;
                        break;
                    }
                }
            }
        }
    }

    curl_multi_close($mh);
    return $results;
}

function _fetch_cg_trending()
{
    @include_once(dirname(__FILE__) . '/cg_config.php');
    $url = 'https://api.coingecko.com/api/v3/search/trending';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'AlgoCompetition/1.0');
    if (function_exists('cg_auth_headers')) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, cg_auth_headers());
    }
    $resp = curl_exec($ch);
    curl_close($ch);

    $trending = array();
    if ($resp) {
        $data = json_decode($resp, true);
        if ($data && isset($data['coins'])) {
            foreach ($data['coins'] as $c) {
                if (isset($c['item']['symbol'])) {
                    $trending[] = strtolower($c['item']['symbol']);
                }
            }
        }
    }
    return $trending;
}

function _sort_by_vol_desc($a, $b)
{
    return $b['vol_24h_usd'] - $a['vol_24h_usd'];
}
?>