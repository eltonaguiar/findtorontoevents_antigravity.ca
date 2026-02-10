<?php
/**
 * Crypto Winner Scanner — finds high-probability momentum plays
 * Uses Crypto.com Exchange public API (no auth needed, 100 req/sec)
 *
 * Actions:
 *   scan          — scan all pairs, score, return top winners (key required)
 *   winners       — get latest cached winners (public)
 *   history       — get past scans + outcomes (public)
 *   resolve       — check if past winners actually went up (key required)
 *   leaderboard   — best patterns by win rate (public)
 *   stats         — overall scanner stats (public)
 *   scan_log      — full analysis log with all indicators (public)
 *
 * PHP 5.2 compatible. No short arrays, no http_response_code().
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_config.php';
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'winners';
$key    = isset($_GET['key']) ? $_GET['key'] : '';
$ADMIN_KEY = 'cryptoscan2026';

// ── Schema (auto-create) ────────────────────────────────────────────
_cw_ensure_schema($conn);

// ── Route ────────────────────────────────────────────────────────────
switch ($action) {
    case 'scan':
        if ($key !== $ADMIN_KEY) { _cw_err('Unauthorized'); }
        _cw_action_scan($conn);
        break;
    case 'winners':
        _cw_action_winners($conn);
        break;
    case 'history':
        _cw_action_history($conn);
        break;
    case 'resolve':
        if ($key !== $ADMIN_KEY) { _cw_err('Unauthorized'); }
        _cw_action_resolve($conn);
        break;
    case 'leaderboard':
        _cw_action_leaderboard($conn);
        break;
    case 'stats':
        _cw_action_stats($conn);
        break;
    case 'scan_log':
        _cw_action_scan_log($conn);
        break;
    default:
        _cw_err('Unknown action: ' . $action);
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN — the main engine
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_scan($conn) {
    $start = microtime(true);

    // 1. Get all instruments from Crypto.com
    $instruments = _cw_api('public/get-instruments');
    if (!$instruments || !isset($instruments['result']['data'])) {
        _cw_err('Failed to fetch instruments from Crypto.com');
    }

    // Filter to CCY_PAIR USDT pairs only (most liquid, easiest to trade)
    // Crypto.com uses 'symbol' field and 'CCY_PAIR' inst_type for spot
    $pairs = array();
    foreach ($instruments['result']['data'] as $inst) {
        $sym = isset($inst['symbol']) ? $inst['symbol'] : (isset($inst['instrument_name']) ? $inst['instrument_name'] : '');
        $itype = isset($inst['inst_type']) ? $inst['inst_type'] : '';
        if ($itype === 'CCY_PAIR' && _cw_ends_with($sym, '_USDT')) {
            $pairs[] = $sym;
        }
    }

    // 2. Get all tickers in one call
    $tickers_raw = _cw_api('public/get-tickers');
    if (!$tickers_raw || !isset($tickers_raw['result']['data'])) {
        _cw_err('Failed to fetch tickers');
    }

    // Index tickers by symbol (Crypto.com uses 'i' for instrument_name in tickers)
    $tickers = array();
    foreach ($tickers_raw['result']['data'] as $t) {
        $key = isset($t['i']) ? $t['i'] : (isset($t['symbol']) ? $t['symbol'] : '');
        if ($key) $tickers[$key] = $t;
    }

    // 3. Pre-filter: only pairs with decent volume and positive movement
    $candidates = array();
    foreach ($pairs as $pair) {
        if (!isset($tickers[$pair])) continue;
        $t = $tickers[$pair];

        $price  = isset($t['a']) ? floatval($t['a']) : 0; // last trade price
        $vol24  = isset($t['v']) ? floatval($t['v']) : 0; // 24h volume (in base)
        $volUsd = isset($t['vv']) ? floatval($t['vv']) : ($vol24 * $price); // vv = 24h volume in quote ccy
        $chg24_raw = isset($t['c']) ? floatval($t['c']) : 0; // 24h change as decimal ratio
        $chg24  = $chg24_raw * 100; // convert to percentage

        // Minimum filters: $20K volume, positive 24h change
        if ($volUsd < 20000) continue;
        if ($chg24 <= 0) continue;

        $candidates[] = array(
            'pair'    => $pair,
            'price'   => $price,
            'vol_usd' => $volUsd,
            'chg_24h' => $chg24,
            'high_24h' => isset($t['h']) ? floatval($t['h']) : $price,
            'low_24h'  => isset($t['l']) ? floatval($t['l']) : $price,
        );
    }

    // Sort by 24h change descending, take top 60 for deep analysis
    usort($candidates, '_cw_sort_by_change');
    $candidates = array_slice($candidates, 0, 60);

    // 4. Deep analysis: get candles for each candidate
    $scored = array();
    foreach ($candidates as $c) {
        // Get 1h candles (last 48 hours) and 5m candles (last 4 hours = 48 candles)
        $candles_1h = _cw_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=H1');
        $candles_5m = _cw_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=M5');

        $c1h = isset($candles_1h['result']['data']) ? $candles_1h['result']['data'] : array();
        $c5m = isset($candles_5m['result']['data']) ? $candles_5m['result']['data'] : array();

        if (count($c1h) < 10 || count($c5m) < 10) continue;

        // Score this pair
        $score_details = _cw_score_pair($c, $c1h, $c5m);
        $c['score'] = $score_details['total'];
        $c['factors'] = $score_details['factors'];
        $c['verdict'] = $score_details['verdict'];
        $c['target_pct'] = $score_details['target_pct'];
        $c['risk_pct'] = $score_details['risk_pct'];

        $scored[] = $c;
    }

    // Sort by score descending
    usort($scored, '_cw_sort_by_score');

    // 5a. Correlation filtering: fetch BTC candles, penalize BTC-correlated moves
    $btc_candles = _cw_api('public/get-candlestick?instrument_name=BTC_USDT&timeframe=H1');
    $btc_returns = array();
    if ($btc_candles && isset($btc_candles['result']['data'])) {
        $btc_data = $btc_candles['result']['data'];
        for ($bi = 1; $bi < count($btc_data); $bi++) {
            $prev = floatval($btc_data[$bi - 1]['c']);
            if ($prev > 0) {
                $btc_returns[] = (floatval($btc_data[$bi]['c']) - $prev) / $prev;
            }
        }
    }
    $corr_filtered = 0;
    if (count($btc_returns) >= 10) {
        foreach ($scored as &$sc_item) {
            if ($sc_item['score'] < 70 || $sc_item['pair'] === 'BTC_USDT') continue;
            // We already have candle data in factors — recalculate returns from chg_24h and momentum
            // Simplified correlation: if coin's 24h change is within 30% of BTC's 24h change,
            // and BTC moved > 2%, consider it BTC-correlated and penalize score by 5
            $btc_ticker = isset($tickers['BTC_USDT']) ? $tickers['BTC_USDT'] : null;
            if ($btc_ticker) {
                $btc_chg = isset($btc_ticker['c']) ? floatval($btc_ticker['c']) * 100 : 0;
                $coin_chg = $sc_item['chg_24h'];
                if (abs($btc_chg) > 2 && abs($coin_chg - $btc_chg) < abs($btc_chg) * 0.3) {
                    $sc_item['score'] = $sc_item['score'] - 5;
                    $sc_item['factors']['btc_correlation'] = array(
                        'btc_chg' => round($btc_chg, 2),
                        'coin_chg' => round($coin_chg, 2),
                        'penalty' => -5,
                        'note' => 'Move correlated with BTC'
                    );
                    $corr_filtered++;
                    // Re-evaluate verdict after penalty
                    if ($sc_item['score'] >= 85) $sc_item['verdict'] = 'STRONG_BUY';
                    elseif ($sc_item['score'] >= 75) $sc_item['verdict'] = 'BUY';
                    elseif ($sc_item['score'] >= 70) $sc_item['verdict'] = 'LEAN_BUY';
                    else $sc_item['verdict'] = 'SKIP';
                } else {
                    $sc_item['factors']['btc_correlation'] = array(
                        'btc_chg' => round($btc_chg, 2),
                        'coin_chg' => round($coin_chg, 2),
                        'penalty' => 0,
                        'note' => 'Independent move'
                    );
                }
            }
        }
        unset($sc_item);
        // Re-sort after penalties
        usort($scored, '_cw_sort_by_score');
    }

    // 5b. Save winners (score >= 70) to DB
    $scan_id = date('YmdHis');
    $winners = array();
    $saved = 0;

    foreach ($scored as $s) {
        if ($s['score'] < 70) continue;
        $winners[] = $s;

        $esc_pair    = $conn->real_escape_string($s['pair']);
        $esc_scan    = $conn->real_escape_string($scan_id);
        $esc_factors = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict = $conn->real_escape_string($s['verdict']);

        $sql = "INSERT INTO cw_winners (scan_id, pair, price_at_signal, score, factors_json, verdict, target_pct, risk_pct, vol_usd_24h, chg_24h, created_at)
                VALUES ('$esc_scan', '$esc_pair', " . floatval($s['price']) . ", " . intval($s['score']) . ", '$esc_factors', '$esc_verdict', " . floatval($s['target_pct']) . ", " . floatval($s['risk_pct']) . ", " . floatval($s['vol_usd']) . ", " . floatval($s['chg_24h']) . ", NOW())";
        $conn->query($sql);
        $saved++;
    }

    $elapsed = round(microtime(true) - $start, 2);

    // Discord alert for strong signals
    if (count($winners) > 0) {
        _cw_discord_alert($winners, $scan_id, count($scored), $elapsed);
    }

    // Save ALL analyzed coins to scan_log for full transparency
    foreach ($scored as $s) {
        $esc_pair_log = $conn->real_escape_string($s['pair']);
        $esc_scan_log = $conn->real_escape_string($scan_id);
        $esc_factors_log = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict_log = $conn->real_escape_string($s['verdict']);
        $sql_log = "INSERT INTO cw_scan_log (scan_id, pair, price, score, factors_json, verdict, chg_24h, vol_usd_24h, created_at)
                    VALUES ('$esc_scan_log', '$esc_pair_log', " . floatval($s['price']) . ", " . intval($s['score']) . ", '$esc_factors_log', '$esc_verdict_log', " . floatval($s['chg_24h']) . ", " . floatval($s['vol_usd']) . ", NOW())";
        $conn->query($sql_log);
    }

    // Also include top candidates (even below threshold) for transparency
    $top_candidates = array();
    foreach (array_slice($scored, 0, 10) as $tc) {
        $top_candidates[] = array(
            'pair' => $tc['pair'],
            'score' => $tc['score'],
            'verdict' => $tc['verdict'],
            'chg_24h' => round($tc['chg_24h'], 2),
            'vol_usd' => round($tc['vol_usd'], 0),
            'factors_summary' => _cw_summarize_factors($tc['factors'])
        );
    }

    echo json_encode(array(
        'ok' => true,
        'scan_id' => $scan_id,
        'total_pairs' => count($pairs),
        'candidates_filtered' => count($candidates),
        'deep_analyzed' => count($scored),
        'winners_found' => count($winners),
        'winners_saved' => $saved,
        'corr_penalized' => $corr_filtered,
        'elapsed_sec' => $elapsed,
        'winners' => array_slice($winners, 0, 15),
        'top_candidates' => $top_candidates
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SCORING ENGINE — multi-factor confluence
// ═══════════════════════════════════════════════════════════════════════
function _cw_score_pair($candidate, $candles_1h, $candles_5m) {
    $factors = array();
    $total = 0;

    // Extract close prices from candles
    $closes_1h = array();
    $volumes_1h = array();
    foreach ($candles_1h as $c) {
        $closes_1h[] = floatval($c['c']);
        $volumes_1h[] = floatval($c['v']);
    }

    $closes_5m = array();
    $volumes_5m = array();
    foreach ($candles_5m as $c) {
        $closes_5m[] = floatval($c['c']);
        $volumes_5m[] = floatval($c['v']);
    }

    $n1h = count($closes_1h);
    $n5m = count($closes_5m);

    // ── Factor 1: Multi-Timeframe Momentum (0-20 points) ──
    // Price going up on 1h AND 5m timeframes
    $mom_1h = ($n1h >= 4) ? ($closes_1h[$n1h-1] / $closes_1h[$n1h-4] - 1) * 100 : 0;
    $mom_5m = ($n5m >= 12) ? ($closes_5m[$n5m-1] / $closes_5m[$n5m-12] - 1) * 100 : 0; // last 1h on 5m

    $mtf_score = 0;
    if ($mom_1h > 0 && $mom_5m > 0) $mtf_score += 10;          // both positive
    if ($mom_1h > 1) $mtf_score += 5;                            // strong 4h momentum
    if ($mom_5m > 0.5) $mtf_score += 5;                          // accelerating
    $factors['multi_timeframe_momentum'] = array('score' => $mtf_score, 'max' => 20, 'mom_4h' => round($mom_1h, 2), 'mom_1h' => round($mom_5m, 2));
    $total += $mtf_score;

    // ── Factor 2: Volume Surge (0-20 points) ──
    // Current volume vs average
    if ($n1h >= 10) {
        $avg_vol = array_sum(array_slice($volumes_1h, 0, $n1h - 1)) / ($n1h - 1);
        $cur_vol = $volumes_1h[$n1h - 1];
        $vol_ratio = ($avg_vol > 0) ? $cur_vol / $avg_vol : 0;

        $vol_score = 0;
        if ($vol_ratio > 1.5) $vol_score += 8;
        if ($vol_ratio > 2.0) $vol_score += 6;
        if ($vol_ratio > 3.0) $vol_score += 6;
        $factors['volume_surge'] = array('score' => $vol_score, 'max' => 20, 'ratio' => round($vol_ratio, 2));
    } else {
        $vol_score = 0;
        $factors['volume_surge'] = array('score' => 0, 'max' => 20, 'ratio' => 0);
    }
    $total += $vol_score;

    // ── Factor 3: RSI Sweet Spot (0-15 points) ──
    // RSI 50-70 = strong momentum, not overbought
    $rsi = _cw_calc_rsi($closes_1h, 14);
    $rsi_score = 0;
    if ($rsi >= 50 && $rsi <= 70) $rsi_score = 15;          // sweet spot
    elseif ($rsi >= 40 && $rsi < 50) $rsi_score = 8;        // warming up
    elseif ($rsi > 70 && $rsi <= 80) $rsi_score = 5;        // hot but risky
    // RSI > 80 or < 40 = 0 points
    $factors['rsi_sweet_spot'] = array('score' => $rsi_score, 'max' => 15, 'rsi' => round($rsi, 1));
    $total += $rsi_score;

    // ── Factor 4: Price Above Moving Averages (0-15 points) ──
    $sma20 = _cw_sma($closes_1h, 20);
    $sma50 = _cw_sma($closes_1h, min(50, $n1h));
    $current_price = $closes_1h[$n1h - 1];

    $ma_score = 0;
    if ($current_price > $sma20) $ma_score += 8;
    if ($current_price > $sma50) $ma_score += 4;
    if ($sma20 > $sma50) $ma_score += 3;  // golden cross structure
    $factors['above_moving_averages'] = array('score' => $ma_score, 'max' => 15, 'price' => $current_price, 'sma20' => round($sma20, 6), 'sma50' => round($sma50, 6));
    $total += $ma_score;

    // ── Factor 5: MACD Bullish (0-10 points) ──
    $macd = _cw_calc_macd($closes_1h);
    $macd_score = 0;
    if ($macd['macd'] > $macd['signal']) $macd_score += 5;        // MACD above signal
    if ($macd['histogram'] > 0 && $macd['hist_rising']) $macd_score += 5; // histogram expanding
    $factors['macd_bullish'] = array('score' => $macd_score, 'max' => 10, 'macd' => round($macd['macd'], 6), 'signal' => round($macd['signal'], 6));
    $total += $macd_score;

    // ── Factor 6: Higher Highs & Higher Lows (0-10 points) ──
    $hh_hl = _cw_check_higher_highs($closes_1h);
    $hh_score = 0;
    if ($hh_hl['higher_highs'] >= 2) $hh_score += 5;
    if ($hh_hl['higher_lows'] >= 2) $hh_score += 5;
    $factors['higher_highs_lows'] = array('score' => $hh_score, 'max' => 10, 'hh' => $hh_hl['higher_highs'], 'hl' => $hh_hl['higher_lows']);
    $total += $hh_score;

    // ── Factor 7: Near 24h High (0-10 points) ──
    // Price near its daily high = breakout potential
    $high = $candidate['high_24h'];
    $low = $candidate['low_24h'];
    $range = ($high > $low) ? $high - $low : 0.0001;
    $position_in_range = ($current_price - $low) / $range;  // 0=at low, 1=at high

    $near_high_score = 0;
    if ($position_in_range > 0.85) $near_high_score = 10;        // near breakout
    elseif ($position_in_range > 0.70) $near_high_score = 6;
    elseif ($position_in_range > 0.55) $near_high_score = 3;
    $factors['near_24h_high'] = array('score' => $near_high_score, 'max' => 10, 'position' => round($position_in_range * 100, 1));
    $total += $near_high_score;

    // ── Volatility-adjusted targets using ATR ──
    $atr = _cw_calc_atr($candles_1h);
    $atr_pct = ($current_price > 0) ? ($atr / $current_price) * 100 : 1.5;
    // Clamp ATR% to sensible range (0.5% to 8%)
    $atr_pct = max(0.5, min(8.0, $atr_pct));

    $verdict = 'SKIP';
    $target_pct = 0;
    $risk_pct = 0;

    if ($total >= 85) {
        $verdict = 'STRONG_BUY';
        // Target = 1.5x ATR (volatility-adjusted), min 2%, max 6%
        $target_pct = round(max(2.0, min(6.0, $atr_pct * 1.5)), 1);
        $risk_pct = round(max(1.0, min(3.0, $atr_pct * 0.75)), 1);
    } elseif ($total >= 75) {
        $verdict = 'BUY';
        $target_pct = round(max(1.5, min(4.0, $atr_pct * 1.2)), 1);
        $risk_pct = round(max(1.0, min(2.5, $atr_pct * 0.75)), 1);
    } elseif ($total >= 70) {
        $verdict = 'LEAN_BUY';
        $target_pct = round(max(1.0, min(3.0, $atr_pct * 1.0)), 1);
        $risk_pct = round(max(1.0, min(2.0, $atr_pct * 0.75)), 1);
    }

    $factors['volatility'] = array('atr' => round($atr, 8), 'atr_pct' => round($atr_pct, 2));

    return array(
        'total' => $total,
        'factors' => $factors,
        'verdict' => $verdict,
        'target_pct' => $target_pct,
        'risk_pct' => $risk_pct
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  RESOLVE — continuous resolve: check if target was hit at ANY point
//  in the 4-hour window by fetching 5-min candles and checking high/low
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_resolve($conn) {
    // Find unresolved winners older than 4 hours
    $sql = "SELECT id, pair, price_at_signal, target_pct, risk_pct, score, created_at
            FROM cw_winners
            WHERE outcome IS NULL
            AND created_at < DATE_SUB(NOW(), INTERVAL 4 HOUR)
            ORDER BY created_at ASC
            LIMIT 50";
    $res = $conn->query($sql);
    if (!$res) { _cw_err('Query failed'); }

    $resolved = 0;
    $wins = 0;
    $losses = 0;
    $details = array();

    while ($row = $res->fetch_assoc()) {
        $entry_price = floatval($row['price_at_signal']);
        $target = floatval($row['target_pct']);
        $risk = floatval($row['risk_pct']);
        $target_price = $entry_price * (1 + $target / 100);
        $stop_price = $entry_price * (1 - $risk / 100);

        // Continuous resolve: fetch 5-min candles to check if target/stop was hit
        // during the 4-hour window (48 x 5-min candles = 4 hours)
        $candles_raw = _cw_api('public/get-candlestick?instrument_name=' . $row['pair'] . '&timeframe=M5');
        $candles = (isset($candles_raw['result']['data'])) ? $candles_raw['result']['data'] : array();

        $peak_price = $entry_price;
        $trough_price = $entry_price;
        $hit_target = false;
        $hit_stop = false;
        $hit_target_first = false;

        if (count($candles) >= 10) {
            // Walk through candles chronologically to find what was hit first
            foreach ($candles as $c) {
                $candle_high = floatval($c['h']);
                $candle_low = floatval($c['l']);
                if ($candle_high > $peak_price) $peak_price = $candle_high;
                if ($candle_low < $trough_price) $trough_price = $candle_low;

                // Check stop first within candle (conservative: assume stop hit before target)
                if (!$hit_stop && !$hit_target && $candle_low <= $stop_price) {
                    $hit_stop = true;
                }
                if (!$hit_target && !$hit_stop && $candle_high >= $target_price) {
                    $hit_target = true;
                    $hit_target_first = true;
                }
                // If both could have been hit in same candle, check which was closer
                if (!$hit_stop && !$hit_target) {
                    if ($candle_low <= $stop_price && $candle_high >= $target_price) {
                        // Both in same candle — use open to guess order
                        $candle_open = floatval($c['o']);
                        if (abs($candle_open - $stop_price) < abs($candle_open - $target_price)) {
                            $hit_stop = true;
                        } else {
                            $hit_target = true;
                            $hit_target_first = true;
                        }
                    }
                }
            }
        }

        // Also get current price for final PnL
        $ticker = _cw_api('public/get-tickers?instrument_name=' . $row['pair']);
        $current_price = $entry_price;
        if ($ticker && isset($ticker['result']['data'][0])) {
            $current_price = floatval($ticker['result']['data'][0]['a']);
        }
        $pnl_pct = (($current_price - $entry_price) / $entry_price) * 100;
        $peak_pnl = (($peak_price - $entry_price) / $entry_price) * 100;

        // Determine outcome using continuous data
        $outcome = 'neutral';
        if ($hit_target_first || $hit_target) {
            $outcome = 'win';
            $wins++;
        } elseif ($hit_stop) {
            $outcome = 'loss';
            $losses++;
        } elseif ($pnl_pct >= $target) {
            $outcome = 'win';
            $wins++;
        } elseif ($pnl_pct <= -$risk) {
            $outcome = 'loss';
            $losses++;
        } elseif ($pnl_pct > 0) {
            $outcome = 'partial_win';
            $wins++;
        } else {
            $outcome = 'partial_loss';
            $losses++;
        }

        // Update DB — store peak_pnl for transparency
        $esc_outcome = $conn->real_escape_string($outcome);
        $sql2 = "UPDATE cw_winners SET outcome = '$esc_outcome', price_at_resolve = $current_price, pnl_pct = " . round($pnl_pct, 4) . ", resolved_at = NOW() WHERE id = " . intval($row['id']);
        $conn->query($sql2);
        $resolved++;

        $details[] = array(
            'pair' => $row['pair'],
            'entry' => $entry_price,
            'current' => $current_price,
            'peak' => round($peak_price, 8),
            'peak_pnl' => round($peak_pnl, 2),
            'pnl_pct' => round($pnl_pct, 2),
            'outcome' => $outcome,
            'hit_target' => $hit_target,
            'hit_stop' => $hit_stop,
            'score' => intval($row['score'])
        );

        usleep(100000); // 100ms between API calls
    }

    echo json_encode(array(
        'ok' => true,
        'resolved' => $resolved,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => ($resolved > 0) ? round(($wins / $resolved) * 100, 1) : 0,
        'resolve_method' => 'continuous',
        'details' => $details
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  WINNERS — get latest cached winners
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_winners($conn) {
    $sql = "SELECT * FROM cw_winners WHERE created_at > DATE_SUB(NOW(), INTERVAL 2 HOUR) ORDER BY score DESC LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) { _cw_err('Query failed'); }

    $winners = array();
    while ($row = $res->fetch_assoc()) {
        $row['factors_json'] = json_decode($row['factors_json'], true);
        $winners[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($winners),
        'winners' => $winners,
        'last_scan' => (count($winners) > 0) ? $winners[0]['created_at'] : null
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  HISTORY — past scans + outcomes
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_history($conn) {
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    if ($limit > 200) $limit = 200;

    $sql = "SELECT id, scan_id, pair, price_at_signal, price_at_resolve, score, verdict, target_pct, risk_pct, pnl_pct, outcome, vol_usd_24h, chg_24h, created_at, resolved_at
            FROM cw_winners ORDER BY created_at DESC LIMIT $limit";
    $res = $conn->query($sql);
    if (!$res) { _cw_err('Query failed'); }

    $rows = array();
    while ($row = $res->fetch_assoc()) {
        $rows[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($rows),
        'history' => $rows
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  LEADERBOARD — best patterns by win rate
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_leaderboard($conn) {
    // By score tier
    $sql = "SELECT
                CASE WHEN score >= 85 THEN 'STRONG_BUY (85+)'
                     WHEN score >= 75 THEN 'BUY (75-84)'
                     ELSE 'LEAN_BUY (70-74)' END as tier,
                COUNT(*) as total,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) as avg_pnl,
                ROUND(AVG(score), 1) as avg_score
            FROM cw_winners
            GROUP BY tier
            ORDER BY avg_score DESC";
    $res = $conn->query($sql);

    $tiers = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $row['win_rate'] = ($resolved > 0) ? round(($row['wins'] / $resolved) * 100, 1) : null;
            $row['significance'] = _cw_binomial_significance(intval($row['wins']), $resolved, 0.5);
            $tiers[] = $row;
        }
    }

    // By pair (top performers)
    $sql2 = "SELECT pair,
                COUNT(*) as signals,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) as avg_pnl,
                ROUND(AVG(score), 1) as avg_score
            FROM cw_winners
            WHERE outcome IS NOT NULL
            GROUP BY pair
            HAVING signals >= 3
            ORDER BY wins DESC, avg_pnl DESC
            LIMIT 20";
    $res2 = $conn->query($sql2);

    $by_pair = array();
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $total = intval($row['signals']);
            $row['win_rate'] = ($total > 0) ? round((intval($row['wins']) / $total) * 100, 1) : 0;
            $by_pair[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'by_tier' => $tiers,
        'by_pair' => $by_pair
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  STATS — overall scanner performance
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_stats($conn) {
    $sql = "SELECT
                COUNT(*) as total_signals,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as total_wins,
                SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as total_losses,
                SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) as avg_pnl,
                MAX(pnl_pct) as best_trade,
                MIN(pnl_pct) as worst_trade,
                COUNT(DISTINCT scan_id) as total_scans,
                COUNT(DISTINCT pair) as unique_pairs,
                MIN(created_at) as first_scan,
                MAX(created_at) as last_scan
            FROM cw_winners";
    $res = $conn->query($sql);
    $stats = $res ? $res->fetch_assoc() : array();

    $resolved = intval($stats['total_wins']) + intval($stats['total_losses']);
    $stats['overall_win_rate'] = ($resolved > 0) ? round(($stats['total_wins'] / $resolved) * 100, 1) : null;
    $stats['resolved'] = $resolved;

    // Statistical significance: binomial test against 50% null hypothesis
    // Is our win rate significantly better than coin flip?
    $significance = _cw_binomial_significance(intval($stats['total_wins']), $resolved, 0.5);
    $stats['significance'] = $significance;

    echo json_encode(array(
        'ok' => true,
        'stats' => $stats
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN LOG — full analysis log with all indicators
// ═══════════════════════════════════════════════════════════════════════
function _cw_action_scan_log($conn) {
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
    if ($limit > 500) $limit = 500;

    $scan_filter = '';
    if (isset($_GET['scan_id']) && $_GET['scan_id'] !== '') {
        $scan_filter = " AND scan_id = '" . $conn->real_escape_string($_GET['scan_id']) . "'";
    }

    // If no specific scan requested, get latest scan_id
    if ($scan_filter === '') {
        $latest_res = $conn->query("SELECT scan_id FROM cw_scan_log ORDER BY created_at DESC LIMIT 1");
        if ($latest_res && $latest_row = $latest_res->fetch_assoc()) {
            $scan_filter = " AND scan_id = '" . $conn->real_escape_string($latest_row['scan_id']) . "'";
        }
    }

    $sql = "SELECT * FROM cw_scan_log WHERE 1=1 $scan_filter ORDER BY score DESC LIMIT $limit";
    $res = $conn->query($sql);
    if (!$res) { _cw_err('Query failed'); }

    $rows = array();
    while ($row = $res->fetch_assoc()) {
        $row['factors_json'] = json_decode($row['factors_json'], true);
        $rows[] = $row;
    }

    // Recent scans for navigation
    $scans_res = $conn->query("SELECT scan_id, MIN(created_at) as created_at, COUNT(*) as analyzed,
            SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as winners
        FROM cw_scan_log GROUP BY scan_id ORDER BY created_at DESC LIMIT 20");
    $recent_scans = array();
    if ($scans_res) {
        while ($s = $scans_res->fetch_assoc()) {
            $recent_scans[] = $s;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($rows),
        'log' => $rows,
        'recent_scans' => $recent_scans
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  TECHNICAL INDICATORS
// ═══════════════════════════════════════════════════════════════════════

function _cw_calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return 50;

    $gains = 0;
    $losses = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) $gains += $diff;
        else $losses += abs($diff);
    }

    $avg_gain = $gains / $period;
    $avg_loss = $losses / $period;

    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _cw_sma($data, $period) {
    $n = count($data);
    if ($n < $period) return $data[$n - 1];
    $sum = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $sum += $data[$i];
    }
    return $sum / $period;
}

function _cw_ema($data, $period) {
    $n = count($data);
    if ($n < $period) return $data[$n - 1];

    $k = 2.0 / ($period + 1);
    $ema = $data[0];
    for ($i = 1; $i < $n; $i++) {
        $ema = $data[$i] * $k + $ema * (1 - $k);
    }
    return $ema;
}

function _cw_calc_macd($closes) {
    $n = count($closes);
    if ($n < 26) return array('macd' => 0, 'signal' => 0, 'histogram' => 0, 'hist_rising' => false);

    // EMA 12 and 26
    $ema12 = array();
    $ema26 = array();
    $k12 = 2.0 / 13;
    $k26 = 2.0 / 27;

    $ema12[0] = $closes[0];
    $ema26[0] = $closes[0];
    for ($i = 1; $i < $n; $i++) {
        $ema12[$i] = $closes[$i] * $k12 + $ema12[$i-1] * (1 - $k12);
        $ema26[$i] = $closes[$i] * $k26 + $ema26[$i-1] * (1 - $k26);
    }

    // MACD line
    $macd_line = array();
    for ($i = 0; $i < $n; $i++) {
        $macd_line[$i] = $ema12[$i] - $ema26[$i];
    }

    // Signal line (EMA 9 of MACD)
    $k9 = 2.0 / 10;
    $signal = array();
    $signal[0] = $macd_line[0];
    for ($i = 1; $i < $n; $i++) {
        $signal[$i] = $macd_line[$i] * $k9 + $signal[$i-1] * (1 - $k9);
    }

    $macd_val = $macd_line[$n-1];
    $sig_val = $signal[$n-1];
    $hist = $macd_val - $sig_val;
    $prev_hist = ($n >= 2) ? ($macd_line[$n-2] - $signal[$n-2]) : 0;

    return array(
        'macd' => $macd_val,
        'signal' => $sig_val,
        'histogram' => $hist,
        'hist_rising' => ($hist > $prev_hist)
    );
}

// Average True Range — measures volatility from candle high/low/close
function _cw_calc_atr($candles_1h, $period = 14) {
    $n = count($candles_1h);
    if ($n < 2) return 0;

    $trs = array();
    for ($i = 1; $i < $n; $i++) {
        $high = floatval($candles_1h[$i]['h']);
        $low  = floatval($candles_1h[$i]['l']);
        $prev_close = floatval($candles_1h[$i - 1]['c']);
        $tr = max($high - $low, abs($high - $prev_close), abs($low - $prev_close));
        $trs[] = $tr;
    }

    $cnt = count($trs);
    if ($cnt < $period) {
        return ($cnt > 0) ? array_sum($trs) / $cnt : 0;
    }
    // Simple average of last $period TRs
    $sum = 0;
    for ($i = $cnt - $period; $i < $cnt; $i++) {
        $sum += $trs[$i];
    }
    return $sum / $period;
}

function _cw_check_higher_highs($closes) {
    $n = count($closes);
    $hh = 0;
    $hl = 0;

    // Check last 6 candles in pairs
    for ($i = max(0, $n - 6); $i < $n - 2; $i += 2) {
        if (isset($closes[$i + 2])) {
            $high1 = max($closes[$i], $closes[$i + 1]);
            $high2 = max($closes[$i + 1], $closes[$i + 2]);
            $low1 = min($closes[$i], $closes[$i + 1]);
            $low2 = min($closes[$i + 1], $closes[$i + 2]);

            if ($high2 > $high1) $hh++;
            if ($low2 > $low1) $hl++;
        }
    }

    return array('higher_highs' => $hh, 'higher_lows' => $hl);
}

// ═══════════════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════════════

function _cw_api($endpoint) {
    $url = 'https://api.crypto.com/exchange/v1/' . $endpoint;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'CryptoWinnerScanner/1.0');
    $body = curl_exec($ch);
    $err = curl_error($ch);
    curl_close($ch);

    if ($err || !$body) return null;
    return json_decode($body, true);
}

function _cw_summarize_factors($factors) {
    if (!is_array($factors)) return '';
    $parts = array();
    foreach ($factors as $name => $f) {
        if (isset($f['score']) && isset($f['max'])) {
            $parts[] = substr($name, 0, 8) . ':' . $f['score'] . '/' . $f['max'];
        }
    }
    return implode(' ', $parts);
}

// Binomial significance test: is observed win rate significantly better than null hypothesis (e.g. 50%)?
// Uses normal approximation to binomial (valid when n*p >= 5 and n*(1-p) >= 5)
// Returns: confidence level, p-value approximation, required sample size for significance
function _cw_binomial_significance($wins, $total, $null_p) {
    if ($total < 1) {
        return array(
            'is_significant' => false,
            'confidence' => 'insufficient_data',
            'p_value' => null,
            'z_score' => null,
            'sample_size' => $total,
            'min_sample_needed' => 30,
            'note' => 'Need at least 30 resolved signals for meaningful statistical analysis'
        );
    }

    $observed_p = $wins / $total;
    $se = sqrt($null_p * (1 - $null_p) / $total);

    if ($se == 0) {
        return array(
            'is_significant' => false,
            'confidence' => 'error',
            'p_value' => null,
            'z_score' => null,
            'sample_size' => $total,
            'min_sample_needed' => 30,
            'note' => 'Standard error is zero'
        );
    }

    $z = ($observed_p - $null_p) / $se;

    // Approximate p-value using z-score (one-tailed: is win rate BETTER than null?)
    // PHP 5.2 doesn't have stats functions, so we approximate
    $abs_z = abs($z);
    if ($abs_z >= 3.29) $p_value = 0.0005;
    elseif ($abs_z >= 2.58) $p_value = 0.005;
    elseif ($abs_z >= 2.33) $p_value = 0.01;
    elseif ($abs_z >= 1.96) $p_value = 0.025;
    elseif ($abs_z >= 1.65) $p_value = 0.05;
    elseif ($abs_z >= 1.28) $p_value = 0.10;
    else $p_value = 0.5;

    // For negative z (worse than null), p-value is 1 - above
    if ($z < 0) $p_value = 1 - $p_value;

    $is_sig = ($z > 0 && $p_value < 0.05);
    $confidence = 'not_significant';
    if ($total < 30) $confidence = 'insufficient_data';
    elseif ($is_sig && $p_value < 0.01) $confidence = 'highly_significant';
    elseif ($is_sig) $confidence = 'significant';
    elseif ($z > 0) $confidence = 'trending_positive';
    else $confidence = 'not_significant';

    // Wilson confidence interval for win rate
    $z95 = 1.96;
    $denom = 1 + $z95 * $z95 / $total;
    $center = ($observed_p + $z95 * $z95 / (2 * $total)) / $denom;
    $margin = $z95 * sqrt(($observed_p * (1 - $observed_p) + $z95 * $z95 / (4 * $total)) / $total) / $denom;
    $ci_low = round(max(0, ($center - $margin)) * 100, 1);
    $ci_high = round(min(1, ($center + $margin)) * 100, 1);

    // Minimum sample size needed for current win rate to be significant at p<0.05
    $min_needed = 30;
    if ($observed_p > $null_p && $observed_p < 1) {
        $effect = $observed_p - $null_p;
        $var = $null_p * (1 - $null_p);
        // n = (z_alpha * sqrt(var) / effect)^2
        $min_needed = max(30, (int)ceil(pow(1.65 * sqrt($var) / $effect, 2)));
    }

    return array(
        'is_significant' => $is_sig,
        'confidence' => $confidence,
        'p_value' => round($p_value, 4),
        'z_score' => round($z, 2),
        'observed_win_rate' => round($observed_p * 100, 1),
        'null_hypothesis' => round($null_p * 100, 1),
        'sample_size' => $total,
        'min_sample_needed' => $min_needed,
        'confidence_interval' => array('low' => $ci_low, 'high' => $ci_high),
        'note' => $total < 30
            ? 'Need at least 30 resolved signals. Currently have ' . $total . '.'
            : ($is_sig
                ? 'Win rate is statistically better than coin flip (p<' . ($p_value < 0.01 ? '0.01' : '0.05') . ')'
                : 'Win rate is NOT yet statistically distinguishable from coin flip. More data needed.')
    );
}

function _cw_ends_with($str, $suffix) {
    $len = strlen($suffix);
    return substr($str, -$len) === $suffix;
}

function _cw_sort_by_change($a, $b) {
    if ($b['chg_24h'] == $a['chg_24h']) return 0;
    return ($b['chg_24h'] > $a['chg_24h']) ? 1 : -1;
}

function _cw_sort_by_score($a, $b) {
    if ($b['score'] == $a['score']) return 0;
    return ($b['score'] > $a['score']) ? 1 : -1;
}

// Send Discord webhook alert for new winners
function _cw_discord_alert($winners, $scan_id, $analyzed, $elapsed) {
    // Read webhook URL from .env file
    $env_file = dirname(__FILE__) . '/../../favcreators/public/api/.env';
    $webhook_url = '';
    if (file_exists($env_file)) {
        $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos($line, 'DISCORD_WEBHOOK_URL=') === 0) {
                $webhook_url = trim(substr($line, 20));
                break;
            }
        }
    }
    if (!$webhook_url) return;

    // Build message
    $strong = 0;
    $buy = 0;
    $lean = 0;
    $lines = array();
    foreach (array_slice($winners, 0, 8) as $w) {
        $pair = str_replace('_USDT', '/USDT', $w['pair']);
        $emoji = '';
        if ($w['verdict'] === 'STRONG_BUY') { $emoji = '🟢'; $strong++; }
        elseif ($w['verdict'] === 'BUY') { $emoji = '🔵'; $buy++; }
        else { $emoji = '🟡'; $lean++; }
        $lines[] = $emoji . ' **' . $pair . '** — Score: ' . $w['score'] . ' (' . $w['verdict'] . ') | Target: +' . $w['target_pct'] . '% | 24h: +' . round($w['chg_24h'], 1) . '%';
    }
    if (count($winners) > 8) {
        $lines[] = '... and ' . (count($winners) - 8) . ' more';
    }

    $title = '🔍 Crypto Scanner: ' . count($winners) . ' winner' . (count($winners) > 1 ? 's' : '') . ' found';
    $description = implode("\n", $lines);
    $footer = 'Scan #' . $scan_id . ' | ' . $analyzed . ' analyzed in ' . $elapsed . 's';

    $embed = array(
        'title' => $title,
        'description' => $description,
        'color' => ($strong > 0) ? 3066993 : (($buy > 0) ? 3447003 : 16776960),
        'footer' => array('text' => $footer),
        'url' => 'https://findtorontoevents.ca/findcryptopairs/winners.html'
    );

    $payload = json_encode(array('embeds' => array($embed)));

    $ch = curl_init($webhook_url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_exec($ch);
    curl_close($ch);
}

function _cw_err($msg) {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => $msg));
    exit;
}

function _cw_ensure_schema($conn) {
    $conn->query("CREATE TABLE IF NOT EXISTS cw_winners (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scan_id VARCHAR(20) NOT NULL,
        pair VARCHAR(30) NOT NULL,
        price_at_signal DOUBLE NOT NULL,
        price_at_resolve DOUBLE DEFAULT NULL,
        score INT NOT NULL DEFAULT 0,
        factors_json TEXT,
        verdict VARCHAR(20) NOT NULL DEFAULT 'SKIP',
        target_pct DOUBLE NOT NULL DEFAULT 2.0,
        risk_pct DOUBLE NOT NULL DEFAULT 1.5,
        pnl_pct DOUBLE DEFAULT NULL,
        outcome VARCHAR(20) DEFAULT NULL,
        vol_usd_24h DOUBLE DEFAULT 0,
        chg_24h DOUBLE DEFAULT 0,
        created_at DATETIME NOT NULL,
        resolved_at DATETIME DEFAULT NULL,
        INDEX idx_scan (scan_id),
        INDEX idx_pair (pair),
        INDEX idx_outcome (outcome),
        INDEX idx_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    $conn->query("CREATE TABLE IF NOT EXISTS cw_scan_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scan_id VARCHAR(20) NOT NULL,
        pair VARCHAR(30) NOT NULL,
        price DOUBLE NOT NULL,
        score INT NOT NULL DEFAULT 0,
        factors_json TEXT,
        verdict VARCHAR(20) NOT NULL DEFAULT 'SKIP',
        chg_24h DOUBLE DEFAULT 0,
        vol_usd_24h DOUBLE DEFAULT 0,
        created_at DATETIME NOT NULL,
        INDEX idx_scan_log_scan (scan_id),
        INDEX idx_scan_log_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Purge scan_log entries older than 7 days to keep table size manageable
    $conn->query("DELETE FROM cw_scan_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY)");
}
?>
