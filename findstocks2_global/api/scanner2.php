<?php
/**
 * DayTrades Miracle Claude — Core Scanner Engine
 * Fetches real-time Yahoo Finance data, runs 8 screening strategies,
 * scores & ranks picks, calculates commission-aware profit targets.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../scanner2.php                       — run full scan (all strategies)
 *   GET .../scanner2.php?strategy=gap_up       — run single strategy
 *   GET .../scanner2.php?ticker=NVDA           — scan single ticker
 *   GET .../scanner2.php?dry_run=1             — scan but don't save to DB
 *   GET .../scanner2.php?top=10                — return top N picks (default 20)
 */
require_once dirname(__FILE__) . '/db_connect2.php';
require_once dirname(__FILE__) . '/questrade_fees2.php';

$results = array('ok' => true, 'picks' => array(), 'scanned' => 0, 'saved' => 0, 'errors' => array(), 'scan_time' => '');

$filter_strategy = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
$filter_ticker   = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
$dry_run         = isset($_GET['dry_run']) ? (int)$_GET['dry_run'] : 0;
$top_n           = isset($_GET['top']) ? (int)$_GET['top'] : 20;
if ($top_n < 1) $top_n = 20;

$scan_start = microtime(true);

// ─── 1. Load watchlist from DB ───
$tickers_to_scan = array();
$ticker_meta = array(); // ticker => array(company, sector, is_cdr)

if ($filter_ticker !== '') {
    $safe = $conn->real_escape_string($filter_ticker);
    $res = $conn->query("SELECT ticker, company_name, sector, is_cdr FROM miracle_watchlist2 WHERE ticker='$safe' AND active=1");
    if ($res && $res->num_rows > 0) {
        $row = $res->fetch_assoc();
        $tickers_to_scan[] = $row['ticker'];
        $ticker_meta[$row['ticker']] = array('company' => $row['company_name'], 'sector' => $row['sector'], 'is_cdr' => (int)$row['is_cdr']);
    } else {
        // Allow scanning unlisted tickers
        $tickers_to_scan[] = $filter_ticker;
        $ticker_meta[$filter_ticker] = array('company' => '', 'sector' => '', 'is_cdr' => questrade_has_cdr2($filter_ticker) ? 1 : 0);
    }
} else {
    $res = $conn->query("SELECT ticker, company_name, sector, is_cdr FROM miracle_watchlist2 WHERE active=1 ORDER BY is_cdr DESC, ticker ASC");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers_to_scan[] = $row['ticker'];
            $ticker_meta[$row['ticker']] = array('company' => $row['company_name'], 'sector' => $row['sector'], 'is_cdr' => (int)$row['is_cdr']);
        }
    }
}

if (count($tickers_to_scan) === 0) {
    $results['ok'] = false;
    $results['errors'][] = 'No tickers in watchlist. Run setup_schema2.php first.';
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── 2. Fetch price data from Yahoo Finance ───
// We fetch 2 months of daily data to compute 50-day indicators
function miracle_fetch_yahoo($ticker) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($ticker)
         . '?range=3mo&interval=1d&includeAdjustedClose=true';

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
            'timeout' => 10
        )
    ));

    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) return null;

    $result = $data['chart']['result'][0];
    if (!isset($result['timestamp']) || !isset($result['indicators']['quote'][0])) return null;

    $timestamps = $result['timestamp'];
    $quote = $result['indicators']['quote'][0];
    $adjclose = isset($result['indicators']['adjclose'][0]['adjclose'])
                ? $result['indicators']['adjclose'][0]['adjclose'] : array();

    $bars = array();
    $count = count($timestamps);
    for ($i = 0; $i < $count; $i++) {
        $o = isset($quote['open'][$i])   ? $quote['open'][$i]   : null;
        $h = isset($quote['high'][$i])   ? $quote['high'][$i]   : null;
        $l = isset($quote['low'][$i])    ? $quote['low'][$i]    : null;
        $c = isset($quote['close'][$i])  ? $quote['close'][$i]  : null;
        $v = isset($quote['volume'][$i]) ? $quote['volume'][$i] : 0;
        if ($o === null || $h === null || $l === null || $c === null) continue;
        $bars[] = array(
            'date'   => date('Y-m-d', $timestamps[$i]),
            'open'   => round($o, 4),
            'high'   => round($h, 4),
            'low'    => round($l, 4),
            'close'  => round($c, 4),
            'volume' => (int)$v
        );
    }
    return count($bars) > 5 ? $bars : null;
}

// ─── 3. Technical Indicator Calculations ───
function calc_sma($closes, $period) {
    $n = count($closes);
    if ($n < $period) return null;
    $sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $sum += $closes[$i];
    }
    return round($sum / $period, 4);
}

function calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return null;
    $gains = 0;
    $losses = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $change = $closes[$i] - $closes[$i - 1];
        if ($change > 0) $gains += $change;
        else $losses += abs($change);
    }
    if ($losses == 0) return 100;
    $rs = ($gains / $period) / ($losses / $period);
    return round(100 - (100 / (1 + $rs)), 2);
}

function calc_atr($bars, $period) {
    $n = count($bars);
    if ($n < $period + 1) return null;
    $tr_sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $hl = $bars[$i]['high'] - $bars[$i]['low'];
        $hc = abs($bars[$i]['high'] - $bars[$i - 1]['close']);
        $lc = abs($bars[$i]['low'] - $bars[$i - 1]['close']);
        $tr = $hl;
        if ($hc > $tr) $tr = $hc;
        if ($lc > $tr) $tr = $lc;
        $tr_sum += $tr;
    }
    return round($tr_sum / $period, 4);
}

function calc_bollinger($closes, $period, $num_std) {
    $n = count($closes);
    if ($n < $period) return null;
    $slice = array_slice($closes, $n - $period);
    $mean = array_sum($slice) / $period;
    $variance = 0;
    foreach ($slice as $v) {
        $variance += ($v - $mean) * ($v - $mean);
    }
    $std = sqrt($variance / $period);
    return array(
        'middle' => round($mean, 4),
        'upper'  => round($mean + $num_std * $std, 4),
        'lower'  => round($mean - $num_std * $std, 4),
        'std'    => round($std, 4)
    );
}

function calc_zscore($closes, $period) {
    $n = count($closes);
    if ($n < $period) return null;
    $slice = array_slice($closes, $n - $period);
    $mean = array_sum($slice) / $period;
    $variance = 0;
    foreach ($slice as $v) {
        $variance += ($v - $mean) * ($v - $mean);
    }
    $std = sqrt($variance / $period);
    if ($std == 0) return 0;
    return round(($closes[$n - 1] - $mean) / $std, 4);
}

function calc_avg_volume($bars, $period) {
    $n = count($bars);
    if ($n < $period) return null;
    $sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $sum += $bars[$i]['volume'];
    }
    return round($sum / $period);
}

function calc_highest_high($bars, $period) {
    $n = count($bars);
    if ($n < $period) return null;
    $max = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        if ($bars[$i]['high'] > $max) $max = $bars[$i]['high'];
    }
    return $max;
}

function calc_lowest_low($bars, $period) {
    $n = count($bars);
    if ($n < $period) return null;
    $min = 999999;
    for ($i = $n - $period; $i < $n; $i++) {
        if ($bars[$i]['low'] < $min) $min = $bars[$i]['low'];
    }
    return $min;
}

function count_consecutive_red($bars) {
    $n = count($bars);
    $count = 0;
    for ($i = $n - 2; $i >= 0; $i--) {
        if ($bars[$i]['close'] < $bars[$i]['open']) {
            $count++;
        } else {
            break;
        }
    }
    return $count;
}

// ─── 4. Strategy Scanners ───

// 4a. Gap Up Momentum
function scan_gap_up($bars, $meta) {
    $n = count($bars);
    if ($n < 21) return null;
    $today = $bars[$n - 1];
    $yesterday = $bars[$n - 2];
    $gap_pct = (($today['open'] - $yesterday['close']) / $yesterday['close']) * 100;

    if ($gap_pct < 3.0) return null;

    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol == 0) return null;
    $vol_ratio = $today['volume'] / $avg_vol;
    if ($vol_ratio < 1.5) return null;

    $entry = $today['close'];
    $tp_pct = $gap_pct * 1.5;
    if ($tp_pct < 3) $tp_pct = 3;
    if ($tp_pct > 20) $tp_pct = 20;
    $sl_pct = $gap_pct * 0.5;
    if ($sl_pct < 1.5) $sl_pct = 1.5;
    if ($sl_pct > 8) $sl_pct = 8;

    $signal_strength = 0;
    if ($gap_pct >= 5) $signal_strength = 30;
    elseif ($gap_pct >= 4) $signal_strength = 25;
    else $signal_strength = 20;

    $vol_score = 0;
    if ($vol_ratio >= 3) $vol_score = 20;
    elseif ($vol_ratio >= 2) $vol_score = 15;
    else $vol_score = 10;

    // Check if close > open (bullish candle confirms gap)
    $candle_bonus = ($today['close'] > $today['open']) ? 5 : 0;

    return array(
        'strategy'   => 'Gap Up Momentum',
        'entry'      => $entry,
        'tp_pct'     => round($tp_pct, 2),
        'sl_pct'     => round($sl_pct, 2),
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score, 'candle' => $candle_bonus),
        'signals'    => array('gap_pct' => round($gap_pct, 2), 'vol_ratio' => round($vol_ratio, 2), 'bullish_candle' => ($today['close'] > $today['open']))
    );
}

// 4b. Volume Surge Breakout
function scan_volume_surge($bars, $meta) {
    $n = count($bars);
    if ($n < 21) return null;
    $today = $bars[$n - 1];

    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol == 0) return null;
    $vol_ratio = $today['volume'] / $avg_vol;
    if ($vol_ratio < 2.5) return null;

    $closes = array();
    for ($i = 0; $i < $n; $i++) $closes[] = $bars[$i]['close'];

    $high_20 = calc_highest_high($bars, 20);
    if ($today['high'] < $high_20 * 0.98) return null; // Must be near/at 20d high

    $rsi = calc_rsi($closes, 14);
    if ($rsi !== null && $rsi > 80) return null; // Overextended

    $atr = calc_atr($bars, 14);
    if ($atr === null || $atr == 0) return null;

    $entry = $today['close'];
    $tp_pct = ($atr * 2 / $entry) * 100;
    $sl_pct = ($atr / $entry) * 100;
    if ($tp_pct < 2) $tp_pct = 3;
    if ($tp_pct > 15) $tp_pct = 15;
    if ($sl_pct < 1) $sl_pct = 2;
    if ($sl_pct > 8) $sl_pct = 8;

    $signal_strength = 0;
    if ($vol_ratio >= 5) $signal_strength = 30;
    elseif ($vol_ratio >= 3) $signal_strength = 25;
    else $signal_strength = 18;

    $vol_score = 20; // Already passed volume filter

    return array(
        'strategy'   => 'Volume Surge Breakout',
        'entry'      => $entry,
        'tp_pct'     => round($tp_pct, 2),
        'sl_pct'     => round($sl_pct, 2),
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score),
        'signals'    => array('vol_ratio' => round($vol_ratio, 2), 'rsi' => $rsi, 'atr' => $atr, 'near_20d_high' => true)
    );
}

// 4c. Oversold Bounce
function scan_oversold_bounce($bars, $meta) {
    $n = count($bars);
    if ($n < 21) return null;
    $today = $bars[$n - 1];

    $closes = array();
    for ($i = 0; $i < $n; $i++) $closes[] = $bars[$i]['close'];

    $rsi = calc_rsi($closes, 14);
    if ($rsi === null || $rsi > 35) return null;

    $bb = calc_bollinger($closes, 20, 2);
    if ($bb === null) return null;
    if ($today['close'] > $bb['lower'] * 1.02) return null; // Must be near/below lower band

    $red_days = count_consecutive_red($bars);
    if ($red_days < 2) return null;

    // Reversal candle: close > open today
    if ($today['close'] <= $today['open']) return null;

    $entry = $today['close'];
    // TP = middle band
    $tp_pct = (($bb['middle'] - $entry) / $entry) * 100;
    if ($tp_pct < 2) $tp_pct = 2;
    if ($tp_pct > 12) $tp_pct = 12;
    // SL = below recent low
    $recent_low = calc_lowest_low($bars, 5);
    $sl_pct = (($entry - $recent_low) / $entry) * 100 + 1;
    if ($sl_pct < 2) $sl_pct = 2;
    if ($sl_pct > 8) $sl_pct = 8;

    $signal_strength = 0;
    if ($rsi < 25) $signal_strength = 30;
    elseif ($rsi < 30) $signal_strength = 25;
    else $signal_strength = 18;

    $vol_score = 0;
    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol > 0) {
        $vr = $today['volume'] / $avg_vol;
        if ($vr >= 2) $vol_score = 15;
        elseif ($vr >= 1.3) $vol_score = 10;
        else $vol_score = 5;
    }

    return array(
        'strategy'   => 'Oversold Bounce',
        'entry'      => $entry,
        'tp_pct'     => round($tp_pct, 2),
        'sl_pct'     => round($sl_pct, 2),
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score, 'red_days' => min($red_days, 5)),
        'signals'    => array('rsi' => $rsi, 'bb_lower' => $bb['lower'], 'bb_middle' => $bb['middle'], 'red_days' => $red_days, 'reversal_candle' => true)
    );
}

// 4d. Momentum Continuation
function scan_momentum_cont($bars, $meta) {
    $n = count($bars);
    if ($n < 52) return null;
    $today = $bars[$n - 1];

    $closes = array();
    for ($i = 0; $i < $n; $i++) $closes[] = $bars[$i]['close'];

    $sma20 = calc_sma($closes, 20);
    $sma50 = calc_sma($closes, 50);
    if ($sma20 === null || $sma50 === null) return null;

    // Uptrend: SMA20 > SMA50
    if ($sma20 <= $sma50) return null;

    // Pullback to SMA20: price within 1.5% of SMA20
    $dist_to_sma20 = abs($today['close'] - $sma20) / $sma20 * 100;
    if ($dist_to_sma20 > 2.0) return null;

    // Bounce: close > open (green candle)
    if ($today['close'] <= $today['open']) return null;

    // Volume confirmation
    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol == 0) return null;
    $vol_ratio = $today['volume'] / $avg_vol;
    if ($vol_ratio < 0.8) return null;

    $entry = $today['close'];
    // TP = previous swing high (5-day high)
    $swing_high = calc_highest_high($bars, 10);
    $tp_pct = (($swing_high - $entry) / $entry) * 100;
    if ($tp_pct < 2) $tp_pct = 3;
    if ($tp_pct > 12) $tp_pct = 12;
    // SL = below SMA50
    $sl_pct = (($entry - $sma50) / $entry) * 100 + 0.5;
    if ($sl_pct < 2) $sl_pct = 2;
    if ($sl_pct > 8) $sl_pct = 8;

    $signal_strength = 22; // Base for trend pullback
    if ($dist_to_sma20 < 0.5) $signal_strength += 5; // Very tight to SMA20
    if ($vol_ratio > 1.5) $signal_strength += 3;

    $trend_score = 20; // SMA20 > SMA50 = full trend alignment

    return array(
        'strategy'   => 'Momentum Continuation',
        'entry'      => $entry,
        'tp_pct'     => round($tp_pct, 2),
        'sl_pct'     => round($sl_pct, 2),
        'score_parts'=> array('signal' => $signal_strength, 'trend' => $trend_score),
        'signals'    => array('sma20' => $sma20, 'sma50' => $sma50, 'dist_to_sma20' => round($dist_to_sma20, 2), 'vol_ratio' => round($vol_ratio, 2))
    );
}

// 4e. Earnings Catalyst Runner
function scan_earnings_runner($bars, $meta) {
    $n = count($bars);
    if ($n < 21) return null;

    // Look for large 1-day moves (>5%) with high volume in last 5 days
    // (proxy for earnings since we don't have earnings calendar)
    $best = null;
    for ($i = $n - 5; $i < $n; $i++) {
        if ($i < 1) continue;
        $daily_return = (($bars[$i]['close'] - $bars[$i - 1]['close']) / $bars[$i - 1]['close']) * 100;
        if ($daily_return < 5) continue;

        $avg_vol = 0;
        $vol_count = 0;
        for ($j = $i - 20; $j < $i; $j++) {
            if ($j >= 0) { $avg_vol += $bars[$j]['volume']; $vol_count++; }
        }
        if ($vol_count > 0) $avg_vol = $avg_vol / $vol_count;
        if ($avg_vol == 0) continue;
        $vol_ratio = $bars[$i]['volume'] / $avg_vol;
        if ($vol_ratio < 2.5) continue;

        $best = array('day' => $i, 'return' => $daily_return, 'vol_ratio' => $vol_ratio);
    }

    if ($best === null) return null;

    $today = $bars[$n - 1];
    $entry = $today['close'];
    $tp_pct = 10.0;
    $sl_pct = 5.0;

    $signal_strength = 0;
    if ($best['return'] >= 10) $signal_strength = 30;
    elseif ($best['return'] >= 7) $signal_strength = 25;
    else $signal_strength = 20;

    $vol_score = 0;
    if ($best['vol_ratio'] >= 5) $vol_score = 20;
    elseif ($best['vol_ratio'] >= 3) $vol_score = 15;
    else $vol_score = 10;

    return array(
        'strategy'   => 'Earnings Catalyst Runner',
        'entry'      => $entry,
        'tp_pct'     => $tp_pct,
        'sl_pct'     => $sl_pct,
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score),
        'signals'    => array('catalyst_return' => round($best['return'], 2), 'catalyst_vol_ratio' => round($best['vol_ratio'], 2), 'days_ago' => $n - 1 - $best['day'])
    );
}

// 4f. CDR Zero-Fee Play
function scan_cdr_priority($bars, $meta) {
    if (!$meta['is_cdr']) return null;
    $n = count($bars);
    if ($n < 21) return null;
    $today = $bars[$n - 1];

    $closes = array();
    for ($i = 0; $i < $n; $i++) $closes[] = $bars[$i]['close'];

    // Check for any momentum signal
    $rsi = calc_rsi($closes, 14);
    $sma20 = calc_sma($closes, 20);
    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol == 0) return null;
    $vol_ratio = $today['volume'] / $avg_vol;

    // Need at least mild momentum: above SMA20 OR RSI between 40-65 (not overbought) OR volume surge
    $has_momentum = false;
    $signals = array('rsi' => $rsi, 'sma20' => $sma20, 'vol_ratio' => round($vol_ratio, 2));

    if ($today['close'] > $sma20 && $rsi !== null && $rsi < 70) {
        $has_momentum = true;
        $signals['reason'] = 'Above SMA20, RSI healthy';
    }
    if ($vol_ratio >= 1.8) {
        $has_momentum = true;
        $signals['reason'] = 'Volume surge';
    }
    if ($rsi !== null && $rsi < 35) {
        $has_momentum = true;
        $signals['reason'] = 'Oversold bounce candidate';
    }

    if (!$has_momentum) return null;

    $entry = $today['close'];
    $tp_pct = 4.0;
    $sl_pct = 2.0;

    // CDR gets lower breakeven so even small moves are profitable
    $signal_strength = 18;
    if ($vol_ratio >= 2) $signal_strength += 5;
    if ($rsi !== null && $rsi > 50 && $rsi < 70) $signal_strength += 3;

    $cdr_bonus = 10; // Full CDR bonus

    return array(
        'strategy'   => 'CDR Zero-Fee Play',
        'entry'      => $entry,
        'tp_pct'     => $tp_pct,
        'sl_pct'     => $sl_pct,
        'score_parts'=> array('signal' => $signal_strength, 'cdr_bonus' => $cdr_bonus),
        'signals'    => $signals
    );
}

// 4g. Sector Momentum Leader
function scan_sector_leader($bars, $meta) {
    // Only scan individual stocks, not ETFs
    if ($meta['sector'] === 'ETF') return null;
    $n = count($bars);
    if ($n < 6) return null;
    $today = $bars[$n - 1];

    // 5-day return
    $five_day_return = (($today['close'] - $bars[$n - 6]['close']) / $bars[$n - 6]['close']) * 100;
    if ($five_day_return < 3.0) return null; // Must be strongly outperforming

    // Volume check
    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol == 0) return null;
    $vol_ratio = $today['volume'] / $avg_vol;
    if ($vol_ratio < 1.0) return null;

    $entry = $today['close'];
    $tp_pct = 5.0;
    $sl_pct = 2.5;

    $signal_strength = 0;
    if ($five_day_return >= 8) $signal_strength = 28;
    elseif ($five_day_return >= 5) $signal_strength = 22;
    else $signal_strength = 18;

    $vol_score = 0;
    if ($vol_ratio >= 2) $vol_score = 15;
    elseif ($vol_ratio >= 1.3) $vol_score = 10;
    else $vol_score = 5;

    return array(
        'strategy'   => 'Sector Momentum Leader',
        'entry'      => $entry,
        'tp_pct'     => $tp_pct,
        'sl_pct'     => $sl_pct,
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score),
        'signals'    => array('five_day_return' => round($five_day_return, 2), 'vol_ratio' => round($vol_ratio, 2), 'sector' => $meta['sector'])
    );
}

// 4h. Mean Reversion Sniper
function scan_mean_reversion($bars, $meta) {
    $n = count($bars);
    if ($n < 52) return null;
    $today = $bars[$n - 1];

    $closes = array();
    for ($i = 0; $i < $n; $i++) $closes[] = $bars[$i]['close'];

    $zscore = calc_zscore($closes, 20);
    if ($zscore === null || $zscore > -1.8) return null;

    // SMA200 check: must still be rising (not broken trend)
    $sma50 = calc_sma($closes, 50);
    if ($sma50 === null) return null;
    // Use SMA50 as proxy for trend (we may not have 200 days of data)
    // Price should be below SMA20 but overall trend not destroyed
    $sma20 = calc_sma($closes, 20);
    if ($sma20 === null) return null;

    // Volume confirmation: volume should be present (not dead stock)
    $avg_vol = calc_avg_volume($bars, 20);
    if ($avg_vol === null || $avg_vol < 100000) return null;
    $vol_ratio = $today['volume'] / $avg_vol;

    $entry = $today['close'];
    // TP = return to mean (SMA20)
    $tp_pct = (($sma20 - $entry) / $entry) * 100;
    if ($tp_pct < 2) $tp_pct = 3;
    if ($tp_pct > 15) $tp_pct = 15;
    // SL = further deviation
    $bb = calc_bollinger($closes, 20, 3);
    $sl_pct = (($entry - $bb['lower']) / $entry) * 100 + 1;
    if ($sl_pct < 2) $sl_pct = 3;
    if ($sl_pct > 10) $sl_pct = 10;

    $signal_strength = 0;
    if ($zscore < -2.5) $signal_strength = 30;
    elseif ($zscore < -2.0) $signal_strength = 25;
    else $signal_strength = 20;

    $vol_score = 0;
    if ($vol_ratio >= 2) $vol_score = 15;
    elseif ($vol_ratio >= 1.2) $vol_score = 10;
    else $vol_score = 5;

    // Trend bonus: if SMA50 is still above where it was 10 days ago, trend intact
    $old_sma50 = calc_sma(array_slice($closes, 0, $n - 10), 50);
    $trend_bonus = ($old_sma50 !== null && $sma50 > $old_sma50) ? 10 : 0;

    return array(
        'strategy'   => 'Mean Reversion Sniper',
        'entry'      => $entry,
        'tp_pct'     => round($tp_pct, 2),
        'sl_pct'     => round($sl_pct, 2),
        'score_parts'=> array('signal' => $signal_strength, 'volume' => $vol_score, 'trend' => $trend_bonus),
        'signals'    => array('zscore' => $zscore, 'sma20' => $sma20, 'sma50' => $sma50, 'vol_ratio' => round($vol_ratio, 2))
    );
}

// ─── 5. Run All Scanners ───
$all_picks = array();
$scan_date = date('Y-m-d');
$scan_time = date('Y-m-d H:i:s');

// Strategy scan_type => scanner function mapping
$strategy_map = array(
    'gap_scanner'     => 'scan_gap_up',
    'volume_scanner'  => 'scan_volume_surge',
    'reversal'        => 'scan_oversold_bounce',
    'trend_pullback'  => 'scan_momentum_cont',
    'earnings'        => 'scan_earnings_runner',
    'cdr_filter'      => 'scan_cdr_priority',
    'sector_scan'     => 'scan_sector_leader',
    'zscore_reversal' => 'scan_mean_reversion'
);

// Load enabled strategies
$enabled_strategies = array();
$sres = $conn->query("SELECT name, scan_type FROM miracle_strategies2 WHERE enabled=1");
if ($sres) {
    while ($srow = $sres->fetch_assoc()) {
        if ($filter_strategy !== '' && $srow['scan_type'] !== $filter_strategy && $srow['name'] !== $filter_strategy) continue;
        $enabled_strategies[] = $srow;
    }
}

// Process tickers in batches of 8 (avoid Yahoo rate limits)
$batch_size = 8;
$total_tickers = count($tickers_to_scan);
$scanned = 0;

for ($batch_start = 0; $batch_start < $total_tickers; $batch_start += $batch_size) {
    $batch = array_slice($tickers_to_scan, $batch_start, $batch_size);

    foreach ($batch as $ticker) {
        $bars = miracle_fetch_yahoo($ticker);
        if ($bars === null) {
            $results['errors'][] = $ticker . ': fetch failed';
            continue;
        }

        $meta = isset($ticker_meta[$ticker]) ? $ticker_meta[$ticker] : array('company' => '', 'sector' => '', 'is_cdr' => 0);

        // Run each enabled strategy scanner
        foreach ($enabled_strategies as $strat) {
            $scan_type = $strat['scan_type'];
            if (!isset($strategy_map[$scan_type])) continue;
            $func = $strategy_map[$scan_type];
            $pick = $func($bars, $meta);

            if ($pick !== null) {
                // Calculate composite score
                $score = 0;
                foreach ($pick['score_parts'] as $part_val) {
                    $score += $part_val;
                }
                // CDR bonus for all strategies
                if ($meta['is_cdr'] && !isset($pick['score_parts']['cdr_bonus'])) {
                    $score += 8;
                }
                // Risk/reward bonus
                $rr = ($pick['sl_pct'] > 0) ? ($pick['tp_pct'] / $pick['sl_pct']) : 1;
                if ($rr >= 3) $score += 20;
                elseif ($rr >= 2) $score += 15;
                elseif ($rr >= 1.5) $score += 10;
                else $score += 5;

                // Cap at 100
                if ($score > 100) $score = 100;

                // Confidence level
                $confidence = 'low';
                if ($score >= 75) $confidence = 'high';
                elseif ($score >= 55) $confidence = 'medium';

                // Calculate Questrade fees (round-trip on $10k position)
                $position_value = 1000; // $1000 position for fee calc
                $shares = ($pick['entry'] > 0) ? floor($position_value / $pick['entry']) : 0;
                $rt_fee = questrade_round_trip_fee2($ticker, $pick['entry'], $shares);

                // Net profit if TP hit
                $gross_profit = $position_value * ($pick['tp_pct'] / 100);
                $net_profit = round($gross_profit - $rt_fee, 2);

                $tp_price = round($pick['entry'] * (1 + $pick['tp_pct'] / 100), 4);
                $sl_price = round($pick['entry'] * (1 - $pick['sl_pct'] / 100), 4);

                $pick_hash = sha1($ticker . $scan_date . $pick['strategy']);

                $all_picks[] = array(
                    'ticker'          => $ticker,
                    'company'         => $meta['company'],
                    'sector'          => $meta['sector'],
                    'strategy'        => $pick['strategy'],
                    'entry_price'     => $pick['entry'],
                    'stop_loss_price' => $sl_price,
                    'take_profit_price'=> $tp_price,
                    'stop_loss_pct'   => $pick['sl_pct'],
                    'take_profit_pct' => $pick['tp_pct'],
                    'score'           => $score,
                    'confidence'      => $confidence,
                    'signals'         => $pick['signals'],
                    'is_cdr'          => $meta['is_cdr'],
                    'questrade_fee'   => $rt_fee,
                    'net_profit_if_tp'=> $net_profit,
                    'risk_reward'     => round($rr, 2),
                    'pick_hash'       => $pick_hash
                );
            }
        }

        $scanned++;
    }

    // Brief pause between batches to be nice to Yahoo
    if ($batch_start + $batch_size < $total_tickers) {
        usleep(500000); // 0.5 second
    }
}

// ─── 6. Sort by score (highest first) and limit ───
// PHP 5.2 compatible sort
$sorted_picks = $all_picks;
$pick_count = count($sorted_picks);
for ($i = 0; $i < $pick_count - 1; $i++) {
    for ($j = 0; $j < $pick_count - $i - 1; $j++) {
        if ($sorted_picks[$j]['score'] < $sorted_picks[$j + 1]['score']) {
            $temp = $sorted_picks[$j];
            $sorted_picks[$j] = $sorted_picks[$j + 1];
            $sorted_picks[$j + 1] = $temp;
        }
    }
}

$top_picks = array_slice($sorted_picks, 0, $top_n);

// ─── 7. Save to database ───
$saved = 0;
if (!$dry_run) {
    foreach ($top_picks as $p) {
        $hash = $conn->real_escape_string($p['pick_hash']);
        // Check duplicate
        $chk = $conn->query("SELECT id FROM miracle_picks2 WHERE pick_hash='$hash'");
        if ($chk && $chk->num_rows > 0) continue;

        $t   = $conn->real_escape_string($p['ticker']);
        $sn  = $conn->real_escape_string($p['strategy']);
        $sig = $conn->real_escape_string(json_encode($p['signals']));
        $conf= $conn->real_escape_string($p['confidence']);

        $sql = "INSERT INTO miracle_picks2 (ticker, strategy_name, scan_date, scan_time, entry_price, stop_loss_price, take_profit_price, stop_loss_pct, take_profit_pct, score, confidence, signals_json, is_cdr, questrade_fee, net_profit_if_tp, risk_reward_ratio, outcome, pick_hash)
                VALUES ('$t','$sn','$scan_date','$scan_time',{$p['entry_price']},{$p['stop_loss_price']},{$p['take_profit_price']},{$p['stop_loss_pct']},{$p['take_profit_pct']},{$p['score']},'$conf','$sig',{$p['is_cdr']},{$p['questrade_fee']},{$p['net_profit_if_tp']},{$p['risk_reward']},'pending','$hash')";
        if ($conn->query($sql)) {
            $saved++;
        }
    }

    // Audit log
    $now = date('Y-m-d H:i:s');
    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $detail = 'Scanned ' . $scanned . ' tickers, found ' . count($all_picks) . ' signals, saved ' . $saved . ' picks';
    $detail = $conn->real_escape_string($detail);
    $conn->query("INSERT INTO miracle_audit2 (action_type, details, ip_address, created_at) VALUES ('scan', '$detail', '$ip', '$now')");
}

$scan_elapsed = round(microtime(true) - $scan_start, 2);

$results['scanned'] = $scanned;
$results['total_signals'] = count($all_picks);
$results['saved'] = $saved;
$results['scan_time'] = $scan_elapsed . 's';
$results['picks'] = $top_picks;

echo json_encode($results);
$conn->close();
?>
