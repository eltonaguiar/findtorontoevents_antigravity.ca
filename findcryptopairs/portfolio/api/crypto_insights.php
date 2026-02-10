<?php
/**
 * Crypto Insights API — analyst recommendations & technical analysis
 * Calculates TA indicators from cr_price_history data.
 * PHP 5.2 compatible — no short arrays, no http_response_code(), no spread operator.
 *
 * Actions:
 *   ?action=technical&symbol=BTC-USD   — Technical indicators for one pair
 *   ?action=recommendations             — Buy/sell recommendations for all pairs
 *   ?action=market_overview              — Market-wide stats & movers
 *   ?action=fear_greed                   — Fear & Greed index from available data
 *
 * All data sourced from cr_price_history (no web scraping).
 * Results cached 30 minutes in /tmp/cr_insights_*.json
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : '';

if ($action === '') {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Missing action parameter. Use: technical, recommendations, market_overview, fear_greed'
    ));
    $conn->close();
    exit;
}

// ─── Cache helpers ──────────────────────────────────────────────────────────

function cr_cache_key($action, $extra) {
    return '/tmp/cr_insights_' . $action . '_' . md5($extra) . '.json';
}

function cr_cache_get($path, $ttl_seconds) {
    if (!file_exists($path)) return false;
    $age = time() - filemtime($path);
    if ($age > $ttl_seconds) return false;
    $raw = file_get_contents($path);
    if ($raw === false) return false;
    $data = json_decode($raw, true);
    if (!is_array($data)) return false;
    return $data;
}

function cr_cache_set($path, $data) {
    $json = json_encode($data);
    @file_put_contents($path, $json);
}

// ─── Price data loader ──────────────────────────────────────────────────────

/**
 * Load closing prices for a symbol ordered by date ASC.
 * Returns array of array('price_date' => ..., 'close' => ..., 'high' => ..., 'low' => ..., 'open' => ..., 'volume' => ...)
 */
function cr_load_prices($conn, $symbol, $limit) {
    $safe = $conn->real_escape_string($symbol);
    $lim = (int)$limit;
    $sql = "SELECT price_date, open, high, low, close, volume
            FROM cr_price_history
            WHERE symbol = '$safe'
            ORDER BY price_date DESC
            LIMIT $lim";
    $res = $conn->query($sql);
    $rows = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $rows[] = $row;
        }
    }
    // Reverse to ASC order (oldest first) for indicator calculations
    $rows = array_reverse($rows);
    return $rows;
}

/**
 * Extract closing prices as float array from rows.
 */
function cr_extract_closes($rows) {
    $closes = array();
    foreach ($rows as $r) {
        $closes[] = (float)$r['close'];
    }
    return $closes;
}

// ─── Technical indicator functions ──────────────────────────────────────────

/**
 * Simple Moving Average over the last $period values.
 * Returns null if not enough data.
 */
function cr_sma($values, $period) {
    $count = count($values);
    if ($count < $period || $period < 1) return null;
    $sum = 0;
    for ($i = $count - $period; $i < $count; $i++) {
        $sum += $values[$i];
    }
    return $sum / $period;
}

/**
 * Full SMA series (for Bollinger Bands / MACD).
 * Returns array with same length as $values; entries before $period are null.
 */
function cr_sma_series($values, $period) {
    $count = count($values);
    $result = array();
    if ($period < 1) {
        for ($i = 0; $i < $count; $i++) $result[] = null;
        return $result;
    }
    $sum = 0;
    for ($i = 0; $i < $count; $i++) {
        $sum += $values[$i];
        if ($i < $period - 1) {
            $result[] = null;
        } else {
            if ($i >= $period) {
                $sum -= $values[$i - $period];
            }
            $result[] = $sum / $period;
        }
    }
    return $result;
}

/**
 * Exponential Moving Average series.
 * Returns array with same length; entries before $period are null, then EMA starts.
 */
function cr_ema_series($values, $period) {
    $count = count($values);
    $result = array();
    if ($count < $period || $period < 1) {
        for ($i = 0; $i < $count; $i++) $result[] = null;
        return $result;
    }
    $multiplier = 2.0 / ($period + 1);
    // Seed EMA with SMA of first $period values
    $sum = 0;
    for ($i = 0; $i < $period; $i++) {
        $sum += $values[$i];
        $result[] = null;
    }
    $ema = $sum / $period;
    $result[$period - 1] = $ema;

    for ($i = $period; $i < $count; $i++) {
        $ema = ($values[$i] - $ema) * $multiplier + $ema;
        $result[] = $ema;
    }
    return $result;
}

/**
 * RSI (Relative Strength Index) using Wilder smoothing.
 * Returns the current RSI value or null if not enough data.
 */
function cr_rsi($closes, $period) {
    $count = count($closes);
    if ($count < $period + 1) return null;

    // Calculate initial gains and losses
    $gains = array();
    $losses = array();
    for ($i = 1; $i < $count; $i++) {
        $change = $closes[$i] - $closes[$i - 1];
        if ($change > 0) {
            $gains[] = $change;
            $losses[] = 0;
        } else {
            $gains[] = 0;
            $losses[] = abs($change);
        }
    }

    // First average using simple average
    $avg_gain = 0;
    $avg_loss = 0;
    for ($i = 0; $i < $period; $i++) {
        $avg_gain += $gains[$i];
        $avg_loss += $losses[$i];
    }
    $avg_gain = $avg_gain / $period;
    $avg_loss = $avg_loss / $period;

    // Wilder smoothing for remaining periods
    $gl_count = count($gains);
    for ($i = $period; $i < $gl_count; $i++) {
        $avg_gain = ($avg_gain * ($period - 1) + $gains[$i]) / $period;
        $avg_loss = ($avg_loss * ($period - 1) + $losses[$i]) / $period;
    }

    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

/**
 * MACD (12, 26, 9): returns array('macd' => ..., 'signal' => ..., 'histogram' => ...)
 * or null if not enough data.
 */
function cr_macd($closes) {
    $count = count($closes);
    if ($count < 35) return null; // Need at least 26 + 9 = 35 for meaningful MACD

    $ema12 = cr_ema_series($closes, 12);
    $ema26 = cr_ema_series($closes, 26);

    // MACD line = EMA12 - EMA26
    $macd_line = array();
    for ($i = 0; $i < $count; $i++) {
        if ($ema12[$i] === null || $ema26[$i] === null) {
            $macd_line[] = null;
        } else {
            $macd_line[] = $ema12[$i] - $ema26[$i];
        }
    }

    // Signal line = EMA(9) of MACD line (skip nulls)
    $macd_valid = array();
    $macd_valid_start = -1;
    for ($i = 0; $i < $count; $i++) {
        if ($macd_line[$i] !== null) {
            if ($macd_valid_start < 0) $macd_valid_start = $i;
            $macd_valid[] = $macd_line[$i];
        }
    }

    if (count($macd_valid) < 9) return null;

    $signal_series = cr_ema_series($macd_valid, 9);
    $signal_count = count($signal_series);

    // Get the latest values
    $latest_macd = $macd_valid[$signal_count - 1];
    $latest_signal = $signal_series[$signal_count - 1];
    if ($latest_signal === null) return null;
    $histogram = $latest_macd - $latest_signal;

    return array(
        'macd' => round($latest_macd, 8),
        'signal' => round($latest_signal, 8),
        'histogram' => round($histogram, 8)
    );
}

/**
 * Bollinger Bands (20, 2 sigma).
 * Returns array('upper' => ..., 'middle' => ..., 'lower' => ..., 'bandwidth' => ...) or null.
 */
function cr_bollinger($closes, $period, $std_dev_mult) {
    $count = count($closes);
    if ($count < $period) return null;

    // Middle = SMA(period)
    $middle = cr_sma($closes, $period);
    if ($middle === null) return null;

    // Standard deviation of last $period values
    $sum_sq = 0;
    for ($i = $count - $period; $i < $count; $i++) {
        $diff = $closes[$i] - $middle;
        $sum_sq += $diff * $diff;
    }
    $std_dev = sqrt($sum_sq / $period);

    $upper = $middle + ($std_dev_mult * $std_dev);
    $lower = $middle - ($std_dev_mult * $std_dev);
    $bandwidth = ($middle > 0) ? (($upper - $lower) / $middle) * 100 : 0;

    return array(
        'upper' => round($upper, 8),
        'middle' => round($middle, 8),
        'lower' => round($lower, 8),
        'bandwidth' => round($bandwidth, 4)
    );
}

/**
 * Determine overall signal from indicators.
 * Returns: STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
 */
function cr_overall_signal($last_close, $sma20, $sma50, $sma200, $rsi, $macd_data, $bollinger) {
    $score = 0; // -5 to +5 scale
    $reasons = array();

    // SMA signals
    if ($sma20 !== null && $last_close > $sma20) {
        $score += 1;
        $reasons[] = 'Price above SMA20';
    } elseif ($sma20 !== null) {
        $score -= 1;
        $reasons[] = 'Price below SMA20';
    }

    if ($sma50 !== null && $last_close > $sma50) {
        $score += 1;
        $reasons[] = 'Price above SMA50';
    } elseif ($sma50 !== null) {
        $score -= 1;
        $reasons[] = 'Price below SMA50';
    }

    if ($sma200 !== null && $last_close > $sma200) {
        $score += 1;
        $reasons[] = 'Price above SMA200 (long-term bullish)';
    } elseif ($sma200 !== null) {
        $score -= 1;
        $reasons[] = 'Price below SMA200 (long-term bearish)';
    }

    // SMA crossover: golden cross / death cross
    if ($sma50 !== null && $sma200 !== null) {
        if ($sma50 > $sma200) {
            $score += 1;
            $reasons[] = 'Golden cross (SMA50 > SMA200)';
        } else {
            $score -= 1;
            $reasons[] = 'Death cross (SMA50 < SMA200)';
        }
    }

    // RSI
    if ($rsi !== null) {
        if ($rsi < 30) {
            $score += 2;
            $reasons[] = 'RSI oversold (' . round($rsi, 1) . ')';
        } elseif ($rsi < 40) {
            $score += 1;
            $reasons[] = 'RSI approaching oversold (' . round($rsi, 1) . ')';
        } elseif ($rsi > 70) {
            $score -= 2;
            $reasons[] = 'RSI overbought (' . round($rsi, 1) . ')';
        } elseif ($rsi > 60) {
            $score -= 1;
            $reasons[] = 'RSI approaching overbought (' . round($rsi, 1) . ')';
        }
    }

    // MACD
    if ($macd_data !== null) {
        if ($macd_data['histogram'] > 0) {
            $score += 1;
            $reasons[] = 'MACD histogram positive (bullish momentum)';
        } else {
            $score -= 1;
            $reasons[] = 'MACD histogram negative (bearish momentum)';
        }
    }

    // Bollinger Bands
    if ($bollinger !== null) {
        if ($last_close <= $bollinger['lower']) {
            $score += 1;
            $reasons[] = 'Price at/below lower Bollinger Band (potential bounce)';
        } elseif ($last_close >= $bollinger['upper']) {
            $score -= 1;
            $reasons[] = 'Price at/above upper Bollinger Band (potential pullback)';
        }
    }

    // Map score to signal
    if ($score >= 4) {
        $signal = 'STRONG_BUY';
    } elseif ($score >= 2) {
        $signal = 'BUY';
    } elseif ($score <= -4) {
        $signal = 'STRONG_SELL';
    } elseif ($score <= -2) {
        $signal = 'SELL';
    } else {
        $signal = 'NEUTRAL';
    }

    return array(
        'signal' => $signal,
        'score' => $score,
        'reasons' => $reasons
    );
}

/**
 * Compute full technical analysis for one symbol.
 * Returns associative array with all indicators, or null on error.
 */
function cr_compute_technicals($conn, $symbol) {
    $rows = cr_load_prices($conn, $symbol, 250);
    $closes = cr_extract_closes($rows);
    $count = count($closes);

    if ($count < 2) {
        return null;
    }

    $last_close = $closes[$count - 1];
    $sma20  = cr_sma($closes, 20);
    $sma50  = cr_sma($closes, 50);
    $sma200 = cr_sma($closes, 200);
    $rsi    = cr_rsi($closes, 14);
    $macd_data = cr_macd($closes);
    $bollinger = cr_bollinger($closes, 20, 2);
    $signal_data = cr_overall_signal($last_close, $sma20, $sma50, $sma200, $rsi, $macd_data, $bollinger);

    // Percentage distance from SMAs
    $sma20_dist  = ($sma20  !== null && $sma20  > 0) ? round(($last_close - $sma20)  / $sma20  * 100, 2) : null;
    $sma50_dist  = ($sma50  !== null && $sma50  > 0) ? round(($last_close - $sma50)  / $sma50  * 100, 2) : null;
    $sma200_dist = ($sma200 !== null && $sma200 > 0) ? round(($last_close - $sma200) / $sma200 * 100, 2) : null;

    $result = array(
        'symbol' => $symbol,
        'last_close' => $last_close,
        'data_points' => $count,
        'last_date' => (count($rows) > 0) ? $rows[$count - 1]['price_date'] : null,
        'sma' => array(
            'sma20'  => ($sma20  !== null) ? round($sma20,  8) : null,
            'sma50'  => ($sma50  !== null) ? round($sma50,  8) : null,
            'sma200' => ($sma200 !== null) ? round($sma200, 8) : null,
            'sma20_distance_pct'  => $sma20_dist,
            'sma50_distance_pct'  => $sma50_dist,
            'sma200_distance_pct' => $sma200_dist
        ),
        'rsi' => array(
            'value'  => ($rsi !== null) ? round($rsi, 2) : null,
            'period' => 14,
            'zone'   => ($rsi === null) ? 'unknown'
                        : (($rsi > 70) ? 'overbought'
                        : (($rsi < 30) ? 'oversold' : 'neutral'))
        ),
        'macd' => ($macd_data !== null) ? $macd_data : array('macd' => null, 'signal' => null, 'histogram' => null),
        'bollinger' => ($bollinger !== null) ? $bollinger : array('upper' => null, 'middle' => null, 'lower' => null, 'bandwidth' => null),
        'overall' => array(
            'signal'  => $signal_data['signal'],
            'score'   => $signal_data['score'],
            'reasons' => $signal_data['reasons']
        ),
        'calculated_at' => date('Y-m-d H:i:s')
    );

    return $result;
}

// ─── Percentage change helper ───────────────────────────────────────────────

function cr_pct_change($old, $new) {
    if ($old == 0) return 0;
    return (($new - $old) / abs($old)) * 100;
}

// ─── ACTION HANDLERS ────────────────────────────────────────────────────────

// ==========================================================================
// action=technical — Single pair technical analysis
// ==========================================================================
if ($action === 'technical') {

    $symbol = isset($_GET['symbol']) ? trim(strtoupper($_GET['symbol'])) : '';
    if ($symbol === '') {
        echo json_encode(array('ok' => false, 'error' => 'Missing symbol parameter. Example: ?action=technical&symbol=BTC-USD'));
        $conn->close();
        exit;
    }

    // Check cache
    $cache_path = cr_cache_key('technical', $symbol);
    $cached = cr_cache_get($cache_path, 1800);
    if ($cached !== false) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Verify symbol exists
    $safe_sym = $conn->real_escape_string($symbol);
    $chk = $conn->query("SELECT symbol, pair_name, category FROM cr_pairs WHERE symbol = '$safe_sym'");
    if (!$chk || $chk->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Symbol not found in cr_pairs: ' . $symbol));
        $conn->close();
        exit;
    }
    $pair_info = $chk->fetch_assoc();

    $tech = cr_compute_technicals($conn, $symbol);
    if ($tech === null) {
        echo json_encode(array('ok' => false, 'error' => 'Not enough price data for ' . $symbol . ' to calculate indicators'));
        $conn->close();
        exit;
    }

    $tech['pair_name'] = $pair_info['pair_name'];
    $tech['category'] = $pair_info['category'];

    $response = array(
        'ok' => true,
        'action' => 'technical',
        'data' => $tech,
        'cached' => false
    );

    cr_cache_set($cache_path, $response);
    echo json_encode($response);

// ==========================================================================
// action=recommendations — Aggregated buy/sell recs for all pairs
// ==========================================================================
} elseif ($action === 'recommendations') {

    $cache_path = cr_cache_key('recommendations', 'all');
    $cached = cr_cache_get($cache_path, 1800);
    if ($cached !== false) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Load all pairs
    $res = $conn->query("SELECT symbol, pair_name, category FROM cr_pairs ORDER BY symbol");
    $pairs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $pairs[] = $row;
        }
    }

    $recommendations = array();
    foreach ($pairs as $pair) {
        $tech = cr_compute_technicals($conn, $pair['symbol']);
        if ($tech === null) continue;

        $signal = $tech['overall']['signal'];
        $score  = $tech['overall']['score'];

        // Map signal to direction
        if ($signal === 'STRONG_BUY' || $signal === 'BUY') {
            $direction = 'BUY';
        } elseif ($signal === 'STRONG_SELL' || $signal === 'SELL') {
            $direction = 'SELL';
        } else {
            $direction = 'HOLD';
        }

        // Map score to confidence (0-100)
        // Score range is roughly -8 to +8; map abs(score) to confidence
        $abs_score = abs($score);
        if ($abs_score >= 6) {
            $confidence = 95;
        } elseif ($abs_score >= 4) {
            $confidence = 80;
        } elseif ($abs_score >= 3) {
            $confidence = 65;
        } elseif ($abs_score >= 2) {
            $confidence = 50;
        } elseif ($abs_score >= 1) {
            $confidence = 35;
        } else {
            $confidence = 20;
        }

        // Build reason text
        $reason_parts = array();
        $rsi_val = $tech['rsi']['value'];
        if ($rsi_val !== null) {
            $reason_parts[] = 'RSI=' . round($rsi_val, 1);
        }
        $sma50_val = $tech['sma']['sma50'];
        if ($sma50_val !== null) {
            if ($tech['last_close'] > $sma50_val) {
                $reason_parts[] = 'above SMA50';
            } else {
                $reason_parts[] = 'below SMA50';
            }
        }
        if ($tech['macd']['histogram'] !== null) {
            $reason_parts[] = 'MACD hist=' . $tech['macd']['histogram'];
        }
        $top_reasons = array_slice($tech['overall']['reasons'], 0, 3);
        foreach ($top_reasons as $r) {
            $reason_parts[] = $r;
        }
        $reason = implode('; ', $reason_parts);

        $recommendations[] = array(
            'symbol'        => $pair['symbol'],
            'pair_name'     => $pair['pair_name'],
            'category'      => $pair['category'],
            'direction'     => $direction,
            'signal'        => $signal,
            'confidence'    => $confidence,
            'score'         => $score,
            'rsi'           => ($rsi_val !== null) ? round($rsi_val, 2) : null,
            'reason'        => $reason,
            'calculated_at' => date('Y-m-d H:i:s')
        );
    }

    // Sort by confidence DESC
    // PHP 5.2 compatible usort
    usort($recommendations, 'cr_sort_by_confidence');

    $response = array(
        'ok' => true,
        'action' => 'recommendations',
        'recommendations' => $recommendations,
        'count' => count($recommendations),
        'cached' => false,
        'calculated_at' => date('Y-m-d H:i:s')
    );

    cr_cache_set($cache_path, $response);
    echo json_encode($response);

// ==========================================================================
// action=market_overview — Bullish/bearish breakdown, movers, overbought/oversold
// ==========================================================================
} elseif ($action === 'market_overview') {

    $cache_path = cr_cache_key('market_overview', 'all');
    $cached = cr_cache_get($cache_path, 1800);
    if ($cached !== false) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    $res = $conn->query("SELECT symbol, pair_name, category FROM cr_pairs ORDER BY symbol");
    $pairs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $pairs[] = $row;
        }
    }

    $bullish = array();
    $bearish = array();
    $neutral_pairs = array();
    $overbought = array();
    $oversold = array();
    $rsi_sum = 0;
    $rsi_count = 0;
    $movers = array();

    foreach ($pairs as $pair) {
        $sym = $pair['symbol'];
        $rows = cr_load_prices($conn, $sym, 250);
        $closes = cr_extract_closes($rows);
        $count = count($closes);
        if ($count < 2) continue;

        $last_close = $closes[$count - 1];
        $rsi = cr_rsi($closes, 14);
        $sma50 = cr_sma($closes, 50);

        // Bullish vs bearish: RSI < 70 AND price > SMA50
        if ($rsi !== null && $sma50 !== null) {
            if ($rsi < 70 && $last_close > $sma50) {
                $bullish[] = $sym;
            } elseif ($rsi > 30 && $last_close < $sma50) {
                $bearish[] = $sym;
            } else {
                $neutral_pairs[] = $sym;
            }
        }

        // RSI tracking
        if ($rsi !== null) {
            $rsi_sum += $rsi;
            $rsi_count++;
            if ($rsi > 70) {
                $overbought[] = array('symbol' => $sym, 'rsi' => round($rsi, 2));
            }
            if ($rsi < 30) {
                $oversold[] = array('symbol' => $sym, 'rsi' => round($rsi, 2));
            }
        }

        // 7-day movers: find close 7 days ago
        if ($count >= 8) {
            $close_7d_ago = $closes[$count - 8];
            $pct = cr_pct_change($close_7d_ago, $last_close);
            $movers[] = array(
                'symbol' => $sym,
                'pair_name' => $pair['pair_name'],
                'close_now' => $last_close,
                'close_7d_ago' => $close_7d_ago,
                'change_pct' => round($pct, 2)
            );
        }
    }

    // Sort movers by absolute change DESC
    usort($movers, 'cr_sort_by_abs_change');
    // Keep top 10 movers
    $movers = array_slice($movers, 0, 10);

    $avg_rsi = ($rsi_count > 0) ? round($rsi_sum / $rsi_count, 2) : null;

    $response = array(
        'ok' => true,
        'action' => 'market_overview',
        'summary' => array(
            'total_pairs_analyzed' => count($pairs),
            'bullish_count' => count($bullish),
            'bearish_count' => count($bearish),
            'neutral_count' => count($neutral_pairs),
            'avg_rsi' => $avg_rsi
        ),
        'bullish_pairs' => $bullish,
        'bearish_pairs' => $bearish,
        'overbought' => $overbought,
        'oversold' => $oversold,
        'biggest_movers_7d' => $movers,
        'cached' => false,
        'calculated_at' => date('Y-m-d H:i:s')
    );

    cr_cache_set($cache_path, $response);
    echo json_encode($response);

// ==========================================================================
// action=fear_greed — Fear & Greed index from internal data
// ==========================================================================
} elseif ($action === 'fear_greed') {

    $cache_path = cr_cache_key('fear_greed', 'all');
    $cached = cr_cache_get($cache_path, 1800);
    if ($cached !== false) {
        $cached['cached'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    $res = $conn->query("SELECT symbol FROM cr_pairs ORDER BY symbol");
    $symbols = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $symbols[] = $row['symbol'];
        }
    }

    $total_pairs = count($symbols);
    if ($total_pairs === 0) {
        echo json_encode(array(
            'ok' => true,
            'action' => 'fear_greed',
            'score' => 50,
            'label' => 'Neutral',
            'factors' => array(),
            'note' => 'No pairs available for analysis',
            'cached' => false,
            'calculated_at' => date('Y-m-d H:i:s')
        ));
        $conn->close();
        exit;
    }

    // Factor 1: % of pairs above SMA200
    $above_sma200 = 0;
    $sma200_eligible = 0;
    // Factor 2: Average RSI
    $rsi_sum = 0;
    $rsi_count = 0;
    // Factor 3: Recent volatility (avg of 7-day % change absolute values)
    $vol_sum = 0;
    $vol_count = 0;

    foreach ($symbols as $sym) {
        $rows = cr_load_prices($conn, $sym, 250);
        $closes = cr_extract_closes($rows);
        $count = count($closes);
        if ($count < 2) continue;

        $last_close = $closes[$count - 1];

        // SMA200
        $sma200 = cr_sma($closes, 200);
        if ($sma200 !== null) {
            $sma200_eligible++;
            if ($last_close > $sma200) {
                $above_sma200++;
            }
        }

        // RSI
        $rsi = cr_rsi($closes, 14);
        if ($rsi !== null) {
            $rsi_sum += $rsi;
            $rsi_count++;
        }

        // 7-day volatility
        if ($count >= 8) {
            $close_7d_ago = $closes[$count - 8];
            $pct = cr_pct_change($close_7d_ago, $last_close);
            $vol_sum += abs($pct);
            $vol_count++;
        }
    }

    // Calculate factor scores (each 0-100)
    $factors = array();

    // Factor 1: SMA200 breadth — more above = more greedy
    // 0% above = 0 (extreme fear), 100% above = 100 (extreme greed)
    if ($sma200_eligible > 0) {
        $sma200_pct = ($above_sma200 / $sma200_eligible) * 100;
        $factor1_score = round($sma200_pct);
    } else {
        $sma200_pct = 50;
        $factor1_score = 50;
    }
    $factors[] = array(
        'name' => 'SMA200 Breadth',
        'description' => round($sma200_pct, 1) . '% of pairs above SMA200 (' . $above_sma200 . '/' . $sma200_eligible . ')',
        'score' => $factor1_score,
        'weight' => 40
    );

    // Factor 2: Avg RSI — map 0-100 RSI to fear/greed
    // RSI 30 => fear (20), RSI 50 => neutral (50), RSI 70 => greed (80)
    if ($rsi_count > 0) {
        $avg_rsi = $rsi_sum / $rsi_count;
        // Linear mapping: RSI 20->10, 30->25, 50->50, 70->75, 80->90
        $factor2_score = round($avg_rsi);
    } else {
        $avg_rsi = 50;
        $factor2_score = 50;
    }
    $factors[] = array(
        'name' => 'Average RSI',
        'description' => 'Average RSI across ' . $rsi_count . ' pairs: ' . round($avg_rsi, 1),
        'score' => $factor2_score,
        'weight' => 35
    );

    // Factor 3: Volatility — high volatility = more fear
    // Map: 0% vol = 50 (neutral), 5% = 40, 10% = 30, 20%+ = 10 (fear)
    //       Note: low volatility in crypto is actually somewhat neutral
    if ($vol_count > 0) {
        $avg_vol = $vol_sum / $vol_count;
        // Invert: high volatility = low score (fear)
        // Clamp to 0-30% range, map to 100-0
        $clamped_vol = min(30, max(0, $avg_vol));
        $factor3_score = round(100 - ($clamped_vol / 30 * 100));
        $factor3_score = max(0, min(100, $factor3_score));
    } else {
        $avg_vol = 0;
        $factor3_score = 50;
    }
    $factors[] = array(
        'name' => 'Volatility (7d)',
        'description' => 'Avg 7-day absolute change: ' . round($avg_vol, 2) . '% across ' . $vol_count . ' pairs',
        'score' => $factor3_score,
        'weight' => 25
    );

    // Weighted composite score
    $total_weight = 0;
    $weighted_sum = 0;
    foreach ($factors as $f) {
        $weighted_sum += $f['score'] * $f['weight'];
        $total_weight += $f['weight'];
    }
    $composite = ($total_weight > 0) ? round($weighted_sum / $total_weight) : 50;
    $composite = max(0, min(100, $composite));

    // Label
    if ($composite <= 20) {
        $label = 'Extreme Fear';
    } elseif ($composite <= 40) {
        $label = 'Fear';
    } elseif ($composite <= 60) {
        $label = 'Neutral';
    } elseif ($composite <= 80) {
        $label = 'Greed';
    } else {
        $label = 'Extreme Greed';
    }

    $response = array(
        'ok' => true,
        'action' => 'fear_greed',
        'score' => $composite,
        'label' => $label,
        'factors' => $factors,
        'cached' => false,
        'calculated_at' => date('Y-m-d H:i:s')
    );

    cr_cache_set($cache_path, $response);
    echo json_encode($response);

// ==========================================================================
// Unknown action
// ==========================================================================
} else {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Unknown action: ' . $action . '. Use: technical, recommendations, market_overview, fear_greed'
    ));
}

// ─── Sort callbacks (PHP 5.2 requires named functions for usort) ────────

function cr_sort_by_confidence($a, $b) {
    if ($a['confidence'] == $b['confidence']) return 0;
    return ($a['confidence'] > $b['confidence']) ? -1 : 1;
}

function cr_sort_by_abs_change($a, $b) {
    $aa = abs($a['change_pct']);
    $bb = abs($b['change_pct']);
    if ($aa == $bb) return 0;
    return ($aa > $bb) ? -1 : 1;
}

$conn->close();
?>
