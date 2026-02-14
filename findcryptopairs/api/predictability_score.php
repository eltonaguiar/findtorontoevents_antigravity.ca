<?php
/**
 * Predictability Score Engine v1.0
 * 
 * Computes a data-driven predictability score for each crypto/forex/stock asset.
 * Based on peer-reviewed quantitative finance research:
 *   - Hurst Exponent (trend persistence vs mean reversion vs random walk)
 *   - Autocorrelation (short-term return predictability)
 *   - Volatility Regime Stability (how consistent the asset's behavior is)
 *   - Signal-to-Noise Ratio (genuine pattern strength vs noise)
 *   - Cross-Engine Agreement (how many of our engines agree on direction)
 *   - Historical Resolution Rate (what % of past signals on this asset hit TP)
 *
 * The score weights picks: high-predictability assets get more confidence,
 * low-predictability assets get flagged as higher-risk.
 *
 * PHP 5.2 compatible. No short arrays, no closures, no ?:
 *
 * Actions:
 *   ?action=score&pair=XXBTZUSD     - Get predictability score for one pair
 *   ?action=scores                  - Get all pair scores
 *   ?action=compute                 - Recompute all scores from fresh data
 *   ?action=leaderboard             - Ranked leaderboard by predictability
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// Create tables
$conn->query("CREATE TABLE IF NOT EXISTS ps_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    asset_class VARCHAR(20) NOT NULL DEFAULT 'CRYPTO',
    hurst_exponent FLOAT DEFAULT 0.5,
    hurst_regime VARCHAR(20) DEFAULT 'RANDOM',
    autocorrelation_1 FLOAT DEFAULT 0,
    autocorrelation_5 FLOAT DEFAULT 0,
    volatility_stability FLOAT DEFAULT 0,
    signal_noise_ratio FLOAT DEFAULT 0,
    engine_agreement FLOAT DEFAULT 0,
    engines_bullish INT DEFAULT 0,
    engines_bearish INT DEFAULT 0,
    engines_total INT DEFAULT 0,
    historical_tp_rate FLOAT DEFAULT 0,
    historical_signals INT DEFAULT 0,
    predictability_score FLOAT DEFAULT 0,
    predictability_grade VARCHAR(5) DEFAULT 'F',
    best_strategy VARCHAR(30) DEFAULT 'UNKNOWN',
    computed_at DATETIME,
    UNIQUE KEY pair_idx (pair)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS ps_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    predictability_score FLOAT DEFAULT 0,
    hurst_exponent FLOAT DEFAULT 0.5,
    computed_at DATETIME,
    KEY pair_date (pair, computed_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'scores';

switch ($action) {
    case 'score':
        $pair = isset($_GET['pair']) ? $conn->real_escape_string($_GET['pair']) : '';
        if ($pair === '') { echo json_encode(array('ok' => false, 'error' => 'pair required')); break; }
        _ps_single_score($conn, $pair);
        break;
    case 'scores':
        _ps_all_scores($conn);
        break;
    case 'compute':
        _ps_compute_all($conn);
        break;
    case 'leaderboard':
        _ps_leaderboard($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  ACTION: Single score
// ═══════════════════════════════════════════════════════════════
function _ps_single_score($conn, $pair) {
    $r = $conn->query("SELECT * FROM ps_scores WHERE pair='" . $conn->real_escape_string($pair) . "'");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        echo json_encode(array('ok' => true, 'score' => $row));
    } else {
        // Compute on-the-fly
        $result = _ps_compute_pair($conn, $pair);
        echo json_encode(array('ok' => true, 'score' => $result, 'computed_fresh' => true));
    }
}

// ═══════════════════════════════════════════════════════════════
//  ACTION: All scores
// ═══════════════════════════════════════════════════════════════
function _ps_all_scores($conn) {
    $r = $conn->query("SELECT * FROM ps_scores ORDER BY predictability_score DESC");
    $scores = array();
    if ($r) { while ($row = $r->fetch_assoc()) { $scores[] = $row; } }
    echo json_encode(array('ok' => true, 'count' => count($scores), 'scores' => $scores));
}

// ═══════════════════════════════════════════════════════════════
//  ACTION: Leaderboard — ranked by predictability
// ═══════════════════════════════════════════════════════════════
function _ps_leaderboard($conn) {
    $r = $conn->query("SELECT pair, asset_class, predictability_score, predictability_grade, 
        hurst_exponent, hurst_regime, best_strategy, engine_agreement, 
        engines_bullish, engines_bearish, historical_tp_rate, historical_signals,
        signal_noise_ratio, computed_at
        FROM ps_scores ORDER BY predictability_score DESC");
    $rows = array();
    if ($r) { while ($row = $r->fetch_assoc()) { $rows[] = $row; } }
    echo json_encode(array('ok' => true, 'count' => count($rows), 'leaderboard' => $rows));
}

// ═══════════════════════════════════════════════════════════════
//  ACTION: Compute all — recompute scores for all tracked pairs
// ═══════════════════════════════════════════════════════════════
function _ps_compute_all($conn) {
    $start = microtime(true);
    $pairs = array(
        'XXBTZUSD','XETHZUSD','SOLUSD','XXRPZUSD','ADAUSD','AVAXUSD',
        'DOTUSD','LINKUSD','NEARUSD','SUIUSD','INJUSD','LTCUSD',
        'XDGUSD','XXLMZUSD','ATOMUSD',
        'PEPEUSD','BONKUSD','FLOKIUSD','WIFUSD','SHIBUSD','TRUMPUSD',
        'PENGUUSD','FARTCOINUSD','VIRTUALUSD','SPXUSD','TURBOUSD',
        'AAVEUSD','COMPUSD','CRVUSD','DYDXUSD','OPUSD','FETUSD',
        'APTUSD','BCHUSD','XZECZUSD','XXMRZUSD'
    );

    // Fetch OHLCV for all pairs (4H, 200 candles = ~33 days)
    $all_ohlcv = _ps_fetch_ohlcv_batch($pairs, 240);
    
    // Fetch engine signals for agreement calculation
    $engine_signals = _ps_fetch_engine_signals();
    
    // Fetch historical signal outcomes
    $historical = _ps_fetch_historical_outcomes($conn);

    $results = array();
    foreach ($pairs as $pair) {
        if (!isset($all_ohlcv[$pair]) || count($all_ohlcv[$pair]) < 30) continue;
        $candles = $all_ohlcv[$pair];
        $closes = array();
        foreach ($candles as $c) { $closes[] = $c['close']; }

        // 1. Hurst Exponent (Rescaled Range method)
        $hurst = _ps_hurst_exponent($closes);
        $hurst_dev = abs($hurst - 0.5); // deviation from random walk
        $hurst_regime = 'RANDOM';
        if ($hurst > 0.6) $hurst_regime = 'TRENDING';
        elseif ($hurst < 0.4) $hurst_regime = 'MEAN_REVERTING';

        // 2. Autocorrelation (lag-1 and lag-5 returns)
        $returns = _ps_log_returns($closes);
        $ac1 = _ps_autocorrelation($returns, 1);
        $ac5 = _ps_autocorrelation($returns, 5);

        // 3. Volatility Stability (rolling vol std / rolling vol mean)
        $vol_stab = _ps_volatility_stability($returns, 20);

        // 4. Signal-to-Noise Ratio
        $snr = _ps_signal_noise_ratio($closes, 20);

        // 5. Engine Agreement
        $eng = _ps_engine_agreement($pair, $engine_signals);

        // 6. Historical TP rate
        $hist = isset($historical[$pair]) ? $historical[$pair] : array('tp_rate' => 0, 'total' => 0);

        // ═══ COMPOSITE SCORE ═══
        // Weight: Hurst deviation (25%), Autocorrelation (15%), Vol stability (15%),
        //         SNR (15%), Engine agreement (15%), Historical TP (15%)
        $score_hurst = min($hurst_dev * 5.0, 1.0);    // 0-1: higher = more predictable
        $score_ac = min(abs($ac1) * 5.0, 1.0);        // 0-1: higher autocorrelation = more predictable
        $score_vol = max(0, 1.0 - $vol_stab);          // 0-1: lower vol instability = better
        $score_snr = min($snr / 2.0, 1.0);             // 0-1: higher SNR = better
        $score_eng = $eng['agreement'];                 // 0-1: from engine consensus
        $score_hist = $hist['tp_rate'];                 // 0-1: historical TP hit rate

        $composite = $score_hurst * 0.25
                   + $score_ac * 0.15
                   + $score_vol * 0.15
                   + $score_snr * 0.15
                   + $score_eng * 0.15
                   + $score_hist * 0.15;
        $composite = round($composite * 100, 1); // 0-100 scale

        // Grade
        $grade = 'F';
        if ($composite >= 75) $grade = 'A';
        elseif ($composite >= 60) $grade = 'B';
        elseif ($composite >= 45) $grade = 'C';
        elseif ($composite >= 30) $grade = 'D';

        // Best strategy recommendation
        $best_strat = 'UNKNOWN';
        if ($hurst > 0.6) $best_strat = 'TREND_FOLLOWING';
        elseif ($hurst < 0.4) $best_strat = 'MEAN_REVERSION';
        elseif (abs($ac1) > 0.15) $best_strat = 'MOMENTUM';
        elseif ($vol_stab < 0.3) $best_strat = 'VOLATILITY_BREAKOUT';
        else $best_strat = 'MULTI_INDICATOR';

        $now = date('Y-m-d H:i:s');
        
        // Upsert
        $conn->query("DELETE FROM ps_scores WHERE pair='" . $conn->real_escape_string($pair) . "'");
        $conn->query(sprintf(
            "INSERT INTO ps_scores (pair, asset_class, hurst_exponent, hurst_regime, 
             autocorrelation_1, autocorrelation_5, volatility_stability, signal_noise_ratio,
             engine_agreement, engines_bullish, engines_bearish, engines_total,
             historical_tp_rate, historical_signals, predictability_score, predictability_grade,
             best_strategy, computed_at)
             VALUES ('%s','CRYPTO',%.4f,'%s',%.4f,%.4f,%.4f,%.4f,%.4f,%d,%d,%d,%.4f,%d,%.1f,'%s','%s','%s')",
            $conn->real_escape_string($pair), $hurst, $hurst_regime,
            $ac1, $ac5, $vol_stab, $snr,
            $eng['agreement'], $eng['bullish'], $eng['bearish'], $eng['total'],
            $hist['tp_rate'], $hist['total'],
            $composite, $grade, $best_strat, $now
        ));

        // History
        $conn->query(sprintf(
            "INSERT INTO ps_history (pair, predictability_score, hurst_exponent, computed_at)
             VALUES ('%s', %.1f, %.4f, '%s')",
            $conn->real_escape_string($pair), $composite, $hurst, $now
        ));

        $results[] = array(
            'pair' => $pair,
            'score' => $composite,
            'grade' => $grade,
            'hurst' => round($hurst, 3),
            'regime' => $hurst_regime,
            'best_strategy' => $best_strat,
            'engines' => $eng['bullish'] . 'B/' . $eng['bearish'] . 'S of ' . $eng['total'],
            'tp_rate' => round($hist['tp_rate'] * 100, 1) . '%'
        );
    }

    // Sort by score descending
    usort($results, '_ps_sort_desc');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'pairs_computed' => count($results),
        'elapsed_ms' => $elapsed,
        'results' => $results
    ));
}

function _ps_sort_desc($a, $b) {
    if ($a['score'] == $b['score']) return 0;
    return ($a['score'] > $b['score']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════
//  COMPUTE: Single pair
// ═══════════════════════════════════════════════════════════════
function _ps_compute_pair($conn, $pair) {
    $ohlcv = _ps_fetch_ohlcv(array($pair), 240);
    if (!isset($ohlcv[$pair]) || count($ohlcv[$pair]) < 30) {
        return array('pair' => $pair, 'error' => 'Insufficient data');
    }
    $closes = array();
    foreach ($ohlcv[$pair] as $c) { $closes[] = $c['close']; }
    $hurst = _ps_hurst_exponent($closes);
    $returns = _ps_log_returns($closes);
    $ac1 = _ps_autocorrelation($returns, 1);

    return array(
        'pair' => $pair,
        'hurst' => round($hurst, 3),
        'hurst_regime' => ($hurst > 0.6) ? 'TRENDING' : (($hurst < 0.4) ? 'MEAN_REVERTING' : 'RANDOM'),
        'autocorrelation' => round($ac1, 4),
        'note' => 'Run ?action=compute for full scores with all components'
    );
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Hurst Exponent (Rescaled Range / R/S method)
//  H > 0.5 = trending (persistent), H < 0.5 = mean-reverting, H = 0.5 = random
// ═══════════════════════════════════════════════════════════════
function _ps_hurst_exponent($series) {
    $n = count($series);
    if ($n < 20) return 0.5;

    // Log returns
    $returns = array();
    for ($i = 1; $i < $n; $i++) {
        if ($series[$i - 1] > 0 && $series[$i] > 0) {
            $returns[] = log($series[$i] / $series[$i - 1]);
        }
    }
    $n_ret = count($returns);
    if ($n_ret < 16) return 0.5;

    // R/S analysis at multiple window sizes
    $window_sizes = array();
    $ws = 8;
    while ($ws <= $n_ret / 2) {
        $window_sizes[] = $ws;
        $ws = (int)($ws * 1.5);
    }
    if (count($window_sizes) < 3) return 0.5;

    $log_n = array();
    $log_rs = array();

    foreach ($window_sizes as $wsize) {
        $num_windows = (int)($n_ret / $wsize);
        if ($num_windows < 1) continue;

        $rs_values = array();
        for ($w = 0; $w < $num_windows; $w++) {
            $start_idx = $w * $wsize;
            $window = array_slice($returns, $start_idx, $wsize);

            // Mean
            $mean = array_sum($window) / $wsize;

            // Cumulative deviation from mean
            $cumdev = array();
            $cum = 0;
            foreach ($window as $val) {
                $cum += ($val - $mean);
                $cumdev[] = $cum;
            }

            // Range
            $r = max($cumdev) - min($cumdev);

            // Std dev
            $sumsq = 0;
            foreach ($window as $val) {
                $sumsq += ($val - $mean) * ($val - $mean);
            }
            $s = sqrt($sumsq / $wsize);

            if ($s > 0) {
                $rs_values[] = $r / $s;
            }
        }

        if (count($rs_values) > 0) {
            $avg_rs = array_sum($rs_values) / count($rs_values);
            if ($avg_rs > 0) {
                $log_n[] = log($wsize);
                $log_rs[] = log($avg_rs);
            }
        }
    }

    if (count($log_n) < 3) return 0.5;

    // Linear regression: log(R/S) = H * log(n) + c
    $hurst = _ps_linear_regression_slope($log_n, $log_rs);
    
    // Clamp to valid range
    if ($hurst < 0.01) $hurst = 0.01;
    if ($hurst > 0.99) $hurst = 0.99;
    return $hurst;
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Autocorrelation at lag k
// ═══════════════════════════════════════════════════════════════
function _ps_autocorrelation($returns, $lag) {
    $n = count($returns);
    if ($n < $lag + 10) return 0;

    $mean = array_sum($returns) / $n;
    $var = 0;
    for ($i = 0; $i < $n; $i++) {
        $var += ($returns[$i] - $mean) * ($returns[$i] - $mean);
    }
    if ($var == 0) return 0;

    $cov = 0;
    for ($i = $lag; $i < $n; $i++) {
        $cov += ($returns[$i] - $mean) * ($returns[$i - $lag] - $mean);
    }

    return $cov / $var;
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Volatility Stability (coefficient of variation of rolling vol)
//  Lower = more stable behavior = more predictable
// ═══════════════════════════════════════════════════════════════
function _ps_volatility_stability($returns, $window) {
    $n = count($returns);
    if ($n < $window + 5) return 1.0;

    $rolling_vols = array();
    for ($i = $window; $i < $n; $i++) {
        $slice = array_slice($returns, $i - $window, $window);
        $mean = array_sum($slice) / $window;
        $sumsq = 0;
        foreach ($slice as $v) { $sumsq += ($v - $mean) * ($v - $mean); }
        $rolling_vols[] = sqrt($sumsq / $window);
    }

    if (count($rolling_vols) < 3) return 1.0;
    $mean_vol = array_sum($rolling_vols) / count($rolling_vols);
    if ($mean_vol == 0) return 1.0;

    $sumsq = 0;
    foreach ($rolling_vols as $v) { $sumsq += ($v - $mean_vol) * ($v - $mean_vol); }
    $std_vol = sqrt($sumsq / count($rolling_vols));

    return $std_vol / $mean_vol; // CV: 0 = perfectly stable, high = unstable
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Signal-to-Noise Ratio (trend strength vs noise)
// ═══════════════════════════════════════════════════════════════
function _ps_signal_noise_ratio($closes, $ma_period) {
    $n = count($closes);
    if ($n < $ma_period + 5) return 0;

    // "Signal" = smoothed price change (MA)
    // "Noise" = std of deviations from MA
    $ma = array();
    for ($i = $ma_period - 1; $i < $n; $i++) {
        $sum = 0;
        for ($j = $i - $ma_period + 1; $j <= $i; $j++) { $sum += $closes[$j]; }
        $ma[] = $sum / $ma_period;
    }

    $signal_change = abs($ma[count($ma) - 1] - $ma[0]);
    
    // Noise = std of (close - MA)
    $deviations = array();
    for ($i = 0; $i < count($ma); $i++) {
        $close_idx = $i + $ma_period - 1;
        $deviations[] = $closes[$close_idx] - $ma[$i];
    }
    $mean_dev = array_sum($deviations) / count($deviations);
    $sumsq = 0;
    foreach ($deviations as $d) { $sumsq += ($d - $mean_dev) * ($d - $mean_dev); }
    $noise = sqrt($sumsq / count($deviations));

    if ($noise == 0) return 0;
    return $signal_change / $noise;
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Log returns
// ═══════════════════════════════════════════════════════════════
function _ps_log_returns($closes) {
    $returns = array();
    for ($i = 1; $i < count($closes); $i++) {
        if ($closes[$i - 1] > 0 && $closes[$i] > 0) {
            $returns[] = log($closes[$i] / $closes[$i - 1]);
        }
    }
    return $returns;
}

// ═══════════════════════════════════════════════════════════════
//  MATH: Linear regression slope
// ═══════════════════════════════════════════════════════════════
function _ps_linear_regression_slope($x, $y) {
    $n = count($x);
    if ($n < 2) return 0;
    $sum_x = array_sum($x);
    $sum_y = array_sum($y);
    $sum_xy = 0;
    $sum_xx = 0;
    for ($i = 0; $i < $n; $i++) {
        $sum_xy += $x[$i] * $y[$i];
        $sum_xx += $x[$i] * $x[$i];
    }
    $denom = $n * $sum_xx - $sum_x * $sum_x;
    if ($denom == 0) return 0;
    return ($n * $sum_xy - $sum_x * $sum_y) / $denom;
}

// ═══════════════════════════════════════════════════════════════
//  ENGINE AGREEMENT: Check how many engines agree on direction
// ═══════════════════════════════════════════════════════════════
function _ps_engine_agreement($pair, $all_signals) {
    $bullish = 0;
    $bearish = 0;
    $total = 0;

    foreach ($all_signals as $engine_name => $signals) {
        foreach ($signals as $sig) {
            $sig_pair = isset($sig['pair']) ? $sig['pair'] : (isset($sig['symbol']) ? $sig['symbol'] : '');
            if (strtoupper($sig_pair) !== strtoupper($pair)) continue;
            $dir = isset($sig['direction']) ? strtoupper($sig['direction']) : '';
            if ($dir === '') {
                $st = isset($sig['signal_type']) ? strtoupper($sig['signal_type']) : '';
                if (strpos($st, 'BUY') !== false || strpos($st, 'LONG') !== false) $dir = 'LONG';
                elseif (strpos($st, 'SELL') !== false || strpos($st, 'SHORT') !== false) $dir = 'SHORT';
            }
            $total++;
            if ($dir === 'LONG' || $dir === 'BUY') $bullish++;
            elseif ($dir === 'SHORT' || $dir === 'SELL') $bearish++;
        }
    }

    $agreement = 0;
    if ($total > 0) {
        $dominant = max($bullish, $bearish);
        $agreement = $dominant / $total;
    }

    return array('agreement' => $agreement, 'bullish' => $bullish, 'bearish' => $bearish, 'total' => $total);
}

// ═══════════════════════════════════════════════════════════════
//  HISTORICAL OUTCOMES: Aggregate TP hit rate across all engines
// ═══════════════════════════════════════════════════════════════
function _ps_fetch_historical_outcomes($conn) {
    $results = array();
    
    // Hybrid Engine
    $r = $conn->query("SELECT pair, status FROM he_signals WHERE status IN ('RESOLVED','TP_HIT','SL_HIT','EXPIRED')");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $p = $row['pair'];
            if (!isset($results[$p])) $results[$p] = array('tp' => 0, 'total' => 0);
            $results[$p]['total']++;
            if ($row['status'] === 'TP_HIT' || $row['status'] === 'RESOLVED') $results[$p]['tp']++;
        }
    }

    // TV Technicals
    $r = $conn->query("SELECT pair, status FROM tv_signals WHERE status IN ('RESOLVED','TP_HIT','SL_HIT','EXPIRED')");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $p = $row['pair'];
            if (!isset($results[$p])) $results[$p] = array('tp' => 0, 'total' => 0);
            $results[$p]['total']++;
            if ($row['status'] === 'TP_HIT' || $row['status'] === 'RESOLVED') $results[$p]['tp']++;
        }
    }

    // Kimi Enhanced
    $r = $conn->query("SELECT pair, status FROM ke_signals WHERE status IN ('RESOLVED','TP_HIT','SL_HIT','EXPIRED')");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $p = $row['pair'];
            if (!isset($results[$p])) $results[$p] = array('tp' => 0, 'total' => 0);
            $results[$p]['total']++;
            if ($row['status'] === 'TP_HIT' || $row['status'] === 'RESOLVED') $results[$p]['tp']++;
        }
    }

    // Convert to rates
    $final = array();
    foreach ($results as $pair => $data) {
        $rate = ($data['total'] > 0) ? ($data['tp'] / $data['total']) : 0;
        $final[$pair] = array('tp_rate' => $rate, 'total' => $data['total']);
    }
    return $final;
}

// ═══════════════════════════════════════════════════════════════
//  FETCH ENGINE SIGNALS: Get active signals from all engines
// ═══════════════════════════════════════════════════════════════
function _ps_fetch_engine_signals() {
    $all = array();
    $endpoints = array(
        'hybrid' => 'https://findtorontoevents.ca/findcryptopairs/api/hybrid_engine.php?action=signals',
        'tv_tech' => 'https://findtorontoevents.ca/findcryptopairs/api/tv_technicals.php?action=signals',
        'kimi' => 'https://findtorontoevents.ca/findcryptopairs/api/kimi_enhanced.php?action=signals',
        'academic' => 'https://findtorontoevents.ca/findcryptopairs/api/academic_edge.php?action=signals',
        'expert' => 'https://findtorontoevents.ca/findcryptopairs/api/expert_consensus.php?action=signals',
        'alpha' => 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php?action=signals'
    );

    $mh = curl_multi_init();
    $handles = array();
    foreach ($endpoints as $name => $url) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 8);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $handles[$name] = $ch;
        curl_multi_add_handle($mh, $ch);
    }
    $running = null;
    do { curl_multi_exec($mh, $running); usleep(10000); } while ($running > 0);
    foreach ($handles as $name => $ch) {
        $resp = curl_multi_getcontent($ch);
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
        if ($resp) {
            $data = json_decode($resp, true);
            if (is_array($data)) {
                $sigs = array();
                if (isset($data['active'])) $sigs = $data['active'];
                elseif (isset($data['signals'])) $sigs = $data['signals'];
                $all[$name] = is_array($sigs) ? $sigs : array();
            }
        }
    }
    curl_multi_close($mh);
    return $all;
}

// ═══════════════════════════════════════════════════════════════
//  DATA FETCHING: Kraken OHLCV batch
// ═══════════════════════════════════════════════════════════════
function _ps_fetch_ohlcv_batch($pairs, $interval) {
    return _ps_fetch_ohlcv($pairs, $interval);
}

function _ps_fetch_ohlcv($pairs, $interval) {
    $results = array();
    $batches = array_chunk($pairs, 5);
    foreach ($batches as $batch) {
        $mh = curl_multi_init();
        $handles = array();
        foreach ($batch as $pair) {
            $ch = curl_init('https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 12);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            $handles[$pair] = $ch;
            curl_multi_add_handle($mh, $ch);
        }
        $running = null;
        do { curl_multi_exec($mh, $running); usleep(10000); } while ($running > 0);
        foreach ($handles as $pair => $ch) {
            $resp = curl_multi_getcontent($ch);
            curl_multi_remove_handle($mh, $ch);
            curl_close($ch);
            if ($resp) {
                $data = json_decode($resp, true);
                if (is_array($data) && isset($data['result'])) {
                    foreach ($data['result'] as $key => $candles) {
                        if ($key === 'last') continue;
                        $parsed = array();
                        foreach ($candles as $c) {
                            $parsed[] = array(
                                'time' => (float)$c[0],
                                'open' => (float)$c[1],
                                'high' => (float)$c[2],
                                'low' => (float)$c[3],
                                'close' => (float)$c[4],
                                'volume' => (float)$c[6]
                            );
                        }
                        $results[$pair] = $parsed;
                    }
                }
            }
        }
        curl_multi_close($mh);
    }
    return $results;
}
