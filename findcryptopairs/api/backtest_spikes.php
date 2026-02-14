<?php
/**
 * SPIKE SIGNAL BACKTESTER v1.0 — Walk-Forward Historical Validation
 *
 * This is NOT a signal generator. This is a TRUTH ENGINE.
 * It walks through every day of available Kraken data and asks:
 *   "If I had entered when signal X fired, what would have happened?"
 *
 * NO look-ahead bias. At each bar t, only data [0..t] is used.
 * NO cherry-picking. Every signal fire is recorded and tracked.
 *
 * Tests: BTC (XXBTZUSD), ETH (XETHZUSD), AVAX (AVAXUSD)
 * Timeframe: Daily candles (1440 min) from Kraken OHLC API
 * Lookback: Maximum available (~720 candles = ~2 years per API call)
 *
 * For each of the 12 signals, and for every combination of 2-3 signals,
 * this engine records:
 *   - Every date the signal fired
 *   - The price at entry
 *   - The max gain in the next 7, 14, 30 days (upside capture)
 *   - The max drawdown in the next 7, 14, 30 days (risk)
 *   - The close-to-close return at +7d, +14d, +30d
 *   - Whether a +10% TP or -5% SL was hit first
 *
 * PHP 5.2 compatible. Real Kraken data only.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(300);

/* ============================================================
   KRAKEN DATA
   ============================================================ */
function _kraken_ohlc_all($pair) {
    /* Fetch as much daily data as possible from Kraken */
    /* First call: no since param = latest 720 candles */
    $all = array();

    /* Try to get older data first by going back ~4 years */
    $timestamps = array(
        time() - (1460 * 86400), /* ~4 years ago */
        time() - (730 * 86400),  /* ~2 years ago */
        0                         /* latest (no since) */
    );

    foreach ($timestamps as $since) {
        $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=1440';
        if ($since > 0) $url .= '&since=' . $since;
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
        $resp = curl_exec($ch);
        curl_close($ch);
        if (!$resp) continue;
        $j = json_decode($resp, true);
        if (!$j || !empty($j['error'])) continue;
        if (!isset($j['result'])) continue;
        $keys = array_keys($j['result']);
        foreach ($keys as $k) {
            if ($k !== 'last' && is_array($j['result'][$k])) {
                foreach ($j['result'][$k] as $candle) {
                    $ts = intval($candle[0]);
                    $all[$ts] = $candle; /* dedup by timestamp */
                }
            }
        }
        sleep(1); /* rate limit */
    }

    /* Sort by timestamp */
    ksort($all);
    return array_values($all);
}

/* ============================================================
   INDICATOR LIBRARY (identical to spike_detector.php)
   ============================================================ */
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
   SIGNAL EVALUATOR AT POINT t (using only data [0..t])
   Returns array of 12 booleans
   ============================================================ */
function _signals_at($t, $closes, $highs, $lows, $volumes, $opens) {
    $n = $t + 1; /* we can only see data [0..t] */
    if ($n < 210) return null; /* need 210 bars of history */

    $price = $closes[$t];
    $active = array();

    /* --- S1: Volume Climax >3x 20-day avg --- */
    $vol_sum = 0;
    for ($i = $t - 20; $i < $t; $i++) $vol_sum += $volumes[$i];
    $vol_avg = $vol_sum / 20;
    $vol_ratio = ($vol_avg > 0) ? $volumes[$t] / $vol_avg : 0;
    $active[1] = ($vol_ratio >= 3.0);

    /* --- S2: RSI(14) < 25 --- */
    /* Compute RSI on data up to t */
    $slice_c = array_slice($closes, 0, $n);
    $rsi_all = _rsi($slice_c, 14);
    $rsi_val = isset($rsi_all[$t]) ? $rsi_all[$t] : 50;
    $active[2] = ($rsi_val < 25);

    /* --- S3: Long Downside Wick >3:1 (strict — no relaxation) --- */
    $body = abs($closes[$t] - $opens[$t]);
    $lw = min($opens[$t], $closes[$t]) - $lows[$t];
    $wick_ratio = ($body > 0.0001) ? $lw / $body : 0;
    $active[3] = ($wick_ratio >= 3.0);

    /* --- S4: ATR Spike >2x 30-day avg ATR --- */
    $slice_h = array_slice($highs, 0, $n);
    $slice_l = array_slice($lows, 0, $n);
    $atr_all = _atr($slice_h, $slice_l, $slice_c, 14);
    $atr_now = isset($atr_all[$t]) ? $atr_all[$t] : 0;
    $atr_sum = 0; $atr_cnt = 0;
    for ($i = $t - 30; $i < $t; $i++) {
        if (isset($atr_all[$i])) { $atr_sum += $atr_all[$i]; $atr_cnt++; }
    }
    $atr_avg = ($atr_cnt > 0) ? $atr_sum / $atr_cnt : $atr_now;
    $atr_ratio = ($atr_avg > 0) ? $atr_now / $atr_avg : 1;
    $active[4] = ($atr_ratio >= 2.0);

    /* --- S5: 200MA Test & Hold (within 3%) --- */
    $sma200_all = _sma($slice_c, 200);
    $sma200 = isset($sma200_all[$t]) ? $sma200_all[$t] : 0;
    $dist_200 = ($sma200 > 0) ? abs($price - $sma200) / $sma200 : 1;
    $active[5] = ($dist_200 < 0.03);

    /* --- S6: Prior Zone Retest (within 5% of 60-90d range) --- */
    $zh = 0; $zl = 999999999;
    for ($i = $t - 90; $i < $t - 60; $i++) {
        if ($i >= 0) {
            if ($highs[$i] > $zh) $zh = $highs[$i];
            if ($lows[$i] < $zl) $zl = $lows[$i];
        }
    }
    $at_zone = ($zh > 0 && (abs($price - $zh) / $zh < 0.05 || abs($price - $zl) / $zl < 0.05));
    $active[6] = $at_zone;

    /* --- S7: Deep Discount from ATH > -30% --- */
    $ath = 0;
    for ($i = 0; $i <= $t; $i++) {
        if ($highs[$i] > $ath) $ath = $highs[$i];
    }
    $ath_dev = ($ath > 0) ? ($price - $ath) / $ath : 0;
    $active[7] = ($ath_dev < -0.30);

    /* --- S8: 200MA Reclaim (was below in last 10d, now above) --- */
    $was_below = false;
    for ($i = $t - 10; $i < $t; $i++) {
        if ($i >= 0 && isset($sma200_all[$i]) && $closes[$i] < $sma200_all[$i]) $was_below = true;
    }
    $active[8] = ($was_below && $sma200 > 0 && $price > $sma200);

    /* --- S9: Golden Cross (50MA crosses above 200MA) --- */
    $sma50_all = _sma($slice_c, 50);
    $sma50 = isset($sma50_all[$t]) ? $sma50_all[$t] : 0;
    $sma50_prev = isset($sma50_all[$t - 1]) ? $sma50_all[$t - 1] : 0;
    $sma200_prev = isset($sma200_all[$t - 1]) ? $sma200_all[$t - 1] : 0;
    /* Cross happened today OR in last 10 days */
    $golden = false;
    for ($i = max(0, $t - 10); $i <= $t; $i++) {
        if ($i > 0 && isset($sma50_all[$i]) && isset($sma50_all[$i - 1]) && isset($sma200_all[$i]) && isset($sma200_all[$i - 1])) {
            if ($sma50_all[$i - 1] < $sma200_all[$i - 1] && $sma50_all[$i] >= $sma200_all[$i]) $golden = true;
        }
    }
    $active[9] = $golden;

    /* --- S10: Higher Lows (2+ consecutive, 5-bar swing detection) --- */
    $swing_lows = array();
    for ($i = 5; $i < $n - 5; $i++) {
        $is_low = true;
        for ($j = $i - 5; $j <= min($i + 5, $t); $j++) {
            if ($j !== $i && $j >= 0 && $j <= $t && $lows[$j] < $lows[$i]) { $is_low = false; break; }
        }
        if ($is_low) $swing_lows[] = $lows[$i];
    }
    $rec = array_slice($swing_lows, -5);
    $hl_cnt = 0;
    for ($i = 1; $i < count($rec); $i++) {
        if ($rec[$i] > $rec[$i - 1]) $hl_cnt++;
    }
    $active[10] = ($hl_cnt >= 2);

    /* --- S11: Base Breakout on Volume --- */
    $rh = 0; $rl = 999999999;
    for ($i = $t - 20; $i < $t; $i++) {
        if ($i >= 0) {
            if ($highs[$i] > $rh) $rh = $highs[$i];
            if ($lows[$i] < $rl) $rl = $lows[$i];
        }
    }
    $breakout = ($price > $rh && $vol_avg > 0 && $volumes[$t] > $vol_avg * 1.5);
    $active[11] = $breakout;

    /* --- S12: RSI Bullish Divergence --- */
    $div = false;
    $price_lows = array();
    for ($i = max(0, $t - 30); $i <= $t; $i++) {
        if ($i >= 2 && $i < $t) {
            if ($lows[$i] < $lows[$i - 1] && $lows[$i] < $lows[$i + 1] && $lows[$i] < $lows[$i - 2]) {
                $r = isset($rsi_all[$i]) ? $rsi_all[$i] : 50;
                $price_lows[] = array('p' => $lows[$i], 'r' => $r);
            }
        }
    }
    if (count($price_lows) >= 2) {
        $last = $price_lows[count($price_lows) - 1];
        $prev = $price_lows[count($price_lows) - 2];
        if ($last['p'] < $prev['p'] && $last['r'] > $prev['r']) $div = true;
    }
    $active[12] = $div;

    return array(
        'signals' => $active,
        'count' => array_sum(array_map('intval', $active)),
        'rsi' => round($rsi_val, 1),
        'atr' => round($atr_now, 2),
        'vol_ratio' => round($vol_ratio, 2),
        'sma200' => round($sma200, 2),
        'sma50' => round($sma50, 2)
    );
}

/* ============================================================
   OUTCOME MEASUREMENT (what happened AFTER entry)
   ============================================================ */
function _measure_outcome($entry_idx, $closes, $highs, $lows, $max_bars) {
    $entry_price = $closes[$entry_idx];
    $total = count($closes);
    $remaining = $total - $entry_idx - 1;
    $horizon = min($max_bars, $remaining);

    if ($horizon < 7) return null; /* not enough future data */

    $max_gain_7 = -99999; $max_dd_7 = 0;
    $max_gain_14 = -99999; $max_dd_14 = 0;
    $max_gain_30 = -99999; $max_dd_30 = 0;
    $ret_7 = 0; $ret_14 = 0; $ret_30 = 0;

    /* TP/SL tracking: +10% TP, -5% SL, +20% big TP */
    $tp10_hit = -1; $sl5_hit = -1;
    $tp20_hit = -1; $sl10_hit = -1;

    for ($d = 1; $d <= $horizon; $d++) {
        $idx = $entry_idx + $d;
        $hi_pct = (($highs[$idx] - $entry_price) / $entry_price) * 100;
        $lo_pct = (($lows[$idx] - $entry_price) / $entry_price) * 100;
        $cl_pct = (($closes[$idx] - $entry_price) / $entry_price) * 100;

        if ($d <= 7) {
            if ($hi_pct > $max_gain_7) $max_gain_7 = $hi_pct;
            if ($lo_pct < $max_dd_7) $max_dd_7 = $lo_pct;
            $ret_7 = $cl_pct;
        }
        if ($d <= 14) {
            if ($hi_pct > $max_gain_14) $max_gain_14 = $hi_pct;
            if ($lo_pct < $max_dd_14) $max_dd_14 = $lo_pct;
            $ret_14 = $cl_pct;
        }
        if ($d <= 30) {
            if ($hi_pct > $max_gain_30) $max_gain_30 = $hi_pct;
            if ($lo_pct < $max_dd_30) $max_dd_30 = $lo_pct;
            $ret_30 = $cl_pct;
        }

        /* TP/SL first-hit tracking */
        if ($tp10_hit < 0 && $hi_pct >= 10) $tp10_hit = $d;
        if ($sl5_hit < 0 && $lo_pct <= -5) $sl5_hit = $d;
        if ($tp20_hit < 0 && $hi_pct >= 20) $tp20_hit = $d;
        if ($sl10_hit < 0 && $lo_pct <= -10) $sl10_hit = $d;
    }

    /* TP/SL outcome: which hit first? */
    $tp10_sl5 = 'NEITHER';
    if ($tp10_hit > 0 && $sl5_hit > 0) {
        $tp10_sl5 = ($tp10_hit <= $sl5_hit) ? 'TP_HIT' : 'SL_HIT';
    } elseif ($tp10_hit > 0) {
        $tp10_sl5 = 'TP_HIT';
    } elseif ($sl5_hit > 0) {
        $tp10_sl5 = 'SL_HIT';
    }

    $tp20_sl10 = 'NEITHER';
    if ($tp20_hit > 0 && $sl10_hit > 0) {
        $tp20_sl10 = ($tp20_hit <= $sl10_hit) ? 'TP_HIT' : 'SL_HIT';
    } elseif ($tp20_hit > 0) {
        $tp20_sl10 = 'TP_HIT';
    } elseif ($sl10_hit > 0) {
        $tp20_sl10 = 'SL_HIT';
    }

    return array(
        'ret_7d' => round($ret_7, 2),
        'ret_14d' => round($horizon >= 14 ? $ret_14 : $ret_7, 2),
        'ret_30d' => round($horizon >= 30 ? $ret_30 : $ret_14, 2),
        'max_gain_7d' => round($max_gain_7, 2),
        'max_gain_14d' => round($horizon >= 14 ? $max_gain_14 : $max_gain_7, 2),
        'max_gain_30d' => round($horizon >= 30 ? $max_gain_30 : $max_gain_14, 2),
        'max_dd_7d' => round($max_dd_7, 2),
        'max_dd_14d' => round($horizon >= 14 ? $max_dd_14 : $max_dd_7, 2),
        'max_dd_30d' => round($horizon >= 30 ? $max_dd_30 : $max_dd_14, 2),
        'tp10_sl5' => $tp10_sl5,
        'tp20_sl10' => $tp20_sl10,
        'bars_available' => $horizon
    );
}

/* ============================================================
   MAIN BACKTEST ENGINE
   ============================================================ */
function _run_backtest($pair, $asset_name) {
    $candles = _kraken_ohlc_all($pair);
    $n = count($candles);

    if ($n < 250) {
        return array('error' => 'Insufficient data for ' . $asset_name . ': only ' . $n . ' candles', 'candles' => $n);
    }

    /* Parse OHLCV */
    $timestamps = array(); $opens = array(); $highs = array();
    $lows = array(); $closes = array(); $volumes = array();
    foreach ($candles as $c) {
        $timestamps[] = intval($c[0]);
        $opens[] = floatval($c[1]);
        $highs[] = floatval($c[2]);
        $lows[] = floatval($c[3]);
        $closes[] = floatval($c[4]);
        $volumes[] = floatval($c[6]);
    }

    $signal_names = array(
        1 => 'Volume Climax (vol>3x 20d avg)',
        2 => 'RSI Extreme (<25 on daily)',
        3 => 'Long Downside Wick (>3:1 strict)',
        4 => 'ATR Spike (>2x 30d avg)',
        5 => '200MA Test & Hold (within 3%)',
        6 => 'Prior Zone Retest (5% of 60-90d)',
        7 => 'Deep ATH Discount (>30% below)',
        8 => '200MA Reclaim (cross above)',
        9 => 'Golden Cross (50>200)',
        10 => 'Higher Lows (2+ consec)',
        11 => 'Base Breakout on Volume',
        12 => 'RSI Bullish Divergence'
    );

    /* Per-signal stats */
    $sig_fires = array();
    $sig_outcomes = array();
    for ($s = 1; $s <= 12; $s++) {
        $sig_fires[$s] = array();
        $sig_outcomes[$s] = array();
    }

    /* Combo stats: 3+ signals and specific combos */
    $combo_fires = array();
    $combo_outcomes = array();

    /* Walk forward: start at bar 210 (need 200 bars history for 200MA + buffer) */
    $start = 210;
    $end = $n - 31; /* need at least 30 bars of future for outcome measurement */

    $last_fire = array(); /* debounce: don't count same signal on consecutive days */
    for ($s = 1; $s <= 12; $s++) $last_fire[$s] = -999;

    $walk_results = array(); /* every bar's signal state */

    for ($t = $start; $t <= $end; $t++) {
        $result = _signals_at($t, $closes, $highs, $lows, $volumes, $opens);
        if ($result === null) continue;

        $date_str = date('Y-m-d', $timestamps[$t]);
        $price = $closes[$t];

        /* Record which signals fired */
        $fired_ids = array();
        foreach ($result['signals'] as $sid => $is_active) {
            if ($is_active) $fired_ids[] = $sid;
        }

        /* Per-signal outcomes (debounce: skip if same signal fired in last 5 days) */
        foreach ($fired_ids as $sid) {
            if (($t - $last_fire[$sid]) < 5) continue; /* debounce */
            $last_fire[$sid] = $t;

            $outcome = _measure_outcome($t, $closes, $highs, $lows, 30);
            if ($outcome === null) continue;

            $sig_fires[$sid][] = array('date' => $date_str, 'price' => $price);
            $sig_outcomes[$sid][] = $outcome;
        }

        /* Combo: 3+ signals fire same day */
        if (count($fired_ids) >= 3) {
            $combo_key = implode('+', $fired_ids);

            /* Debounce combos too */
            if (!isset($combo_fires[$combo_key]) || ($t - end($combo_fires[$combo_key])['bar']) >= 10) {
                $outcome = _measure_outcome($t, $closes, $highs, $lows, 30);
                if ($outcome !== null) {
                    if (!isset($combo_fires[$combo_key])) {
                        $combo_fires[$combo_key] = array();
                        $combo_outcomes[$combo_key] = array();
                    }
                    $combo_fires[$combo_key][] = array('date' => $date_str, 'price' => $price, 'bar' => $t);
                    $combo_outcomes[$combo_key][] = $outcome;
                }
            }
        }
    }

    /* ============================================================
       AGGREGATE STATISTICS
       ============================================================ */
    $signal_stats = array();
    for ($s = 1; $s <= 12; $s++) {
        $fires = count($sig_fires[$s]);
        if ($fires === 0) {
            $signal_stats[$s] = array(
                'name' => $signal_names[$s],
                'fires' => 0,
                'verdict' => 'NEVER_FIRED'
            );
            continue;
        }

        $rets_7 = array(); $rets_14 = array(); $rets_30 = array();
        $gains_7 = array(); $gains_30 = array();
        $dds_7 = array(); $dds_30 = array();
        $tp10_wins = 0; $tp10_losses = 0; $tp10_neither = 0;
        $tp20_wins = 0; $tp20_losses = 0;

        foreach ($sig_outcomes[$s] as $o) {
            $rets_7[] = $o['ret_7d'];
            $rets_14[] = $o['ret_14d'];
            $rets_30[] = $o['ret_30d'];
            $gains_7[] = $o['max_gain_7d'];
            $gains_30[] = $o['max_gain_30d'];
            $dds_7[] = $o['max_dd_7d'];
            $dds_30[] = $o['max_dd_30d'];
            if ($o['tp10_sl5'] === 'TP_HIT') $tp10_wins++;
            elseif ($o['tp10_sl5'] === 'SL_HIT') $tp10_losses++;
            else $tp10_neither++;
            if ($o['tp20_sl10'] === 'TP_HIT') $tp20_wins++;
            elseif ($o['tp20_sl10'] === 'SL_HIT') $tp20_losses++;
        }

        $avg_ret7 = array_sum($rets_7) / $fires;
        $avg_ret14 = array_sum($rets_14) / $fires;
        $avg_ret30 = array_sum($rets_30) / $fires;

        /* Win rate: how often was 7d return > 0? */
        $wins_7 = 0;
        foreach ($rets_7 as $r) { if ($r > 0) $wins_7++; }
        $wins_30 = 0;
        foreach ($rets_30 as $r) { if ($r > 0) $wins_30++; }

        /* Standard deviation of 7d returns for Sharpe */
        $mean = $avg_ret7;
        $var = 0;
        foreach ($rets_7 as $r) { $var += ($r - $mean) * ($r - $mean); }
        $std = ($fires > 1) ? sqrt($var / ($fires - 1)) : 0;
        $sharpe = ($std > 0) ? ($mean / $std) * sqrt(52) : 0; /* annualized weekly Sharpe approx */

        $signal_stats[$s] = array(
            'name' => $signal_names[$s],
            'fires' => $fires,
            'fire_dates' => array_slice($sig_fires[$s], 0, 5), /* first 5 */
            'avg_ret_7d' => round($avg_ret7, 2),
            'avg_ret_14d' => round($avg_ret14, 2),
            'avg_ret_30d' => round($avg_ret30, 2),
            'win_rate_7d' => round($wins_7 / $fires * 100, 1),
            'win_rate_30d' => round($wins_30 / $fires * 100, 1),
            'avg_max_gain_7d' => round(array_sum($gains_7) / $fires, 2),
            'avg_max_gain_30d' => round(array_sum($gains_30) / $fires, 2),
            'avg_max_dd_7d' => round(array_sum($dds_7) / $fires, 2),
            'avg_max_dd_30d' => round(array_sum($dds_30) / $fires, 2),
            'worst_dd_30d' => round(min($dds_30), 2),
            'best_gain_30d' => round(max($gains_30), 2),
            'tp10_sl5_wr' => round(($tp10_wins + $tp10_losses > 0) ? $tp10_wins / ($tp10_wins + $tp10_losses) * 100 : 0, 1),
            'tp10_sl5_detail' => $tp10_wins . 'W/' . $tp10_losses . 'L/' . $tp10_neither . 'N',
            'tp20_sl10_wr' => round(($tp20_wins + $tp20_losses > 0) ? $tp20_wins / ($tp20_wins + $tp20_losses) * 100 : 0, 1),
            'sharpe_approx' => round($sharpe, 2),
            'verdict' => _verdict($avg_ret7, $avg_ret30, $wins_7 / $fires, $sharpe)
        );
    }

    /* Combo stats */
    $combo_stats = array();
    foreach ($combo_fires as $key => $fires_arr) {
        $cnt = count($fires_arr);
        if ($cnt < 2) continue; /* need at least 2 occurrences */

        $rets = array();
        $tp_w = 0; $tp_l = 0;
        foreach ($combo_outcomes[$key] as $o) {
            $rets[] = $o['ret_30d'];
            if ($o['tp10_sl5'] === 'TP_HIT') $tp_w++;
            elseif ($o['tp10_sl5'] === 'SL_HIT') $tp_l++;
        }
        $avg = array_sum($rets) / $cnt;
        $wins = 0;
        foreach ($rets as $r) { if ($r > 0) $wins++; }

        $ids = explode('+', $key);
        $names = array();
        foreach ($ids as $id) {
            $names[] = isset($signal_names[intval($id)]) ? $signal_names[intval($id)] : 'S' . $id;
        }

        $combo_stats[] = array(
            'signals' => $key,
            'signal_names' => $names,
            'fires' => $cnt,
            'avg_ret_30d' => round($avg, 2),
            'win_rate_30d' => round($wins / $cnt * 100, 1),
            'tp10_sl5_wr' => round(($tp_w + $tp_l > 0) ? $tp_w / ($tp_w + $tp_l) * 100 : 0, 1),
            'sample_dates' => array_slice(array_map(create_function('$f', 'return $f["date"];'), $fires_arr), 0, 5)
        );
    }

    /* Sort combos by win rate descending */
    usort($combo_stats, create_function('$a,$b', 'if ($a["win_rate_30d"] == $b["win_rate_30d"]) return 0; return ($a["win_rate_30d"] > $b["win_rate_30d"]) ? -1 : 1;'));

    /* Rank signals by predictive power */
    $ranked = $signal_stats;
    uasort($ranked, create_function('$a,$b', 'if (!isset($a["avg_ret_30d"]) || !isset($b["avg_ret_30d"])) return 0; return ($a["avg_ret_30d"] > $b["avg_ret_30d"]) ? -1 : 1;'));

    return array(
        'asset' => $asset_name,
        'pair' => $pair,
        'candles_total' => $n,
        'date_range' => date('Y-m-d', $timestamps[0]) . ' to ' . date('Y-m-d', $timestamps[$n - 1]),
        'bars_tested' => $end - $start + 1,
        'signal_stats' => $signal_stats,
        'signal_ranking' => array_keys($ranked),
        'combo_stats' => array_slice($combo_stats, 0, 20),
        'methodology' => array(
            'timeframe' => 'Daily (1440-min) candles from Kraken OHLC API',
            'walk_forward' => 'Start at bar 210, walk to bar N-31. At each bar, only data [0..t] visible.',
            'debounce' => 'Same signal not counted twice within 5 days. Combos debounced 10 days.',
            'outcome' => 'Return measured at +7d, +14d, +30d close. Max gain/drawdown from highs/lows.',
            'tp_sl' => 'Two systems tested: +10% TP / -5% SL, and +20% TP / -10% SL. First-hit wins.',
            'no_relaxation' => 'Signal 3 (Wicks) uses STRICT 3:1 threshold. No "last 3 days" relaxation.'
        )
    );
}

function _verdict($avg7, $avg30, $wr, $sharpe) {
    if ($avg30 > 5 && $wr > 0.55 && $sharpe > 0.5) return 'STRONG_PREDICTOR';
    if ($avg30 > 2 && $wr > 0.50) return 'WEAK_PREDICTOR';
    if ($avg30 < -2 && $wr < 0.45) return 'CONTRARIAN_SIGNAL';
    return 'NO_EDGE';
}

/* ============================================================
   API ROUTING
   ============================================================ */
$action = isset($_GET['action']) ? $_GET['action'] : 'status';
switch ($action) {
    case 'backtest':
        $asset = isset($_GET['asset']) ? strtoupper($_GET['asset']) : 'BTC';
        $pairs = array(
            'BTC' => 'XXBTZUSD',
            'ETH' => 'XETHZUSD',
            'AVAX' => 'AVAXUSD'
        );
        if (!isset($pairs[$asset])) {
            echo json_encode(array('ok' => false, 'error' => 'Unknown asset. Use BTC, ETH, or AVAX'));
            break;
        }
        $result = _run_backtest($pairs[$asset], $asset);
        echo json_encode(array('ok' => true, 'backtest' => $result));
        break;

    case 'backtest_all':
        $all = array();
        $pairs = array(
            'BTC' => 'XXBTZUSD',
            'ETH' => 'XETHZUSD',
            'AVAX' => 'AVAXUSD'
        );
        foreach ($pairs as $name => $pair) {
            $all[$name] = _run_backtest($pair, $name);
            sleep(2);
        }
        echo json_encode(array('ok' => true, 'backtests' => $all));
        break;

    case 'status':
        echo json_encode(array(
            'ok' => true,
            'engine' => 'Spike Signal Backtester v1.0',
            'purpose' => 'Walk-forward historical validation of 12 spike signals',
            'assets' => array('BTC', 'ETH', 'AVAX'),
            'timeframe' => 'Daily candles from Kraken',
            'signals_tested' => 12,
            'actions' => array(
                'backtest?asset=BTC' => 'Full backtest for single asset',
                'backtest_all' => 'Full backtest for BTC + ETH + AVAX (slow, ~60s)',
                'status' => 'This endpoint'
            )
        ));
        break;

    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action. Use: backtest, backtest_all, status'));
        break;
}
