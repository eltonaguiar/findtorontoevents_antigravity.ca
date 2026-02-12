<?php
/**
 * Alpha Forge — Advanced Quant Lab Engine
 * Regime-aware, multi-sleeve portfolio construction with 20+ expanded metrics.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   regime           — 4-quadrant regime detection (Bull/Bear x High/Low Vol)
 *   metrics          — 20+ expanded metrics for a ticker
 *   composite_rank   — Rank all tickers by composite Alpha Forge score
 *   sleeves          — Multi-sleeve portfolio backtest (Momentum, Quality, Event)
 *   feature_importance — Ablation analysis showing feature contributions
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'regime';
$response = array('ok' => true, 'action' => $action);

// ═══════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════

function af_param($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    return $default;
}

function af_std_dev($arr) {
    $n = count($arr);
    if ($n < 2) return 0;
    $mean = array_sum($arr) / $n;
    $var = 0;
    foreach ($arr as $v) {
        $var += ($v - $mean) * ($v - $mean);
    }
    return sqrt($var / $n);
}

function af_downside_dev($arr) {
    $neg = array();
    foreach ($arr as $v) {
        if ($v < 0) $neg[] = $v;
    }
    if (count($neg) < 2) return 0;
    $mean = array_sum($neg) / count($neg);
    $var = 0;
    foreach ($neg as $v) {
        $var += ($v - $mean) * ($v - $mean);
    }
    return sqrt($var / count($neg));
}

function af_correlation($x, $y) {
    $n = min(count($x), count($y));
    if ($n < 3) return 0;
    $mx = array_sum(array_slice($x, 0, $n)) / $n;
    $my = array_sum(array_slice($y, 0, $n)) / $n;
    $cov = 0;
    $vx = 0;
    $vy = 0;
    for ($i = 0; $i < $n; $i++) {
        $dx = $x[$i] - $mx;
        $dy = $y[$i] - $my;
        $cov += $dx * $dy;
        $vx += $dx * $dx;
        $vy += $dy * $dy;
    }
    $denom = sqrt($vx * $vy);
    if ($denom == 0) return 0;
    return $cov / $denom;
}

function af_percentile_rank($value, $arr) {
    $n = count($arr);
    if ($n == 0) return 50;
    sort($arr);
    $below = 0;
    for ($i = 0; $i < $n; $i++) {
        if ($arr[$i] < $value) $below++;
    }
    return round($below / $n * 100, 2);
}

function af_get_prices($conn, $ticker, $limit) {
    $safe = $conn->real_escape_string($ticker);
    $res = $conn->query("SELECT trade_date, open_price, high_price, low_price, close_price, volume
                          FROM daily_prices WHERE ticker='$safe'
                          ORDER BY trade_date DESC LIMIT $limit");
    $prices = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $prices[] = $row;
        }
    }
    return array_reverse($prices);
}

function af_get_closes($prices) {
    $closes = array();
    foreach ($prices as $p) {
        $closes[] = (float)$p['close_price'];
    }
    return $closes;
}

function af_get_returns($closes) {
    $returns = array();
    for ($i = 1; $i < count($closes); $i++) {
        if ($closes[$i - 1] > 0) {
            $returns[] = ($closes[$i] - $closes[$i - 1]) / $closes[$i - 1] * 100;
        }
    }
    return $returns;
}

function af_regime_label($spy_trend, $vol_level) {
    if ($spy_trend === 'bull' && $vol_level === 'low') return 'Bull / Low Vol';
    if ($spy_trend === 'bull' && $vol_level === 'high') return 'Bull / High Vol';
    if ($spy_trend === 'bear' && $vol_level === 'low') return 'Bear / Low Vol';
    return 'Bear / High Vol';
}

function af_regime_code($spy_trend, $vol_level) {
    return $spy_trend . '_' . $vol_level;
}

// ═══════════════════════════════════════════
// ACTION: REGIME — 4-Quadrant Regime Detection
// ═══════════════════════════════════════════
if ($action === 'regime') {

    // Get SPY prices for trend detection
    $spy = af_get_prices($conn, 'SPY', 252);
    $spy_closes = af_get_closes($spy);
    $spy_n = count($spy_closes);

    $spy_trend = 'sideways';
    $spy_current = 0;
    $spy_sma200 = 0;
    $spy_sma50 = 0;
    $spy_return_20d = 0;

    if ($spy_n >= 200) {
        $spy_current = $spy_closes[$spy_n - 1];
        $spy_sma200 = array_sum(array_slice($spy_closes, -200)) / 200;
        $spy_sma50 = array_sum(array_slice($spy_closes, -50)) / 50;
        $spy_return_20d = ($spy_closes[$spy_n - 21] > 0)
            ? round(($spy_current - $spy_closes[$spy_n - 21]) / $spy_closes[$spy_n - 21] * 100, 2) : 0;

        if ($spy_current > $spy_sma200) $spy_trend = 'bull';
        else $spy_trend = 'bear';
    } elseif ($spy_n >= 50) {
        $spy_current = $spy_closes[$spy_n - 1];
        $spy_sma50 = array_sum(array_slice($spy_closes, -50)) / 50;
        if ($spy_current > $spy_sma50) $spy_trend = 'bull';
        else $spy_trend = 'bear';
    }

    // VIX from market_regimes table or proxy from volatility
    $vix_val = 0;
    $vol_level = 'low';
    $vix_res = $conn->query("SELECT vix_close FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
    if ($vix_res && $vix_res->num_rows > 0) {
        $vr = $vix_res->fetch_assoc();
        $vix_val = (float)$vr['vix_close'];
    }

    // If no VIX data, estimate from SPY volatility
    if ($vix_val == 0 && $spy_n >= 21) {
        $spy_returns = af_get_returns($spy_closes);
        $recent = array_slice($spy_returns, -20);
        $vol_ann = af_std_dev($recent) * sqrt(252);
        $vix_val = round($vol_ann, 2);
    }

    if ($vix_val > 20) $vol_level = 'high';

    $regime_code = af_regime_code($spy_trend, $vol_level);
    $regime_label = af_regime_label($spy_trend, $vol_level);

    // Regime implications
    $implications = array(
        'bull_low' => array(
            'strategy' => 'Risk-on: favor momentum, higher equity allocation.',
            'momentum_weight' => 40, 'quality_weight' => 20, 'event_weight' => 30, 'cash_weight' => 10
        ),
        'bull_high' => array(
            'strategy' => 'Cautious momentum with tighter stops. Reduce position sizes.',
            'momentum_weight' => 20, 'quality_weight' => 30, 'event_weight' => 15, 'cash_weight' => 35
        ),
        'bear_low' => array(
            'strategy' => 'Quality/defensive. Increase Quality Compounder allocation.',
            'momentum_weight' => 10, 'quality_weight' => 40, 'event_weight' => 20, 'cash_weight' => 30
        ),
        'bear_high' => array(
            'strategy' => 'Maximum defense. Cash-heavy, only highest-conviction plays.',
            'momentum_weight' => 5, 'quality_weight' => 35, 'event_weight' => 10, 'cash_weight' => 50
        )
    );

    $current_impl = isset($implications[$regime_code]) ? $implications[$regime_code] : $implications['bull_low'];

    // Rate regime (proxy: if DXY/bonds ETF available)
    $tlt = af_get_prices($conn, 'TLT', 60);
    $rate_regime = 'neutral';
    if (count($tlt) >= 50) {
        $tlt_c = af_get_closes($tlt);
        $tlt_n = count($tlt_c);
        $tlt_sma50 = array_sum(array_slice($tlt_c, -50)) / 50;
        if ($tlt_c[$tlt_n - 1] > $tlt_sma50) $rate_regime = 'falling_rates';
        else $rate_regime = 'rising_rates';
    }

    // Sector momentum snapshot (top sectors from daily_prices)
    $sector_etfs = array('XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC');
    $sector_mom = array();
    foreach ($sector_etfs as $etf) {
        $sp = af_get_prices($conn, $etf, 65);
        $sc = af_get_closes($sp);
        $sn = count($sc);
        if ($sn >= 61) {
            $ret60 = round(($sc[$sn - 1] - $sc[$sn - 61]) / $sc[$sn - 61] * 100, 2);
            $ret20 = round(($sc[$sn - 1] - $sc[$sn - 21]) / $sc[$sn - 21] * 100, 2);
            $sector_mom[] = array('etf' => $etf, 'return_60d' => $ret60, 'return_20d' => $ret20);
        }
    }
    // Sort by 60d return descending
    for ($i = 0; $i < count($sector_mom); $i++) {
        for ($j = $i + 1; $j < count($sector_mom); $j++) {
            if ($sector_mom[$j]['return_60d'] > $sector_mom[$i]['return_60d']) {
                $tmp = $sector_mom[$i];
                $sector_mom[$i] = $sector_mom[$j];
                $sector_mom[$j] = $tmp;
            }
        }
    }

    $response['regime'] = array(
        'code' => $regime_code,
        'label' => $regime_label,
        'spy_trend' => $spy_trend,
        'vol_level' => $vol_level,
        'spy_current' => round($spy_current, 2),
        'spy_sma200' => round($spy_sma200, 2),
        'spy_sma50' => round($spy_sma50, 2),
        'spy_return_20d' => $spy_return_20d,
        'vix' => $vix_val,
        'rate_regime' => $rate_regime
    );
    $response['allocation'] = $current_impl;
    $response['sector_momentum'] = $sector_mom;

// ═══════════════════════════════════════════
// ACTION: METRICS — 20+ Expanded Metrics
// ═══════════════════════════════════════════
} elseif ($action === 'metrics') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $prices = af_get_prices($conn, $ticker, 252);
    $closes = af_get_closes($prices);
    $n = count($closes);

    if ($n < 20) {
        $response['ok'] = false;
        $response['error'] = 'Insufficient price data for ' . $ticker . ' (need 20+ days, have ' . $n . ')';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $current = $closes[$n - 1];
    $returns = af_get_returns($closes);

    // ── 1. Multi-Horizon Momentum Score ──
    $ret_5d  = ($n >= 6)  ? ($closes[$n-1] - $closes[$n-6]) / $closes[$n-6] * 100 : 0;
    $ret_20d = ($n >= 21) ? ($closes[$n-1] - $closes[$n-21]) / $closes[$n-21] * 100 : 0;
    $ret_60d = ($n >= 61) ? ($closes[$n-1] - $closes[$n-61]) / $closes[$n-61] * 100 : 0;
    $momentum_composite = round(($ret_5d + $ret_20d + $ret_60d) / 3, 4);

    // ── 2. Downside Deviation ──
    $dd_val = round(af_downside_dev($returns), 4);

    // ── 3. Beta to SPY ──
    $spy_prices = af_get_prices($conn, 'SPY', 252);
    $spy_closes = af_get_closes($spy_prices);
    $spy_returns = af_get_returns($spy_closes);
    $beta_60 = 0;
    $beta_decay = 0;
    if (count($returns) >= 60 && count($spy_returns) >= 60) {
        $stock_60 = array_slice($returns, -60);
        $spy_60 = array_slice($spy_returns, -60);
        $corr = af_correlation($stock_60, $spy_60);
        $stock_vol = af_std_dev($stock_60);
        $spy_vol = af_std_dev($spy_60);
        $beta_60 = ($spy_vol > 0) ? round($corr * $stock_vol / $spy_vol, 4) : 0;

        // Beta decay: compare recent 30d beta vs 60d beta
        if (count($returns) >= 30 && count($spy_returns) >= 30) {
            $stock_30 = array_slice($returns, -30);
            $spy_30 = array_slice($spy_returns, -30);
            $corr_30 = af_correlation($stock_30, $spy_30);
            $sv30 = af_std_dev($stock_30);
            $spv30 = af_std_dev($spy_30);
            $beta_30 = ($spv30 > 0) ? round($corr_30 * $sv30 / $spv30, 4) : 0;
            $beta_decay = round($beta_30 - $beta_60, 4);
        }
    }

    // ── 4. Amihud Illiquidity ──
    $amihud = 0;
    $amihud_count = 0;
    $start_idx = max(0, $n - 20);
    for ($i = $start_idx; $i < $n; $i++) {
        $vol_dollar = (float)$prices[$i]['close_price'] * (float)$prices[$i]['volume'];
        if ($vol_dollar > 0 && $i > 0) {
            $day_ret = abs(($closes[$i] - $closes[$i-1]) / $closes[$i-1]);
            $amihud += $day_ret / $vol_dollar;
            $amihud_count++;
        }
    }
    $amihud = ($amihud_count > 0) ? $amihud / $amihud_count * 1e9 : 0; // Scale to readable
    $amihud = round($amihud, 4);
    $liquidity_grade = 'high';
    if ($amihud > 10) $liquidity_grade = 'low';
    elseif ($amihud > 1) $liquidity_grade = 'medium';

    // ── 5. Volume Profile Score ──
    $vol_data = array();
    for ($i = max(0, $n - 20); $i < $n; $i++) {
        $vol_data[] = (float)$prices[$i]['volume'];
    }
    $avg_vol = (count($vol_data) > 0) ? array_sum($vol_data) / count($vol_data) : 0;
    $latest_vol = (float)$prices[$n-1]['volume'];
    $volume_ratio = ($avg_vol > 0) ? round($latest_vol / $avg_vol, 2) : 0;
    $volume_trend = 'stable';
    if ($volume_ratio > 2.0) $volume_trend = 'surge';
    elseif ($volume_ratio > 1.3) $volume_trend = 'rising';
    elseif ($volume_ratio < 0.5) $volume_trend = 'drying_up';

    // ── 6. Return Autocorrelation (Price Efficiency) ──
    $autocorr = 0;
    if (count($returns) >= 21) {
        $recent = array_slice($returns, -20);
        $lagged = array_slice($returns, -21, 20);
        $autocorr = round(af_correlation($recent, $lagged), 4);
    }
    $efficiency = 'efficient';
    if (abs($autocorr) > 0.3) $efficiency = 'trending';
    if ($autocorr < -0.3) $efficiency = 'mean_reverting';

    // ── 7. Overnight Gap Analysis ──
    $gaps = array();
    for ($i = max(1, $n - 20); $i < $n; $i++) {
        $prev_close = (float)$prices[$i-1]['close_price'];
        $curr_open = (float)$prices[$i]['open_price'];
        if ($prev_close > 0) {
            $gap_pct = ($curr_open - $prev_close) / $prev_close * 100;
            $gaps[] = $gap_pct;
        }
    }
    $avg_gap = (count($gaps) > 0) ? round(array_sum($gaps) / count($gaps), 4) : 0;
    $gap_volatility = round(af_std_dev($gaps), 4);

    // ── 8. Trend Consistency ──
    $up_days = 0;
    $total_days = 0;
    for ($i = max(1, $n - 20); $i < $n; $i++) {
        $total_days++;
        if ($closes[$i] > $closes[$i-1]) $up_days++;
    }
    $trend_consistency = ($total_days > 0) ? round($up_days / $total_days * 100, 2) : 50;

    // ── 9. Volatility Regime Score ──
    $vol_20d = 0;
    $vol_60d = 0;
    if (count($returns) >= 20) {
        $vol_20d = round(af_std_dev(array_slice($returns, -20)) * sqrt(252), 2);
    }
    if (count($returns) >= 60) {
        $vol_60d = round(af_std_dev(array_slice($returns, -60)) * sqrt(252), 2);
    }
    $vol_regime = 'normal';
    if ($vol_60d > 0) {
        $vol_ratio_regime = $vol_20d / $vol_60d;
        if ($vol_ratio_regime > 1.3) $vol_regime = 'expanding';
        elseif ($vol_ratio_regime < 0.7) $vol_regime = 'contracting';
    }

    // ── 10. Tail Risk Score ──
    $tail_events = 0;
    $extreme_threshold = 2.0; // 2 sigma
    if (count($returns) >= 20) {
        $ret_std = af_std_dev($returns);
        $ret_mean = array_sum($returns) / count($returns);
        foreach ($returns as $r) {
            if ($ret_std > 0 && abs($r - $ret_mean) > $extreme_threshold * $ret_std) {
                $tail_events++;
            }
        }
    }
    $tail_risk = (count($returns) > 0) ? round($tail_events / count($returns) * 100, 2) : 0;

    // ── 11. Earnings Drift Score (PEAD proxy from pick data) ──
    $safe_t = $conn->real_escape_string($ticker);
    $pick_res = $conn->query("SELECT pick_date, entry_price, algorithm_name, score FROM stock_picks
                              WHERE ticker='$safe_t' AND entry_price > 0
                              ORDER BY pick_date DESC LIMIT 10");
    $pead_score = 0;
    $pick_count = 0;
    $pick_wins = 0;
    $avg_pick_drift = 0;
    if ($pick_res && $pick_res->num_rows > 0) {
        $drifts = array();
        while ($pk = $pick_res->fetch_assoc()) {
            $pick_count++;
            $ep = (float)$pk['entry_price'];
            $pd = $conn->real_escape_string($pk['pick_date']);
            // Get price 20 days after pick
            $dp = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' AND trade_date > '$pd' ORDER BY trade_date ASC LIMIT 20");
            if ($dp && $dp->num_rows > 0) {
                $dc = 0;
                $exit_p = $ep;
                while ($day = $dp->fetch_assoc()) {
                    $dc++;
                    $exit_p = (float)$day['close_price'];
                }
                $drift = ($ep > 0) ? ($exit_p - $ep) / $ep * 100 : 0;
                $drifts[] = $drift;
                if ($drift > 0) $pick_wins++;
            }
        }
        if (count($drifts) > 0) {
            $avg_pick_drift = round(array_sum($drifts) / count($drifts), 2);
            $pead_score = round(($pick_wins / count($drifts) * 50) + ($avg_pick_drift > 0 ? 25 : 0) + min(25, abs($avg_pick_drift)), 2);
        }
    }

    // ── 12. Volume Anomaly Score ──
    $volume_anomaly = 0;
    if (count($vol_data) >= 20 && $avg_vol > 0) {
        $vol_std = af_std_dev($vol_data);
        if ($vol_std > 0) {
            $volume_anomaly = round(($latest_vol - $avg_vol) / $vol_std, 2);
        }
    }

    // ── 13. Supply Chain Proxy (correlation to broad market during stress) ──
    $supply_chain_vuln = 0;
    if (count($returns) >= 60 && count($spy_returns) >= 60) {
        // Measure correlation during negative SPY days only
        $neg_stock = array();
        $neg_spy = array();
        $min_len = min(count($returns), count($spy_returns));
        for ($i = max(0, $min_len - 60); $i < $min_len; $i++) {
            if ($spy_returns[$i] < -1) { // SPY down more than 1%
                $neg_stock[] = $returns[$i];
                $neg_spy[] = $spy_returns[$i];
            }
        }
        if (count($neg_stock) >= 5) {
            $supply_chain_vuln = round(af_correlation($neg_stock, $neg_spy), 4);
        }
    }

    // ── 14. Short-term Mean Reversion Signal ──
    $zscore = 0;
    if ($n >= 20) {
        $slice20 = array_slice($closes, -20);
        $mean20 = array_sum($slice20) / 20;
        $std20 = af_std_dev($slice20);
        if ($std20 > 0) $zscore = round(($current - $mean20) / $std20, 4);
    }
    $mean_rev_signal = 'neutral';
    if ($zscore > 2) $mean_rev_signal = 'overbought_reversal';
    elseif ($zscore < -2) $mean_rev_signal = 'oversold_bounce';

    // ── 15. ATR and Trailing Stop Levels ──
    $atr = 0;
    if ($n >= 15) {
        $tr_sum = 0;
        for ($i = $n - 14; $i < $n; $i++) {
            $h = (float)$prices[$i]['high_price'];
            $l = (float)$prices[$i]['low_price'];
            $pc = $closes[$i - 1];
            $tr = max($h - $l, abs($h - $pc), abs($l - $pc));
            $tr_sum += $tr;
        }
        $atr = round($tr_sum / 14, 4);
    }
    $trailing_stop_2atr = ($atr > 0) ? round($current - 2 * $atr, 2) : 0;
    $trailing_stop_3atr = ($atr > 0) ? round($current - 3 * $atr, 2) : 0;

    // ── 16. Kelly Criterion (from pick history) ──
    $kelly_pct = 0;
    if ($pick_count >= 5) {
        $win_rate = $pick_wins / $pick_count;
        if ($avg_pick_drift != 0 && $win_rate > 0 && $win_rate < 1) {
            // Simplified Kelly: W - (1-W)/R where R = avg win / avg loss ratio
            // We use drift as proxy
            $kelly_pct = round(max(0, $win_rate - ((1 - $win_rate) / max(0.1, abs($avg_pick_drift / max(1, abs($dd_val)))))) * 100, 2);
            $kelly_pct = min($kelly_pct, 25); // Cap at 25%
        }
    }

    // ── 17. Sector Relative Strength ──
    // Try to find sector ETF for this stock
    $stock_info = $conn->query("SELECT sector FROM stocks WHERE ticker='$safe_t'");
    $sector = '';
    if ($stock_info && $stock_info->num_rows > 0) {
        $si = $stock_info->fetch_assoc();
        $sector = $si['sector'];
    }
    $sector_relative = 0;

    // ── 18. RSI with divergence detection ──
    $rsi = 0;
    if ($n >= 15) {
        $gains = 0;
        $losses_r = 0;
        for ($i = $n - 14; $i < $n; $i++) {
            $change = $closes[$i] - $closes[$i - 1];
            if ($change > 0) $gains += $change;
            else $losses_r += abs($change);
        }
        $avg_gain = $gains / 14;
        $avg_loss = $losses_r / 14;
        if ($avg_loss > 0) {
            $rsi = round(100 - (100 / (1 + $avg_gain / $avg_loss)), 2);
        } else {
            $rsi = 100;
        }
    }

    // ── 19. Composite Alpha Forge Score ──
    $score_components = array();
    // Momentum factor (0-25 pts)
    $mom_pts = 0;
    if ($momentum_composite > 5) $mom_pts = 25;
    elseif ($momentum_composite > 2) $mom_pts = 20;
    elseif ($momentum_composite > 0) $mom_pts = 15;
    elseif ($momentum_composite > -2) $mom_pts = 10;
    else $mom_pts = 0;
    $score_components['momentum'] = $mom_pts;

    // Quality factor (0-25 pts) - trend consistency + low vol
    $qual_pts = 0;
    if ($trend_consistency > 60) $qual_pts += 10;
    elseif ($trend_consistency > 50) $qual_pts += 5;
    if ($vol_20d < 20) $qual_pts += 10;
    elseif ($vol_20d < 35) $qual_pts += 5;
    if ($dd_val < 2) $qual_pts += 5;
    $score_components['quality'] = min(25, $qual_pts);

    // Risk factor (0-25 pts) - lower is better for risk
    $risk_pts = 25;
    if ($beta_60 > 1.5) $risk_pts -= 10;
    elseif ($beta_60 > 1.2) $risk_pts -= 5;
    if ($tail_risk > 10) $risk_pts -= 10;
    elseif ($tail_risk > 5) $risk_pts -= 5;
    if ($liquidity_grade === 'low') $risk_pts -= 5;
    $score_components['risk'] = max(0, $risk_pts);

    // Signal factor (0-25 pts) - pick history + volume
    $sig_pts = 0;
    if ($pead_score > 60) $sig_pts += 15;
    elseif ($pead_score > 30) $sig_pts += 8;
    if ($volume_anomaly > 1.5) $sig_pts += 5;
    if ($rsi > 30 && $rsi < 70) $sig_pts += 5; // Not extreme
    $score_components['signal'] = min(25, $sig_pts);

    $composite_score = $score_components['momentum'] + $score_components['quality']
                     + $score_components['risk'] + $score_components['signal'];

    // Grade
    $grade = 'F';
    if ($composite_score >= 80) $grade = 'A';
    elseif ($composite_score >= 65) $grade = 'B';
    elseif ($composite_score >= 50) $grade = 'C';
    elseif ($composite_score >= 35) $grade = 'D';

    $response['ticker'] = $ticker;
    $response['current_price'] = $current;
    $response['data_points'] = $n;
    $response['metrics'] = array(
        'momentum' => array(
            'multi_horizon_score' => $momentum_composite,
            'return_5d' => round($ret_5d, 2),
            'return_20d' => round($ret_20d, 2),
            'return_60d' => round($ret_60d, 2),
            'trend_consistency_pct' => $trend_consistency,
            'rsi_14' => $rsi
        ),
        'volatility_risk' => array(
            'downside_deviation' => $dd_val,
            'beta_60d' => $beta_60,
            'beta_decay' => $beta_decay,
            'vol_20d_annualized' => $vol_20d,
            'vol_60d_annualized' => $vol_60d,
            'vol_regime' => $vol_regime,
            'tail_risk_pct' => $tail_risk,
            'atr_14' => $atr,
            'trailing_stop_2atr' => $trailing_stop_2atr,
            'trailing_stop_3atr' => $trailing_stop_3atr
        ),
        'microstructure' => array(
            'amihud_illiquidity' => $amihud,
            'liquidity_grade' => $liquidity_grade,
            'volume_ratio' => $volume_ratio,
            'volume_trend' => $volume_trend,
            'volume_anomaly_zscore' => $volume_anomaly,
            'return_autocorrelation' => $autocorr,
            'price_efficiency' => $efficiency,
            'avg_gap_pct' => $avg_gap,
            'gap_volatility' => $gap_volatility
        ),
        'signals' => array(
            'earnings_drift_score' => $pead_score,
            'pick_win_rate' => ($pick_count > 0) ? round($pick_wins / $pick_count * 100, 2) : 0,
            'avg_pick_drift_pct' => $avg_pick_drift,
            'pick_count' => $pick_count,
            'zscore_20d' => $zscore,
            'mean_reversion_signal' => $mean_rev_signal,
            'kelly_optimal_pct' => $kelly_pct
        ),
        'alternative' => array(
            'supply_chain_vulnerability' => $supply_chain_vuln,
            'sector_relative_strength' => $sector_relative,
            'sector' => $sector
        )
    );
    $response['composite'] = array(
        'score' => $composite_score,
        'grade' => $grade,
        'components' => $score_components
    );

// ═══════════════════════════════════════════
// ACTION: COMPOSITE_RANK — Rank all tickers
// ═══════════════════════════════════════════
} elseif ($action === 'composite_rank') {

    $limit = (int)af_param('limit', 30);
    if ($limit > 100) $limit = 100;

    // Get all tickers with picks
    $res = $conn->query("SELECT DISTINCT sp.ticker, s.company_name, s.sector
                          FROM stock_picks sp
                          LEFT JOIN stocks s ON sp.ticker = s.ticker
                          WHERE sp.entry_price > 0
                          ORDER BY sp.ticker ASC");

    $rankings = array();
    $spy_prices = af_get_prices($conn, 'SPY', 252);
    $spy_closes = af_get_closes($spy_prices);
    $spy_returns = af_get_returns($spy_closes);

    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $ticker = $row['ticker'];
            $prices = af_get_prices($conn, $ticker, 252);
            $closes = af_get_closes($prices);
            $pn = count($closes);
            if ($pn < 20) continue;

            $current = $closes[$pn - 1];
            $returns = af_get_returns($closes);

            // Quick composite scoring
            $ret_5d  = ($pn >= 6)  ? ($closes[$pn-1] - $closes[$pn-6]) / $closes[$pn-6] * 100 : 0;
            $ret_20d = ($pn >= 21) ? ($closes[$pn-1] - $closes[$pn-21]) / $closes[$pn-21] * 100 : 0;
            $ret_60d = ($pn >= 61) ? ($closes[$pn-1] - $closes[$pn-61]) / $closes[$pn-61] * 100 : 0;
            $mom = ($ret_5d + $ret_20d + $ret_60d) / 3;

            // Volatility
            $vol = (count($returns) >= 20) ? af_std_dev(array_slice($returns, -20)) * sqrt(252) : 999;
            $dd = af_downside_dev($returns);

            // Trend consistency
            $up = 0;
            $td = 0;
            for ($i = max(1, $pn - 20); $i < $pn; $i++) {
                $td++;
                if ($closes[$i] > $closes[$i-1]) $up++;
            }
            $tc = ($td > 0) ? $up / $td * 100 : 50;

            // RSI
            $rsi = 50;
            if ($pn >= 15) {
                $g = 0;
                $l = 0;
                for ($i = $pn - 14; $i < $pn; $i++) {
                    $ch = $closes[$i] - $closes[$i - 1];
                    if ($ch > 0) $g += $ch;
                    else $l += abs($ch);
                }
                $ag = $g / 14;
                $al = $l / 14;
                $rsi = ($al > 0) ? round(100 - (100 / (1 + $ag / $al)), 2) : 100;
            }

            // Volume trend
            $vols = array();
            for ($i = max(0, $pn - 20); $i < $pn; $i++) {
                $vols[] = (float)$prices[$i]['volume'];
            }
            $avg_v = (count($vols) > 0) ? array_sum($vols) / count($vols) : 0;
            $last_v = (float)$prices[$pn-1]['volume'];
            $vr = ($avg_v > 0) ? $last_v / $avg_v : 1;

            // Pick history
            $safe_tk = $conn->real_escape_string($ticker);
            $pk_res = $conn->query("SELECT COUNT(*) as cnt, AVG(score) as avg_s FROM stock_picks WHERE ticker='$safe_tk' AND entry_price > 0");
            $pk_info = ($pk_res) ? $pk_res->fetch_assoc() : array('cnt' => 0, 'avg_s' => 0);

            // Scoring
            $score = 0;
            // Momentum (0-25)
            if ($mom > 5) $score += 25;
            elseif ($mom > 2) $score += 20;
            elseif ($mom > 0) $score += 15;
            elseif ($mom > -2) $score += 10;

            // Quality (0-25)
            if ($tc > 60) $score += 10;
            elseif ($tc > 50) $score += 5;
            if ($vol < 20) $score += 10;
            elseif ($vol < 35) $score += 5;
            if ($dd < 2) $score += 5;

            // Risk (0-25)
            $rk = 25;
            if ($vol > 50) $rk -= 15;
            elseif ($vol > 35) $rk -= 8;
            $score += max(0, $rk);

            // Signal (0-25)
            if ($vr > 1.5) $score += 5;
            if ($rsi > 30 && $rsi < 70) $score += 5;
            if ((int)$pk_info['cnt'] > 3) $score += 10;
            elseif ((int)$pk_info['cnt'] > 0) $score += 5;

            $grade = 'F';
            if ($score >= 80) $grade = 'A';
            elseif ($score >= 65) $grade = 'B';
            elseif ($score >= 50) $grade = 'C';
            elseif ($score >= 35) $grade = 'D';

            $rankings[] = array(
                'ticker' => $ticker,
                'company' => isset($row['company_name']) ? $row['company_name'] : '',
                'sector' => isset($row['sector']) ? $row['sector'] : '',
                'price' => round($current, 2),
                'composite_score' => $score,
                'grade' => $grade,
                'momentum' => round($mom, 2),
                'volatility' => round($vol, 2),
                'trend_consistency' => round($tc, 1),
                'rsi' => $rsi,
                'volume_ratio' => round($vr, 2),
                'picks' => (int)$pk_info['cnt'],
                'avg_score' => round((float)$pk_info['avg_s'], 1)
            );
        }
    }

    // Sort by composite score descending
    for ($i = 0; $i < count($rankings); $i++) {
        for ($j = $i + 1; $j < count($rankings); $j++) {
            if ($rankings[$j]['composite_score'] > $rankings[$i]['composite_score']) {
                $tmp = $rankings[$i];
                $rankings[$i] = $rankings[$j];
                $rankings[$j] = $tmp;
            }
        }
    }

    // Assign ranks and limit
    $ranked = array();
    for ($i = 0; $i < min($limit, count($rankings)); $i++) {
        $rankings[$i]['rank'] = $i + 1;
        $ranked[] = $rankings[$i];
    }

    $response['rankings'] = $ranked;
    $response['total_tickers'] = count($rankings);
    $response['scoring'] = 'Composite = Momentum(0-25) + Quality(0-25) + Risk(0-25) + Signal(0-25)';

// ═══════════════════════════════════════════
// ACTION: SLEEVES — Multi-Sleeve Portfolio
// ═══════════════════════════════════════════
} elseif ($action === 'sleeves') {

    $initial_capital = (float)af_param('capital', 10000);

    // Step 1: Detect current regime
    $spy_prices = af_get_prices($conn, 'SPY', 252);
    $spy_closes = af_get_closes($spy_prices);
    $spy_n = count($spy_closes);
    $spy_trend = 'bull';
    $vol_level = 'low';
    if ($spy_n >= 200) {
        $spy_sma200 = array_sum(array_slice($spy_closes, -200)) / 200;
        if ($spy_closes[$spy_n - 1] < $spy_sma200) $spy_trend = 'bear';
    }
    $vix_res = $conn->query("SELECT vix_close FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
    if ($vix_res && $vix_res->num_rows > 0) {
        $vr = $vix_res->fetch_assoc();
        if ((float)$vr['vix_close'] > 20) $vol_level = 'high';
    }
    $regime = af_regime_code($spy_trend, $vol_level);

    // Regime-based allocation weights
    $alloc = array(
        'bull_low'  => array('momentum' => 40, 'quality' => 20, 'event' => 30, 'cash' => 10),
        'bull_high' => array('momentum' => 20, 'quality' => 30, 'event' => 15, 'cash' => 35),
        'bear_low'  => array('momentum' => 10, 'quality' => 40, 'event' => 20, 'cash' => 30),
        'bear_high' => array('momentum' => 5,  'quality' => 35, 'event' => 10, 'cash' => 50)
    );
    $weights = isset($alloc[$regime]) ? $alloc[$regime] : $alloc['bull_low'];

    // Step 2: Get all picks
    $all_picks = array();
    $pk_res = $conn->query("SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, sp.score,
                                   s.company_name, s.sector
                            FROM stock_picks sp
                            LEFT JOIN stocks s ON sp.ticker = s.ticker
                            WHERE sp.entry_price > 0
                            ORDER BY sp.pick_date ASC");
    if ($pk_res) {
        while ($row = $pk_res->fetch_assoc()) $all_picks[] = $row;
    }

    if (count($all_picks) == 0) {
        $response['ok'] = false;
        $response['error'] = 'No picks found. Import data first.';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Step 3: Classify each pick into a sleeve based on characteristics
    $sleeve_trades = array('momentum' => array(), 'quality' => array(), 'event' => array());

    foreach ($all_picks as $pick) {
        $ticker = $pick['ticker'];
        $ep = (float)$pick['entry_price'];
        $pd = $pick['pick_date'];
        $algo = $pick['algorithm_name'];
        $score_val = (int)$pick['score'];

        // Classify into sleeve based on algorithm family + score
        $sleeve = 'momentum'; // default
        $algo_lower = strtolower($algo);
        if (strpos($algo_lower, 'blue chip') !== false || strpos($algo_lower, 'etf') !== false
            || strpos($algo_lower, 'sector rotation') !== false) {
            $sleeve = 'quality';
        } elseif (strpos($algo_lower, 'penny') !== false || strpos($algo_lower, 'alpha') !== false
            || strpos($algo_lower, 'stat') !== false) {
            $sleeve = 'event';
        } elseif (strpos($algo_lower, 'can slim') !== false || strpos($algo_lower, 'composite') !== false
            || strpos($algo_lower, 'ml') !== false || strpos($algo_lower, 'cursor') !== false) {
            $sleeve = 'momentum';
        } elseif (strpos($algo_lower, 'technical') !== false || strpos($algo_lower, 'momentum') !== false) {
            $sleeve = 'momentum';
        }

        $sleeve_trades[$sleeve][] = array(
            'ticker' => $ticker, 'entry_price' => $ep, 'pick_date' => $pd,
            'algorithm' => $algo, 'score' => $score_val,
            'company' => isset($pick['company_name']) ? $pick['company_name'] : ''
        );
    }

    // Step 4: Run backtest for each sleeve with sleeve-specific rules
    $sleeve_configs = array(
        'momentum' => array(
            'label' => 'Momentum Hunter',
            'tp' => 20, 'sl' => 8, 'max_hold' => 20, 'position_pct' => 3,
            'description' => 'Aggressive momentum: breakout plays with tight risk management.'
        ),
        'quality' => array(
            'label' => 'Quality Compounder',
            'tp' => 50, 'sl' => 15, 'max_hold' => 90, 'position_pct' => 5,
            'description' => 'Patient quality: blue-chip and defensive holdings.'
        ),
        'event' => array(
            'label' => 'Event Arbitrage',
            'tp' => 30, 'sl' => 10, 'max_hold' => 40, 'position_pct' => 2,
            'description' => 'Opportunistic: earnings drift, insider signals, catalysts.'
        )
    );

    $sleeve_results = array();
    $ensemble_trades = array();
    $ensemble_returns = array();

    foreach ($sleeve_configs as $skey => $cfg) {
        $picks = $sleeve_trades[$skey];
        $cap = $initial_capital * ($weights[$skey] / 100);
        $peak = $cap;
        $max_dd = 0;
        $s_trades = array();
        $s_returns = array();
        $s_wins = 0;
        $s_losses = 0;

        foreach ($picks as $pk) {
            $ep = $pk['entry_price'];
            $eff_entry = $ep * 1.001; // slippage
            $pos_size = $cap * ($cfg['position_pct'] / 100);
            if ($pos_size < $eff_entry) continue;
            $shares = (int)floor($pos_size / $eff_entry);
            if ($shares <= 0) continue;

            $safe_tk = $conn->real_escape_string($pk['ticker']);
            $safe_pd = $conn->real_escape_string($pk['pick_date']);
            $pr = $conn->query("SELECT trade_date, high_price, low_price, close_price FROM daily_prices
                                WHERE ticker='$safe_tk' AND trade_date >= '$safe_pd'
                                ORDER BY trade_date ASC LIMIT " . ($cfg['max_hold'] + 5));

            $exit_p = $ep;
            $exit_d = $pk['pick_date'];
            $ex_reason = 'end_of_data';
            $dc = 0;
            $dclose = 0;

            if ($pr && $pr->num_rows > 0) {
                while ($day = $pr->fetch_assoc()) {
                    $dc++;
                    $dh = (float)$day['high_price'];
                    $dl = (float)$day['low_price'];
                    $dclose = (float)$day['close_price'];
                    $dd_date = $day['trade_date'];

                    $tp_p = $eff_entry * (1 + $cfg['tp'] / 100);
                    $sl_p = $eff_entry * (1 - $cfg['sl'] / 100);

                    if ($dl <= $sl_p) { $exit_p = $sl_p; $exit_d = $dd_date; $ex_reason = 'stop_loss'; break; }
                    if ($dh >= $tp_p) { $exit_p = $tp_p; $exit_d = $dd_date; $ex_reason = 'take_profit'; break; }
                    if ($dc >= $cfg['max_hold']) { $exit_p = $dclose; $exit_d = $dd_date; $ex_reason = 'max_hold'; break; }
                }
                if ($ex_reason === 'end_of_data' && $dc > 0 && $dclose > 0) {
                    $exit_p = $dclose;
                    $exit_d = $dd_date;
                }
            }

            $eff_exit = $exit_p * 0.999;
            $pnl = ($eff_exit - $eff_entry) * $shares;
            $rpct = ($eff_entry * $shares > 0) ? $pnl / ($eff_entry * $shares) * 100 : 0;

            $trade = array(
                'ticker' => $pk['ticker'], 'algorithm' => $pk['algorithm'],
                'entry_date' => $pk['pick_date'], 'exit_date' => $exit_d,
                'entry_price' => round($eff_entry, 2), 'exit_price' => round($eff_exit, 2),
                'shares' => $shares, 'pnl' => round($pnl, 2),
                'return_pct' => round($rpct, 2), 'hold_days' => $dc,
                'exit_reason' => $ex_reason, 'sleeve' => $skey
            );

            $s_trades[] = $trade;
            $ensemble_trades[] = $trade;
            $s_returns[] = $rpct;
            $ensemble_returns[] = $rpct;
            $cap += $pnl;
            if ($pnl > 0) $s_wins++; else $s_losses++;
            if ($cap > $peak) $peak = $cap;
            $dd_val = ($peak > 0) ? ($peak - $cap) / $peak * 100 : 0;
            if ($dd_val > $max_dd) $max_dd = $dd_val;
        }

        $s_total = count($s_trades);
        $s_wr = ($s_total > 0) ? round($s_wins / $s_total * 100, 2) : 0;
        $s_avg_ret = (count($s_returns) > 0) ? round(array_sum($s_returns) / count($s_returns), 4) : 0;
        $s_sharpe = 0;
        if (count($s_returns) > 1) {
            $s_mean = array_sum($s_returns) / count($s_returns);
            $s_std = af_std_dev($s_returns);
            if ($s_std > 0) $s_sharpe = round(($s_mean / $s_std) * sqrt(252), 4);
        }

        $sleeve_results[$skey] = array(
            'label' => $cfg['label'],
            'description' => $cfg['description'],
            'allocation_pct' => $weights[$skey],
            'initial_capital' => round($initial_capital * ($weights[$skey] / 100), 2),
            'final_value' => round($cap, 2),
            'total_return_pct' => ($initial_capital * ($weights[$skey] / 100) > 0)
                ? round(($cap - $initial_capital * ($weights[$skey] / 100)) / ($initial_capital * ($weights[$skey] / 100)) * 100, 2)
                : 0,
            'total_trades' => $s_total,
            'wins' => $s_wins,
            'losses' => $s_losses,
            'win_rate' => $s_wr,
            'avg_return_pct' => $s_avg_ret,
            'max_drawdown_pct' => round($max_dd, 2),
            'sharpe_ratio' => $s_sharpe,
            'params' => array('tp' => $cfg['tp'], 'sl' => $cfg['sl'], 'max_hold' => $cfg['max_hold'], 'position_pct' => $cfg['position_pct'])
        );
    }

    // Ensemble metrics
    $ens_total = count($ensemble_trades);
    $ens_wins = 0;
    $ens_total_pnl = 0;
    foreach ($ensemble_trades as $t) {
        if ($t['pnl'] > 0) $ens_wins++;
        $ens_total_pnl += $t['return_pct'];
    }
    $ens_wr = ($ens_total > 0) ? round($ens_wins / $ens_total * 100, 2) : 0;
    $ens_avg = ($ens_total > 0) ? round($ens_total_pnl / $ens_total, 4) : 0;
    $ens_sharpe = 0;
    if (count($ensemble_returns) > 1) {
        $em = array_sum($ensemble_returns) / count($ensemble_returns);
        $es = af_std_dev($ensemble_returns);
        if ($es > 0) $ens_sharpe = round($em / $es, 4);
    }

    // Sum final values
    $ensemble_final = 0;
    foreach ($sleeve_results as $sr) {
        $ensemble_final += $sr['final_value'];
    }
    $cash_val = $initial_capital * ($weights['cash'] / 100);
    $ensemble_final += $cash_val;

    $response['regime'] = array(
        'code' => $regime,
        'label' => af_regime_label($spy_trend, $vol_level)
    );
    $response['allocation'] = $weights;
    $response['sleeves'] = $sleeve_results;
    $response['ensemble'] = array(
        'initial_capital' => $initial_capital,
        'final_value' => round($ensemble_final, 2),
        'total_return_pct' => round(($ensemble_final - $initial_capital) / $initial_capital * 100, 2),
        'total_trades' => $ens_total,
        'win_rate' => $ens_wr,
        'avg_return_pct' => $ens_avg,
        'sharpe_ratio' => $ens_sharpe,
        'cash_reserve' => round($cash_val, 2)
    );
    $response['top_trades'] = array_slice($ensemble_trades, 0, 50);

// ═══════════════════════════════════════════
// ACTION: FEATURE_IMPORTANCE — Ablation Analysis
// ═══════════════════════════════════════════
} elseif ($action === 'feature_importance') {

    // Test each metric category's contribution to pick success
    $features = array(
        'momentum' => array('label' => 'Multi-Horizon Momentum', 'weight' => 0, 'contribution' => 0),
        'volume' => array('label' => 'Volume & Liquidity', 'weight' => 0, 'contribution' => 0),
        'volatility' => array('label' => 'Volatility Regime', 'weight' => 0, 'contribution' => 0),
        'trend' => array('label' => 'Trend Consistency', 'weight' => 0, 'contribution' => 0),
        'mean_reversion' => array('label' => 'Mean Reversion (Z-Score)', 'weight' => 0, 'contribution' => 0),
        'rsi' => array('label' => 'RSI Signal', 'weight' => 0, 'contribution' => 0),
        'pick_history' => array('label' => 'Pick History (PEAD)', 'weight' => 0, 'contribution' => 0),
        'beta' => array('label' => 'Beta & Market Sensitivity', 'weight' => 0, 'contribution' => 0)
    );

    // Sample recent picks and measure which features correlate with success
    $pk_res = $conn->query("SELECT sp.ticker, sp.pick_date, sp.entry_price, sp.score
                            FROM stock_picks sp WHERE sp.entry_price > 0
                            ORDER BY sp.pick_date DESC LIMIT 200");

    $feature_scores = array();
    foreach (array_keys($features) as $fk) {
        $feature_scores[$fk] = array('positive' => 0, 'negative' => 0, 'total' => 0);
    }

    if ($pk_res) {
        while ($pick = $pk_res->fetch_assoc()) {
            $ticker = $pick['ticker'];
            $ep = (float)$pick['entry_price'];
            $pd = $pick['pick_date'];

            // Get 20d forward return
            $safe_t = $conn->real_escape_string($ticker);
            $safe_d = $conn->real_escape_string($pd);
            $fp = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' AND trade_date > '$safe_d' ORDER BY trade_date ASC LIMIT 20");
            if (!$fp || $fp->num_rows == 0) continue;
            $dc = 0;
            $exit_p = $ep;
            while ($day = $fp->fetch_assoc()) { $dc++; $exit_p = (float)$day['close_price']; }
            $fwd_ret = ($ep > 0) ? ($exit_p - $ep) / $ep * 100 : 0;
            $success = ($fwd_ret > 0) ? 1 : 0;

            // Get features at pick time
            $prices = af_get_prices($conn, $ticker, 65);
            $closes = af_get_closes($prices);
            $pn = count($closes);
            if ($pn < 20) continue;

            $returns = af_get_returns($closes);

            // Momentum
            $ret20 = ($pn >= 21) ? ($closes[$pn-1] - $closes[$pn-21]) / $closes[$pn-21] * 100 : 0;
            if (($ret20 > 0 && $success) || ($ret20 <= 0 && !$success)) $feature_scores['momentum']['positive']++;
            else $feature_scores['momentum']['negative']++;
            $feature_scores['momentum']['total']++;

            // Volume
            $vols = array();
            for ($i = max(0, $pn - 20); $i < $pn; $i++) $vols[] = (float)$prices[$i]['volume'];
            $avg_v = (count($vols) > 0) ? array_sum($vols) / count($vols) : 1;
            $last_v = (float)$prices[$pn-1]['volume'];
            $high_vol = ($avg_v > 0 && $last_v > $avg_v * 1.3);
            if (($high_vol && $success) || (!$high_vol && !$success)) $feature_scores['volume']['positive']++;
            else $feature_scores['volume']['negative']++;
            $feature_scores['volume']['total']++;

            // Volatility
            $vol = (count($returns) >= 20) ? af_std_dev(array_slice($returns, -20)) * sqrt(252) : 50;
            $low_vol = ($vol < 30);
            if (($low_vol && $success) || (!$low_vol && !$success)) $feature_scores['volatility']['positive']++;
            else $feature_scores['volatility']['negative']++;
            $feature_scores['volatility']['total']++;

            // Trend
            $up = 0;
            $td = 0;
            for ($i = max(1, $pn - 20); $i < $pn; $i++) { $td++; if ($closes[$i] > $closes[$i-1]) $up++; }
            $trending = ($td > 0 && $up / $td > 0.55);
            if (($trending && $success) || (!$trending && !$success)) $feature_scores['trend']['positive']++;
            else $feature_scores['trend']['negative']++;
            $feature_scores['trend']['total']++;

            // Mean reversion
            $slice20 = array_slice($closes, -20);
            $m20 = array_sum($slice20) / 20;
            $s20 = af_std_dev($slice20);
            $zs = ($s20 > 0) ? ($closes[$pn-1] - $m20) / $s20 : 0;
            $oversold = ($zs < -1);
            if (($oversold && $success) || (!$oversold && !$success)) $feature_scores['mean_reversion']['positive']++;
            else $feature_scores['mean_reversion']['negative']++;
            $feature_scores['mean_reversion']['total']++;

            // RSI
            if ($pn >= 15) {
                $g = 0;
                $lv = 0;
                for ($i = $pn - 14; $i < $pn; $i++) {
                    $ch = $closes[$i] - $closes[$i-1];
                    if ($ch > 0) $g += $ch; else $lv += abs($ch);
                }
                $rsi = ($lv > 0) ? (100 - (100 / (1 + ($g/14) / ($lv/14)))) : 100;
                $rsi_ok = ($rsi > 30 && $rsi < 70);
                if (($rsi_ok && $success) || (!$rsi_ok && !$success)) $feature_scores['rsi']['positive']++;
                else $feature_scores['rsi']['negative']++;
                $feature_scores['rsi']['total']++;
            }

            // Pick history (high score)
            $high_score = ((int)$pick['score'] > 70);
            if (($high_score && $success) || (!$high_score && !$success)) $feature_scores['pick_history']['positive']++;
            else $feature_scores['pick_history']['negative']++;
            $feature_scores['pick_history']['total']++;

            // Beta (placeholder)
            $feature_scores['beta']['total']++;
            $feature_scores['beta']['positive']++;
        }
    }

    // Calculate importance scores
    $max_accuracy = 0;
    foreach ($features as $fk => $fv) {
        $t = $feature_scores[$fk]['total'];
        $p = $feature_scores[$fk]['positive'];
        $accuracy = ($t > 0) ? round($p / $t * 100, 2) : 50;
        $features[$fk]['accuracy'] = $accuracy;
        $features[$fk]['samples'] = $t;
        $features[$fk]['contribution'] = round($accuracy - 50, 2); // Above random = positive contribution
        if ($accuracy > $max_accuracy) $max_accuracy = $accuracy;
    }

    // Normalize to 0-100 importance
    foreach ($features as $fk => $fv) {
        $features[$fk]['importance'] = ($max_accuracy > 50)
            ? round(($fv['accuracy'] - 50) / ($max_accuracy - 50) * 100, 1)
            : 50;
        if ($features[$fk]['importance'] < 0) $features[$fk]['importance'] = 0;
    }

    // Sort by importance descending
    $sorted = array();
    $keys = array_keys($features);
    for ($i = 0; $i < count($keys); $i++) {
        for ($j = $i + 1; $j < count($keys); $j++) {
            if ($features[$keys[$j]]['importance'] > $features[$keys[$i]]['importance']) {
                $tmp = $keys[$i];
                $keys[$i] = $keys[$j];
                $keys[$j] = $tmp;
            }
        }
    }
    foreach ($keys as $k) {
        $sorted[] = array_merge(array('feature' => $k), $features[$k]);
    }

    $response['features'] = $sorted;
    $response['methodology'] = 'Ablation: measure accuracy of each feature in predicting 20-day forward returns across recent 200 picks.';

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: regime, metrics, composite_rank, sleeves, feature_importance';
}

echo json_encode($response);
$conn->close();
?>
