<?php
/**
 * Feature Store Population Pipeline v1.0
 *
 * Fetches OHLCV data from Kraken, computes 40+ technical features per asset,
 * and writes them to ml_feature_store in the stocks DB.
 *
 * Also populates:
 *   - ml_regime_snapshots (daily market regime)
 *   - ml_learning_curve (engine improvement tracking)
 *   - ml_platform_daily (platform-wide daily metrics)
 *
 * This is the SINGLE MOST IMPORTANT pipeline for ML training.
 * Without populated features, no model can be trained.
 *
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=populate          — Populate features for all pairs (latest candle)
 *   ?action=populate_regime   — Compute daily regime snapshot
 *   ?action=populate_daily    — Compute daily platform metrics
 *   ?action=populate_learning — Update learning curves for all engines
 *   ?action=populate_all      — Run all population steps
 *   ?action=status            — Show feature store stats
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

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

switch ($action) {
    case 'populate':         _fsp_populate_features($conn); break;
    case 'populate_regime':  _fsp_populate_regime($conn); break;
    case 'populate_daily':   _fsp_populate_daily($conn); break;
    case 'populate_learning': _fsp_populate_learning($conn); break;
    case 'populate_all':     _fsp_populate_all($conn); break;
    case 'status':           _fsp_status($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  POPULATE ALL: Run every pipeline step
// ═══════════════════════════════════════════════════════════════
function _fsp_populate_all($conn) {
    $start = microtime(true);
    $results = array();

    // 1. Features
    ob_start();
    _fsp_populate_features($conn);
    $r1 = json_decode(ob_get_clean(), true);
    $results['features'] = is_array($r1) ? $r1 : array('error' => 'failed');

    // 2. Regime
    ob_start();
    _fsp_populate_regime($conn);
    $r2 = json_decode(ob_get_clean(), true);
    $results['regime'] = is_array($r2) ? $r2 : array('error' => 'failed');

    // 3. Daily
    ob_start();
    _fsp_populate_daily($conn);
    $r3 = json_decode(ob_get_clean(), true);
    $results['daily'] = is_array($r3) ? $r3 : array('error' => 'failed');

    // 4. Learning
    ob_start();
    _fsp_populate_learning($conn);
    $r4 = json_decode(ob_get_clean(), true);
    $results['learning'] = is_array($r4) ? $r4 : array('error' => 'failed');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array('ok' => true, 'elapsed_ms' => $elapsed, 'results' => $results));
}

// ═══════════════════════════════════════════════════════════════
//  STATUS: Feature store stats
// ═══════════════════════════════════════════════════════════════
function _fsp_status($conn) {
    $tables = array(
        'ml_feature_store', 'ml_regime_snapshots',
        'ml_platform_daily', 'ml_learning_curve',
        'ml_model_registry', 'ml_ab_tests',
        'ml_ensemble_weights', 'ml_calibration_log'
    );
    $stats = array();
    foreach ($tables as $tbl) {
        $r = $conn->query("SELECT COUNT(*) as cnt FROM " . $tbl);
        $rows = 0;
        if ($r) { $cnt_row = $r->fetch_assoc(); $rows = (int)$cnt_row['cnt']; }
        $stats[] = array('table' => $tbl, 'rows' => $rows);
    }
    // Feature store per-pair breakdown
    $pairs = array();
    $r = $conn->query("SELECT pair, COUNT(*) as cnt, MAX(timestamp) as latest FROM ml_feature_store GROUP BY pair ORDER BY cnt DESC");
    if ($r) { while ($row = $r->fetch_assoc()) { $pairs[] = $row; } }

    echo json_encode(array('ok' => true, 'tables' => $stats, 'feature_store_pairs' => $pairs));
}

// ═══════════════════════════════════════════════════════════════
//  POPULATE FEATURES: Compute 40+ features per pair
// ═══════════════════════════════════════════════════════════════
function _fsp_populate_features($conn) {
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

    $all_ohlcv = _fsp_fetch_ohlcv($pairs, 240);
    $engine_signals = _fsp_fetch_engine_signals();
    $ps_scores = array();
    $r = $conn->query("SELECT pair, hurst_exponent, autocorrelation_1, volatility_stability, signal_noise_ratio FROM ps_scores");
    if ($r) { while ($row = $r->fetch_assoc()) { $ps_scores[$row['pair']] = $row; } }

    $inserted = 0;
    $now = date('Y-m-d H:i:s');

    foreach ($pairs as $pair) {
        if (!isset($all_ohlcv[$pair])) continue;
        $candles = $all_ohlcv[$pair];
        $n = count($candles);
        if ($n < 55) continue;

        // Get closes, highs, lows, volumes
        $closes = array();
        $highs = array();
        $lows = array();
        $volumes = array();
        foreach ($candles as $c) {
            $closes[] = $c['close'];
            $highs[] = $c['high'];
            $lows[] = $c['low'];
            $volumes[] = $c['volume'];
        }

        $last = $n - 1;
        $close = $closes[$last];

        // ── Returns ──
        $ret1 = ($last >= 1 && $closes[$last - 1] > 0) ? (($close / $closes[$last - 1]) - 1) : 0;
        $ret5 = ($last >= 5 && $closes[$last - 5] > 0) ? (($close / $closes[$last - 5]) - 1) : 0;
        $ret20 = ($last >= 20 && $closes[$last - 20] > 0) ? (($close / $closes[$last - 20]) - 1) : 0;
        $log_ret = ($last >= 1 && $closes[$last - 1] > 0 && $close > 0) ? log($close / $closes[$last - 1]) : 0;

        // ── RSI 14 ──
        $rsi = _fsp_rsi($closes, 14);

        // ── MACD (12,26,9) ──
        $macd = _fsp_macd($closes);

        // ── Stochastic (14,3) ──
        $stoch = _fsp_stochastic($closes, $highs, $lows, 14, 3);

        // ── Williams %R ──
        $will_r = _fsp_williams_r($closes, $highs, $lows, 14);

        // ── CCI 20 ──
        $cci = _fsp_cci($closes, $highs, $lows, 20);

        // ── ROC 10 ──
        $roc = ($last >= 10 && $closes[$last - 10] > 0) ? (($close - $closes[$last - 10]) / $closes[$last - 10]) * 100 : 0;

        // ── SMAs ──
        $sma20 = _fsp_sma($closes, 20);
        $sma50 = _fsp_sma($closes, 50);

        // ── EMAs ──
        $ema9 = _fsp_ema($closes, 9);
        $ema21 = _fsp_ema($closes, 21);

        // ── ADX ──
        $adx_data = _fsp_adx($closes, $highs, $lows, 14);

        // ── Price vs SMA ──
        $p_sma20 = ($sma20 > 0) ? ($close - $sma20) / $sma20 : 0;
        $p_sma50 = ($sma50 > 0) ? ($close - $sma50) / $sma50 : 0;

        // ── ATR 14 ──
        $atr = _fsp_atr($closes, $highs, $lows, 14);

        // ── Bollinger Bands ──
        $bb = _fsp_bollinger($closes, 20, 2);

        // ── Realized Volatility ──
        $rv20 = _fsp_realized_vol($closes, 20);

        // ── Volume features ──
        $vol_sma20 = _fsp_sma($volumes, 20);
        $vol_ratio = ($vol_sma20 > 0) ? $volumes[$last] / $vol_sma20 : 0;
        $obv = _fsp_obv($closes, $volumes);

        // ── Predictability features ──
        $ps = isset($ps_scores[$pair]) ? $ps_scores[$pair] : array();
        $hurst = isset($ps['hurst_exponent']) ? (float)$ps['hurst_exponent'] : 0.5;
        $ac1 = isset($ps['autocorrelation_1']) ? (float)$ps['autocorrelation_1'] : 0;
        $vol_stab = isset($ps['volatility_stability']) ? (float)$ps['volatility_stability'] : 0;
        $snr = isset($ps['signal_noise_ratio']) ? (float)$ps['signal_noise_ratio'] : 0;

        // ── Engine consensus ──
        $eng = _fsp_count_engine_signals($pair, $engine_signals);

        // ── Insert ──
        $sql = sprintf(
            "INSERT INTO ml_feature_store (pair, asset_class, timestamp, timeframe,
             close_price, return_1, return_5, return_20, log_return,
             rsi_14, macd_value, macd_signal, macd_histogram, stoch_k, stoch_d, williams_r, cci_20, roc_10,
             sma_20, sma_50, ema_9, ema_21, adx_14, plus_di, minus_di, price_vs_sma20, price_vs_sma50,
             atr_14, bollinger_upper, bollinger_lower, bollinger_width, bollinger_pct_b, realized_vol_20,
             volume, volume_sma_20, volume_ratio, obv,
             hurst_exponent, autocorrelation_1, volatility_stability, signal_noise_ratio,
             engines_bullish, engines_bearish, engines_total, engine_agreement)
             VALUES ('%s','CRYPTO','%s','4H',
             %.8f,%.6f,%.6f,%.6f,%.6f,
             %.2f,%.6f,%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,
             %.8f,%.8f,%.8f,%.8f,%.2f,%.2f,%.2f,%.6f,%.6f,
             %.8f,%.8f,%.8f,%.6f,%.4f,%.6f,
             %.2f,%.2f,%.4f,%.2f,
             %.4f,%.4f,%.4f,%.4f,
             %d,%d,%d,%.4f)",
            $conn->real_escape_string($pair), $now,
            $close, $ret1, $ret5, $ret20, $log_ret,
            $rsi, $macd['value'], $macd['signal'], $macd['histogram'], $stoch['k'], $stoch['d'], $will_r, $cci, $roc,
            $sma20, $sma50, $ema9, $ema21, $adx_data['adx'], $adx_data['plus_di'], $adx_data['minus_di'], $p_sma20, $p_sma50,
            $atr, $bb['upper'], $bb['lower'], $bb['width'], $bb['pct_b'], $rv20,
            $volumes[$last], $vol_sma20, $vol_ratio, $obv,
            $hurst, $ac1, $vol_stab, $snr,
            $eng['bullish'], $eng['bearish'], $eng['total'], $eng['agreement']
        );

        if ($conn->query($sql)) $inserted++;
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array('ok' => true, 'features_inserted' => $inserted, 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════
//  POPULATE REGIME: Daily market regime snapshot
// ═══════════════════════════════════════════════════════════════
function _fsp_populate_regime($conn) {
    $today = date('Y-m-d');

    $r = $conn->query("SELECT hurst_exponent, hurst_regime, predictability_score FROM ps_scores");
    $trending = 0; $mean_rev = 0; $random_val = 0; $avg_hurst = 0; $count = 0;
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $count++;
            $avg_hurst += (float)$row['hurst_exponent'];
            if ($row['hurst_regime'] === 'TRENDING') $trending++;
            elseif ($row['hurst_regime'] === 'MEAN_REVERTING') $mean_rev++;
            else $random_val++;
        }
    }
    if ($count > 0) $avg_hurst = $avg_hurst / $count;

    // BTC trend
    $btc_trend = 'NEUTRAL';
    $r2 = $conn->query("SELECT return_1, price_vs_sma20 FROM ml_feature_store WHERE pair='XXBTZUSD' ORDER BY timestamp DESC LIMIT 1");
    if ($r2 && $r2->num_rows > 0) {
        $btc = $r2->fetch_assoc();
        if ((float)$btc['price_vs_sma20'] > 0.02) $btc_trend = 'BULLISH';
        elseif ((float)$btc['price_vs_sma20'] < -0.02) $btc_trend = 'BEARISH';
    }

    // Recommended strategy
    $rec = 'MULTI_INDICATOR';
    if ($trending > $random_val && $trending > $mean_rev) $rec = 'TREND_FOLLOWING';
    elseif ($mean_rev > $random_val) $rec = 'MEAN_REVERSION';

    $conn->query("DELETE FROM ml_regime_snapshots WHERE snapshot_date='" . $today . "' AND asset_class='CRYPTO'");
    $conn->query(sprintf(
        "INSERT INTO ml_regime_snapshots (snapshot_date, asset_class, btc_trend, avg_hurst,
         trending_pairs, mean_reverting_pairs, random_pairs, recommended_strategy,
         regime_confidence, created_at) VALUES ('%s','CRYPTO','%s',%.4f,%d,%d,%d,'%s',%.2f,'%s')",
        $today, $btc_trend, $avg_hurst,
        $trending, $mean_rev, $random_val, $rec,
        ($count > 0) ? (max($trending, $mean_rev, $random_val) / $count) : 0,
        date('Y-m-d H:i:s')
    ));

    echo json_encode(array(
        'ok' => true,
        'date' => $today,
        'btc_trend' => $btc_trend,
        'avg_hurst' => round($avg_hurst, 3),
        'trending' => $trending,
        'mean_reverting' => $mean_rev,
        'random' => $random_val,
        'recommended_strategy' => $rec
    ));
}

// ═══════════════════════════════════════════════════════════════
//  POPULATE DAILY: Platform-wide daily metrics
// ═══════════════════════════════════════════════════════════════
function _fsp_populate_daily($conn) {
    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    // Count signals generated today across both DBs
    $signals_crypto = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM ua_predictions WHERE DATE(collected_at)='" . $today . "'");
    if ($r) { $row = $r->fetch_assoc(); $signals_crypto = (int)$row['cnt']; }

    // Count from lm_signals
    $signals_stocks = 0; $signals_forex = 0;
    $r = $conn->query("SELECT asset_class, COUNT(*) as cnt FROM lm_signals WHERE DATE(signal_time)='" . $today . "' GROUP BY asset_class");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $ac = strtoupper($row['asset_class']);
            if ($ac === 'STOCKS' || $ac === 'STOCK') $signals_stocks = (int)$row['cnt'];
            elseif ($ac === 'FOREX') $signals_forex = (int)$row['cnt'];
            elseif ($ac === 'CRYPTO') $signals_crypto += (int)$row['cnt'];
        }
    }

    // Resolved today
    $resolved = 0; $wins = 0; $daily_pnl = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt, SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END) as w,
        SUM(pnl_pct) as pnl FROM ua_predictions WHERE status!='ACTIVE' AND DATE(resolved_at)='" . $today . "'");
    if ($r) {
        $row = $r->fetch_assoc();
        $resolved = (int)$row['cnt'];
        $wins = (int)$row['w'];
        $daily_pnl = (float)$row['pnl'];
    }

    // Cumulative P&L
    $cum_pnl = 0;
    $r = $conn->query("SELECT SUM(pnl_pct) as total FROM ua_predictions WHERE status!='ACTIVE'");
    if ($r) { $row = $r->fetch_assoc(); $cum_pnl = (float)$row['total']; }

    // Avg predictability
    $avg_pred = 0;
    $r = $conn->query("SELECT AVG(predictability_score) as avg_ps FROM ps_scores");
    if ($r) { $row = $r->fetch_assoc(); $avg_pred = round((float)$row['avg_ps'], 1); }

    // Active engines count
    $engines_active = 0;
    $r = $conn->query("SELECT COUNT(DISTINCT engine_name) as cnt FROM ua_predictions WHERE status='ACTIVE'");
    if ($r) { $row = $r->fetch_assoc(); $engines_active = (int)$row['cnt']; }

    $wr = ($resolved > 0) ? round($wins / $resolved * 100, 1) : 0;

    $conn->query("DELETE FROM ml_platform_daily WHERE metric_date='" . $today . "'");
    $conn->query(sprintf(
        "INSERT INTO ml_platform_daily (metric_date, total_signals_generated, signals_crypto, signals_stocks,
         signals_forex, resolved_today, wins_today, losses_today, daily_win_rate, daily_pnl, cumulative_pnl,
         avg_predictability, engines_active, engines_total, created_at)
         VALUES ('%s',%d,%d,%d,%d,%d,%d,%d,%.1f,%.2f,%.2f,%.1f,%d,13,'%s')",
        $today, $signals_crypto + $signals_stocks + $signals_forex,
        $signals_crypto, $signals_stocks, $signals_forex,
        $resolved, $wins, $resolved - $wins, $wr, $daily_pnl, $cum_pnl,
        $avg_pred, $engines_active, $now
    ));

    echo json_encode(array(
        'ok' => true,
        'date' => $today,
        'signals' => array('crypto' => $signals_crypto, 'stocks' => $signals_stocks, 'forex' => $signals_forex),
        'resolved_today' => $resolved,
        'win_rate' => $wr,
        'cumulative_pnl' => $cum_pnl
    ));
}

// ═══════════════════════════════════════════════════════════════
//  POPULATE LEARNING: Engine improvement tracking
// ═══════════════════════════════════════════════════════════════
function _fsp_populate_learning($conn) {
    $today = date('Y-m-d');
    $engines = array();

    $r = $conn->query("SELECT engine_name, COUNT(*) as total,
        SUM(CASE WHEN pnl_pct > 0 AND status != 'ACTIVE' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status != 'ACTIVE' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE 0 END) as total_pnl
        FROM ua_predictions GROUP BY engine_name");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $res = (int)$row['resolved'];
            $wr = ($res > 0) ? round((int)$row['wins'] / $res * 100, 1) : 0;
            $total_pnl = (float)$row['total_pnl'];
            $pf = 0;

            $conn->query(sprintf(
                "REPLACE INTO ml_learning_curve (engine_name, data_date, sample_count,
                 rolling_win_rate, rolling_profit_factor) VALUES ('%s','%s',%d,%.1f,%.2f)",
                $conn->real_escape_string($row['engine_name']), $today,
                (int)$row['total'], $wr, $pf
            ));
            $engines[] = array('engine' => $row['engine_name'], 'total' => (int)$row['total'], 'resolved' => $res, 'win_rate' => $wr);
        }
    }

    echo json_encode(array('ok' => true, 'engines_tracked' => count($engines), 'engines' => $engines));
}

// ═══════════════════════════════════════════════════════════════
//  INDICATOR CALCULATIONS (PHP 5.2 compatible)
// ═══════════════════════════════════════════════════════════════

function _fsp_sma($data, $period) {
    $n = count($data);
    if ($n < $period) return 0;
    $sum = 0;
    for ($i = $n - $period; $i < $n; $i++) $sum += $data[$i];
    return $sum / $period;
}

function _fsp_ema($data, $period) {
    $n = count($data);
    if ($n < $period) return 0;
    $k = 2.0 / ($period + 1);
    $ema = _fsp_sma(array_slice($data, 0, $period), $period);
    for ($i = $period; $i < $n; $i++) {
        $ema = $data[$i] * $k + $ema * (1 - $k);
    }
    return $ema;
}

function _fsp_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return 50;
    $gains = 0; $losses = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $chg = $closes[$i] - $closes[$i - 1];
        if ($chg > 0) $gains += $chg;
        else $losses += abs($chg);
    }
    $avg_gain = $gains / $period;
    $avg_loss = $losses / $period;
    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _fsp_macd($closes) {
    $ema12 = _fsp_ema($closes, 12);
    $ema26 = _fsp_ema($closes, 26);
    $value = $ema12 - $ema26;

    // Signal line: EMA9 of MACD values (approximation using recent)
    $n = count($closes);
    $macd_series = array();
    $k12 = 2.0 / 13; $k26 = 2.0 / 27;
    $e12 = _fsp_sma(array_slice($closes, 0, 12), 12);
    $e26 = _fsp_sma(array_slice($closes, 0, 26), 26);
    for ($i = 26; $i < $n; $i++) {
        $e12 = $closes[$i] * $k12 + $e12 * (1 - $k12);
        $e26 = $closes[$i] * $k26 + $e26 * (1 - $k26);
        $macd_series[] = $e12 - $e26;
    }
    $signal = (count($macd_series) >= 9) ? _fsp_ema($macd_series, 9) : $value;
    return array('value' => $value, 'signal' => $signal, 'histogram' => $value - $signal);
}

function _fsp_stochastic($closes, $highs, $lows, $period, $smooth) {
    $n = count($closes);
    if ($n < $period) return array('k' => 50, 'd' => 50);
    $hh = $lows[$n - 1]; $ll = $lows[$n - 1];
    for ($i = $n - $period; $i < $n; $i++) {
        if ($highs[$i] > $hh) $hh = $highs[$i];
        if ($lows[$i] < $ll) $ll = $lows[$i];
    }
    $k = ($hh != $ll) ? (($closes[$n - 1] - $ll) / ($hh - $ll)) * 100 : 50;
    return array('k' => $k, 'd' => $k); // simplified D
}

function _fsp_williams_r($closes, $highs, $lows, $period) {
    $n = count($closes);
    if ($n < $period) return -50;
    $hh = $highs[$n - $period]; $ll = $lows[$n - $period];
    for ($i = $n - $period; $i < $n; $i++) {
        if ($highs[$i] > $hh) $hh = $highs[$i];
        if ($lows[$i] < $ll) $ll = $lows[$i];
    }
    return ($hh != $ll) ? (($hh - $closes[$n - 1]) / ($hh - $ll)) * -100 : -50;
}

function _fsp_cci($closes, $highs, $lows, $period) {
    $n = count($closes);
    if ($n < $period) return 0;
    $tps = array();
    for ($i = $n - $period; $i < $n; $i++) {
        $tps[] = ($highs[$i] + $lows[$i] + $closes[$i]) / 3;
    }
    $mean = array_sum($tps) / $period;
    $md = 0;
    foreach ($tps as $tp) $md += abs($tp - $mean);
    $md = $md / $period;
    return ($md != 0) ? ($tps[$period - 1] - $mean) / (0.015 * $md) : 0;
}

function _fsp_atr($closes, $highs, $lows, $period) {
    $n = count($closes);
    if ($n < $period + 1) return 0;
    $trs = array();
    for ($i = $n - $period; $i < $n; $i++) {
        $tr = max($highs[$i] - $lows[$i], abs($highs[$i] - $closes[$i - 1]), abs($lows[$i] - $closes[$i - 1]));
        $trs[] = $tr;
    }
    return array_sum($trs) / count($trs);
}

function _fsp_bollinger($closes, $period, $mult) {
    $n = count($closes);
    if ($n < $period) return array('upper' => 0, 'lower' => 0, 'width' => 0, 'pct_b' => 0.5);
    $sma = _fsp_sma($closes, $period);
    $sumsq = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $sumsq += ($closes[$i] - $sma) * ($closes[$i] - $sma);
    }
    $std = sqrt($sumsq / $period);
    $upper = $sma + $mult * $std;
    $lower = $sma - $mult * $std;
    $width = ($sma > 0) ? ($upper - $lower) / $sma : 0;
    $pct_b = ($upper != $lower) ? ($closes[$n - 1] - $lower) / ($upper - $lower) : 0.5;
    return array('upper' => $upper, 'lower' => $lower, 'width' => $width, 'pct_b' => $pct_b);
}

function _fsp_adx($closes, $highs, $lows, $period) {
    $n = count($closes);
    if ($n < $period + 1) return array('adx' => 0, 'plus_di' => 0, 'minus_di' => 0);
    $plus_dm_sum = 0; $minus_dm_sum = 0; $tr_sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $up = $highs[$i] - $highs[$i - 1];
        $dn = $lows[$i - 1] - $lows[$i];
        $plus_dm_sum += ($up > $dn && $up > 0) ? $up : 0;
        $minus_dm_sum += ($dn > $up && $dn > 0) ? $dn : 0;
        $tr_sum += max($highs[$i] - $lows[$i], abs($highs[$i] - $closes[$i - 1]), abs($lows[$i] - $closes[$i - 1]));
    }
    $plus_di = ($tr_sum > 0) ? ($plus_dm_sum / $tr_sum) * 100 : 0;
    $minus_di = ($tr_sum > 0) ? ($minus_dm_sum / $tr_sum) * 100 : 0;
    $di_sum = $plus_di + $minus_di;
    $dx = ($di_sum > 0) ? abs($plus_di - $minus_di) / $di_sum * 100 : 0;
    return array('adx' => $dx, 'plus_di' => $plus_di, 'minus_di' => $minus_di);
}

function _fsp_realized_vol($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return 0;
    $returns = array();
    for ($i = $n - $period; $i < $n; $i++) {
        if ($closes[$i - 1] > 0 && $closes[$i] > 0) {
            $returns[] = log($closes[$i] / $closes[$i - 1]);
        }
    }
    if (count($returns) < 2) return 0;
    $mean = array_sum($returns) / count($returns);
    $sumsq = 0;
    foreach ($returns as $r) $sumsq += ($r - $mean) * ($r - $mean);
    return sqrt($sumsq / count($returns));
}

function _fsp_obv($closes, $volumes) {
    $n = count($closes);
    $obv = 0;
    for ($i = 1; $i < $n; $i++) {
        if ($closes[$i] > $closes[$i - 1]) $obv += $volumes[$i];
        elseif ($closes[$i] < $closes[$i - 1]) $obv -= $volumes[$i];
    }
    return $obv;
}

// ═══ Data fetching ═══

function _fsp_fetch_ohlcv($pairs, $interval) {
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
                                'time' => (float)$c[0], 'open' => (float)$c[1],
                                'high' => (float)$c[2], 'low' => (float)$c[3],
                                'close' => (float)$c[4], 'volume' => (float)$c[6]
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

function _fsp_fetch_engine_signals() {
    $all = array();
    $urls = array(
        'hybrid' => 'https://findtorontoevents.ca/findcryptopairs/api/hybrid_engine.php?action=signals',
        'tv_tech' => 'https://findtorontoevents.ca/findcryptopairs/api/tv_technicals.php?action=signals'
    );
    foreach ($urls as $name => $url) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 8);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp) {
            $data = json_decode($resp, true);
            if (is_array($data)) {
                $sigs = isset($data['active']) ? $data['active'] : (isset($data['signals']) ? $data['signals'] : array());
                $all[$name] = is_array($sigs) ? $sigs : array();
            }
        }
    }
    return $all;
}

function _fsp_count_engine_signals($pair, $all_signals) {
    $bull = 0; $bear = 0; $total = 0;
    foreach ($all_signals as $eng => $sigs) {
        foreach ($sigs as $s) {
            $sp = isset($s['pair']) ? strtoupper($s['pair']) : '';
            if ($sp !== strtoupper($pair)) continue;
            $total++;
            $d = isset($s['direction']) ? strtoupper($s['direction']) : '';
            if ($d === 'LONG' || $d === 'BUY') $bull++;
            elseif ($d === 'SHORT' || $d === 'SELL') $bear++;
        }
    }
    $agr = ($total > 0) ? max($bull, $bear) / $total : 0;
    return array('bullish' => $bull, 'bearish' => $bear, 'total' => $total, 'agreement' => $agr);
}
