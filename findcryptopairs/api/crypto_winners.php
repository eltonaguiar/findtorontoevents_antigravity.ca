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

    // 5. Save winners (score >= 70) to DB
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

    // ── Determine verdict and targets ──
    $verdict = 'SKIP';
    $target_pct = 0;
    $risk_pct = 0;

    if ($total >= 85) {
        $verdict = 'STRONG_BUY';
        $target_pct = 3.0;
        $risk_pct = 1.5;
    } elseif ($total >= 75) {
        $verdict = 'BUY';
        $target_pct = 2.0;
        $risk_pct = 1.5;
    } elseif ($total >= 70) {
        $verdict = 'LEAN_BUY';
        $target_pct = 1.5;
        $risk_pct = 1.5;
    }

    return array(
        'total' => $total,
        'factors' => $factors,
        'verdict' => $verdict,
        'target_pct' => $target_pct,
        'risk_pct' => $risk_pct
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  RESOLVE — check if past winners actually went up
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
        // Get current price from Crypto.com
        $ticker = _cw_api('public/get-tickers?instrument_name=' . $row['pair']);
        if (!$ticker || !isset($ticker['result']['data'][0])) continue;

        $current_price = floatval($ticker['result']['data'][0]['a']);
        $entry_price = floatval($row['price_at_signal']);
        $pnl_pct = (($current_price - $entry_price) / $entry_price) * 100;

        $target = floatval($row['target_pct']);
        $risk = floatval($row['risk_pct']);

        // Determine outcome
        $outcome = 'neutral';
        if ($pnl_pct >= $target) {
            $outcome = 'win';
            $wins++;
        } elseif ($pnl_pct <= -$risk) {
            $outcome = 'loss';
            $losses++;
        } elseif ($pnl_pct > 0) {
            $outcome = 'partial_win';
            $wins++; // count as win for stats
        } else {
            $outcome = 'partial_loss';
            $losses++;
        }

        // Update DB
        $esc_outcome = $conn->real_escape_string($outcome);
        $sql2 = "UPDATE cw_winners SET outcome = '$esc_outcome', price_at_resolve = $current_price, pnl_pct = " . round($pnl_pct, 4) . ", resolved_at = NOW() WHERE id = " . intval($row['id']);
        $conn->query($sql2);
        $resolved++;

        $details[] = array(
            'pair' => $row['pair'],
            'entry' => $entry_price,
            'current' => $current_price,
            'pnl_pct' => round($pnl_pct, 2),
            'outcome' => $outcome,
            'score' => intval($row['score'])
        );

        usleep(100000); // 100ms between ticker calls
    }

    echo json_encode(array(
        'ok' => true,
        'resolved' => $resolved,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => ($resolved > 0) ? round(($wins / $resolved) * 100, 1) : 0,
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

    echo json_encode(array(
        'ok' => true,
        'stats' => $stats
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
}
?>
