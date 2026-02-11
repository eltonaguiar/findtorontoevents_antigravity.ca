<?php
/**
 * Forex Insights API — analyst recommendations and technical analysis.
 * All data sourced from fxp_price_history table (no web scraping).
 * PHP 5.2 compatible: no short arrays, no closures, no spread operator.
 *
 * Actions:
 *   ?action=technical&symbol=EURUSD=X   — Technical indicators for one pair
 *   ?action=recommendations              — Aggregate buy/sell/hold for all pairs
 *   ?action=market_overview              — Bullish/bearish counts, RSI, movers
 *   ?action=session_analysis             — Active forex trading sessions + pair recs
 *
 * Cache: 30-minute file cache in /tmp/fx_insights_*.json
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : '';

if ($action === '') {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Missing action parameter. Use: technical, recommendations, market_overview, session_analysis'
    ));
    $conn->close();
    exit;
}

// ============================================================
// File cache helpers (30 min TTL)
// ============================================================

function fx_cache_key($action, $extra) {
    return '/tmp/fx_insights_' . $action . '_' . md5($extra) . '.json';
}

function fx_cache_get($action, $extra) {
    $file = fx_cache_key($action, $extra);
    if (!file_exists($file)) return null;
    $age = time() - filemtime($file);
    if ($age > 1800) return null; // 30 min TTL
    $raw = @file_get_contents($file);
    if ($raw === false) return null;
    $data = json_decode($raw, true);
    return $data;
}

function fx_cache_set($action, $extra, $data) {
    $file = fx_cache_key($action, $extra);
    @file_put_contents($file, json_encode($data));
}

// ============================================================
// Price history loader
// ============================================================

/**
 * Load closing prices for a symbol, ordered oldest to newest.
 * Returns array of arrays with keys: price_date, close_price, high_price, low_price, open_price
 */
function fx_load_prices($conn, $symbol) {
    // Strip =X suffix if present for DB lookup
    $clean = str_replace('=X', '', strtoupper(trim($symbol)));
    $safe = $conn->real_escape_string($clean);
    $sql = "SELECT price_date, open_price, high_price, low_price, close_price
            FROM fxp_price_history
            WHERE symbol = '$safe'
            ORDER BY price_date ASC";
    $res = $conn->query($sql);
    $rows = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $rows[] = $row;
        }
    }
    return $rows;
}

/**
 * Load all pair symbols from fxp_pairs.
 */
function fx_load_all_pairs($conn) {
    $res = $conn->query("SELECT symbol, base_currency, quote_currency, category FROM fxp_pairs ORDER BY symbol");
    $pairs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $pairs[] = $row;
        }
    }
    return $pairs;
}

// ============================================================
// Technical indicator calculations
// ============================================================

/**
 * Simple Moving Average over the last $period closing prices.
 * Returns null if not enough data.
 */
function fx_calc_sma($closes, $period) {
    $n = count($closes);
    if ($n < $period) return null;
    $sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $sum += $closes[$i];
    }
    return $sum / $period;
}

/**
 * RSI(14) using Wilder smoothing.
 * Returns null if not enough data.
 */
function fx_calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return null;

    // First avg gain/loss from initial $period changes
    $gains = 0;
    $losses = 0;
    for ($i = 1; $i <= $period; $i++) {
        $change = $closes[$i] - $closes[$i - 1];
        if ($change > 0) {
            $gains += $change;
        } else {
            $losses += abs($change);
        }
    }
    $avg_gain = $gains / $period;
    $avg_loss = $losses / $period;

    // Wilder smoothing for remaining periods
    for ($i = $period + 1; $i < $n; $i++) {
        $change = $closes[$i] - $closes[$i - 1];
        if ($change > 0) {
            $avg_gain = ($avg_gain * ($period - 1) + $change) / $period;
            $avg_loss = ($avg_loss * ($period - 1) + 0) / $period;
        } else {
            $avg_gain = ($avg_gain * ($period - 1) + 0) / $period;
            $avg_loss = ($avg_loss * ($period - 1) + abs($change)) / $period;
        }
    }

    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

/**
 * MACD (fast, slow, signal). Returns array(macd_line, signal_line, histogram) or null.
 */
function fx_calc_macd($closes, $fast_period, $slow_period, $signal_period) {
    $n = count($closes);
    if ($n < $slow_period + $signal_period) return null;

    // Calculate EMA helper
    $fast_ema = fx_calc_ema_series($closes, $fast_period);
    $slow_ema = fx_calc_ema_series($closes, $slow_period);

    if ($fast_ema === null || $slow_ema === null) return null;

    // MACD line = fast EMA - slow EMA (aligned to slow start index)
    $macd_line = array();
    $start = $slow_period - 1;
    for ($i = $start; $i < $n; $i++) {
        $macd_line[] = $fast_ema[$i] - $slow_ema[$i];
    }

    if (count($macd_line) < $signal_period) return null;

    // Signal line = EMA of MACD line
    $signal_ema = fx_calc_ema_series($macd_line, $signal_period);
    if ($signal_ema === null) return null;

    $last_macd = $macd_line[count($macd_line) - 1];
    $last_signal = $signal_ema[count($signal_ema) - 1];
    $histogram = $last_macd - $last_signal;

    return array(
        'macd_line' => round($last_macd, 6),
        'signal_line' => round($last_signal, 6),
        'histogram' => round($histogram, 6)
    );
}

/**
 * Calculate EMA series. Returns array of same length as input with EMA values,
 * or null if not enough data. Early values (before period) use SMA as seed.
 */
function fx_calc_ema_series($values, $period) {
    $n = count($values);
    if ($n < $period) return null;

    $multiplier = 2.0 / ($period + 1);
    $ema = array();

    // Seed with SMA of first $period values
    $sum = 0;
    for ($i = 0; $i < $period; $i++) {
        $sum += $values[$i];
        $ema[$i] = $sum / ($i + 1); // partial for early values
    }
    $ema[$period - 1] = $sum / $period; // proper SMA seed

    // EMA for remaining
    for ($i = $period; $i < $n; $i++) {
        $ema[$i] = ($values[$i] - $ema[$i - 1]) * $multiplier + $ema[$i - 1];
    }

    return $ema;
}

/**
 * Bollinger Bands (period, num_std_dev). Returns array(upper, middle, lower) or null.
 */
function fx_calc_bollinger($closes, $period, $num_std) {
    $n = count($closes);
    if ($n < $period) return null;

    $middle = fx_calc_sma($closes, $period);
    if ($middle === null) return null;

    // Standard deviation of last $period values
    $sum_sq = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $diff = $closes[$i] - $middle;
        $sum_sq += $diff * $diff;
    }
    $std_dev = sqrt($sum_sq / $period);

    return array(
        'upper' => round($middle + $num_std * $std_dev, 6),
        'middle' => round($middle, 6),
        'lower' => round($middle - $num_std * $std_dev, 6),
        'bandwidth' => ($middle > 0) ? round(($num_std * 2 * $std_dev) / $middle * 100, 4) : 0
    );
}

/**
 * ATR (Average True Range) for volatility-based position sizing (Kimi P1).
 * Returns ATR value or null if not enough data.
 */
function fx_calc_atr($rows, $period) {
    $n = count($rows);
    if ($n < $period + 1) return null;

    $trs = array();
    for ($i = 1; $i < $n; $i++) {
        $h = (float)$rows[$i]['high_price'];
        $l = (float)$rows[$i]['low_price'];
        $pc = (float)$rows[$i - 1]['close_price'];
        $tr = max($h - $l, abs($h - $pc), abs($l - $pc));
        $trs[] = $tr;
    }

    // Wilder smoothing
    $atr = 0;
    for ($i = 0; $i < $period; $i++) {
        $atr += $trs[$i];
    }
    $atr = $atr / $period;
    for ($i = $period; $i < count($trs); $i++) {
        $atr = ($atr * ($period - 1) + $trs[$i]) / $period;
    }
    return $atr;
}

/**
 * ATR-based position sizing (Kimi P1).
 * Risk 2% of capital per trade, size inversely to volatility.
 * Returns array('position_pct' => float, 'atr' => float, 'atr_pct' => float)
 */
function fx_atr_position_size($rows, $current_price, $capital) {
    if (!isset($capital)) $capital = 10000;
    $atr = fx_calc_atr($rows, 14);
    if ($atr === null || $current_price <= 0) {
        return array('position_pct' => 10.0, 'atr' => null, 'atr_pct' => null, 'method' => 'default');
    }

    $atr_pct = ($atr / $current_price) * 100;
    $risk_per_trade = 0.02; // 2% risk

    // Position size = (risk capital) / (ATR * 1.5 as stop distance)
    $stop_distance = $atr * 1.5;
    $risk_amount = $capital * $risk_per_trade;
    $units = ($stop_distance > 0) ? $risk_amount / $stop_distance : 0;
    $position_value = $units * $current_price;
    $position_pct = ($capital > 0) ? ($position_value / $capital) * 100 : 10.0;

    // Clamp between 2% and 25%
    $position_pct = max(2.0, min(25.0, $position_pct));

    return array(
        'position_pct' => round($position_pct, 2),
        'atr' => round($atr, 6),
        'atr_pct' => round($atr_pct, 4),
        'stop_distance_pct' => round(($stop_distance / $current_price) * 100, 4),
        'method' => 'atr_based'
    );
}

/**
 * Determine overall signal from indicators.
 * Returns one of: STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
 */
function fx_determine_signal($current_price, $sma20, $sma50, $sma200, $rsi, $macd, $bollinger) {
    $score = 0; // -5 to +5 scale

    // SMA trend signals
    if ($sma20 !== null && $current_price > $sma20) $score += 1;
    if ($sma20 !== null && $current_price < $sma20) $score -= 1;

    if ($sma50 !== null && $current_price > $sma50) $score += 1;
    if ($sma50 !== null && $current_price < $sma50) $score -= 1;

    if ($sma200 !== null && $current_price > $sma200) $score += 1;
    if ($sma200 !== null && $current_price < $sma200) $score -= 1;

    // SMA crossover: 20 > 50 is bullish
    if ($sma20 !== null && $sma50 !== null) {
        if ($sma20 > $sma50) $score += 1;
        if ($sma20 < $sma50) $score -= 1;
    }

    // RSI signals
    if ($rsi !== null) {
        if ($rsi < 30) $score += 1;       // oversold = buy
        if ($rsi < 20) $score += 1;       // deeply oversold = strong buy
        if ($rsi > 70) $score -= 1;       // overbought = sell
        if ($rsi > 80) $score -= 1;       // deeply overbought = strong sell
    }

    // MACD signals
    if ($macd !== null) {
        if ($macd['histogram'] > 0) $score += 1;
        if ($macd['histogram'] < 0) $score -= 1;
        if ($macd['macd_line'] > 0 && $macd['signal_line'] > 0) $score += 1;
        if ($macd['macd_line'] < 0 && $macd['signal_line'] < 0) $score -= 1;
    }

    // Bollinger Band signals
    if ($bollinger !== null) {
        if ($current_price <= $bollinger['lower']) $score += 1; // at lower band = buy
        if ($current_price >= $bollinger['upper']) $score -= 1; // at upper band = sell
    }

    // Map score to signal
    if ($score >= 5) return 'STRONG_BUY';
    if ($score >= 2) return 'BUY';
    if ($score <= -5) return 'STRONG_SELL';
    if ($score <= -2) return 'SELL';
    return 'NEUTRAL';
}

/**
 * Build a full technical analysis result for one symbol.
 * Returns the analysis array or null on error.
 */
function fx_analyze_symbol($conn, $symbol) {
    $prices = fx_load_prices($conn, $symbol);
    $n = count($prices);
    if ($n < 15) return null; // need at least some data

    // Extract close prices as flat array
    $closes = array();
    for ($i = 0; $i < $n; $i++) {
        $closes[] = (float)$prices[$i]['close_price'];
    }
    $current_price = $closes[$n - 1];
    $latest_date = $prices[$n - 1]['price_date'];

    // SMA calculations
    $sma20  = fx_calc_sma($closes, 20);
    $sma50  = fx_calc_sma($closes, 50);
    $sma200 = fx_calc_sma($closes, 200);

    // Distance % from current price to each SMA
    $sma20_dist  = ($sma20 !== null && $sma20 != 0)  ? round(($current_price - $sma20)  / $sma20  * 100, 4) : null;
    $sma50_dist  = ($sma50 !== null && $sma50 != 0)  ? round(($current_price - $sma50)  / $sma50  * 100, 4) : null;
    $sma200_dist = ($sma200 !== null && $sma200 != 0) ? round(($current_price - $sma200) / $sma200 * 100, 4) : null;

    // RSI
    $rsi = fx_calc_rsi($closes, 14);

    // MACD (12, 26, 9)
    $macd = fx_calc_macd($closes, 12, 26, 9);

    // Bollinger Bands (20, 2)
    $bollinger = fx_calc_bollinger($closes, 20, 2);

    // Overall signal
    $signal = fx_determine_signal($current_price, $sma20, $sma50, $sma200, $rsi, $macd, $bollinger);

    // Percent change calculations
    $pct_1d = ($n >= 2 && $closes[$n - 2] != 0)
        ? round(($current_price - $closes[$n - 2]) / $closes[$n - 2] * 100, 4)
        : null;

    $pct_7d = null;
    if ($n >= 6) {
        $idx7 = $n - 6; // approx 5 trading days
        if ($closes[$idx7] != 0) {
            $pct_7d = round(($current_price - $closes[$idx7]) / $closes[$idx7] * 100, 4);
        }
    }

    return array(
        'symbol'        => str_replace('=X', '', strtoupper(trim($symbol))),
        'current_price' => round($current_price, 6),
        'latest_date'   => $latest_date,
        'data_points'   => $n,
        'pct_change_1d' => $pct_1d,
        'pct_change_7d' => $pct_7d,
        'sma' => array(
            'sma20'     => ($sma20 !== null) ? round($sma20, 6) : null,
            'sma20_distance_pct' => $sma20_dist,
            'sma50'     => ($sma50 !== null) ? round($sma50, 6) : null,
            'sma50_distance_pct' => $sma50_dist,
            'sma200'    => ($sma200 !== null) ? round($sma200, 6) : null,
            'sma200_distance_pct' => $sma200_dist
        ),
        'rsi' => array(
            'value'      => ($rsi !== null) ? round($rsi, 2) : null,
            'period'     => 14,
            'condition'  => fx_rsi_condition($rsi)
        ),
        'macd' => ($macd !== null) ? array(
            'macd_line'   => $macd['macd_line'],
            'signal_line' => $macd['signal_line'],
            'histogram'   => $macd['histogram'],
            'fast_period' => 12,
            'slow_period' => 26,
            'signal_period' => 9
        ) : null,
        'bollinger' => ($bollinger !== null) ? array(
            'upper'     => $bollinger['upper'],
            'middle'    => $bollinger['middle'],
            'lower'     => $bollinger['lower'],
            'bandwidth' => $bollinger['bandwidth'],
            'period'    => 20,
            'std_dev'   => 2
        ) : null,
        'signal' => $signal
    );
}

/**
 * Return human-readable RSI condition.
 */
function fx_rsi_condition($rsi) {
    if ($rsi === null) return 'insufficient_data';
    if ($rsi >= 80) return 'extremely_overbought';
    if ($rsi >= 70) return 'overbought';
    if ($rsi >= 60) return 'bullish';
    if ($rsi >= 40) return 'neutral';
    if ($rsi >= 30) return 'bearish';
    if ($rsi >= 20) return 'oversold';
    return 'extremely_oversold';
}

/**
 * Sort callback for recommendations by confidence DESC.
 */
function fx_sort_by_confidence($a, $b) {
    if ($a['confidence'] == $b['confidence']) return 0;
    return ($a['confidence'] > $b['confidence']) ? -1 : 1;
}

/**
 * Sort callback for movers by absolute pct change DESC.
 */
function fx_sort_by_abs_change($a, $b) {
    $aa = abs($a['pct_change_7d']);
    $bb = abs($b['pct_change_7d']);
    if ($aa == $bb) return 0;
    return ($aa > $bb) ? -1 : 1;
}

/**
 * Map overall signal to direction for recommendations.
 */
function fx_signal_to_direction($signal) {
    if ($signal === 'STRONG_BUY' || $signal === 'BUY') return 'BUY';
    if ($signal === 'STRONG_SELL' || $signal === 'SELL') return 'SELL';
    return 'HOLD';
}

/**
 * Calculate confidence from RSI and signal strength.
 */
function fx_calc_confidence($signal, $rsi, $macd, $sma20, $sma50, $current_price) {
    $conf = 50; // base

    // Signal strength
    if ($signal === 'STRONG_BUY' || $signal === 'STRONG_SELL') {
        $conf += 20;
    } elseif ($signal === 'BUY' || $signal === 'SELL') {
        $conf += 10;
    } else {
        $conf -= 10; // neutral = lower confidence
    }

    // RSI extremes add confidence
    if ($rsi !== null) {
        if ($rsi < 25 || $rsi > 75) $conf += 10;
        if ($rsi < 20 || $rsi > 80) $conf += 10;
    }

    // MACD histogram magnitude
    if ($macd !== null && $macd['histogram'] != 0) {
        $conf += 5;
    }

    // SMA alignment
    if ($sma20 !== null && $sma50 !== null) {
        $both_above = ($current_price > $sma20 && $current_price > $sma50);
        $both_below = ($current_price < $sma20 && $current_price < $sma50);
        if ($both_above || $both_below) $conf += 5;
    }

    // Clamp 0-100
    if ($conf < 0) $conf = 0;
    if ($conf > 100) $conf = 100;
    return $conf;
}

/**
 * Build a reason text for recommendation.
 */
function fx_build_reason($signal, $rsi, $macd, $sma20, $sma50, $current_price) {
    $parts = array();

    // Signal
    $parts[] = 'Overall signal: ' . $signal;

    // RSI
    if ($rsi !== null) {
        $parts[] = 'RSI(' . round($rsi, 1) . ') ' . fx_rsi_condition($rsi);
    }

    // MACD
    if ($macd !== null) {
        if ($macd['histogram'] > 0) {
            $parts[] = 'MACD histogram positive (bullish momentum)';
        } elseif ($macd['histogram'] < 0) {
            $parts[] = 'MACD histogram negative (bearish momentum)';
        }
    }

    // SMA position
    if ($sma20 !== null && $sma50 !== null) {
        if ($sma20 > $sma50) {
            $parts[] = 'SMA20 above SMA50 (bullish crossover)';
        } else {
            $parts[] = 'SMA20 below SMA50 (bearish crossover)';
        }
    }

    // Price vs SMAs
    if ($sma20 !== null) {
        if ($current_price > $sma20) {
            $parts[] = 'Price above SMA20';
        } else {
            $parts[] = 'Price below SMA20';
        }
    }

    return implode('. ', $parts);
}


// ============================================================
// ACTION: technical — single pair technical indicators
// ============================================================

if ($action === 'technical') {
    $symbol = isset($_GET['symbol']) ? trim($_GET['symbol']) : '';
    if ($symbol === '') {
        echo json_encode(array('ok' => false, 'error' => 'Missing symbol parameter. Example: ?action=technical&symbol=EURUSD=X'));
        $conn->close();
        exit;
    }

    // Check cache
    $cached = fx_cache_get('technical', $symbol);
    if ($cached !== null) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    $analysis = fx_analyze_symbol($conn, $symbol);
    if ($analysis === null) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Insufficient price data for ' . $symbol . '. Need at least 15 data points.',
            'symbol' => str_replace('=X', '', strtoupper(trim($symbol)))
        ));
        $conn->close();
        exit;
    }

    $result = array(
        'ok' => true,
        'action' => 'technical',
        'analysis' => $analysis,
        'calculated_at' => gmdate('Y-m-d\TH:i:s\Z')
    );

    fx_cache_set('technical', $symbol, $result);

    echo json_encode($result);
    $conn->close();
    exit;
}

// ============================================================
// ACTION: recommendations — aggregate buy/sell/hold for all pairs
// ============================================================

if ($action === 'recommendations') {
    // Check cache
    $cached = fx_cache_get('recommendations', 'all');
    if ($cached !== null) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    $pairs = fx_load_all_pairs($conn);
    $recommendations = array();

    foreach ($pairs as $pair) {
        $sym = $pair['symbol'];
        $analysis = fx_analyze_symbol($conn, $sym);
        if ($analysis === null) continue;

        $sig = $analysis['signal'];
        $rsi_val = ($analysis['rsi'] !== null && $analysis['rsi']['value'] !== null) ? $analysis['rsi']['value'] : null;
        $macd_data = $analysis['macd'];
        $sma20_val = ($analysis['sma']['sma20'] !== null) ? $analysis['sma']['sma20'] : null;
        $sma50_val = ($analysis['sma']['sma50'] !== null) ? $analysis['sma']['sma50'] : null;
        $cur = $analysis['current_price'];

        $direction = fx_signal_to_direction($sig);
        $confidence = fx_calc_confidence($sig, $rsi_val, $macd_data, $sma20_val, $sma50_val, $cur);
        $reason = fx_build_reason($sig, $rsi_val, $macd_data, $sma20_val, $sma50_val, $cur);

        // Kimi: ATR-based position sizing
        $prices_raw = fx_load_prices($conn, $sym);
        $atr_sizing = fx_atr_position_size($prices_raw, $cur, 10000);

        $recommendations[] = array(
            'symbol'        => $sym,
            'base_currency' => $pair['base_currency'],
            'quote_currency'=> $pair['quote_currency'],
            'category'      => $pair['category'],
            'current_price' => $cur,
            'direction'     => $direction,
            'signal'        => $sig,
            'confidence'    => $confidence,
            'reason'        => $reason,
            'rsi'           => ($rsi_val !== null) ? round($rsi_val, 2) : null,
            'position_sizing' => $atr_sizing,
            'calculated_at' => gmdate('Y-m-d\TH:i:s\Z')
        );
    }

    // Sort by confidence DESC using named function
    usort($recommendations, 'fx_sort_by_confidence');

    $result = array(
        'ok' => true,
        'action' => 'recommendations',
        'recommendations' => $recommendations,
        'count' => count($recommendations),
        'summary' => array(
            'buy_count'  => 0,
            'sell_count' => 0,
            'hold_count' => 0
        ),
        'calculated_at' => gmdate('Y-m-d\TH:i:s\Z')
    );

    // Tally summary
    foreach ($recommendations as $rec) {
        if ($rec['direction'] === 'BUY')  $result['summary']['buy_count']++;
        if ($rec['direction'] === 'SELL') $result['summary']['sell_count']++;
        if ($rec['direction'] === 'HOLD') $result['summary']['hold_count']++;
    }

    fx_cache_set('recommendations', 'all', $result);

    echo json_encode($result);
    $conn->close();
    exit;
}

// ============================================================
// ACTION: market_overview — forex market overview
// ============================================================

if ($action === 'market_overview') {
    // Check cache
    $cached = fx_cache_get('market_overview', 'all');
    if ($cached !== null) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    $pairs = fx_load_all_pairs($conn);
    $bullish_count = 0;
    $bearish_count = 0;
    $neutral_count = 0;
    $rsi_sum = 0;
    $rsi_count = 0;
    $overbought = array();
    $oversold = array();
    $movers = array();

    foreach ($pairs as $pair) {
        $sym = $pair['symbol'];
        $analysis = fx_analyze_symbol($conn, $sym);
        if ($analysis === null) continue;

        $sig = $analysis['signal'];
        if ($sig === 'STRONG_BUY' || $sig === 'BUY') {
            $bullish_count++;
        } elseif ($sig === 'STRONG_SELL' || $sig === 'SELL') {
            $bearish_count++;
        } else {
            $neutral_count++;
        }

        // RSI aggregation
        $rsi_val = ($analysis['rsi'] !== null && $analysis['rsi']['value'] !== null) ? $analysis['rsi']['value'] : null;
        if ($rsi_val !== null) {
            $rsi_sum += $rsi_val;
            $rsi_count++;

            if ($rsi_val >= 70) {
                $overbought[] = array(
                    'symbol' => $sym,
                    'rsi' => round($rsi_val, 2),
                    'signal' => $sig
                );
            }
            if ($rsi_val <= 30) {
                $oversold[] = array(
                    'symbol' => $sym,
                    'rsi' => round($rsi_val, 2),
                    'signal' => $sig
                );
            }
        }

        // 7-day movers
        if ($analysis['pct_change_7d'] !== null) {
            $movers[] = array(
                'symbol' => $sym,
                'pct_change_7d' => $analysis['pct_change_7d'],
                'current_price' => $analysis['current_price'],
                'signal' => $sig
            );
        }
    }

    // Sort movers by absolute change DESC using named function
    usort($movers, 'fx_sort_by_abs_change');

    // Take top 10 movers
    $top_movers = array();
    $mover_limit = count($movers) < 10 ? count($movers) : 10;
    for ($i = 0; $i < $mover_limit; $i++) {
        $top_movers[] = $movers[$i];
    }

    $avg_rsi = ($rsi_count > 0) ? round($rsi_sum / $rsi_count, 2) : null;
    $total_analyzed = $bullish_count + $bearish_count + $neutral_count;

    $result = array(
        'ok' => true,
        'action' => 'market_overview',
        'total_pairs_analyzed' => $total_analyzed,
        'sentiment' => array(
            'bullish' => $bullish_count,
            'bearish' => $bearish_count,
            'neutral' => $neutral_count,
            'bullish_pct' => ($total_analyzed > 0) ? round($bullish_count / $total_analyzed * 100, 1) : 0,
            'bearish_pct' => ($total_analyzed > 0) ? round($bearish_count / $total_analyzed * 100, 1) : 0,
            'neutral_pct' => ($total_analyzed > 0) ? round($neutral_count / $total_analyzed * 100, 1) : 0,
            'market_bias' => fx_market_bias($bullish_count, $bearish_count, $neutral_count)
        ),
        'rsi_overview' => array(
            'average_rsi' => $avg_rsi,
            'pairs_measured' => $rsi_count,
            'overbought_pairs' => $overbought,
            'overbought_count' => count($overbought),
            'oversold_pairs' => $oversold,
            'oversold_count' => count($oversold)
        ),
        'biggest_movers_7d' => $top_movers,
        'calculated_at' => gmdate('Y-m-d\TH:i:s\Z')
    );

    fx_cache_set('market_overview', 'all', $result);

    echo json_encode($result);
    $conn->close();
    exit;
}

/**
 * Determine overall market bias label.
 */
function fx_market_bias($bullish, $bearish, $neutral) {
    $total = $bullish + $bearish + $neutral;
    if ($total === 0) return 'no_data';
    $bull_pct = $bullish / $total * 100;
    $bear_pct = $bearish / $total * 100;
    if ($bull_pct >= 60) return 'strongly_bullish';
    if ($bull_pct >= 45) return 'mildly_bullish';
    if ($bear_pct >= 60) return 'strongly_bearish';
    if ($bear_pct >= 45) return 'mildly_bearish';
    return 'mixed';
}


// ============================================================
// ACTION: session_analysis — active trading sessions & pair recs
// ============================================================

if ($action === 'session_analysis') {
    // Check cache (5 min for session since it changes with time)
    $cached = fx_cache_get('session', 'current');
    if ($cached !== null) {
        // Session cache is shorter — check 5 min
        $cache_file = fx_cache_key('session', 'current');
        $cache_age = time() - filemtime($cache_file);
        if ($cache_age <= 300) {
            $cached['cached'] = true;
            echo json_encode($cached);
            $conn->close();
            exit;
        }
    }

    $utc_hour = (int)gmdate('G');
    $utc_minute = (int)gmdate('i');
    $utc_time_str = gmdate('H:i');
    $utc_day = (int)gmdate('w'); // 0=Sun, 6=Sat

    // Define sessions (UTC)
    $sessions = array(
        array(
            'name' => 'Sydney',
            'open_hour'  => 21,
            'close_hour' => 6,
            'wraps_midnight' => true,
            'major_pairs' => array('AUDUSD', 'NZDUSD', 'AUDJPY', 'NZDJPY'),
            'description' => 'Australian and New Zealand dollar pairs most active'
        ),
        array(
            'name' => 'Tokyo',
            'open_hour'  => 0,
            'close_hour' => 9,
            'wraps_midnight' => false,
            'major_pairs' => array('USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY'),
            'description' => 'Japanese yen pairs most active. Lower volatility session.'
        ),
        array(
            'name' => 'London',
            'open_hour'  => 8,
            'close_hour' => 17,
            'wraps_midnight' => false,
            'major_pairs' => array('EURUSD', 'GBPUSD', 'EURGBP', 'USDCHF', 'EURJPY'),
            'description' => 'Highest volume session. EUR and GBP pairs most active.'
        ),
        array(
            'name' => 'New York',
            'open_hour'  => 13,
            'close_hour' => 22,
            'wraps_midnight' => false,
            'major_pairs' => array('EURUSD', 'GBPUSD', 'USDCAD', 'USDJPY', 'USDCHF'),
            'description' => 'USD pairs most active. High liquidity during London overlap.'
        )
    );

    $active_sessions = array();
    $all_recommended_pairs = array();
    $overlaps = array();

    foreach ($sessions as $sess) {
        $is_active = false;
        if ($sess['wraps_midnight']) {
            // Session spans midnight: active if hour >= open OR hour < close
            if ($utc_hour >= $sess['open_hour'] || $utc_hour < $sess['close_hour']) {
                $is_active = true;
            }
        } else {
            if ($utc_hour >= $sess['open_hour'] && $utc_hour < $sess['close_hour']) {
                $is_active = true;
            }
        }

        $sess_info = array(
            'name'        => $sess['name'],
            'is_active'   => $is_active,
            'hours_utc'   => sprintf('%02d:00 - %02d:00 UTC', $sess['open_hour'], $sess['close_hour']),
            'major_pairs' => $sess['major_pairs'],
            'description' => $sess['description']
        );

        if ($is_active) {
            $active_sessions[] = $sess_info;
            foreach ($sess['major_pairs'] as $mp) {
                // Track which sessions recommend each pair
                if (!isset($all_recommended_pairs[$mp])) {
                    $all_recommended_pairs[$mp] = array();
                }
                $all_recommended_pairs[$mp][] = $sess['name'];
            }
        }
    }

    // Detect overlaps
    $active_names = array();
    foreach ($active_sessions as $as) {
        $active_names[] = $as['name'];
    }

    if (count($active_names) >= 2) {
        // Check known important overlaps
        $has_london = in_array('London', $active_names);
        $has_ny = in_array('New York', $active_names);
        $has_tokyo = in_array('Tokyo', $active_names);
        $has_sydney = in_array('Sydney', $active_names);

        if ($has_london && $has_ny) {
            $overlaps[] = array(
                'sessions' => 'London + New York',
                'hours_utc' => '13:00 - 17:00 UTC',
                'significance' => 'Highest liquidity period. Best for EUR/USD, GBP/USD. Tightest spreads.',
                'volatility' => 'high'
            );
        }
        if ($has_tokyo && $has_london) {
            $overlaps[] = array(
                'sessions' => 'Tokyo + London',
                'hours_utc' => '08:00 - 09:00 UTC',
                'significance' => 'Brief overlap. Good for EUR/JPY, GBP/JPY cross pairs.',
                'volatility' => 'medium'
            );
        }
        if ($has_sydney && $has_tokyo) {
            $overlaps[] = array(
                'sessions' => 'Sydney + Tokyo',
                'hours_utc' => '00:00 - 06:00 UTC',
                'significance' => 'Asia-Pacific session. AUD/JPY, NZD/JPY active.',
                'volatility' => 'low-medium'
            );
        }
    }

    // Build recommended pairs with session context
    $pair_recs = array();
    foreach ($all_recommended_pairs as $sym => $sess_names) {
        $pair_recs[] = array(
            'symbol' => $sym,
            'recommended_by_sessions' => $sess_names,
            'session_count' => count($sess_names),
            'note' => (count($sess_names) > 1)
                ? $sym . ' active in multiple sessions (' . implode(', ', $sess_names) . ') — higher liquidity'
                : $sym . ' primarily active in ' . $sess_names[0] . ' session'
        );
    }

    // Weekend check
    $is_weekend = ($utc_day === 0 || $utc_day === 6);

    $result = array(
        'ok' => true,
        'action' => 'session_analysis',
        'current_utc_time' => gmdate('Y-m-d H:i:s') . ' UTC',
        'utc_hour' => $utc_hour,
        'is_weekend' => $is_weekend,
        'weekend_note' => $is_weekend ? 'Forex markets are closed on weekends (Sat-Sun). Sessions shown are for reference.' : null,
        'active_sessions' => $active_sessions,
        'active_session_count' => count($active_sessions),
        'overlaps' => $overlaps,
        'recommended_pairs' => $pair_recs,
        'all_sessions' => array(
            array('name' => 'Sydney',   'hours_utc' => '21:00 - 06:00 UTC', 'note' => 'Wraps midnight'),
            array('name' => 'Tokyo',    'hours_utc' => '00:00 - 09:00 UTC', 'note' => 'Asia session'),
            array('name' => 'London',   'hours_utc' => '08:00 - 17:00 UTC', 'note' => 'Highest volume'),
            array('name' => 'New York', 'hours_utc' => '13:00 - 22:00 UTC', 'note' => 'Americas session')
        ),
        'trading_tips' => array(
            'London-NY overlap (13:00-17:00 UTC) has the highest liquidity and tightest spreads.',
            'Avoid trading during low-liquidity gaps (22:00-00:00 UTC) as spreads widen.',
            'Major news releases (NFP, ECB, BOJ) cause volatility spikes — check economic calendar.',
            'EUR pairs are most active during London session, JPY pairs during Tokyo.'
        ),
        'calculated_at' => gmdate('Y-m-d\TH:i:s\Z')
    );

    fx_cache_set('session', 'current', $result);

    echo json_encode($result);
    $conn->close();
    exit;
}

// ============================================================
// Unknown action fallback
// ============================================================

echo json_encode(array(
    'ok' => false,
    'error' => 'Unknown action: ' . $action . '. Use: technical, recommendations, market_overview, session_analysis'
));
$conn->close();
?>
