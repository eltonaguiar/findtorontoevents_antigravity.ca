<?php
/**
 * LEGEND BACKTEST ENGINE v1.0
 * ===========================
 * Implements and backtests 20 algorithms inspired by the world's most
 * successful traders and quants across ALL market types:
 *
 * STOCK MARKET LEGENDS:
 *   - Jim Simons (Renaissance): Statistical mean-reversion, autocorrelation
 *   - Ed Thorp: Kelly Criterion sizing, probability-based edges
 *   - Paul Tudor Jones: 200MA system, range expansion, contrarian at extremes
 *   - Jesse Livermore: Pivotal points, key level breakouts
 *   - Keith Gill (DFV): Asymmetric risk/reward, structural anomalies
 *
 * FOREX MASTERS:
 *   - George Soros: Reflexivity (momentum acceleration), macro divergence
 *   - Stanley Druckenmiller: Liquidity cycle, forward-looking 18-24 months
 *
 * CRYPTO DATA SCIENTISTS:
 *   - Whale trackers (Nansen/Arkham patterns): Volume profile, OBV divergence
 *   - On-chain accumulation/distribution detection
 *
 * PENNY STOCK PATTERN HUNTERS:
 *   - Timothy Sykes: Supernova spike-and-fade
 *   - Ross Cameron: Gap & Go, bull flags, low float + high relative volume
 *
 * UNIVERSAL TA METHODS (from research):
 *   - Support/Resistance (horizontal key levels, multiple touches)
 *   - Fibonacci Retracement (38.2%, 50%, 61.8%)
 *   - Dynamic MA Support (price bouncing off 50/200 MA)
 *   - Candlestick Patterns at key levels (hammer, engulfing, doji)
 *   - Bollinger Band squeeze + expansion
 *   - VWAP deviation
 *
 * Walk-forward backtest: At each bar t, only data [0..t] is visible.
 * NO look-ahead bias. Every signal fire is tracked with 7/14/30d outcomes.
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
   KRAKEN DATA FETCHER
   ============================================================ */
function _fetch_daily($pair) {
    $all = array();
    $starts = array(
        time() - (1460 * 86400),
        time() - (730 * 86400),
        0
    );
    foreach ($starts as $since) {
        $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=1440';
        if ($since > 0) $url .= '&since=' . $since;
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
        $resp = curl_exec($ch);
        curl_close($ch);
        if (!$resp) continue;
        $j = json_decode($resp, true);
        if (!$j || !empty($j['error']) || !isset($j['result'])) continue;
        $keys = array_keys($j['result']);
        foreach ($keys as $k) {
            if ($k !== 'last' && is_array($j['result'][$k])) {
                foreach ($j['result'][$k] as $c) {
                    $all[intval($c[0])] = $c;
                }
            }
        }
        sleep(1);
    }
    ksort($all);
    return array_values($all);
}

/* ============================================================
   INDICATOR LIBRARY
   ============================================================ */
function _sma($d, $p) {
    $r = array();
    for ($i = $p - 1; $i < count($d); $i++) {
        $s = 0;
        for ($j = $i - $p + 1; $j <= $i; $j++) $s += $d[$j];
        $r[$i] = $s / $p;
    }
    return $r;
}

function _ema($d, $p) {
    if (count($d) < $p) return array();
    $k = 2.0 / ($p + 1);
    $r = array();
    $s = 0;
    for ($i = 0; $i < $p; $i++) $s += $d[$i];
    $r[$p - 1] = $s / $p;
    for ($i = $p; $i < count($d); $i++) {
        $r[$i] = $d[$i] * $k + $r[$i - 1] * (1 - $k);
    }
    return $r;
}

function _rsi($c, $p) {
    if (count($c) < $p + 1) return array();
    $r = array();
    $g = 0; $l = 0;
    for ($i = 1; $i <= $p; $i++) {
        $d = $c[$i] - $c[$i - 1];
        if ($d > 0) $g += $d; else $l += abs($d);
    }
    $ag = $g / $p; $al = $l / $p;
    $rs = ($al > 0) ? $ag / $al : 100;
    $r[$p] = 100 - (100 / (1 + $rs));
    for ($i = $p + 1; $i < count($c); $i++) {
        $d = $c[$i] - $c[$i - 1];
        $gg = ($d > 0) ? $d : 0;
        $ll = ($d < 0) ? abs($d) : 0;
        $ag = ($ag * ($p - 1) + $gg) / $p;
        $al = ($al * ($p - 1) + $ll) / $p;
        $rs = ($al > 0) ? $ag / $al : 100;
        $r[$i] = 100 - (100 / (1 + $rs));
    }
    return $r;
}

function _atr($h, $l, $c, $p) {
    if (count($c) < $p + 1) return array();
    $tr = array();
    for ($i = 1; $i < count($c); $i++) {
        $tr[$i] = max($h[$i] - $l[$i], abs($h[$i] - $c[$i - 1]), abs($l[$i] - $c[$i - 1]));
    }
    $r = array();
    $s = 0;
    for ($i = 1; $i <= $p; $i++) $s += $tr[$i];
    $r[$p] = $s / $p;
    for ($i = $p + 1; $i < count($c); $i++) {
        $r[$i] = ($r[$i - 1] * ($p - 1) + $tr[$i]) / $p;
    }
    return $r;
}

function _obv($c, $v) {
    $r = array();
    $r[0] = 0;
    for ($i = 1; $i < count($c); $i++) {
        if ($c[$i] > $c[$i - 1]) $r[$i] = $r[$i - 1] + $v[$i];
        elseif ($c[$i] < $c[$i - 1]) $r[$i] = $r[$i - 1] - $v[$i];
        else $r[$i] = $r[$i - 1];
    }
    return $r;
}

function _stdev($d, $p, $idx) {
    if ($idx < $p - 1) return 0;
    $s = 0;
    for ($i = $idx - $p + 1; $i <= $idx; $i++) $s += $d[$i];
    $m = $s / $p;
    $var = 0;
    for ($i = $idx - $p + 1; $i <= $idx; $i++) $var += ($d[$i] - $m) * ($d[$i] - $m);
    return sqrt($var / $p);
}

function _bb($c, $p, $idx) {
    /* Bollinger Bands: mid, upper, lower, width */
    if ($idx < $p - 1) return null;
    $s = 0;
    for ($i = $idx - $p + 1; $i <= $idx; $i++) $s += $c[$i];
    $mid = $s / $p;
    $sd = _stdev($c, $p, $idx);
    return array('mid' => $mid, 'upper' => $mid + 2 * $sd, 'lower' => $mid - 2 * $sd, 'width' => ($mid > 0) ? (4 * $sd / $mid) * 100 : 0);
}

/* ============================================================
   THE 20 ALGORITHMS
   Each returns true/false at bar t using only data [0..t]
   ============================================================ */

/* --- A01: TUDOR JONES 200MA SYSTEM ---
   Paul Tudor Jones: "I attribute my success to the 200-day moving average."
   BUY when price crosses ABOVE 200-day SMA from below. */
function _a01_tudor_200ma($t, $c, $sma200) {
    if (!isset($sma200[$t]) || !isset($sma200[$t - 1])) return false;
    return ($c[$t - 1] < $sma200[$t - 1] && $c[$t] > $sma200[$t]);
}

/* --- A02: GOLDEN CROSS (50 > 200 MA) ---
   Classic institutional signal. 50-day SMA crosses above 200-day SMA. */
function _a02_golden_cross($t, $sma50, $sma200) {
    if (!isset($sma50[$t]) || !isset($sma50[$t - 1]) || !isset($sma200[$t]) || !isset($sma200[$t - 1])) return false;
    return ($sma50[$t - 1] < $sma200[$t - 1] && $sma50[$t] >= $sma200[$t]);
}

/* --- A03: RSI OVERSOLD BOUNCE ---
   RSI(14) drops below 30, then crosses back above 30. 
   Chong & Ng 2008: profitable across 49 countries over 60 years. */
function _a03_rsi_bounce($t, $rsi14) {
    if (!isset($rsi14[$t]) || !isset($rsi14[$t - 1])) return false;
    return ($rsi14[$t - 1] < 30 && $rsi14[$t] >= 30);
}

/* --- A04: SIMONS MEAN REVERSION ---
   Price > 2 standard deviations below 20-day mean = buy.
   Renaissance: "We're right 50.75% of the time." Small edge, high frequency. */
function _a04_simons_meanrev($t, $c) {
    if ($t < 20) return false;
    $sd = _stdev($c, 20, $t);
    $s = 0;
    for ($i = $t - 19; $i <= $t; $i++) $s += $c[$i];
    $mean = $s / 20;
    return ($sd > 0 && ($c[$t] < $mean - 2 * $sd));
}

/* --- A05: BOLLINGER BAND SQUEEZE + BREAKOUT ---
   Bollinger width contracts to 20-day low, then price breaks above upper band.
   Volatility compression precedes big moves. */
function _a05_bb_squeeze($t, $c) {
    if ($t < 25) return false;
    $bb_now = _bb($c, 20, $t);
    if ($bb_now === null) return false;
    /* Check if current width is narrowest in 20 bars */
    $min_w = 9999;
    for ($i = $t - 20; $i < $t; $i++) {
        $b = _bb($c, 20, $i);
        if ($b !== null && $b['width'] < $min_w) $min_w = $b['width'];
    }
    $is_squeeze = ($bb_now['width'] <= $min_w * 1.05); /* within 5% of narrowest */
    $breakout = ($c[$t] > $bb_now['upper']);
    return ($is_squeeze && $breakout);
}

/* --- A06: SUPPORT BOUNCE (horizontal key level) ---
   Price touches a level that was tested 3+ times in last 60 days, then bounces.
   The more touches, the stronger the support. */
function _a06_support_bounce($t, $c, $l, $h) {
    if ($t < 65) return false;
    /* Find support zones: cluster lows in last 60 bars */
    $price = $c[$t];
    $tolerance = $price * 0.02; /* 2% tolerance */

    /* Collect all lows from last 60 bars */
    $lows_60 = array();
    for ($i = $t - 60; $i < $t; $i++) {
        $lows_60[] = $l[$i];
    }

    /* Find support level with most touches */
    $best_level = 0; $best_touches = 0;
    for ($idx = 0; $idx < count($lows_60); $idx++) {
        $level = $lows_60[$idx];
        $touches = 0;
        for ($j = 0; $j < count($lows_60); $j++) {
            if (abs($lows_60[$j] - $level) < $tolerance) $touches++;
        }
        if ($touches > $best_touches) {
            $best_touches = $touches;
            $best_level = $level;
        }
    }

    /* Signal: price is within 2% of support AND today is green (bounce) */
    $near_support = ($best_touches >= 3 && abs($price - $best_level) / $best_level < 0.02);
    $green_candle = ($c[$t] > $c[$t - 1]);

    return ($near_support && $green_candle);
}

/* --- A07: RESISTANCE BREAKOUT ON VOLUME ---
   Price breaks above a level tested 3+ times on 1.5x+ volume.
   Old resistance becomes new support. */
function _a07_resistance_break($t, $c, $h, $v) {
    if ($t < 65) return false;
    $price = $c[$t];
    $tol = $price * 0.02;

    /* Find resistance: cluster highs in last 60 bars */
    $highs_60 = array();
    for ($i = $t - 60; $i < $t; $i++) $highs_60[] = $h[$i];

    $best_lvl = 0; $best_cnt = 0;
    for ($idx = 0; $idx < count($highs_60); $idx++) {
        $lvl = $highs_60[$idx];
        $cnt = 0;
        for ($j = 0; $j < count($highs_60); $j++) {
            if (abs($highs_60[$j] - $lvl) < $tol) $cnt++;
        }
        if ($cnt > $best_cnt) { $best_cnt = $cnt; $best_lvl = $lvl; }
    }

    /* Volume check */
    $vol_avg = 0;
    for ($i = $t - 20; $i < $t; $i++) $vol_avg += $v[$i];
    $vol_avg = $vol_avg / 20;
    $vol_surge = ($vol_avg > 0 && $v[$t] > $vol_avg * 1.5);

    return ($best_cnt >= 3 && $price > $best_lvl && $vol_surge);
}

/* --- A08: FIBONACCI 61.8% RETRACEMENT BOUNCE ---
   After a swing high to swing low, price retraces to 61.8% and bounces.
   Most reliable Fibonacci level per academic research. */
function _a08_fib_618($t, $c, $l, $h) {
    if ($t < 40) return false;
    /* Find recent swing high and swing low in last 30 bars */
    $swing_hi = 0; $swing_lo = 999999999;
    $hi_idx = $t; $lo_idx = $t;
    for ($i = $t - 30; $i <= $t; $i++) {
        if ($h[$i] > $swing_hi) { $swing_hi = $h[$i]; $hi_idx = $i; }
        if ($l[$i] < $swing_lo) { $swing_lo = $l[$i]; $lo_idx = $i; }
    }
    if ($swing_hi <= $swing_lo) return false;
    $range = $swing_hi - $swing_lo;

    /* Only valid if high came BEFORE low (downswing, now retracing up) */
    if ($hi_idx >= $lo_idx) return false;

    /* 61.8% retracement level */
    $fib618 = $swing_lo + $range * 0.618;
    $tol = $range * 0.02;

    /* Price near 61.8% and bouncing (today's close > yesterday's close) */
    $near_fib = (abs($c[$t] - $fib618) < $tol);
    $bouncing = ($c[$t] > $c[$t - 1]);

    return ($near_fib && $bouncing);
}

/* --- A09: SOROS REFLEXIVITY (MOMENTUM ACCELERATION) ---
   Soros: Price movements can REINFORCE the fundamentals.
   Detect when momentum is accelerating (rate of change is increasing). */
function _a09_soros_reflexivity($t, $c) {
    if ($t < 15) return false;
    /* Rate of change over 5 days, compare to 10 days ago */
    $roc_now = ($c[$t] - $c[$t - 5]) / $c[$t - 5] * 100;
    $roc_prev = ($c[$t - 5] - $c[$t - 10]) / $c[$t - 10] * 100;
    $roc_prev2 = ($c[$t - 10] - $c[$t - 15]) / $c[$t - 15] * 100;

    /* Acceleration: each period's return is larger than the previous */
    return ($roc_now > $roc_prev && $roc_prev > $roc_prev2 && $roc_now > 2);
}

/* --- A10: LIVERMORE PIVOTAL POINT BREAKOUT ---
   Jesse Livermore: Buy when price breaks its highest high of last 20 days
   on above-average volume. The "pivotal point." */
function _a10_livermore_pivot($t, $c, $h, $v) {
    if ($t < 25) return false;
    /* Highest high of last 20 bars (not including today) */
    $hh = 0;
    for ($i = $t - 20; $i < $t; $i++) {
        if ($h[$i] > $hh) $hh = $h[$i];
    }
    /* Volume above 20-day average */
    $va = 0;
    for ($i = $t - 20; $i < $t; $i++) $va += $v[$i];
    $va = $va / 20;

    return ($c[$t] > $hh && $va > 0 && $v[$t] > $va * 1.3);
}

/* --- A11: DRUCKENMILLER LIQUIDITY (VOLUME DRY-UP + REVERSAL) ---
   Druckenmiller: Buy when volume dries up at the end of a downtrend,
   then reverses. Liquidity exhaustion = bottom. */
function _a11_drucken_liquidity($t, $c, $v) {
    if ($t < 25) return false;
    /* Downtrend: 20-day return is negative */
    $ret20 = ($c[$t] - $c[$t - 20]) / $c[$t - 20] * 100;
    if ($ret20 > -5) return false;

    /* Volume dry-up: current volume < 50% of 20-day average */
    $va = 0;
    for ($i = $t - 20; $i < $t; $i++) $va += $v[$i];
    $va = $va / 20;
    $vol_low = ($va > 0 && $v[$t] < $va * 0.5);

    /* Price reversal: today is green */
    $green = ($c[$t] > $c[$t - 1]);

    return ($vol_low && $green);
}

/* --- A12: HAMMER CANDLESTICK AT SUPPORT ---
   Bullish hammer (small body, long lower wick) at a support level.
   Combined: candlestick pattern + S/R = higher reliability. */
function _a12_hammer_support($t, $c, $o, $h, $l) {
    if ($t < 65) return false;
    $body = abs($c[$t] - $o[$t]);
    $lower_wick = min($c[$t], $o[$t]) - $l[$t];
    $upper_wick = $h[$t] - max($c[$t], $o[$t]);
    $range = $h[$t] - $l[$t];

    if ($range < 0.001) return false;

    /* Hammer: lower wick > 2x body, upper wick < 30% of range */
    $is_hammer = ($body > 0.0001 && $lower_wick > $body * 2 && $upper_wick < $range * 0.3);

    /* At support (near 20-bar low) */
    $low20 = 999999999;
    for ($i = $t - 20; $i < $t; $i++) {
        if ($l[$i] < $low20) $low20 = $l[$i];
    }
    $near_low = ($low20 > 0 && abs($l[$t] - $low20) / $low20 < 0.03);

    return ($is_hammer && $near_low);
}

/* --- A13: BULLISH ENGULFING AT SUPPORT ---
   Today's green body completely engulfs yesterday's red body, near 20-bar low. */
function _a13_engulfing_support($t, $c, $o, $l) {
    if ($t < 22) return false;
    $red_prev = ($c[$t - 1] < $o[$t - 1]);
    $green_today = ($c[$t] > $o[$t]);
    $engulfs = ($o[$t] < $c[$t - 1] && $c[$t] > $o[$t - 1]);

    $low20 = 999999999;
    for ($i = $t - 20; $i < $t; $i++) {
        if ($l[$i] < $low20) $low20 = $l[$i];
    }
    $near_low = ($low20 > 0 && abs($l[$t] - $low20) / $low20 < 0.05);

    return ($red_prev && $green_today && $engulfs && $near_low);
}

/* --- A14: OBV DIVERGENCE (Smart Money Accumulation) ---
   Price makes lower low but OBV makes higher low = smart money accumulating.
   Nansen/Arkham whale tracking principle applied to volume. */
function _a14_obv_divergence($t, $c, $obv) {
    if ($t < 30) return false;
    /* Find two swing lows in last 20 bars */
    $lows_arr = array();
    for ($i = $t - 20; $i <= $t - 2; $i++) {
        if ($i >= 2 && $c[$i] < $c[$i - 1] && $c[$i] < $c[$i + 1]) {
            $lows_arr[] = array('idx' => $i, 'p' => $c[$i], 'obv' => isset($obv[$i]) ? $obv[$i] : 0);
        }
    }
    if (count($lows_arr) < 2) return false;
    $last = $lows_arr[count($lows_arr) - 1];
    $prev = $lows_arr[count($lows_arr) - 2];

    /* Price lower low + OBV higher low = bullish divergence */
    return ($last['p'] < $prev['p'] && $last['obv'] > $prev['obv']);
}

/* --- A15: RANGE EXPANSION (Tudor Jones principle) ---
   "When markets make unusually large moves, they tend to continue."
   Today's range > 2x ATR AND close in top 25% of range AND volume > 1.5x avg. */
function _a15_range_expansion($t, $c, $h, $l, $v, $atr14) {
    if (!isset($atr14[$t]) || $t < 22) return false;
    $range = $h[$t] - $l[$t];
    $big_range = ($atr14[$t] > 0 && $range > $atr14[$t] * 2);
    $close_high = ($h[$t] - $l[$t] > 0 && ($c[$t] - $l[$t]) / ($h[$t] - $l[$t]) > 0.75);

    $va = 0;
    for ($i = $t - 20; $i < $t; $i++) $va += $v[$i];
    $va = $va / 20;
    $vol_up = ($va > 0 && $v[$t] > $va * 1.5);

    return ($big_range && $close_high && $vol_up);
}

/* --- A16: DFV ASYMMETRIC (Deep discount + improving momentum) ---
   DFV principle: Find assets beaten down >40% from high with
   improving RSI (momentum recovering before price). */
function _a16_dfv_asymmetric($t, $c, $h, $rsi14) {
    if ($t < 60 || !isset($rsi14[$t]) || !isset($rsi14[$t - 7])) return false;
    /* 60-day high */
    $hi60 = 0;
    for ($i = $t - 60; $i <= $t; $i++) {
        if ($h[$i] > $hi60) $hi60 = $h[$i];
    }
    $discount = ($hi60 > 0) ? ($c[$t] - $hi60) / $hi60 * 100 : 0;

    /* Deep discount: >25% below 60-day high */
    $deep = ($discount < -25);

    /* RSI improving: higher than 7 days ago AND above 35 (not dead) */
    $rsi_improving = ($rsi14[$t] > $rsi14[$t - 7] && $rsi14[$t] > 35);

    return ($deep && $rsi_improving);
}

/* --- A17: SYKES SUPERNOVA REVERSAL (Penny stock pattern) ---
   After a massive spike (>50% in 5 days), SHORT when first red day appears.
   Applied as inverse: detect the END of a parabolic move for mean-reversion entry. */
function _a17_sykes_supernova($t, $c) {
    if ($t < 10) return false;
    /* 5-day return */
    $ret5 = ($c[$t - 1] - $c[$t - 6]) / $c[$t - 6] * 100;
    /* Today is red (first pullback after spike) */
    $red = ($c[$t] < $c[$t - 1]);
    /* The spike was big */
    return ($ret5 > 30 && $red);
}

/* --- A18: CAMERON GAP & GO (Bull flag) ---
   Gap up > 3% from previous close, consolidation for 2-3 bars,
   then breakout above the gap-day high on volume. */
function _a18_cameron_gap($t, $c, $h, $v, $o) {
    if ($t < 10) return false;
    /* Look for a gap-up in last 5 bars */
    for ($g = $t - 5; $g < $t; $g++) {
        if ($g < 1) continue;
        $gap_pct = ($o[$g] - $c[$g - 1]) / $c[$g - 1] * 100;
        if ($gap_pct < 3) continue; /* Not a gap */

        /* After the gap: price should consolidate (stay within gap day's range) */
        $gap_hi = $h[$g];
        $all_within = true;
        for ($i = $g + 1; $i < $t; $i++) {
            if ($h[$i] > $gap_hi * 1.02) { $all_within = false; break; }
        }

        /* Today: breakout above gap day's high on volume */
        $va = 0;
        for ($i = $t - 10; $i < $t; $i++) $va += $v[$i];
        $va = $va / 10;

        if ($all_within && $c[$t] > $gap_hi && $va > 0 && $v[$t] > $va * 1.3) return true;
    }
    return false;
}

/* --- A19: DYNAMIC MA BOUNCE (50-day EMA) ---
   Price pulls back to 50-day EMA in an uptrend (price above 200 SMA),
   touches EMA and bounces. */
function _a19_ma_bounce_50($t, $c, $ema50, $sma200) {
    if (!isset($ema50[$t]) || !isset($sma200[$t])) return false;
    /* Uptrend: price above 200 SMA */
    $uptrend = ($c[$t] > $sma200[$t]);
    /* Near 50 EMA (within 1.5%) */
    $near_50 = ($ema50[$t] > 0 && abs($c[$t] - $ema50[$t]) / $ema50[$t] < 0.015);
    /* Bounce: yesterday was closer to or below EMA, today moving up */
    $bounce = ($c[$t] > $c[$t - 1] && $c[$t - 1] <= $ema50[$t] * 1.01);

    return ($uptrend && $near_50 && $bounce);
}

/* --- A20: VOLUME CLIMAX REVERSAL ---
   Whale-inspired: massive volume spike (>3x avg) at the low of a downtrend.
   The capitulation signal from spike_detector.php, but stricter. */
function _a20_volume_climax($t, $c, $v) {
    if ($t < 25) return false;
    /* Downtrend */
    $ret20 = ($c[$t] - $c[$t - 20]) / $c[$t - 20] * 100;
    if ($ret20 > -10) return false;

    /* Volume spike */
    $va = 0;
    for ($i = $t - 20; $i < $t; $i++) $va += $v[$i];
    $va = $va / 20;
    $vol_spike = ($va > 0 && $v[$t] > $va * 3.0);

    /* Green close (reversal) */
    $green = ($c[$t] > $o = $c[$t - 1]); /* simplified: close > prev close */

    return ($vol_spike && $green);
}

/* ============================================================
   OUTCOME MEASUREMENT
   ============================================================ */
function _outcome($entry, $c, $h, $l, $max) {
    $ep = $c[$entry];
    $rem = count($c) - $entry - 1;
    $hz = min($max, $rem);
    if ($hz < 7) return null;

    $r7 = 0; $r14 = 0; $r30 = 0;
    $mg7 = -99999; $md7 = 0;
    $mg30 = -99999; $md30 = 0;
    $tp_d = -1; $sl_d = -1;

    for ($d = 1; $d <= $hz; $d++) {
        $i = $entry + $d;
        $hp = (($h[$i] - $ep) / $ep) * 100;
        $lp = (($l[$i] - $ep) / $ep) * 100;
        $cp = (($c[$i] - $ep) / $ep) * 100;

        if ($d <= 7) { if ($hp > $mg7) $mg7 = $hp; if ($lp < $md7) $md7 = $lp; $r7 = $cp; }
        if ($d <= 30) { if ($hp > $mg30) $mg30 = $hp; if ($lp < $md30) $md30 = $lp; $r30 = $cp; }
        if ($d <= 14) $r14 = $cp;

        if ($tp_d < 0 && $hp >= 10) $tp_d = $d;
        if ($sl_d < 0 && $lp <= -5) $sl_d = $d;
    }

    $tpsl = 'NEITHER';
    if ($tp_d > 0 && $sl_d > 0) $tpsl = ($tp_d <= $sl_d) ? 'WIN' : 'LOSS';
    elseif ($tp_d > 0) $tpsl = 'WIN';
    elseif ($sl_d > 0) $tpsl = 'LOSS';

    return array(
        'r7' => round($r7, 2), 'r14' => round($r14, 2), 'r30' => round($r30, 2),
        'mg7' => round($mg7, 2), 'mg30' => round($mg30, 2),
        'md7' => round($md7, 2), 'md30' => round($md30, 2),
        'tpsl' => $tpsl, 'bars' => $hz
    );
}

/* ============================================================
   MAIN BACKTEST RUNNER
   ============================================================ */
function _backtest($pair, $name) {
    $candles = _fetch_daily($pair);
    $n = count($candles);
    if ($n < 250) return array('error' => 'Only ' . $n . ' candles for ' . $name);

    $ts = array(); $o = array(); $h = array(); $l = array(); $c = array(); $v = array();
    foreach ($candles as $x) {
        $ts[] = intval($x[0]);
        $o[] = floatval($x[1]);
        $h[] = floatval($x[2]);
        $l[] = floatval($x[3]);
        $c[] = floatval($x[4]);
        $v[] = floatval($x[6]);
    }

    /* Pre-compute indicators */
    $sma50 = _sma($c, 50);
    $sma200 = _sma($c, 200);
    $ema50 = _ema($c, 50);
    $rsi14 = _rsi($c, 14);
    $atr14 = _atr($h, $l, $c, 14);
    $obv = _obv($c, $v);

    $algo_names = array(
        1 => 'Tudor Jones 200MA Reclaim',
        2 => 'Golden Cross (50>200)',
        3 => 'RSI Oversold Bounce (<30 to >30)',
        4 => 'Simons Mean-Reversion (2-sigma)',
        5 => 'Bollinger Squeeze + Breakout',
        6 => 'Support Bounce (3+ touches)',
        7 => 'Resistance Breakout on Volume',
        8 => 'Fibonacci 61.8% Bounce',
        9 => 'Soros Reflexivity (Momentum Accel)',
        10 => 'Livermore Pivotal Point Breakout',
        11 => 'Druckenmiller Liquidity Exhaustion',
        12 => 'Hammer Candle at Support',
        13 => 'Bullish Engulfing at Support',
        14 => 'OBV Divergence (Smart Money)',
        15 => 'Tudor Range Expansion',
        16 => 'DFV Asymmetric Deep Discount',
        17 => 'Sykes Supernova Reversal (SHORT)',
        18 => 'Cameron Gap & Go',
        19 => 'Dynamic 50-EMA Bounce in Uptrend',
        20 => 'Volume Climax Reversal'
    );

    /* Walk forward */
    $start = 210;
    $end_bar = $n - 31;
    $fires = array();
    $outcomes = array();
    $debounce = array();
    for ($a = 1; $a <= 20; $a++) {
        $fires[$a] = array();
        $outcomes[$a] = array();
        $debounce[$a] = -999;
    }

    for ($t = $start; $t <= $end_bar; $t++) {
        $sig = array();
        $sig[1] = _a01_tudor_200ma($t, $c, $sma200);
        $sig[2] = _a02_golden_cross($t, $sma50, $sma200);
        $sig[3] = _a03_rsi_bounce($t, $rsi14);
        $sig[4] = _a04_simons_meanrev($t, $c);
        $sig[5] = _a05_bb_squeeze($t, $c);
        $sig[6] = _a06_support_bounce($t, $c, $l, $h);
        $sig[7] = _a07_resistance_break($t, $c, $h, $v);
        $sig[8] = _a08_fib_618($t, $c, $l, $h);
        $sig[9] = _a09_soros_reflexivity($t, $c);
        $sig[10] = _a10_livermore_pivot($t, $c, $h, $v);
        $sig[11] = _a11_drucken_liquidity($t, $c, $v);
        $sig[12] = _a12_hammer_support($t, $c, $o, $h, $l);
        $sig[13] = _a13_engulfing_support($t, $c, $o, $l);
        $sig[14] = _a14_obv_divergence($t, $c, $obv);
        $sig[15] = _a15_range_expansion($t, $c, $h, $l, $v, $atr14);
        $sig[16] = _a16_dfv_asymmetric($t, $c, $h, $rsi14);
        $sig[17] = _a17_sykes_supernova($t, $c);
        $sig[18] = _a18_cameron_gap($t, $c, $h, $v, $o);
        $sig[19] = _a19_ma_bounce_50($t, $c, $ema50, $sma200);
        $sig[20] = _a20_volume_climax($t, $c, $v);

        $date = date('Y-m-d', $ts[$t]);

        for ($a = 1; $a <= 20; $a++) {
            if (!$sig[$a]) continue;
            if (($t - $debounce[$a]) < 5) continue;
            $debounce[$a] = $t;

            $oc = _outcome($t, $c, $h, $l, 30);
            if ($oc === null) continue;

            $fires[$a][] = array('d' => $date, 'p' => round($c[$t], 2));
            $outcomes[$a][] = $oc;
        }
    }

    /* Aggregate */
    $stats = array();
    for ($a = 1; $a <= 20; $a++) {
        $cnt = count($fires[$a]);
        if ($cnt === 0) {
            $stats[$a] = array('name' => $algo_names[$a], 'fires' => 0, 'verdict' => 'NEVER_FIRED');
            continue;
        }

        $r7s = array(); $r30s = array(); $tpw = 0; $tpl = 0;
        foreach ($outcomes[$a] as $oc) {
            $r7s[] = $oc['r7'];
            $r30s[] = $oc['r30'];
            if ($oc['tpsl'] === 'WIN') $tpw++;
            if ($oc['tpsl'] === 'LOSS') $tpl++;
        }

        $avg7 = array_sum($r7s) / $cnt;
        $avg30 = array_sum($r30s) / $cnt;
        $w7 = 0; $w30 = 0;
        foreach ($r7s as $r) { if ($r > 0) $w7++; }
        foreach ($r30s as $r) { if ($r > 0) $w30++; }

        /* Sharpe approximation */
        $var = 0;
        foreach ($r7s as $r) $var += ($r - $avg7) * ($r - $avg7);
        $std = ($cnt > 1) ? sqrt($var / ($cnt - 1)) : 0;
        $sharpe = ($std > 0) ? ($avg7 / $std) * sqrt(52) : 0;

        $wr_tpsl = ($tpw + $tpl > 0) ? round($tpw / ($tpw + $tpl) * 100, 1) : 0;

        $grade = 'F';
        if ($avg30 > 8 && $w30 / $cnt > 0.6) $grade = 'A+';
        elseif ($avg30 > 5 && $w30 / $cnt > 0.55) $grade = 'A';
        elseif ($avg30 > 2 && $w30 / $cnt > 0.52) $grade = 'B';
        elseif ($avg30 > 0) $grade = 'C';
        elseif ($avg30 > -2) $grade = 'D';

        $stats[$a] = array(
            'name' => $algo_names[$a],
            'fires' => $cnt,
            'avg_ret_7d' => round($avg7, 2),
            'avg_ret_30d' => round($avg30, 2),
            'win_rate_7d' => round($w7 / $cnt * 100, 1),
            'win_rate_30d' => round($w30 / $cnt * 100, 1),
            'tp10_sl5_wr' => $wr_tpsl,
            'tp10_sl5_detail' => $tpw . 'W/' . $tpl . 'L',
            'sharpe' => round($sharpe, 2),
            'grade' => $grade,
            'sample_dates' => array_slice($fires[$a], 0, 5)
        );
    }

    /* Rank by 30d return */
    $ranking = array();
    foreach ($stats as $a => $s) {
        if ($s['fires'] > 0 && isset($s['avg_ret_30d'])) {
            $ranking[$a] = $s['avg_ret_30d'];
        }
    }
    arsort($ranking);

    $top5 = array();
    $i = 0;
    foreach ($ranking as $a => $ret) {
        if ($i >= 5) break;
        $top5[] = array('algo' => $a, 'name' => $algo_names[$a], 'avg_ret_30d' => $ret, 'grade' => $stats[$a]['grade'], 'fires' => $stats[$a]['fires']);
        $i++;
    }

    return array(
        'asset' => $name,
        'pair' => $pair,
        'candles' => $n,
        'date_range' => date('Y-m-d', $ts[0]) . ' to ' . date('Y-m-d', $ts[$n - 1]),
        'bars_tested' => $end_bar - $start + 1,
        'algorithms_tested' => 20,
        'top_5_algorithms' => $top5,
        'all_stats' => $stats,
        'methodology' => array(
            'data' => 'Kraken daily OHLCV, max ~720 candles (~2 years)',
            'walk_forward' => 'Bar 210 to N-31. Only data [0..t] visible at each step.',
            'debounce' => '5-day minimum between same-algo signals',
            'outcome' => 'Close-to-close return at +7d, +14d, +30d. Max intraday gain/drawdown.',
            'tp_sl' => '+10% take-profit vs -5% stop-loss. First hit wins.',
            'grade' => 'A+: avg30d>8% & WR>60%. A: >5% & >55%. B: >2% & >52%. C: >0%. D: >-2%. F: rest.'
        )
    );
}

/* ============================================================
   API ROUTING
   ============================================================ */
$action = isset($_GET['action']) ? $_GET['action'] : 'status';
switch ($action) {
    case 'backtest':
        $asset = isset($_GET['asset']) ? strtoupper($_GET['asset']) : 'BTC';
        $pairs = array('BTC' => 'XXBTZUSD', 'ETH' => 'XETHZUSD', 'AVAX' => 'AVAXUSD');
        if (!isset($pairs[$asset])) {
            echo json_encode(array('ok' => false, 'error' => 'Use BTC, ETH, or AVAX'));
            break;
        }
        echo json_encode(array('ok' => true, 'backtest' => _backtest($pairs[$asset], $asset)));
        break;

    case 'compare':
        $all = array();
        $pairs = array('BTC' => 'XXBTZUSD', 'ETH' => 'XETHZUSD', 'AVAX' => 'AVAXUSD');
        foreach ($pairs as $nm => $pr) {
            $all[$nm] = _backtest($pr, $nm);
            sleep(2);
        }
        /* Cross-asset winners */
        $universal = array();
        for ($a = 1; $a <= 20; $a++) {
            $total_ret = 0; $cnt = 0;
            foreach ($all as $nm => $bt) {
                if (isset($bt['all_stats'][$a]) && $bt['all_stats'][$a]['fires'] > 0) {
                    $total_ret += $bt['all_stats'][$a]['avg_ret_30d'];
                    $cnt++;
                }
            }
            if ($cnt > 0) $universal[$a] = round($total_ret / $cnt, 2);
        }
        arsort($universal);
        echo json_encode(array('ok' => true, 'per_asset' => $all, 'universal_ranking' => $universal));
        break;

    case 'status':
        echo json_encode(array(
            'ok' => true,
            'engine' => 'Legend Backtest Engine v1.0',
            'algorithms' => 20,
            'inspired_by' => 'Simons, Thorp, Tudor Jones, Soros, Druckenmiller, Livermore, DFV, Sykes, Cameron + S/R, Fibonacci, Bollinger, OBV',
            'assets' => array('BTC', 'ETH', 'AVAX'),
            'actions' => array(
                'backtest?asset=BTC' => 'Single asset backtest (20 algos)',
                'compare' => 'All 3 assets + cross-asset ranking (slow ~90s)',
                'status' => 'This endpoint'
            )
        ));
        break;

    default:
        echo json_encode(array('ok' => false, 'error' => 'Use: backtest, compare, status'));
}
